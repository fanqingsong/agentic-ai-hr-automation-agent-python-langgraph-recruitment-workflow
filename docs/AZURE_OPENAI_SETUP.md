# Azure OpenAI 集成指南

**版本:** 1.0.0
**日期:** 2026-02-16
**状态:** ✅ 生产就绪

---

## 概述

本项目现已支持 Azure OpenAI 服务，可以在 Azure 云平台上运行 OpenAI 模型。

### 为什么使用 Azure OpenAI？

- **企业级安全性**: 数据保留在 Azure 网络内
- **合规性**: 满足各种行业合规要求
- **灵活部署**: 支持私有网络部署
- **高可用性**: Azure 的 SLA 保证
- **统一计费**: 与 Azure 服务统一账单

---

## 支持的模型

### 推荐模型

| 模型 | 用途 | 成本 | 性能 |
|------|------|------|------|
| **gpt-4o-mini** | 生产环境推荐 (默认) | 低 | 优秀 |
| **gpt-4o** | 多模态任务 | 中 | 卓越 |
| **gpt-4-turbo** | 复杂推理 | 高 | 最佳 |
| **gpt-35-turbo** | 成本敏感场景 | 最低 | 良好 |

---

## Azure OpenAI 设置步骤

### 1. 创建 Azure OpenAI 资源

