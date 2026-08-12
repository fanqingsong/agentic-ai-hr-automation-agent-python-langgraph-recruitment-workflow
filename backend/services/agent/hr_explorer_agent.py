# ============================================================================
# HR explorer Deep Agent factory (read-only knowledge exploration).
# ============================================================================

import logging
from functools import lru_cache

from copilotkit import CopilotKitMiddleware
from deepagents import create_deep_agent
from deepagents.middleware import FilesystemMiddleware
from langgraph.checkpoint.memory import MemorySaver

from backend.config import Config
from backend.services.agent import prompts, tools
from backend.services.llm_provider import LLMFactory

logger = logging.getLogger(__name__)


def _build_model():
    """Reuse the project's multi-provider LLM factory for the explorer agent."""
    return LLMFactory.create_llm(
        provider=Config.LLM_PROVIDER,
        temperature=0.2,
        max_tokens=2500,
    )


@lru_cache(maxsize=1)
def get_hr_explorer_agent():
    """Compile (once) the read-only HR explorer Deep Agent graph."""
    model = _build_model()
    checkpointer = MemorySaver()

    middleware = [
        CopilotKitMiddleware(),
        FilesystemMiddleware(tools=["read_file", "ls", "glob", "grep"]),
    ]

    subagents = [
        {
            "name": "candidate_researcher",
            "description": "Deep research on candidates via MongoDB, Qdrant, and Neo4j.",
            "system_prompt": prompts.CANDIDATE_RESEARCHER_PROMPT,
            "tools": tools.CANDIDATE_TOOLS,
        },
        {
            "name": "job_researcher",
            "description": "Deep research on job posts via MongoDB, Qdrant, and Neo4j.",
            "system_prompt": prompts.JOB_RESEARCHER_PROMPT,
            "tools": tools.JOB_TOOLS,
        },
        {
            "name": "matching_analyst",
            "description": "Analyze candidate-job fit using evaluations and skill graphs.",
            "system_prompt": prompts.MATCHING_ANALYST_PROMPT,
            "tools": tools.MATCHING_TOOLS,
        },
    ]

    agent = create_deep_agent(
        model=model,
        tools=tools.ALL_TOOLS,
        system_prompt=prompts.HR_EXPLORER_PROMPT,
        middleware=middleware,
        subagents=subagents,
        checkpointer=checkpointer,
        name="hr_explorer",
    )
    logger.info("HR explorer Deep Agent compiled (provider=%s)", Config.LLM_PROVIDER)
    return agent
