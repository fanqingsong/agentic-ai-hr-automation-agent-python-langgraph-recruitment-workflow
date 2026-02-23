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


async def extract_job_skills_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Extract required skills from job description"""
    try:
        job_description = state.get("job_description", "")
        if not job_description:
            state["errors"].append("No job description provided")
            return state

        llm = create_job_skills_llm()
        parser = JsonOutputParser(pydantic_object=JobSkills)

        prompt = ChatPromptTemplate.from_messages([
            ("system", "Extract technical and soft skills required for this job position. "
                      "Return as JSON with 'tech_skills' and 'soft_skills' arrays."),
            ("human", "Job Description:\n{job_description}")
        ])

        chain = prompt | llm | parser
        result = await chain.ainvoke({"job_description": job_description})

        state["job_skills"] = JobSkills(**result)
        logger.info(f"Job skills extracted: {len(result.get('tech_skills', []))} technical skills")

    except Exception as e:
        error_msg = f"Job skills extraction error: {str(e)}"
        logger.error(error_msg)
        state["errors"].append(error_msg)
        state["job_skills"] = JobSkills(tech_skills=[], soft_skills=[])

    return state
