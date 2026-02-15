# MinIO 存储集成指南

## 概述

MinIO 是一个高性能的对象存储系统，兼容 Amazon S3 API。本项目已集成 MinIO 作为存储后端，可以替代 Google Cloud Storage 进行本地或私有云部署。

---

## 优势

### 使用 MinIO 的好处

- ✅ **完全自托管** - 无需依赖外部云服务
- ✅ **数据隐私** - 数据完全在您的控制下
- ✅ **成本为零** - 无需支付存储费用
- ✅ **高性能** - 本地/局域网访问速度快
- ✅ **S3 兼容** - 可轻松迁移到 AWS S3
- ✅ **易于部署** - Docker 一键部署

---

## 快速开始

### 1. 使用 Docker Compose 启动

```bash
# 启动所有服务 (MinIO + MongoDB + API)
docker-compose up -d

# 查看日志
docker-compose logs -f minio

# 停止服务
docker-compose down
```

### 2. 访问 MinIO Console

打开浏览器访问: http://localhost:9001

**默认凭据:**
- 用户名: `minioadmin`
- 密码: `minioadmin123`

### 3. 创建 Bucket (自动创建)

启动时自动创建 `cv-uploads` bucket，无需手动创建。

---

## 配置说明

### 环境变量

在 `.env` 文件中添加:

```bash
# 存储类型选择
STORAGE_TYPE=minio  # 或 gcs (Google Cloud Storage)

# MinIO 配置
MINIO_ENDPOINT=localhost:9000  # MinIO 服务器地址
MINIO_ACCESS_KEY=minioadmin    # 访问密钥
MINIO_SECRET_KEY=minioadmin123 # 密钥
MINIO_BUCKET=cv-uploads        # 存储桶名称
MINIO_SECURE=false             # 是否使用 HTTPS

# 生产环境建议使用更强的凭据:
# MINIO_ROOT_USER=your_secure_username
# MINIO_ROOT_PASSWORD=your_secure_password_32_chars
```

### Docker Compose 配置

在 `docker-compose.yml` 中:

```yaml
services:
  minio:
    image: minio/minio:latest
    environment:
      - MINIO_ROOT_USER=${MINIO_ROOT_USER:-minioadmin}
      - MINIO_ROOT_PASSWORD=${MINIO_ROOT_PASSWORD:-minioadmin123}
    ports:
      - "9000:9000"   # API 端口
      - "9001:9001"   # Console 端口
    volumes:
      - minio_data:/data
    command: server /data --console-address ":9001"
```

---

## 使用方法

### Python 代码

#### 1. 使用存储抽象层 (推荐)

```python
from src.minio_storage import get_storage

# 获取存储实例
storage = get_storage()

# 上传 PDF
with open("resume.pdf", "rb") as f:
    pdf_data = f.read()

result = storage.upload_pdf(pdf_data, "john_doe_resume.pdf")
print(f"文件 URL: {result['signed_url']}")

# 获取文件 URL
url = storage.get_file_url(result["object_name"])

# 下载文件
data = storage.download_file(result["object_name"])

# 删除文件
storage.delete_file(result["object_name"])
```

#### 2. 使用上传服务

```python
from src.upload_service import get_cv_upload_service

# 初始化上传服务
uploader = get_cv_upload_service()

# 上传本地文件
result = uploader.upload_cv_file(
    file_path="./resume.pdf",
    candidate_name="John Doe"
)

if result["success"]:
    print(f"上传成功: {result['file_url']}")
```

#### 3. LangGraph 节点

```python
from src.upload_service import upload_cv_node

# 在 LangGraph 工作流中
graph.add_node("upload_cv", upload_cv_node)
```

---

## 切换存储后端

### MinIO ↔ Google Cloud Storage

只需更改环境变量:

```bash
# 使用 MinIO
STORAGE_TYPE=minio

# 使用 Google Cloud Storage
STORAGE_TYPE=gcs
GOOGLE_CLOUD_STORAGE_BUCKET=your-bucket-name
```

代码无需修改，自动切换。

---

## MinIO Console 使用

### 1. 登录

