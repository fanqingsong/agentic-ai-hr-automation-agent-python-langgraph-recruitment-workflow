# ============================================================================
# MINIO STORAGE SERVICE
# ============================================================================

"""
MinIO object storage service
本地/私有云对象存储解决方案
"""

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

from src.config import Config

logger = logging.getLogger(__name__)


class MinIOStorage:
    """
    MinIO 存储服务类

    提供文件上传、下载、预签名 URL 生成等功能
    """

    def __init__(
        self,
        endpoint: str = None,
        access_key: str = None,
        secret_key: str = None,
        bucket_name: str = None,
        secure: bool = False
    ):
        """
        初始化 MinIO 客户端

        Args:
            endpoint: MinIO 服务器地址 (host:port)
            access_key: 访问密钥
            secret_key: 密钥
            bucket_name: 存储桶名称
            secure: 是否使用 HTTPS
        """
        if not MINIO_AVAILABLE:
            raise ImportError(
                "MinIO 库未安装。请运行: pip install minio"
            )

        # 从参数或环境变量获取配置
        self.endpoint = endpoint or Config.MINIO_ENDPOINT
        self.access_key = access_key or Config.MINIO_ACCESS_KEY
        self.secret_key = secret_key or Config.MINIO_SECRET_KEY
        self.bucket_name = bucket_name or Config.MINIO_BUCKET
        self.secure = secure or Config.MINIO_SECURE

        # 初始化 MinIO 客户端
        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )

        # 初始化存储桶
        self._ensure_bucket_exists()

        logger.info(
            f"MinIO 客户端初始化成功: "
            f"endpoint={self.endpoint}, bucket={self.bucket_name}"
        )

    def _ensure_bucket_exists(self):
        """确保存储桶存在，如果不存在则创建"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"存储桶 '{self.bucket_name}' 创建成功")

                # 设置为公共读取 (可选)
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
                import json
                self.client.set_bucket_policy(self.bucket_name, json.dumps(policy))
                logger.info(f"存储桶 '{self.bucket_name}' 设置为公共读取")

        except S3Error as e:
            logger.error(f"存储桶操作失败: {str(e)}")
            raise

    def upload_file(
        self,
        file_data: bytes,
        object_name: str,
        content_type: str = "application/pdf"
    ) -> str:
        """
        上传文件到 MinIO

        Args:
            file_data: 文件字节数据
            object_name: 对象名称 (文件路径)
            content_type: MIME 类型

        Returns:
            对象名称
        """
        try:
            # 创建字节流
            data_stream = io.BytesIO(file_data)
            data_stream.seek(0)

            # 上传文件
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=data_stream,
                length=len(file_data),
                content_type=content_type
            )

            logger.info(f"文件上传成功: {object_name}")
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
        """
        上传 PDF 文件

        Args:
            pdf_bytes: PDF 文件字节数据
            filename: 文件名
            folder: 文件夹路径

        Returns:
            包含预签名 URL 的字典
        """
        import uuid

        # 生成唯一对象名称
        ext = filename.rsplit('.', 1)[-1] if '.' in filename else 'pdf'
        unique_name = f"{folder}/{uuid.uuid4().hex}.{ext}"

        # 上传文件
        self.upload_file(
            file_data=pdf_bytes,
            object_name=unique_name,
            content_type="application/pdf"
        )

        # 生成预签名 URL (24小时有效)
        from datetime import timedelta
        expires = timedelta(hours=24)

        try:
            signed_url = self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=unique_name,
                expires=expires
            )

            # 如果是本地 MinIO,确保 URL 正确
            if not self.secure:
                signed_url = signed_url.replace("http://", "http://")

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
        """
        生成文件访问的预签名 URL

        Args:
            object_name: 对象名称
            expires: 过期时间

        Returns:
            预签名 URL
        """
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
        """
        下载文件

        Args:
            object_name: 对象名称

        Returns:
            文件字节数据
        """
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
        """
        删除文件

        Args:
            object_name: 对象名称

        Returns:
            是否成功
        """
        try:
            self.client.remove_object(
                bucket_name=self.bucket_name,
                object_name=object_name
            )
            logger.info(f"文件删除成功: {object_name}")
            return True
        except S3Error as e:
            logger.error(f"文件删除失败: {str(e)}")
            return False

    def list_files(self, prefix: str = "", recursive: bool = False) -> list:
        """
        列出存储桶中的文件

        Args:
            prefix: 前缀过滤
            recursive: 是否递归

        Returns:
            对象列表
        """
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
        """
        获取文件的公共 URL (如果存储桶设置为公共读取)

        Args:
            object_name: 对象名称

        Returns:
            公共 URL
        """
        protocol = "https" if self.secure else "http"
        return f"{protocol}://{self.endpoint}/{self.bucket_name}/{object_name}"


# ============================================================================
# 存储服务 (统一接口)
# ============================================================================

class StorageService:
    """
    存储服务统一接口
    目前仅支持 MinIO
    """

    def __init__(self):
        """初始化存储服务"""
        self.backend = MinIOStorage()
        logger.info("存储服务初始化成功 (MinIO)")

    def upload_pdf(self, pdf_bytes: bytes, filename: str, folder: str = "cvs") -> dict:
        """上传 PDF 文件"""
        return self.backend.upload_pdf(pdf_bytes, filename, folder)

    def get_file_url(self, object_name: str, expires: timedelta = timedelta(hours=24)) -> str:
        """获取文件 URL"""
        return self.backend.get_file_url(object_name, expires)

    def download_file(self, object_name: str) -> bytes:
        """下载文件"""
        return self.backend.download_file(object_name)

    def delete_file(self, object_name: str) -> bool:
        """删除文件"""
        return self.backend.delete_file(object_name)


# ============================================================================
# 便捷函数
# ============================================================================

def get_storage() -> StorageService:
    """
    获取存储服务实例

    Returns:
        存储服务实例
    """
    return StorageService()


# ============================================================================
# 使用示例
# ============================================================================

if __name__ == "__main__":
    import asyncio

    async def example_minio_usage():
        """MinIO 使用示例"""

        # 1. 直接使用 MinIOStorage
        storage = MinIOStorage(
            endpoint="localhost:9000",
            access_key="minioadmin",
            secret_key="minioadmin123",
            bucket_name="cv-uploads",
            secure=False
        )

        # 2. 上传 PDF 文件
        with open("test.pdf", "rb") as f:
            pdf_data = f.read()

        result = storage.upload_pdf(pdf_data, "resume.pdf")
        print(f"上传成功: {result}")

        # 3. 获取文件 URL
        url = storage.get_file_url(result["object_name"])
        print(f"文件 URL: {url}")

        # 4. 列出文件
        files = storage.list_files(prefix="cvs/")
        print(f"文件列表: {files}")

    # asyncio.run(example_minio_usage())
