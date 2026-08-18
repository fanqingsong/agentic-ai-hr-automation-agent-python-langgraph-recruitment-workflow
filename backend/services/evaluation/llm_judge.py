# ============================================================================
# Agent evaluation: LLM-as-judge evaluators (optional, extra LLM cost).
#
# Disabled by default (LANGFUSE_LLM_JUDGE_ENABLED=false / use_llm_judge API
# flag). Two judges:
# - judge_candidate_evaluation: quality of Graph2's candidate-vs-job evaluation
# - judge_agent_response: helpfulness/groundedness of the HR explorer agent
# ============================================================================

import json
import logging
import re
from typing import Any, Dict, Optional, Tuple

from langchain_core.prompts import ChatPromptTemplate

from backend.config import Config
from backend.services.evaluation.evaluators import EvaluatorResult
from backend.services.llm_provider import get_cached_llm

logger = logging.getLogger(__name__)


def _judge_llm():
    """Low-temperature LLM for judging (cached like every other role)."""
    return get_cached_llm(
        provider=Config.LLM_PROVIDER,
        temperature=0.0,
        max_tokens=600,
    )


async def _run_judge(prompt: ChatPromptTemplate, variables: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Invoke the judge LLM and parse its strict-JSON answer."""
    chain = prompt | _judge_llm()
    raw = await chain.ainvoke(variables)
    text = raw.content if hasattr(raw, "content") else str(raw)
    if isinstance(text, list):  # multimodal content blocks
        text = "".join(str(b) for b in text)

    # Tolerate markdown fences around the JSON object.
    text = text.strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        text = m.group(0)
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    logger.warning("LLM judge returned non-JSON output: %.200s", text)
    return None


def _to_result(parsed: Optional[Dict[str, Any]], name: str, fallback_comment: str) -> EvaluatorResult:
    if not parsed:
        return EvaluatorResult(name, 0.0, fallback_comment)
    try:
        score = float(parsed.get("score", 0))
    except (TypeError, ValueError):
        score = 0.0
    score = max(0.0, min(100.0, score)) / 100.0
    comment = str(parsed.get("reasoning", ""))[:500]
    return EvaluatorResult(name, round(score, 3), comment)


# ----------------------------------------------------------------------------
# Graph 2: candidate evaluation quality judge
# ----------------------------------------------------------------------------

_CANDIDATE_JUDGE_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a strict reviewer of automated HR candidate evaluations. "
     "Given the candidate summary, the job description, and the evaluation the system produced, "
     "judge the QUALITY of the evaluation itself: is the score justified by the evidence, is the "
     "reasoning grounded in the summary/job description, and are strengths/gaps accurate? "
     "Respond with ONLY a single valid JSON object, no markdown: "
     '{"score": <0-100 integer>, "reasoning": "<one or two sentences>"}'),
    ("human",
     "Candidate Summary:\n{summary}\n\nJob Description:\n{job_description}\n\n"
     "System Evaluation:\n{evaluation}"),
])


async def judge_candidate_evaluation(
    summary: str,
    job_description: str,
    evaluation: Dict[str, Any],
) -> EvaluatorResult:
    """LLM-as-judge score for the quality of a candidate evaluation output."""
    try:
        parsed = await _run_judge(
            _CANDIDATE_JUDGE_PROMPT,
            {
                "summary": (summary or "")[:4000],
                "job_description": (job_description or "")[:4000],
                "evaluation": json.dumps(evaluation, ensure_ascii=False, default=str)[:4000],
            },
        )
        return _to_result(parsed, "llm_judge_quality", "judge output unparseable")
    except Exception as e:
        logger.warning("candidate-evaluation judge failed: %s", e)
        return EvaluatorResult("llm_judge_quality", 0.0, f"judge error: {e}")


# ----------------------------------------------------------------------------
# HR explorer agent: response quality judge
# ----------------------------------------------------------------------------

_AGENT_JUDGE_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a strict reviewer of an HR assistant agent. Given the user's question and the "
     "agent's final answer, judge helpfulness and groundedness: does it answer the question, is "
     "it specific (names, numbers, concrete candidates/jobs/skills), and free of hallucinated "
     "structure? Respond with ONLY a single valid JSON object, no markdown: "
     '{"score": <0-100 integer>, "reasoning": "<one or two sentences>"}'),
    ("human",
     "User question:\n{question}\n\nAgent answer:\n{answer}"),
])


async def judge_agent_response(question: str, answer: str) -> EvaluatorResult:
    """LLM-as-judge score for the HR explorer agent's final response."""
    try:
        parsed = await _run_judge(
            _AGENT_JUDGE_PROMPT,
            {"question": (question or "")[:4000], "answer": (answer or "")[:6000]},
        )
        return _to_result(parsed, "agent_response_quality", "judge output unparseable")
    except Exception as e:
        logger.warning("agent-response judge failed: %s", e)
        return EvaluatorResult("agent_response_quality", 0.0, f"judge error: {e}")


# ----------------------------------------------------------------------------
# Trace payload helpers: pull question/answer or summary/jd out of a trace
# ----------------------------------------------------------------------------

def _messages_from_payload(payload: Any) -> list:
    """Extract message-like dicts from a traced LangGraph state payload."""
    if isinstance(payload, dict):
        msgs = payload.get("messages")
        if isinstance(msgs, list):
            return msgs
    return []


def _message_text(message: Any) -> str:
    if isinstance(message, dict):
        content = message.get("content", "")
    else:
        content = getattr(message, "content", "")
    if isinstance(content, list):
        return " ".join(
            str(b.get("text", "")) if isinstance(b, dict) else str(b) for b in content
        )
    return str(content or "")


def extract_agent_qa(trace_input: Any, trace_output: Any) -> Tuple[str, str]:
    """Best-effort (question, answer) extraction from an hr_explorer trace."""
    input_msgs = _messages_from_payload(trace_input)
    output_msgs = _messages_from_payload(trace_output)

    question = next(
        (_message_text(m) for m in reversed(input_msgs)
         if (m.get("type") if isinstance(m, dict) else getattr(m, "type", "")) == "human"),
        "",
    )
    answer = next(
        (_message_text(m) for m in reversed(output_msgs)
         if (m.get("type") if isinstance(m, dict) else getattr(m, "type", "")) == "ai"),
        "",
    )
    return question, answer
