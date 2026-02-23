# ============================================================================
# Upload node: CV upload to storage (MinIO/local)
# ============================================================================

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


async def upload_cv_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Upload CV to storage (MinIO/local)"""
    from backend.services.hr.upload_service import CVUploadService

    try:
        cv_file_path = state.get("cv_file_path")
        if not cv_file_path:
            state["errors"].append("No CV file path provided")
            return state

        uploader = CVUploadService()
        result = uploader.upload_cv_file(cv_file_path, state.get("candidate_name", "candidate"))

        if result.get("success"):
            state["cv_file_url"] = result.get("file_url", "")
            state["cv_link"] = result.get("file_url", "")
            state["cv_object_name"] = result.get("object_name", "")
            logger.info(f"CV uploaded successfully: {result.get('object_name')}")
        else:
            state["errors"].append(f"CV upload failed: {result.get('error', 'Unknown error')}")

    except Exception as e:
        error_msg = f"Upload CV node error: {str(e)}"
        logger.error(error_msg)
        state["errors"].append(error_msg)

    return state