访问 http://localhost:9001，使用默认凭据登录。

### 2. 查看文件

- 左侧菜单: **Object Browser**
- 选择 Bucket: `cv-uploads`
- 查看上传的 CV 文件

### 3. 分享文件

- 右键点击文件
- 选择 **Share**
- 生成预签名 URL (默认24小时有效)

### 4. 管理访问权限

- 选择 Bucket
- 点击 **Manage** 按钮
- 设置访问策略 (公共读取/私有)

---

## 生产部署

### 安全建议

1. **更改默认凭据**
   ```bash
   MINIO_ROOT_USER=your_admin
   MINIO_ROOT_PASSWORD=your_secure_password_32_chars_minimum
   ```

2. **启用 HTTPS**
   ```bash
   MINIO_SECURE=true
   ```

3. **使用反向代理**

   配置 Nginx/Traefik 处理 SSL:
   ```nginx
   server {
       listen 443 ssl;
       server_name minio.yourdomain.com;

       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;

       location / {
           proxy_pass http://localhost:9000;
       }
   }
   ```

4. **数据持久化**
   ```yaml
   volumes:
     - /mnt/minio_data:/data  # 使用独立磁盘
   ```

5. **备份策略**
   ```bash
   # 使用 MinIO 客户端镜像备份
   mc mirror minio/cv-uploads /backup/cv-uploads
   ```

---

## 性能优化

### 1. 并发上传

```python
# 批量上传时使用并发
import asyncio

async def upload_batch(files):
    uploader = get_cv_upload_service()
    tasks = [uploader.upload_cv_file(f) for f in files]
    results = await asyncio.gather(*tasks)
    return results
```

### 2. 缓存策略

```python
# 缓存预签名 URL
from functools import lru_cache

@lru_cache(maxsize=128)
def get_cached_url(object_name):
    return storage.get_file_url(object_name)
```

### 3. CDN 集成

对于生产环境,可以集成 CDN:

```nginx
# Nginx 配置示例
location /cv-uploads/ {
    proxy_pass http://minio:9000;
    proxy_cache my_cache;
    proxy_cache_valid 200 24h;
}
```

---

## 监控和维护

### 健康检查

```bash
# MinIO 健康检查端点
curl http://localhost:9000/minio/health/live
```

### 日志查看

```bash
# Docker 日志
docker-compose logs -f minio

# 或在 MinIO Console 中查看:
# 左侧菜单 → Logs
```

### 存储使用情况

```python
from minio import Minio

client = Minio("localhost:9000", ...)
# 获取 bucket 统计信息
stats = client.get_bucket_policy("cv-uploads")
```

---

## 故障排查

### 问题 1: 无法连接 MinIO

**症状:** `Connection refused`

**解决方案:**
```bash
# 检查 MinIO 是否运行
docker ps | grep minio

# 检查端口是否被占用
netstat -tlnp | grep 9000

# 查看日志
docker logs minio
```

### 问题 2: 上传失败

**症状:** `Access Denied`

**解决方案:**
```bash
# 检查凭据
echo $MINIO_ACCESS_KEY
echo $MINIO_SECRET_KEY

# 确认 bucket 存在
mc ls minio/cv-uploads
```

### 问题 3: 预签名 URL 无法访问

**症状:** `403 Forbidden`

**解决方案:**
```bash
# 检查 bucket 策略
mc policy get minio/cv-uploads

# 设置为公共读取
mc anonymous set download minio/cv-uploads
```

### 问题 4: Docker 容器无法访问 MinIO

**症状:** API 容器报错 `Connection refused`

**解决方案:**
```bash
# 使用 Docker 网络内的地址
MINIO_ENDPOINT=minio:9000  # 而不是 localhost:9000
```

---

## 高级配置

### 1. 多站点部署

```yaml
# 主 MinIO 节点
minio1:
  image: minio/minio
  command: server http://minio{1...4}/data{1...2}

# 扩展节点
minio2:
  # ... 类似配置
```

### 2. 生命周期管理

