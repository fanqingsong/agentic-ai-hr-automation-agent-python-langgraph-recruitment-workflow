# ============================================================================
# CV nodes: extract CV data, generate candidate summary
# ============================================================================

import logging
from typing import Dict, Any

from backend.services.hr.data_extraction import extract_cv_data

logger = logging.getLogger(__name__)


async def extract_cv_data_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Extract structured data from CV"""
    try:
        cv_file_path = state.get("cv_file_path")
        if not cv_file_path:
            state["errors"].append("No CV file path for extraction")
            return state

        extracted_data = await extract_cv_data(cv_file_path)
        state["extracted_cv_data"] = extracted_data
        logger.info(f"CV data extracted for {state.get('candidate_name')}")

    except Exception as e:
        error_msg = f"CV extraction error: {str(e)}"
        logger.error(error_msg)
        state["errors"].append(error_msg)

    return state


async def generate_summary_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate candidate summary from extracted CV data"""
    try:
        extracted_data = state.get("extracted_cv_data", {})
        if not extracted_data:
            state["summary"] = "No CV data available"
            return state

        personal_info = extracted_data.get("personal_info", {})
        experience = extracted_data.get("experience", [])
        skills = extracted_data.get("skills", {})

        summary_parts = [
            f"{personal_info.get('name', 'Unknown')} is a candidate with ",
            f"{len(experience)} years of experience. "
        ]

        if experience:
            latest_role = experience[0].get("title", "Unknown")
            latest_company = experience[0].get("company", "Unknown")
            summary_parts.append(f"Most recently worked as {latest_role} at {latest_company}. ")

        tech_skills = skills.get("technical_skills", [])
        if tech_skills:
            summary_parts.append(f"Key technical skills include: {', '.join(tech_skills[:5])}. ")

        state["summary"] = "".join(summary_parts)
        logger.info(f"Summary generated for {state.get('candidate_name')}")

    except Exception as e:
        error_msg = f"Summary generation error: {str(e)}"
        logger.error(error_msg)
        state["errors"].append(error_msg)
        state["summary"] = f"Summary for {state.get('candidate_name', 'candidate')}"

    return state
