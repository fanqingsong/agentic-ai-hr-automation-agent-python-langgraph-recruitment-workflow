# ============================================================================
# MINIO STORAGE SERVICE
# ============================================================================

import io
import logging
from typing import Optional
from datetime import timedelta

try:
    from minio import Minio
    from minio.error import S3Error
    MINIO_AVAILABLE = True
except ImportError:
    MINIO_AVAILABLE = False

from backend.config import Config

logger = logging.getLogger(__name__)


class MinIOStorage:
    """MinIO 存储服务类"""

    def __init__(
        self,
        endpoint: str = None,
        access_key: str = None,
        secret_key: str = None,
        bucket_name: str = None,
        secure: bool = False
    ):
        if not MINIO_AVAILABLE:
            raise ImportError("MinIO 库未安装。请运行: pip install minio")
        self.endpoint = endpoint or Config.MINIO_ENDPOINT
        self.access_key = access_key or Config.MINIO_ACCESS_KEY
        self.secret_key = secret_key or Config.MINIO_SECRET_KEY
        self.bucket_name = bucket_name or Config.MINIO_BUCKET
        self.secure = secure or Config.MINIO_SECURE
        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        import json
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": "*"},
                            "Action": ["s3:GetObject"],
                            "Resource": [f"arn:aws:s3:::{self.bucket_name}/*"]
                        }
                    ]
                }
                self.client.set_bucket_policy(self.bucket_name, json.dumps(policy))
        except S3Error as e:
            logger.error(f"存储桶操作失败: {str(e)}")
            raise

    def upload_file(
        self,
        file_data: bytes,
        object_name: str,
        content_type: str = "application/pdf"
    ) -> str:
        try:
            data_stream = io.BytesIO(file_data)
            data_stream.seek(0)
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=data_stream,
                length=len(file_data),
                content_type=content_type
            )
            return object_name
        except S3Error as e:
            logger.error(f"文件上传失败: {str(e)}")
            raise

    def upload_pdf(
        self,
        pdf_bytes: bytes,
        filename: str,
        folder: str = "cvs"
    ) -> dict:
        import uuid
        ext = filename.rsplit('.', 1)[-1] if '.' in filename else 'pdf'
        unique_name = f"{folder}/{uuid.uuid4().hex}.{ext}"
        self.upload_file(
            file_data=pdf_bytes,
            object_name=unique_name,
            content_type="application/pdf"
        )
        expires = timedelta(hours=24)
        try:
            signed_url = self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=unique_name,
                expires=expires
            )
            return {
                "object_name": unique_name,
                "signed_url": signed_url,
                "expires_in_hours": 24
            }
        except S3Error as e:
            logger.error(f"生成预签名 URL 失败: {str(e)}")
            raise

    def get_file_url(
        self,
        object_name: str,
        expires: timedelta = timedelta(hours=24)
    ) -> str:
        try:
            return self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                expires=expires
            )
        except S3Error as e:
            logger.error(f"生成预签名 URL 失败: {str(e)}")
            raise

    def download_file(self, object_name: str) -> bytes:
        try:
            response = self.client.get_object(
                bucket_name=self.bucket_name,
                object_name=object_name
            )
            return response.read()
        except S3Error as e:
            logger.error(f"文件下载失败: {str(e)}")
            raise

    def delete_file(self, object_name: str) -> bool:
        try:
            self.client.remove_object(
                bucket_name=self.bucket_name,
                object_name=object_name
            )
            return True
        except S3Error as e:
            logger.error(f"文件删除失败: {str(e)}")
            return False

    def list_files(self, prefix: str = "", recursive: bool = False) -> list:
        try:
            objects = self.client.list_objects(
                bucket_name=self.bucket_name,
                prefix=prefix,
                recursive=recursive
            )
            return [obj.object_name for obj in objects]
        except S3Error as e:
            logger.error(f"列出文件失败: {str(e)}")
            return []

    def get_public_url(self, object_name: str) -> str:
        protocol = "https" if self.secure else "http"
        return f"{protocol}://{self.endpoint}/{self.bucket_name}/{object_name}"


class StorageService:
    """存储服务统一接口"""

    def __init__(self):
        self.backend = MinIOStorage()

    def upload_pdf(self, pdf_bytes: bytes, filename: str, folder: str = "cvs") -> dict:
        return self.backend.upload_pdf(pdf_bytes, filename, folder)

    def get_file_url(self, object_name: str, expires: timedelta = timedelta(hours=24)) -> str:
        return self.backend.get_file_url(object_name, expires)

    def download_file(self, object_name: str) -> bytes:
        return self.backend.download_file(object_name)

    def delete_file(self, object_name: str) -> bool:
        return self.backend.delete_file(object_name)


def get_storage() -> StorageService:
    return StorageService()
