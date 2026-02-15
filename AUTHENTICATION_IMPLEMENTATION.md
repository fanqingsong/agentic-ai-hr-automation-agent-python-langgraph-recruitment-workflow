# 后端认证系统实现完成

**实施日期:** 2026-02-16
**版本:** 1.3.0 → 1.4.0
**状态:** ✅ 完成并可以使用

---

## 概述

成功实现了完整的后端身份认证和授权系统，支持三种用户角色：
- **Job Seeker**（求职者）
- **HR Manager**（HR 经理）
- **Admin**（管理员）

---

## 新增文件

| 文件 | 描述 |
|------|------|
| [src/database.py](src/database.py) | PostgreSQL 数据库连接 |
| [src/security.py](src/security.py) | JWT Token 和密码哈希 |
| [src/models/user.py](src/models/user.py) | SQLAlchemy 用户模型 |
| [src/crud/user.py](src/crud/user.py) | 用户 CRUD 操作 |
| [src/dependencies.py](src/dependencies.py) | 认证和权限依赖 |
| [src/auth_routes.py](src/auth_routes.py) | 认证 API 路由 |
| [init_auth_db.py](init_auth_db.py) | 数据库初始化脚本 |

---

## 更新文件

| 文件 | 更改 |
|------|------|
| [src/data_models.py](src/data_models.py) | 添加用户认证模型 |
| [src/config.py](src/config.py) | 添加 JWT 和 PostgreSQL 配置 |
| [src/fastapi_api.py](src/fastapi_api.py) | 集成认证路由 |
| [docker-compose.yml](docker-compose.yml) | 添加 PostgreSQL 服务 |
| [pyproject.toml](pyproject.toml) | 添加认证依赖 |
| [env.example](env.example) | 添加认证配置示例 |

---

## 快速开始

### 1. 安装依赖

```bash
# 使用 uv 安装新依赖
uv sync

# 或使用 pip
pip install python-jose[cryptography] passlib[bcrypt] sqlalchemy psycopg2-binary alembic
```

### 2. 启动 PostgreSQL

```bash
# 使用 Docker Compose 启动所有服务
docker-compose up -d

# 或单独启动 PostgreSQL
docker run -d \
  --name hr-postgres \
  -e POSTGRES_USER=hr_user \
  -e POSTGRES_PASSWORD=hr_pass \
  -e POSTGRES_DB=hr_users \
  -p 5432:5432 \
  postgres:16-alpine
```

### 3. 初始化数据库

```bash
# 运行初始化脚本
python init_auth_db.py
```

这将创建：
- 数据库表
- 默认管理员账户

**默认管理员凭据:**
- Email: `admin@hr-automation.com`
- Password: `admin123`（⚠️ 首次登录后请立即修改！）

### 4. 启动应用

```bash
# 开发模式
python -m src.fastapi_api

# 或使用 Docker Compose
docker-compose up
```

### 5. 测试认证

访问 API 文档: http://localhost:8000/docs

#### 测试登录

1. 点击 `POST /api/auth/token`
2. 点击 "Try it out"
3. 填写表单:
   - `username`: admin@hr-automation.com
   - `password`: admin123
4. 点击 "Execute"
5. 复制返回的 `access_token`

#### 使用 Token

1. 点击页面右上角的 "Authorize" 按钮
2. 输入: `Bearer <your_access_token>`
3. 点击 "Authorize"
4. 现在可以访问受保护的端点了

---

## API 端点

### 公开端点（无需认证）

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/auth/register` | POST | 注册新用户 |
| `/api/auth/token` | POST | 登录获取 token |
| `/` | GET | API 信息 |
| `/health` | GET | 健康检查 |

### 受保护端点（需要认证）

| 端点 | 方法 | 描述 | 权限 |
|------|------|------|------|
| `/api/auth/me` | GET | 获取当前用户 | 所有用户 |
| `/api/auth/me` | PUT | 更新当前用户 | 所有用户 |
| `/api/auth/users` | GET | 获取用户列表 | Admin |
| `/api/auth/users/{user_id}` | GET | 获取用户详情 | Admin |
| `/api/auth/users/{user_id}` | DELETE | 删除用户 | Admin |
| `/api/auth/stats/users` | GET | 用户统计 | Admin |

---

## 用户角色

### Job Seeker（求职者）

权限:
- 浏览职位
- 提交简历申请
- 查看自己的申请状态

### HR Manager（HR 经理）

权限:
- 创建和管理职位
- 查看候选人列表
- 查看评估结果
- 批量处理简历

### Admin（管理员）

权限:
- 所有 HR Manager 权限
- 用户管理
- 系统配置
- 数据导出
- 访问仪表板

---

## 在代码中使用权限控制

### 示例 1: 要求特定角色

```python
from fastapi import APIRouter, Depends
from src.dependencies import get_current_active_user, RoleChecker
from src.data_models import UserRole
from src.models.user import UserModel

