# MinIO 存储集成完成总结

**实施日期:** 2025-02-16
**版本:** 1.1.0 → 1.2.0
**状态:** ✅ 完成并测试

---

## 实施概述

成功集成 MinIO 对象存储服务，替代 Google Cloud Storage，实现完全自托管的存储解决方案。

---

## 新增文件

| 文件 | 行数 | 描述 |
|------|------|------|
| [backend/minio_storage.py](backend/minio_storage.py) | ~350 | MinIO 存储服务类 |
| [backend/upload_service.py](backend/upload_service.py) | ~230 | 统一上传服务接口 |
| [docker-compose.yml](docker-compose.yml) | 更新 | 添加 MinIO + MongoDB 服务 |
| [docker-compose.minio.yml](docker-compose.minio.yml) | ~100 | 独立的 MinIO 配置 |
| [docs/MINIO_SETUP.md](docs/MINIO_SETUP.md) | ~650 | 完整的 MinIO 设置指南 |

**总代码量:** ~580 行
**总文档量:** ~650 行

---

## 核心功能

### 1. MinIO 存储服务类

**文件:** [backend/minio_storage.py](backend/minio_storage.py)

**主要类和功能:**

#### MinIOStorage 类
```python
class MinIOStorage:
    def upload_file(file_data, object_name, content_type) -> str
    def upload_pdf(pdf_bytes, filename, folder) -> dict
    def get_file_url(object_name, expires) -> str
    def download_file(object_name) -> bytes
    def delete_file(object_name) -> bool
    def list_files(prefix, recursive) -> list
```

**特性:**
- ✅ S3 兼容 API
- ✅ 预签名 URL (默认24小时有效)
- ✅ 自动 bucket 创建
- ✅ 公共读取策略设置
- ✅ 完整的错误处理

#### StorageBackend 抽象层
```python
class StorageBackend:
    def __init__(storage_type)  # "minio" 或 "gcs"
    def upload_pdf(...)
    def get_file_url(...)
    def download_file(...)
    def delete_file(...)
```

**特性:**
- ✅ 统一接口支持多种存储后端
- ✅ 自动切换 MinIO/GCS
- ✅ 无需修改应用代码

### 2. 上传服务

**文件:** [backend/upload_service.py](backend/upload_service.py)

#### CVUploadService 类
```python
class CVUploadService:
    def upload_cv_file(file_path, candidate_name) -> Dict[str, Any]
    def upload_cv_bytes(file_data, filename) -> Dict[str, Any]
    def get_cv_url(object_name) -> str
    def delete_cv(object_name) -> bool
```

#### LangGraph 节点函数
```python
async def upload_cv_node(state: Dict[str, Any]) -> Dict[str, Any]
```

---

## 配置更新

### 环境变量 ([env.example](env.example))

```bash
# 存储类型选择
STORAGE_TYPE=minio  # 或 gcs

# MinIO 配置
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_BUCKET=cv-uploads
MINIO_SECURE=false

# Google Cloud Storage (如果使用 GCS)
GOOGLE_CLOUD_STORAGE_BUCKET=your-bucket-name
```

### 配置类更新 ([backend/config.py](backend/config.py))

新增配置属性:
```python
class Config:
    # 存储类型
    STORAGE_TYPE: str = os.getenv("STORAGE_TYPE", "minio")

    # MinIO 配置
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
    MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "cv-uploads")
    MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"
```

---

## Docker Compose 更新

### 完整栈配置 ([docker-compose.yml](docker-compose.yml))

**服务列表:**
1. **MinIO** - 对象存储 (端口 9000, 9001)
2. **MongoDB** - 数据库 (端口 27017)
3. **HR Automation API** - 主应用 (端口 8000)

**特性:**
- ✅ 一键启动所有服务
- ✅ 自动创建 bucket
- ✅ 数据持久化卷
- ✅ 健康检查
- ✅ 网络隔离

**启动命令:**
```bash
docker-compose up -d
```

### 访问端点

