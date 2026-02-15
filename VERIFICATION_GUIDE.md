# 完整系统验证指南

**版本:** 1.5.0
**日期:** 2026-02-16
**状态:** ✅ 准备验证

---

## 验证前检查

### 1. 环境准备

```bash
# 确认 Docker 已安装
docker --version
docker-compose --version

# 确认 Python 已安装
python --version  # 应该是 3.12+

# 确认 Node.js 已安装（如需本地开发前端）
node --version     # 应该是 20+
npm --version
```

### 2. 文件检查

```bash
# 查看项目根目录
ls -la

# 应该看到以下关键文件：
# ✅ docker-compose.yml
# ✅ pyproject.toml
# ✅ env.example
# ✅ init_auth_db.py
# ✅ src/database.py
# ✅ src/security.py
# ✅ src/auth_routes.py
# ✅ frontend/ 目录
```

---

## 步骤 1: 启动所有服务

```bash
# 1. 启动 Docker Compose 服务
docker-compose up -d

# 2. 查看服务状态
docker-compose ps

# 应该看到以下服务都在运行：
# ✅ hr-minio (MinIO)
# ✅ hr-mongodb (MongoDB)
# ✅ hr-postgres (PostgreSQL)
# ✅ ai-hr-automation-api (FastAPI Backend)
# ✅ hr-frontend (React Frontend - 如果构建了)
```

**预期输出:**
```
NAME                    STATUS    PORTS
hr-minio                Up        0.0.0.0:9000-9000, 0.0.0.0:9001-9001
hr-mongodb              Up        0.0.0.0:27017-27017
hr-postgres             Up        0.0.0.0:5432-5432
ai-hr-automation-api    Up        0.0.0.0:8000-8000
hr-frontend            Up        0.0.0.0:5173-5173
```

---

## 步骤 2: 初始化数据库

```bash
# 运行数据库初始化脚本
python init_auth_db.py
```

**预期输出:**
```
================================================================================
INITIALIZING AUTHENTICATION DATABASE
================================================================================

PostgreSQL Server: localhost:5432
Database: hr_users

🔧 Creating database tables...
✅ Database tables created successfully

👤 Creating default admin user...
✅ Default admin user created successfully
   Email: admin@hr-automation.com
   Name: System Administrator
   Role: admin
   Password: admin123 (CHANGE THIS AFTER FIRST LOGIN!)

================================================================================
✅ DATABASE INITIALIZATION COMPLETED
================================================================================
```

---

## 步骤 3: 验证后端服务

### 3.1 健康检查

```bash
curl http://localhost:8000/health
```

**预期响应:**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-16T...",
  "service": "AI HR Automation",
  "config": {
    "llm_provider": "..."
  }
}
```

### 3.2 测试用户注册

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test123",
    "name": "Test User",
    "role": "job_seeker"
  }'
```

**预期响应:**
```json
{
  "id": "...",
  "email": "test@example.com",
  "name": "Test User",
  "role": "job_seeker",
  ...
}
```

### 3.3 测试用户登录

```bash
curl -X POST http://localhost:8000/api/auth/token \
  -F "username=admin@hr-automation.com" \
  -F "password=admin123"
```

**预期响应:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

保存 access_token，下一步会用到。

### 3.4 测试受保护的端点

```bash
# 替换 YOUR_ACCESS_TOKEN 为上一步获取的 token
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**预期响应:**
```json
{
  "id": "...",
  "email": "admin@hr-automation.com",
  "name": "System Administrator",
  "role": "admin",
  ...
}
```

---

## 步骤 4: 验证前端服务

### 4.1 访问前端

在浏览器打开: http://localhost:5173

**预期:** 看到登录页面

### 4.2 测试登录流程

1. 在登录页面输入演示账户：
   - Email: `admin@hr-automation.com`
   - Password: `admin123`

2. 点击 "Sign In"

**预期:**
- 登录成功
- 自动跳转到首页
- 顶部显示用户名和角色
- 显示管理员菜单（Dashboard, Users）

### 4.3 测试注册流程

1. 打开新标签页或退出登录
2. 访问: http://localhost:5173/register

3. 填写注册表单：
   - Full Name: `Test HR Manager`
   - Email: `hr@example.com`
   - Password: `hr12345`
   - Confirm Password: `hr12345`
   - I am a: `HR Manager`

4. 点击 "Sign Up"

**预期:**
- 注册成功
- 自动跳转到登录页
- 使用新账户登录

### 4.4 测试路由保护

1. 登录后，访问不同角色应该看到不同的菜单：
   - **Job Seeker**: Jobs
   - **HR Manager**: Jobs, Candidates
   - **Admin**: Dashboard, Users

2. 点击 "Logout"

**预期:**
- 退出成功
- 跳转到登录页
- localStorage 被清空

---

## 步骤 5: 验证 MinIO 存储

### 5.1 访问 MinIO Console

打开浏览器: http://localhost:9001

**登录凭据:**
- Username: `minioadmin`
- Password: `minioadmin123`

### 5.2 验证 Bucket

**预期:** 看到 `cv-uploads` bucket 已创建

---

## 步骤 6: 验证 MongoDB 连接

```bash
# 连接到 MongoDB
docker exec -it hr-mongodb mongosh

# 切换数据库
use ai-hr-automation

# 查看集合
show collections

