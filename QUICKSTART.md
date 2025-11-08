# 🚀 快速启动指南

## ✅ 已完成的修复

### ChromaDB 集合名称修复
- ✅ `app/tools/vdb.py`: 集合名称 "kb" → "knowledge_base"
- ✅ `app/memory/vector_store.py`: 默认集合名称 "kb" → "knowledge_base"
- ✅ 测试通过: `python -m scripts.ingest` 成功导入 3 条数据

## 📦 安装依赖

### 方案 1: 使用虚拟环境（强烈推荐）

```powershell
# 1. 创建虚拟环境
cd D:\AI_Learning\LLM\agentic_ai_artc
python -m venv .venv

# 2. 激活虚拟环境
.\.venv\Scripts\activate

# 3. 安装所有依赖
pip install -r requirements.txt

# 4. 验证安装
pip list
```

### 方案 2: 全局安装（不推荐）

```powershell
cd D:\AI_Learning\LLM\agentic_ai_artc
pip install -r requirements.txt
```

## 🔧 创建 .env 文件

在项目根目录创建 `.env` 文件：

```env
# 基础配置
API_TOKEN=changeme
CORS_ALLOW_ORIGINS=["*"]

# LLM 配置（默认使用 mock，无需 API key）
LLM_PROVIDER=mock

# 存储配置
SQLITE_PATH=./mvp.db
VECTOR_BACKEND=chroma

# Weather API
WEATHER_API=open-meteo

# DeepSeek（可选）
DEEPSEEK_API_KEY=
DEEPSEEK_MODEL=deepseek-chat

# Gemini（可选）
GEMINI_API_KEY=
GEMINI_MODEL=gemini-pro

# OpenAI（可选）
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
```

快速创建（PowerShell）：
```powershell
@"
API_TOKEN=changeme
LLM_PROVIDER=mock
SQLITE_PATH=./mvp.db
VECTOR_BACKEND=chroma
WEATHER_API=open-meteo
"@ | Out-File -FilePath .env -Encoding UTF8
```

## 🎯 测试步骤

### 1. 导入知识库数据
```bash
python -m scripts.ingest
# 预期输出: {"ingested": 3}
```

### 2. 测试配置加载
```bash
python -c "from app.utils.config import settings; print(f'✓ LLM: {settings.LLM_PROVIDER}')"
```

### 3. 测试 FastAPI 导入
```bash
python -c "from app.main import app; print('✓ FastAPI app ready')"
```

### 4. 启动服务
```bash
uvicorn app.main:app --reload --port 8000
```

### 5. 测试 API（新终端）
```bash
# 健康检查
curl http://127.0.0.1:8000/health

# 测试 Agent
curl -H "Authorization: Bearer changeme" -X POST http://127.0.0.1:8000/agent/invoke -H "Content-Type: application/json" -d "{\"input\":\"Hello\"}"
```

### 6. 运行测试套件
```bash
pytest tests/ -v
```

## 🌐 访问 Web UI

```bash
# 启动 Streamlit UI
streamlit run ui/app.py
```

访问: http://localhost:8501

## 📋 检查清单

- [ ] 创建虚拟环境
- [ ] 激活虚拟环境
- [ ] 安装依赖 (`pip install -r requirements.txt`)
- [ ] 创建 `.env` 文件
- [ ] 导入测试数据 (`python -m scripts.ingest`)
- [ ] 启动服务 (`uvicorn app.main:app --reload`)
- [ ] 测试 API
- [ ] 运行测试套件 (`pytest tests/ -v`)
- [ ] 启动 Web UI (`streamlit run ui/app.py`)

## 🐛 常见问题

### 问题 1: ModuleNotFoundError
**症状**: `ModuleNotFoundError: No module named 'fastapi'`

**解决**:
```bash
pip install -r requirements.txt
```

### 问题 2: ChromaDB 集合名称错误
**症状**: `InvalidArgumentError: name: Expected a name containing 3-512 characters`

**解决**: ✅ 已修复（集合名称改为 "knowledge_base"）

### 问题 3: .env 文件未找到
**症状**: 使用默认配置

**解决**: 创建 `.env` 文件（参考上面的模板）

## 🎉 成功标志

启动成功后，你应该看到：
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

访问 http://127.0.0.1:8000/docs 查看 API 文档！

