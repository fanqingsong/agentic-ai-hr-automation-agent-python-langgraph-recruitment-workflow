# ============================================================================
# AI-Powered HR Automation with LangGraph
# Complete CV Review to Candidate Evaluation System

# Get the full source code of complete project:
# https://aicampusmagazines.gumroad.com/l/gscdiq

## Developed By AICampus - Gateway for future AI research & learning
## Developer: Furqan Khan
## Email: furqan.cloud.dev@gmail.com
# ============================================================================

import os
import json
from datetime import datetime
import sys
from io import BytesIO
from pathlib import Path

from src.config import Config

from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langgraph.graph import StateGraph, END
from langgraph.types import RetryPolicy

from src.google_cloud import GCSUploader
from src.llm_provider import create_summary_llm, create_evaluation_llm, create_job_skills_llm
from src.notifications import *
from src.data_extraction import extract_cv_data
from src.fastapi_api import HRJobPost, JobApplication
from src.skills_match import map_job_to_candidate_skills

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_google_services_available() -> bool:
    """
    Check if Google Services are properly configured

    Returns:
        True if Google Services are available, False otherwise
    """
    try:
        # Check if credentials file exists
        if not os.path.exists(Config.GOOGLE_CREDENTIALS_PATH):
            logger.warning(f"⚠️ Google credentials not found at: {Config.GOOGLE_CREDENTIALS_PATH}")
            return False

        if not Config.GOOGLE_SHEET_ID:
            logger.warning("⚠️ GOOGLE_SHEET_ID not configured")
            return False

        # Try to initialize Google Services
        try:
            GoogleServices()
            logger.info("✅ Google Services are available and configured")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Google Services initialization failed: {str(e)}")
            return False

    except Exception as e:
        logger.warning(f"⚠️ Error checking Google Services: {str(e)}")
        return False


# ============================================================================
# LANGGRAPH NODES
# ============================================================================


# ============================================================================
# LANGGRAPH WORKFLOW
# ============================================================================

def create_hr_workflow():
    """Create the LangGraph workflow"""

    # Initialize the graph
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("upload_cv", upload_cv_node)
    graph.add_node("extract_cv_data_node", extract_cv_data_node)
    graph.add_node("extract_job_skills_node", extract_job_skills_node)
    graph.add_node("generate_summary", generate_summary_node)

    # Define the policy: 1 initial attempt + 1 retry = 2 max_attempts
    retry_once = RetryPolicy(max_attempts=2)
    graph.add_node("evaluate", evaluate_candidate_node, retry_policy=retry_once)
    graph.add_node("skills_match_node", skills_match_node)

    graph.add_node("save_results", save_to_sheets_node)

    graph.add_node("score_decision", score_decision_node)
    graph.add_node("fan_out_notifications", fan_out_notifications)

    graph.add_node("send_email", send_hr_email_node)
    graph.add_node("send_slack", send_slack_notification_node)
    graph.add_node("send_whatsapp", send_whatsapp)

    # Define the flow
    graph.set_entry_point("upload_cv")
    graph.add_edge("upload_cv", "extract_cv_data_node")
    graph.add_edge("extract_cv_data_node", "extract_job_skills_node")
    graph.add_edge("extract_job_skills_node", "generate_summary")
    graph.add_edge("generate_summary", "evaluate")
    graph.add_edge("evaluate", "skills_match_node")
    graph.add_edge("skills_match_node", "score_decision")


    # Conditional routing
    graph.add_conditional_edges(
        "score_decision",
        route_on_score,
        {
            "notify_hr": "fan_out_notifications",
            "end": END
        }
    )

    # Parallel execution
    graph.add_edge("fan_out_notifications", "send_email")
    graph.add_edge("fan_out_notifications", "send_slack")
    graph.add_edge("fan_out_notifications", "send_whatsapp")

    # All end independently
    graph.add_edge("send_email", END)
    graph.add_edge("send_slack", END)
    graph.add_edge("send_whatsapp", END)

    return graph.compile()



async def process_job_application_submission(candidate_data: dict, hr_job_post: HRJobPost):
    """
    Process a Job Form submission

    Args:
        candidate_data: Dictionary containing form response data
        Expected keys: 'name', 'email', and either 'cv_file_url' or 'cv_file_path'

        hr_job_post (HRJobPost): Validated Pydantic model for the job.

    """
    return await process_candidate(candidate_data, hr_job_post)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

async def process_candidate(candidate_data: dict, hr_job_post: HRJobPost):
    """
    Main function to process a candidate application

    Args:
       candidate_data: Dictionary containing form response data
       hr_job_post: Validated Pydantic model for the job.

    Returns:
        Final state with all processing results

    Note: cv_file_path must be provided
    """

    if not candidate_data['cv_file_path']:
        raise ValueError("cv_file_path must be provided")


    # Initialize state
    initial_state = AgentState(
        candidate_name=candidate_data['name'],
        candidate_email=candidate_data['email'],
        cv_file_url="",
        cv_file_path=candidate_data.get('cv_file_path') or "",
        extracted_cv_data={},
        cv_link="",
        summary="",
        job_title=hr_job_post.job_application.title,
        job_description=hr_job_post.job_application.description,
        job_description_html=hr_job_post.job_application.description_html,
        hr_email=hr_job_post.hr.email,
        evaluation={},
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        errors=[],
        messages=[]
    )

    # Create and run workflow
    app = create_hr_workflow()
    final_state = await app.ainvoke(initial_state)
    return final_state



# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Process a single candidate
    # Use absolute path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)  # Go up one level from src/
    # Process with local file (recommended for testing)
    local_cv_path = os.path.join(project_root, "resumes", "john_doe_resume.pdf")

    ##---------------------------------------------
    job_description = """We are looking for a Senior AI Automation Engineer to design, develop, and maintain Python-based automation agents that streamline workflows, orchestrate system interactions, and reduce operational overhead.
    This role focuses on building intelligent, event-driven automation, not QA or test automation."""

    job_application = JobApplication(title="Senior AI Engineer", description=job_description, description_html="")
    hr_job_post = HRJobPost(id=1,ulid=1,job_application=job_application)

    candidate_data: dict = {"candidate_name": "john doe", "candidate_email": "john.doe@domain.com", "cv_file_path": local_cv_path }

    result = process_candidate(
       candidate_data=candidate_data,
       hr_job_post=hr_job_post
    )

    print(f"Result: {result}")
    print("Processing Complete!")
    print(f"Score: {result['evaluation'].get('score')}/10")
    print(f"Summary: {result['summary']}")
    print(f"Errors: {result['errors']}")

    # Generate outputs
    # Batch convert all messages in the list to dictionaries ( AIMessage, HumanMessage etc.)
    # result['messages'] = messages_to_dict(result['messages'])

    messages_content = [msg.content for msg in result['messages']]
    result['messages'] = messages_content

    # 1. Get the project root directory (two levels up from src/hr_automation.py)
    project_root = Path(__file__).resolve().parent.parent
    # 2. Define the target directory and file path
    output_dir = project_root / "outputs"
    output_file = output_dir / "agent_final_state.json"
    # 3. Create the 'outputs' folder if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # 4. Save the file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4, ensure_ascii=False)