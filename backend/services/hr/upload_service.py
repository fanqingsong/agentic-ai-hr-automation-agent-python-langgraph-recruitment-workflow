# ============================================================================
# CV UPLOAD SERVICE
# ============================================================================

import logging
from pathlib import Path
from typing import Dict, Any

from backend.config import Config
from backend.services.storage import get_storage

logger = logging.getLogger(__name__)


class CVUploadService:
    """CV 上传服务 - 统一接口处理文件上传"""

    def __init__(self):
        self.storage = get_storage()
        logger.info(f"CV Upload Service initialized with {Config.STORAGE_TYPE} storage")

    def upload_cv_file(
        self,
        file_path: str,
        candidate_name: str = None
    ) -> Dict[str, Any]:
        """上传 CV 文件"""
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            with open(path, "rb") as f:
                file_data = f.read()
            if candidate_name:
                filename = f"{candidate_name.replace(' ', '_')}_resume.pdf"
            else:
                filename = path.name
            result = self.storage.upload_pdf(
                pdf_bytes=file_data,
                filename=filename,
                folder="cvs"
            )
            logger.info(f"CV uploaded successfully: {result.get('object_name')}")
            return {
                "success": True,
                "file_url": result.get("signed_url"),
                "object_name": result.get("object_name"),
                "expires_in_hours": result.get("expires_in_hours", 24)
            }
        except Exception as e:
            logger.error(f"CV upload failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def upload_cv_bytes(self, file_data: bytes, filename: str) -> Dict[str, Any]:
        """上传 CV 字节数据"""
        try:
            result = self.storage.upload_pdf(
                pdf_bytes=file_data,
                filename=filename,
                folder="cvs"
            )
            return {
                "success": True,
                "file_url": result.get("signed_url"),
                "object_name": result.get("object_name"),
                "expires_in_hours": result.get("expires_in_hours", 24)
            }
        except Exception as e:
            logger.error(f"CV upload failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_cv_url(self, object_name: str) -> str:
        return self.storage.get_file_url(object_name)

    def delete_cv(self, object_name: str) -> bool:
        try:
            return self.storage.delete_file(object_name)
        except Exception as e:
            logger.error(f"Failed to delete CV: {str(e)}")
            return False


def get_cv_upload_service() -> CVUploadService:
    return CVUploadService()
