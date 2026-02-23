# ============================================================================
# Evaluation nodes: evaluate candidate, skills match, score decision, routing
# ============================================================================

import logging
import re
from typing import Dict, Any

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from backend.schemas.hr import CandidateEvaluation
from backend.services.llm_provider import create_evaluation_llm

logger = logging.getLogger(__name__)


def _parse_evaluation_fallback(raw: str) -> Dict[str, Any]:
    """Extract score and reasoning from markdown-style LLM output when JSON parsing fails."""
    out = {"score": 50, "reasoning": raw[:2000], "strengths": [], "gaps": [], "decision": "unknown"}
    # Score: try "**Score: 60/100**" or "Score: 60" or "60/100"
    score_m = re.search(r"\*\*Score:\s*(\d+)\s*/\s*100\*\*", raw, re.IGNORECASE)
    if not score_m:
        score_m = re.search(r"Score:\s*(\d+)\s*(?:/\s*100)?", raw, re.IGNORECASE)
    if not score_m:
        score_m = re.search(r"(\d+)\s*/\s*100", raw)
    if score_m:
        try:
            out["score"] = max(1, min(100, int(score_m.group(1))))
        except (ValueError, IndexError):
            pass
    reasoning_m = re.search(r"\*\*Reasoning:\*\*\s*(.+?)(?=\n\s*\*\*|\Z)", raw, re.DOTALL | re.IGNORECASE)
    if reasoning_m:
        out["reasoning"] = reasoning_m.group(1).strip()[:2000]
    return out


async def evaluate_candidate_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate candidate against job requirements"""
    try:
        summary = state.get("summary", "")
        job_description = state.get("job_description", "")

        if not summary or not job_description:
            state["evaluation"] = {"score": 50, "reasoning": "Insufficient data for evaluation"}
            state["evaluation_score"] = 50
            return state

        llm = create_evaluation_llm()
        parser = JsonOutputParser(pydantic_object=CandidateEvaluation)
        format_instructions = parser.get_format_instructions()

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert HR evaluator. Evaluate the candidate based on their summary "
                      "and the job requirements. You must respond with ONLY a single valid JSON object, "
                      "no markdown, no extra text. Include: score (1-100), reasoning, strengths (list of strings), "
                      "gaps (list of strings), and decision (string, e.g. hire/not hire).\n\n{format_instructions}"),
            ("human", "Candidate Summary:\n{summary}\n\nJob Description:\n{job_description}")
        ])

        chain = prompt.partial(format_instructions=format_instructions) | llm | parser
        result = await chain.ainvoke({"summary": summary, "job_description": job_description})

        state["evaluation"] = result
        state["evaluation_score"] = result.get("score", 50)
        logger.info(f"Candidate evaluated with score: {state['evaluation_score']}/100")

    except Exception as e:
        error_msg = f"Evaluation error: {str(e)}"
        logger.error(error_msg)
        # If LLM returned markdown instead of JSON, try to extract score/reasoning from error message (contains raw output)
        if "Invalid json" in str(e) or "OUTPUT_PARSING" in str(e):
            try:
                raw_text = str(e)
                if "Invalid json output:" in raw_text:
                    raw_text = raw_text.split("Invalid json output:", 1)[-1].strip()
                result = _parse_evaluation_fallback(raw_text)
                state["evaluation"] = result
                state["evaluation_score"] = result.get("score", 50)
                logger.info(f"Parsed evaluation from markdown fallback, score: {state['evaluation_score']}/100")
            except Exception as fallback_err:
                logger.warning(f"Fallback parse failed: {fallback_err}")
                state["evaluation"] = {"score": 50, "reasoning": f"Evaluation failed: {str(e)}"}
                state["evaluation_score"] = 50
        else:
            state["errors"].append(error_msg)
            state["evaluation"] = {"score": 50, "reasoning": f"Evaluation failed: {str(e)}"}
            state["evaluation_score"] = 50

    return state


async def skills_match_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Match candidate skills with job requirements"""
    try:
        extracted_data = state.get("extracted_cv_data", {})
        job_skills = state.get("job_skills")

        if not extracted_data or not job_skills:
            state["skills_match"] = {"strong": [], "partial": [], "missing": []}
            return state

        candidate_skills = extracted_data.get("skills", {})
        tech_skills = candidate_skills.get("technical_skills", [])
        tools = candidate_skills.get("tools", [])

        all_candidate_skills = set(tech_skills + tools)
        required_skills = set(job_skills.tech_skills)

        strong_matches = [s for s in required_skills if s.lower() in [cs.lower() for cs in all_candidate_skills]]
        missing_skills = list(required_skills - set(strong_matches))

        state["skills_match"] = {
            "strong": strong_matches,
            "partial": [],
            "missing": missing_skills
        }
        logger.info(f"Skills matched: {len(strong_matches)} strong, {len(missing_skills)} missing")

    except Exception as e:
        error_msg = f"Skills matching error: {str(e)}"
        logger.error(error_msg)
        state["errors"].append(error_msg)
        state["skills_match"] = {"strong": [], "partial": [], "missing": []}

    return state


async def score_decision_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Make decision based on evaluation score"""
    try:
        score = state.get("evaluation_score", 0)

        if score >= 70:
            state["tag"] = "high_potential"
            state["notify_hr"] = True
            state["notification_message"] = f"High potential candidate with score {score}/100"
        elif score >= 50:
            state["tag"] = "moderate"
            state["notify_hr"] = True
            state["notification_message"] = f"Moderate candidate with score {score}/100"
        else:
            state["tag"] = "low_potential"
            state["notify_hr"] = False
            state["notification_message"] = f"Low score candidate ({score}/100)"

        logger.info(f"Decision made: {state['tag']}, notify_hr: {state['notify_hr']}")

    except Exception as e:
        error_msg = f"Score decision error: {str(e)}"
        logger.error(error_msg)
        state["errors"].append(error_msg)
        state["tag"] = "error"
        state["notify_hr"] = False

    return state


def route_on_score(state: Dict[str, Any]) -> str:
    """Route based on evaluation score"""
    if state.get("notify_hr"):
        return "notify_hr"
    return "end"
