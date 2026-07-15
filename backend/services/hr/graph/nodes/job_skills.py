# ============================================================================
# Job skills node: extract required skills from job description
# ============================================================================

import logging
from typing import Dict, Any

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from backend.schemas.hr import JobSkills
from backend.services.llm_provider import create_job_skills_llm

logger = logging.getLogger(__name__)


async def extract_job_skills(job_description: str) -> JobSkills:
    """Run the LLM once to extract required skills from a job description.

    Reusable outside the graph so callers (e.g. batch evaluation) can extract
    a job's skills a single time and reuse them across many candidates instead
    of re-running the LLM for every (job, candidate) pair.
    """
    if not job_description:
        return JobSkills(tech_skills=[], soft_skills=[])

    llm = create_job_skills_llm()
    parser = JsonOutputParser(pydantic_object=JobSkills)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "Extract technical and soft skills required for this job position. "
                  "Return as JSON with 'tech_skills' and 'soft_skills' arrays."),
        ("human", "Job Description:\n{job_description}")
    ])

    chain = prompt | llm | parser
    result = await chain.ainvoke({"job_description": job_description})
    logger.info(f"Job skills extracted: {len(result.get('tech_skills', []))} technical skills")
    return JobSkills(**result)


async def extract_job_skills_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Extract required skills from job description.

    Skips the LLM call when skills were pre-computed (e.g. cached on the job
    document or extracted once by a batch caller) and injected into the state.
    """
    # Reuse pre-computed/cached skills to avoid redundant LLM calls.
    if state.get("job_skills"):
        return state

    try:
        job_description = state.get("job_description", "")
        if not job_description:
            state["errors"].append("No job description provided")
            return state

        state["job_skills"] = await extract_job_skills(job_description)

    except Exception as e:
        error_msg = f"Job skills extraction error: {str(e)}"
        logger.error(error_msg)
        state["errors"].append(error_msg)
        state["job_skills"] = JobSkills(tech_skills=[], soft_skills=[])

    return state
