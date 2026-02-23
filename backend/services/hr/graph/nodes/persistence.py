# ============================================================================
# Persistence node: save candidate to MongoDB (Graph1)
# ============================================================================

import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Keys to exclude from the document saved to MongoDB (internal/injected)
_NON_PERSISTED_KEYS = frozenset({"_candidates_collection", "messages"})


async def save_candidate_to_mongodb(state: Dict[str, Any]) -> Dict[str, Any]:
    """Save candidate document to db.candidates. Requires state['_candidates_collection']."""
    try:
        collection = state.get("_candidates_collection")
        if collection is None:
            state.setdefault("errors", []).append("No _candidates_collection in state; cannot save to MongoDB")
            return state

        doc = {
            "candidate_name": state.get("candidate_name", ""),
            "candidate_email": state.get("candidate_email", ""),
            "cv_file_url": state.get("cv_file_url", ""),
            "cv_object_name": state.get("cv_object_name", ""),
            "cv_link": state.get("cv_link", ""),
            "extracted_cv_data": state.get("extracted_cv_data", {}),
            "summary": state.get("summary", ""),
            "timestamp": state.get("timestamp") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "errors": state.get("errors", []),
        }
        if state.get("user_id"):
            doc["user_id"] = state["user_id"]
        if state.get("user_email"):
            doc["user_email"] = state["user_email"]

        result = await collection.insert_one(doc)
        state["candidate_id"] = str(result.inserted_id)
        logger.info(f"Candidate saved to MongoDB: {state['candidate_id']}")

    except Exception as e:
        error_msg = f"Save candidate to MongoDB error: {str(e)}"
        logger.error(error_msg)
        state.setdefault("errors", []).append(error_msg)

    return state
