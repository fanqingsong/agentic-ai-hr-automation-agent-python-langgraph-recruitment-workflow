# ============================================================================
# CV UPLOAD SERVICE
# ============================================================================

"""
CV 文件上传服务
支持 MinIO 和 Google Cloud Storage
"""

import logging
from pathlib import Path
from typing import Dict, Any

from src.config import Config
from src.minio_storage import get_storage

logger = logging.getLogger(__name__)


class CVUploadService:
    """
    CV 上传服务

    统一接口处理文件上传，支持多种存储后端
    """

    def __init__(self):
        """初始化上传服务"""
        # 根据配置选择存储后端
        self.storage = get_storage()
        logger.info(f"CV Upload Service initialized with {Config.STORAGE_TYPE} storage")

    def upload_cv_file(
        self,
        file_path: str,
        candidate_name: str = None
    ) -> Dict[str, Any]:
        """
        上传 CV 文件

        Args:
            file_path: 本地文件路径
            candidate_name: 候选人姓名 (用于文件命名)

        Returns:
            包含文件 URL 的字典
        """
        try:
            # 读取文件
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            with open(path, "rb") as f:
                file_data = f.read()

            # 生成文件名
            if candidate_name:
                filename = f"{candidate_name.replace(' ', '_')}_resume.pdf"
            else:
                filename = path.name

            # 上传到存储后端
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
            return {
                "success": False,
                "error": str(e)
            }

    def upload_cv_bytes(
        self,
        file_data: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """
        上传 CV 字节数据

        Args:
            file_data: 文件字节数据
            filename: 文件名

        Returns:
            包含文件 URL 的字典
        """
        try:
            # 上传到存储后端
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
            return {
                "success": False,
                "error": str(e)
            }

    def get_cv_url(self, object_name: str) -> str:
        """
        获取 CV 文件访问 URL

        Args:
            object_name: 对象名称

        Returns:
            访问 URL
        """
        try:
            return self.storage.get_file_url(object_name)
        except Exception as e:
            logger.error(f"Failed to get CV URL: {str(e)}")
            raise

    def delete_cv(self, object_name: str) -> bool:
        """
        删除 CV 文件

        Args:
            object_name: 对象名称

        Returns:
            是否成功
        """
        try:
            return self.storage.delete_file(object_name)
        except Exception as e:
            logger.error(f"Failed to delete CV: {str(e)}")
            return False


# ============================================================================
# LangGraph 节点函数
# ============================================================================

async def upload_cv_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph 上传 CV 节点

    从本地文件路径上传 CV 到存储后端

    Args:
        state: Agent 状态

    Returns:
        更新后的状态
    """
    try:
        file_path = state.get("cv_file_path")
        candidate_name = state.get("candidate_name", "candidate")

        if not file_path:
            raise ValueError("cv_file_path is required")

        # 初始化上传服务
        uploader = CVUploadService()

        # 上传文件
        result = uploader.upload_cv_file(file_path, candidate_name)

        if result.get("success"):
            state["cv_file_url"] = result.get("file_url")
            state["cv_object_name"] = result.get("object_name")
            logger.info(f"CV uploaded successfully: {result.get('object_name')}")
        else:
            error_msg = result.get("error", "Upload failed")
            state["errors"].append(f"CV upload failed: {error_msg}")
            logger.error(f"CV upload failed: {error_msg}")

        return state

    except Exception as e:
        error_msg = f"Upload CV node error: {str(e)}"
        logger.error(error_msg)
        state["errors"].append(error_msg)
        return state


# ============================================================================
# 便捷函数
# ============================================================================

def get_cv_upload_service() -> CVUploadService:
    """
    获取 CV 上传服务实例

    Returns:
        CVUploadService 实例
    """
    return CVUploadService()


# ============================================================================
# 使用示例
# ============================================================================

if __name__ == "__main__":
    import asyncio

    async def example_upload():
        """上传服务示例"""

        # 1. 初始化服务
        uploader = get_cv_upload_service()

        # 2. 上传文件
        result = uploader.upload_cv_file(
            file_path="./test_resume.pdf",
            candidate_name="John Doe"
        )

        if result["success"]:
            print(f"上传成功!")
            print(f"文件 URL: {result['file_url']}")
            print(f"对象名称: {result['object_name']}")
        else:
            print(f"上传失败: {result['error']}")

    # asyncio.run(example_upload())