| 服务 | URL | 凭据 |
|------|-----|------|
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin123 |
| MinIO API | http://localhost:9000 | - |
| MongoDB | mongodb://localhost:27017 | - |
| HR API | http://localhost:8000 | - |

---

## 依赖更新

### pyproject.toml

新增依赖:
```toml
dependencies = [
    # ... 现有依赖 ...
    "minio>=7.0.0",  # MinIO object storage client
]
```

**安装:**
```bash
uv sync
```

---

## 使用方法

### 1. 基本上传

```python
from src.minio_storage import get_storage

# 获取存储实例
storage = get_storage()

# 上传 PDF
with open("resume.pdf", "rb") as f:
    pdf_data = f.read()

result = storage.upload_pdf(pdf_data, "john_doe_resume.pdf")
print(f"文件 URL: {result['signed_url']}")
```

### 2. 使用上传服务

```python
from src.upload_service import get_cv_upload_service

uploader = get_cv_upload_service()

# 上传本地文件
result = uploader.upload_cv_file(
    file_path="./resume.pdf",
    candidate_name="John Doe"
)

if result["success"]:
    print(f"上传成功: {result['file_url']}")
```

### 3. LangGraph 工作流集成

```python
from src.upload_service import upload_cv_node
from langgraph.graph import StateGraph

graph = StateGraph(AgentState)
graph.add_node("upload_cv", upload_cv_node)
```

---

## 切换存储后端

### MinIO ↔ Google Cloud Storage

只需更改环境变量，无需修改代码:

```bash
# 使用 MinIO
STORAGE_TYPE=minio
MINIO_ENDPOINT=localhost:9000

# 使用 Google Cloud Storage
STORAGE_TYPE=gcs
GOOGLE_CLOUD_STORAGE_BUCKET=your-bucket
```

---

## MinIO Console 使用

### 1. 登录

访问: http://localhost:9001

**默认凭据:**
- 用户名: `minioadmin`
- 密码: `minioadmin123`

### 2. 管理文件

- **Object Browser** - 浏览和下载文件
- **Access Keys** - 管理访问密钥
- **Buckets** - 管理存储桶
- **Monitoring** - 查看服务器状态

### 3. 分享文件

1. 右键点击文件
2. 选择 "Share"
3. 生成预签名 URL

---

## 测试指南

### 1. 测试 MinIO 连接

```python
from src.minio_storage import MinIOStorage

storage = MinIOStorage(
    endpoint="localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin123",
    bucket_name="cv-uploads",
    secure=False
)

# 测试上传
with open("test.pdf", "rb") as f:
    result = storage.upload_pdf(f.read(), "test.pdf")

print(f"✅ 上传成功: {result}")
```

### 2. 测试存储切换

```bash
# 测试 MinIO
STORAGE_TYPE=minio python -c "from src.minio_storage import get_storage; print(get_storage())"

# 测试 GCS
STORAGE_TYPE=gcs python -c "from src.minio_storage import get_storage; print(get_storage())"
```

### 3. 测试 API 端点

```bash
# 启动服务
docker-compose up -d

# 测试健康检查
curl http://localhost:8000/health

# 测试文件上传
curl -X POST http://localhost:8000/api/candidate-application-submit \
  -F "job_id=job_123" \
  -F "name=Test User" \
  -F "email=test@example.com" \
  -F "cv_file=@resume.pdf"
```

---

## 生产部署

### 安全建议

1. **更改默认凭据**
   ```bash
   MINIO_ROOT_USER=your_secure_username
   MINIO_ROOT_PASSWORD=your_secure_password_32_chars_minimum
   ```

2. **启用 HTTPS**
   ```bash
   MINIO_SECURE=true
   ```

3. **使用反向代理** (Nginx/Traefik)

4. **数据持久化**
   ```yaml
   volumes:
     - /mnt/minio_data:/data
   ```

5. **备份策略**
   ```bash
   mc mirror minio/cv-uploads /backup/cv-uploads
   ```

### 性能优化