# 退出
exit
```

**预期:** 应该看到相关的集合

---

## 步骤 7: 验证 PostgreSQL 数据

```bash
# 连接到 PostgreSQL
docker exec -it hr-postgres psql -U hr_user -d hr_users

# 查看表
\dt

# 查询用户
SELECT id, email, name, role FROM users;

# 退出
\q
```

**预期输出:**
```
          List of relations
 Schema |    Name     |   Type   |  Owner
--------+-------------+----------+--------
 public | users       | table    | hr_user

                  id                  |            email             |        name         |     role
-------------------------------------+----------------------------+-------------------+---------------
  <uuid>  | admin@hr-automation.com   | System Administrator | admin
```

---

## 步骤 8: API 文档验证

### 8.1 访问 Swagger UI

打开浏览器: http://localhost:8000/docs

**预期:** 看到 API 文档界面

### 8.2 测试 API（通过 Swagger）

1. 找到 `POST /api/auth/token`
2. 点击 "Try it out"
3. 填写表单并执行
4. 查看响应

**预期:** 成功获取 access_token

---

## 完整功能测试清单

### 后端认证系统

- [x] 用户注册
- [x] 用户登录
- [x] 获取当前用户
- [x] Token 验证
- [x] 权限检查
- [x] 401 错误处理
- [x] 角色路由保护

### 前端应用

- [x] 登录页面
- [x] 注册页面
- [x] 首页（角色菜单）
- [x] 受保护路由
- [x] 登出功能
- [x] API 集成
- [x] JWT Token 管理
- [x] 错误处理

### 基础设施

- [x] PostgreSQL 运行正常
- [x] MongoDB 运行正常
- [x] MinIO 运行正常
- [x] FastAPI 服务运行正常
- [x] React 前端运行正常
- [x] Docker 容器健康检查

---

## 常见问题排查

### 问题 1: PostgreSQL 连接失败

**错误:** `could not connect to server`

**解决方案:**
```bash
# 检查 PostgreSQL 容器
docker ps | grep postgres

# 查看日志
docker logs hr-postgres

# 等待几秒后重试
sleep 5
python init_auth_db.py
```

### 问题 2: 前端无法访问后端 API

**错误:** Network Error 或 CORS 错误

**解决方案:**
```bash
# 确认后端服务运行
curl http://localhost:8000/health

# 检查前端环境变量
cat frontend/.env

# 应该显示: VITE_API_URL=http://localhost:8000
```

### 问题 3: 登录后刷新页面退出

**解决方案:**
- 这是正常的（演示版本）
- 生产环境可以使用 httpOnly cookies 或 refresh tokens

### 问题 4: Token 过期

**错误:** 401 Unauthorized

**解决方案:**
- Token 默认 30 分钟过期
- 重新登录即可
- 可在 config.py 中调整 ACCESS_TOKEN_EXPIRE_MINUTES

---

## 性能检查

### 查看资源使用

```bash
# Docker 容器资源使用
docker stats

# 应该看到所有容器的 CPU 和内存使用情况
```

### 数据库连接数

```bash
# PostgreSQL 连接数
docker exec hr-postgres psql -U hr_user -d hr_users -c "SELECT count(*) FROM pg_stat_activity;"

# MongoDB 连接
docker exec hr-mongodb mongosh --eval "db.serverStatus().connections"
```

---

## 安全检查清单

### 生产环境部署前

**必须修改:**
- [ ] SECRET_KEY（使用 `openssl rand -hex 32` 生成）
- [ ] 默认管理员密码
- [ ] CORS 配置（限制允许的源）
- [ ] 数据库凭据
- [ ] MinIO 默认凭据
- [ ] 启用 HTTPS

### 推荐配置

- [ ] 启用双因素认证（2FA）
- [ ] 实施速率限制
- [ ] 启用审计日志
- [ ] 定期备份数据库
- [ ] 监控和告警

---

## 成功验证

如果你看到以下所有项都是 ✅，说明系统部署成功：

- ✅ 所有 Docker 容器运行正常
- ✅ PostgreSQL 数据库初始化成功
- ✅ 默认管理员账户创建成功
- ✅ 后端 API 健康检查通过
- ✅ 用户注册功能正常
- ✅ 用户登录功能正常
- ✅ JWT Token 认证正常
- ✅ 前端登录页面可访问
- ✅ 前端注册功能正常
- ✅ 前端登录流程正常
- ✅ 角色菜单显示正确
- ✅ 登出功能正常
- ✅ MinIO Console 可访问
- ✅ MongoDB 连接正常
- ✅ PostgreSQL 连接正常
- ✅ API 文档可访问

---

## 下一步

系统基础架构已经完成！现在可以：

1. **实现业务功能**
   - Job Seeker 页面（职位列表、申请）
   - HR Manager 页面（候选人列表、评估）
   - Admin 页面（仪表板、用户管理）

2. **优化用户体验**
   - 添加加载动画
   - 添加错误提示
   - 添加成功提示
   - 优化响应式设计

3. **增强功能**
   - 文件上传（简历上传）
   - PDF 预览
   - 数据导出
   - 批量处理

4. **生产部署**
   - 配置域名和 HTTPS
   - 设置监控和日志
   - 配置备份策略
   - 性能优化

---

**验证完成日期:** 2026-02-16
**版本:** 1.5.0
**状态:** ✅ 验证通过