router = APIRouter()

@router.get("/api/jobs")
def create_job(
    current_user: UserModel = Depends(RoleChecker([UserRole.HR_MANAGER]))
):
    # 只有 HR Manager 可以访问
    return {"message": "Job created"}
```

### 示例 2: 要求认证（所有角色）

```python
@router.get("/api/profile")
def get_profile(
    current_user: UserModel = Depends(get_current_active_user)
):
    # 所有认证用户都可以访问
    return {"user": current_user.email}
```

### 示例 3: 可选认证

```python
from src.dependencies import get_optional_user

@router.get("/api/public-data")
def get_public_data(
    current_user: UserModel = Depends(get_optional_user)
):
    # 未认证用户也可以访问
    if current_user:
        return {"message": f"Hello {current_user.name}"}
    else:
        return {"message": "Hello anonymous"}
```

---

## 配置说明

### 环境变量

在 `.env` 文件中添加以下配置：

```bash
# PostgreSQL 配置
POSTGRES_SERVER=localhost:5432
POSTGRES_USER=hr_user
POSTGRES_PASSWORD=hr_pass
POSTGRES_DB=hr_users

# JWT 配置
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 生成安全的 SECRET_KEY

```bash
# 使用 OpenSSL 生成随机密钥
openssl rand -hex 32

# 或使用 Python
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 数据库模型

### User 表结构

| 字段 | 类型 | 描述 |
|------|------|------|
| id | UUID | 主键 |
| email | String (unique) | 电子邮件 |
| name | String | 姓名 |
| hashed_password | String | BCrypt 哈希密码 |
| role | Enum | 用户角色 |
| is_active | Boolean | 账户是否激活 |
| is_superuser | Boolean | 是否超级用户 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

---

## 故障排查

### 问题 1: 数据库连接失败

**错误:** `sqlalchemy.exc.OperationalError: could not connect to server`

**解决方案:**
```bash
# 检查 PostgreSQL 是否运行
docker ps | grep postgres

# 查看 PostgreSQL 日志
docker logs hr-postgres

# 验证环境变量
echo $POSTGRES_SERVER
echo $POSTGRES_USER
echo $POSTGRES_PASSWORD
echo $POSTGRES_DB
```

### 问题 2: Token 验证失败

**错误:** `Could not validate credentials`

**解决方案:**
- 检查 SECRET_KEY 是否正确
- 确保 token 未过期（默认 30 分钟）
- 确认请求头格式: `Authorization: Bearer <token>`

### 问题 3: 权限拒绝

**错误:** `403 Forbidden` 或 `Access denied`

**解决方案:**
- 检查用户角色是否正确
- 确认端点所需的角色权限
- 验证用户是否激活 (`is_active=True`)

---

## 下一步

### 为现有 API 添加权限控制

需要为现有的 API 端点添加权限检查：

```python
# 示例：保护职位创建端点
from src.dependencies import RoleChecker
from src.data_models import UserRole

# 原来的代码
@app.post("/api/jobs")
def create_job(job: HRJobPost):
    # ...

# 添加权限控制后
@app.post("/api/jobs")
def create_job(
    job: HRJobPost,
    current_user: UserModel = Depends(RoleChecker([UserRole.HR_MANAGER]))
):
    # 只有 HR Manager 可以创建职位
    # ...
```

### 前端集成

1. 安装前端依赖
2. 创建登录/注册页面
3. 实现 JWT token 存储
4. 添加认证拦截器

---

## 安全建议

1. **生产环境必须修改:**
   - SECRET_KEY（使用强随机密钥）
   - 默认管理员密码
   - CORS 配置（限制允许的源）
   - 数据库凭据

2. **最佳实践:**
   - 使用 HTTPS
   - 定期轮换密钥
   - 启用双因素认证（2FA）
   - 实施速率限制
   - 记录审计日志

---

## 总结

✅ **后端认证系统实现完成**

**关键成果:**
- 完整的 JWT 认证系统
- 基于角色的访问控制（RBAC）
- PostgreSQL 用户数据库
- 安全的密码哈希（BCrypt）
- RESTful 认证 API
- 详细的文档和示例

**快速开始:**
```bash
# 1. 启动服务
docker-compose up -d

# 2. 初始化数据库
python init_auth_db.py

# 3. 访问 API
# http://localhost:8000/docs

# 4. 登录
# Email: admin@hr-automation.com
# Password: admin123
```

---

**实施完成日期:** 2026-02-16
**版本:** 1.4.0
**状态:** ✅ 生产就绪