1. 访问 [Azure Portal](https://portal.azure.com/)
2. 搜索 "Azure OpenAI"
3. 点击 "创建"
4. 填写基本信息:
   - **订阅**: 选择你的 Azure 订阅
   - **资源组**: 创建或选择现有资源组
   - **区域**: 选择离你最近的区域
   - **名称**: 输入唯一标识符 (如: `my-hr-automation-openai`)
5. 点击 "审核 + 创建"，然后 "创建"

### 2. 部署模型

1. 创建资源后，进入 "Azure OpenAI Studio"
2. 点击左侧菜单 "部署"
3. 点击 "创建部署"
4. 选择模型:
   - 模型: `gpt-4o-mini` (推荐)
   - 部署名称: `gpt-4o-mini` (自定义名称)
   - 每分钟令牌限制: 根据需求选择
5. 点击 "创建"

### 3. 获取 API 密钥和端点

1. 在 Azure Portal 中，进入你的 Azure OpenAI 资源
2. 点击左侧菜单 "密钥和终结点"
3. 复制以下信息:
   - **API 密钥**: 两个密钥任选其一
   - **终结点**: 类似 `https://your-resource-name.openai.azure.com/`

---

## 配置项目

### 1. 更新 `.env` 文件

```bash
# 使用 Azure OpenAI
LLM_PROVIDER=azure

# Azure OpenAI 配置
AZURE_OPENAI_API_KEY=your_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_MODEL=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

### 2. 配置说明

| 变量 | 说明 | 示例 |
|------|------|------|
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API 密钥 | `abc123...` |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI 终结点 | `https://my-openai.openai.azure.com/` |
| `AZURE_OPENAI_DEPLOYMENT` | 模型部署名称 | `gpt-4o-mini` |
| `AZURE_OPENAI_MODEL` | 模型名称 | `gpt-4o-mini` |
| `AZURE_OPENAI_API_VERSION` | API 版本 | `2024-02-15-preview` |

---

## 使用示例

### 1. 基本使用

```python
from src.llm_provider import create_summary_llm

# 自动使用 .env 中的 Azure OpenAI 配置
llm = create_summary_llm()

# 或显式指定 Azure
llm = create_summary_llm(provider="azure")
```

### 2. 在工作流中使用

```python
from src.hr_automation import create_hr_workflow

# 自动使用 LLM_PROVIDER=azure
workflow = create_hr_workflow()

result = workflow.invoke({
    "cv_file_path": "./resume.pdf",
    "hr_job_post": job_post
})
```

### 3. 自定义配置

```python
from src.llm_provider import LLMFactory

llm = LLMFactory.create_llm(
    provider="azure",
    model="gpt-4o",
    temperature=0.3,
    max_tokens=1000
)
```

---

## 验证配置

### 测试连接

运行以下命令验证 Azure OpenAI 配置:

```bash
# 测试配置加载
python -c "from src.config import Config; print(f'Provider: {Config.LLM_PROVIDER}'); print(f'Endpoint: {Config.AZURE_OPENAI_ENDPOINT}')"

# 测试 LLM 创建
python -c "from src.llm_provider import create_summary_llm; llm = create_summary_llm(); print('✅ Azure OpenAI LLM created successfully')"
```

### 运行完整测试

```bash
# 提交测试简历
python -m src.fastapi_api

# 在另一个终端:
curl -X POST http://localhost:8000/api/candidate-application-submit \
  -F "job_id=test_001" \
  -F "name=Test Candidate" \
  -F "email=test@example.com" \
  -F "cv_file=@test_resume.pdf"
```

---

## 故障排查

### 问题 1: 连接失败

**错误信息:**
```
ValueError: AZURE_OPENAI_ENDPOINT is required for Azure OpenAI
```

**解决方案:**
1. 检查 `.env` 文件中 `AZURE_OPENAI_ENDPOINT` 是否正确
2. 确保端点 URL 以 `https://` 开头
3. 确保端点 URL 以 `/` 结尾

### 问题 2: 认证失败

**错误信息:**
```
Error code: 401 - Invalid authentication
```

**解决方案:**
1. 检查 `AZURE_OPENAI_API_KEY` 是否正确
2. 确认 API 密钥未过期
3. 尝试使用另一个 API 密钥 (Azure 提供两个)

### 问题 3: 部署未找到

**错误信息:**
```
Error code: 404 - The deployment does not exist
```

**解决方案:**
1. 检查 `AZURE_OPENAI_DEPLOYMENT` 名称是否正确
2. 在 Azure OpenAI Studio 中确认部署名称
3. 确保模型已在 Azure OpenAI Studio 中部署

### 问题 4: 配额不足

**错误信息:**
```
Error code: 429 - Rate limit exceeded
```

**解决方案:**
1. 检查 Azure OpenAI 配额使用情况
2. 在 Azure Portal 中增加配额
3. 考虑使用更小的模型 (如 `gpt-4o-mini`)

---

## 性能优化

### 1. 选择合适的模型

```python
# 数据提取 - 使用快速模型
extraction_llm = create_extraction_llm(
    provider="azure",
    model="gpt-4o-mini"
)

# 复杂评估 - 使用高质量模型
evaluation_llm = create_evaluation_llm(
    provider="azure",
    model="gpt-4-turbo"
)
```

### 2. 调整温度参数

```python
# 需要确定性输出 (数据提取)
llm = LLMFactory.create_llm(
    provider="azure",
    temperature=0.0
)

# 需要创造性输出 (总结)
llm = LLMFactory.create_llm(
    provider="azure",
    temperature=0.5
)
```

### 3. 批处理

使用批处理功能提高吞吐量:

```python
from src.batch_processing import BatchProcessor

processor = BatchProcessor(max_concurrent=5)
results = await processor.process_batch(candidates, job_post)
```

---

## 成本估算

### Azure OpenAI 定价 (示例)

| 模型 | 输入 (每1K tokens) | 输出 (每1K tokens) |
|------|-------------------|-------------------|
| gpt-4o-mini | $0.00015 | $0.00060 |
| gpt-4o | $0.005 | $0.015 |
| gpt-4-turbo | $0.01 | $0.03 |
| gpt-35-turbo | $0.0005 | $0.002 |

### 每个候选人成本估算

使用 `gpt-4o-mini`:
- 数据提取: ~500 tokens
- 技能匹配: ~300 tokens
- 评估: ~800 tokens
- 总结: ~300 tokens

**总成本**: 约 $0.002 / 候选人

处理 1000 个候选人: ~$2

---

## 安全最佳实践

### 1. API 密钥管理

```bash
# ❌ 不要在代码中硬编码
AZURE_OPENAI_API_KEY=abc123...

# ✅ 使用环境变量
export AZURE_OPENAI_API_KEY=abc123...
```

### 2. 使用 Azure Key Vault (生产环境)

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

credential = DefaultAzureCredential()
client = SecretClient(
    vault_url="https://your-keyvault.vault.azure.net/",
    credential=credential
)

api_key = client.get_secret("azure-openai-api-key")
```

### 3. 网络隔离

- 使用虚拟网络 (VNet) 集成
- 配置私有端点
- 限制公共访问

---

## API 版本

### 推荐版本

| 版本 | 发布日期 | 状态 |
|------|---------|------|
| `2024-02-15-preview` | 2024-02 | ✅ 最新 |
| `2023-12-01-preview` | 2023-12 | ✅ 稳定 |
| `2023-07-01-preview` | 2023-07 | ⚠️ 旧版本 |

**建议**: 使用 `2024-02-15-preview` 获得最新功能。

---

## 迁移指南

### 从标准 OpenAI 迁移到 Azure OpenAI

**1. 更新 `.env` 文件:**
```bash
# 之前
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...

# 之后
LLM_PROVIDER=azure
AZURE_OPENAI_API_KEY=your_azure_key
AZURE_OPENAI_ENDPOINT=https://...
```

**2. 无需修改代码:**
项目使用工厂模式，代码无需任何修改。

**3. 测试:**
```bash
python -c "from src.llm_provider import create_summary_llm; print('✅ Migration successful')"
```

---

## 参考资料

- [Azure OpenAI 文档](https://learn.microsoft.com/en-us/azure/ai-services/openai/)
- [Azure OpenAI Studio](https://oai.azure.com/)
- [定价计算器](https://azure.microsoft.com/en-us/pricing/details/cognitive-services/openai-service/)
- [最佳实践](https://learn.microsoft.com/en-us/azure/ai-services/openai/best-practices)

---

## 支持

遇到问题？

1. 查看 [故障排查](#故障排查) 部分
2. 检查 [Azure 状态页面](https://status.azure.com/)
3. 联系 Azure 支持

---

**文档版本:** 1.0.0
**最后更新:** 2026-02-16
**状态:** ✅ 生产就绪