```python
# 自动删除旧文件 (7天后)
from datetime import timedelta

config = {
    "Rules": [
        {
            "ID": "ExpireOldCVs",
            "Status": "Enabled",
            "Filter": {"Prefix": "cvs/"},
            "Expiration": {"Days": 7}
        }
    ]
}
client.set_bucket_lifecycle("cv-uploads", config)
```

### 3. 事件通知

```python
# 配置 Webhook 通知
from minio import NotificationConfig

config = NotificationConfig(
    queue_config=[
        {
            "QueueArn": "arn:minio:sqs::your-webhook:webhook",
            "Events": ["s3:ObjectCreated:*"],
            "Filter": {
                "Prefix": "cvs/",
                "Suffix": ".pdf"
            }
        }
    ]
)
client.set_bucket_notification("cv-uploads", config)
```

---

## 命令行工具 (mc)

MinIO Client (`mc`) 是强大的命令行工具。

### 安装

```bash
# Linux/macOS
wget https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc
sudo mv mc /usr/local/bin/

# 或使用 Docker
docker run minio/mc --help
```

### 配置别名

```bash
# 添加 MinIO 服务器
mc alias set local http://localhost:9000 minioadmin minioadmin123

# 列出文件
mc ls local/cv-uploads

# 上传文件
mc cp resume.pdf local/cv-uploads/

# 下载文件
mc cp local/cv-uploads/resume.pdf ./resume.pdf

# 同步目录
mc mirror ./local_folder/ local/cv-uploads/
```

---

## 迁移指南

### 从 Google Cloud Storage 迁移到 MinIO

```python
from src.minio_storage import MinIOStorage
from google.cloud import storage as gcs

# 初始化 MinIO
minio = MinIOStorage(...)

# 迁移文件
gcs_client = storage.Client()
bucket = gcs_client.bucket("your-bucket")

for blob in bucket.list_blobs():
    # 下载从 GCS
    data = blob.download_as_bytes()

    # 上传到 MinIO
    minio.upload_file(data, blob.name)
    print(f"Migrated: {blob.name}")
```

### 从 MinIO 迁移到 AWS S3

```bash
# 使用 MinIO 客户端
mc mirror minio/cv-uploads s3/your-bucket/

# 或使用 AWS CLI
aws s3 sync --endpoint-url http://localhost:9000 \
  s3://cv-uploads/ s3://your-bucket/
```

---

## API 参考

### MinIOStorage 类

```python
class MinIOStorage:
    def __init__(self, endpoint, access_key, secret_key, bucket_name, secure)

    def upload_file(self, file_data: bytes, object_name: str, content_type: str) -> str
    def upload_pdf(self, pdf_bytes: bytes, filename: str, folder: str) -> dict
    def get_file_url(self, object_name: str, expires: timedelta) -> str
    def download_file(self, object_name: str) -> bytes
    def delete_file(self, object_name: str) -> bool
    def list_files(self, prefix: str, recursive: bool) -> list
```

### StorageBackend 抽象层

```python
class StorageBackend:
    def __init__(self, storage_type: str = "minio")
    def upload_pdf(self, pdf_bytes: bytes, filename: str, folder: str) -> dict
    def get_file_url(self, object_name: str, expires: timedelta) -> str
    def download_file(self, object_name: str) -> bytes
    def delete_file(self, object_name: str) -> bool
```

---

## 相关链接

- **MinIO 官网:** https://min.io
- **文档:** https://min.io/docs/minio/linux/index.html
- **Python SDK:** https://min.io/docs/minio/linux/developers/python/minio-py.html
- **Docker Hub:** https://hub.docker.com/r/minio/minio

---

## 总结

MinIO 提供了一个强大、自托管的对象存储解决方案,可以完全替代 Google Cloud Storage:

- **开发环境** - 本地 Docker 部署,零成本
- **生产环境** - 私有云或混合云部署
- **迁移灵活** - S3 兼容,可轻松迁移到任何云提供商

**开始使用:**

```bash
# 1. 启动服务
docker-compose up -d

# 2. 访问控制台
open http://localhost:9001

# 3. 开始上传
python -c "from src.upload_service import get_cv_upload_service; ..."
```

---

**文档版本:** 1.0.0
**最后更新:** 2025-02-16