1. **并发上传**
   ```python
   import asyncio
   tasks = [upload_file(f) for f in files]
   await asyncio.gather(*tasks)
   ```

2. **CDN 集成**
   - 使用 Nginx 缓存
   - 或集成 CloudFlare

3. **扩展性**
   - MinIO 支持多节点集群
   - 可水平扩展

---

## 对比：MinIO vs Google Cloud Storage

| 特性 | MinIO | Google Cloud Storage |
|------|-------|---------------------|
| **成本** | 免费 (自托管) | $0.026/GB/月 |
| **隐私** | 完全控制 | Google 基础设施 |
| **性能** | 本地网络快 | 取决于网络 |
| **部署** | Docker 简单 | 需要 GCP 项目 |
| **S3 兼容** | ✅ 是 | ❌ 否 |
| **迁移成本** | 低 | 中 |
| **维护** | 需要 | Google 负责 |
| **可扩展性** | 集群模式 | 自动 |

---

## 故障排查

### 常见问题

#### 1. 连接失败
```bash
# 检查 MinIO 是否运行
docker ps | grep minio

# 查看日志
docker logs minio
```

#### 2. 权限错误
```bash
# 检查凭据
echo $MINIO_ACCESS_KEY
echo $MINIO_SECRET_KEY
```

#### 3. Bucket 不存在
```python
# 手动创建
from minio import Minio
client = Minio("localhost:9000", ...)
client.make_bucket("cv-uploads")
```

#### 4. 预签名 URL 403
```bash
# 设置公共读取策略
mc anonymous set download local/cv-uploads
```

---

## API 参考

### MinIOStorage 类

```python
class MinIOStorage:
    """MinIO 存储服务"""

    def __init__(
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket_name: str,
        secure: bool = False
    )

    def upload_file(
        file_data: bytes,
        object_name: str,
        content_type: str = "application/pdf"
    ) -> str

    def upload_pdf(
        pdf_bytes: bytes,
        filename: str,
        folder: str = "cvs"
    ) -> dict

    def get_file_url(
        object_name: str,
        expires: timedelta = timedelta(hours=24)
    ) -> str

    def download_file(object_name: str) -> bytes

    def delete_file(object_name: str) -> bool

    def list_files(
        prefix: str = "",
        recursive: bool = False
    ) -> list
```

---

## 文档资源

- **完整指南:** [docs/MINIO_SETUP.md](docs/MINIO_SETUP.md)
- **MinIO 官网:** https://min.io
- **Python SDK:** https://min.io/docs/minio/linux/developers/python/minio-py.html
- **Docker Hub:** https://hub.docker.com/r/minio/minio

---

## 迁移检查清单

### 从 GCS 迁移到 MinIO

- [ ] 安装 MinIO (`docker-compose up -d`)
- [ ] 更新 `.env` 文件 (`STORAGE_TYPE=minio`)
- [ ] 测试连接 (`python test_minio.py`)
- [ ] 迁移现有文件 (使用迁移脚本)
- [ ] 更新生产配置
- [ ] 切换 DNS/负载均衡器
- [ ] 监控日志和错误

---

## 后续改进

### 可能的增强

1. **多站点部署** - MinIO 集群模式
2. **生命周期管理** - 自动删除旧文件
3. **事件通知** - Webhook 集成
4. **监控集成** - Prometheus + Grafana
5. **备份自动化** - 定时备份脚本

---

## 总结

✅ **成功集成 MinIO 存储服务**

**关键成果:**
- 完全自托管的存储解决方案
- S3 兼容，易于迁移
- 无需依赖 Google Cloud
- 零额外成本
- 统一的抽象层接口

**快速开始:**
```bash
# 1. 启动服务
docker-compose up -d

# 2. 访问控制台
open http://localhost:9001

# 3. 开始使用
python -c "from src.upload_service import get_cv_upload_service; ..."
```

---

**实施完成日期:** 2025-02-16
**版本:** 1.2.0
**状态:** ✅ 生产就绪
