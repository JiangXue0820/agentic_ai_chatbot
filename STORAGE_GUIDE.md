# 存储架构指南

## 📁 存储目录结构

项目现已采用统一的 `storage/` 目录来管理所有持久化数据：

```
agentic_ai_artc/
├── storage/                    # 统一存储根目录
│   ├── memory/                 # SQLite 数据库存储
│   │   └── mvp.db             # 对话记忆和上下文
│   └── vectordb/               # ChromaDB 向量数据库
│       ├── chroma.sqlite3     # ChromaDB 元数据
│       └── [embedding files]   # 向量数据文件
├── app/
│   ├── memory/
│   │   ├── sqlite_store.py    # ✓ 已更新：确保目录存在
│   │   └── vector_store.py    # ✓ 已更新：PersistentClient
│   └── utils/
│       └── config.py           # ✓ 已更新：存储路径配置
└── ...
```

## 🔧 配置说明

### 环境变量（.env）

```env
# Storage Configuration
STORAGE_DIR=./storage                  # 存储根目录
SQLITE_PATH=./storage/memory/mvp.db   # SQLite 数据库
CHROMA_PATH=./storage/vectordb        # ChromaDB 目录
```

### 配置参数（app/utils/config.py）

```python
class Settings(BaseSettings):
    # Storage Configuration
    STORAGE_DIR: str = "./storage"
    SQLITE_PATH: str = "./storage/memory/mvp.db"
    CHROMA_PATH: str = "./storage/vectordb"
```

## ✅ 关键改进

### 1. 统一存储位置
- **之前**: 数据文件散落在项目根目录
- **现在**: 所有数据集中在 `storage/` 目录

### 2. 持久化向量数据
- **之前**: `chromadb.Client()` - 临时存储，重启后丢失
- **现在**: `chromadb.PersistentClient()` - 持久化存储

### 3. 自动目录创建
- **之前**: 需要手动创建目录
- **现在**: 代码自动创建所需目录

## 📊 数据持久化对比

| 存储类型 | 位置 | 持久化 | 说明 |
|---------|------|--------|------|
| **对话记忆** | `./storage/memory/mvp.db` | ✅ 永久 | SQLite 数据库 |
| **向量数据** | `./storage/vectordb/` | ✅ 永久 | ChromaDB 持久化 |

## 🔍 查看存储数据

### 查看 SQLite 数据库

```bash
# 方法 1: Python
python -c "import sqlite3; conn = sqlite3.connect('./storage/memory/mvp.db'); print(conn.execute('SELECT * FROM memories').fetchall())"

# 方法 2: SQLite CLI
sqlite3 ./storage/memory/mvp.db
> SELECT * FROM memories;
> .exit
```

### 查看 ChromaDB 数据

```python
# 创建脚本 check_storage.py
import chromadb

client = chromadb.PersistentClient(path="./storage/vectordb")
collections = client.list_collections()

print(f"Collections: {[c.name for c in collections]}")

for coll in collections:
    print(f"\nCollection: {coll.name}")
    print(f"  Count: {coll.count()}")
    if coll.count() > 0:
        print(f"  Sample: {coll.peek(3)}")
```

运行：
```bash
python check_storage.py
```

## 🧹 清理存储数据

### 清理所有数据

```bash
# Windows PowerShell
Remove-Item -Recurse -Force ./storage

# Linux/Mac
rm -rf ./storage
```

### 清理特定数据

```bash
# 只清理向量数据
Remove-Item -Recurse -Force ./storage/vectordb

# 只清理记忆数据
Remove-Item ./storage/memory/mvp.db
```

重启服务后，目录会自动重新创建。

## 🚀 迁移现有数据

如果你有旧的数据文件，可以这样迁移：

```bash
# 1. 创建新目录结构
mkdir -p storage/memory
mkdir -p storage/vectordb

# 2. 移动旧数据（如果存在）
mv mvp.db storage/memory/
mv chroma storage/vectordb/

# 3. 重启服务
uvicorn app.main:app --reload
```

## 📝 代码变更摘要

### app/utils/config.py
- ✅ 添加 `STORAGE_DIR` 配置
- ✅ 更新 `SQLITE_PATH` 路径
- ✅ 添加 `CHROMA_PATH` 配置
- ✅ 添加 `ensure_storage_dirs()` 函数

### app/memory/vector_store.py
- ✅ `chromadb.Client()` → `chromadb.PersistentClient(path=settings.CHROMA_PATH)`
- ✅ 导入 `settings` 读取配置

### app/memory/sqlite_store.py
- ✅ 添加目录创建逻辑确保 parent 目录存在

### ENV_SETUP.md
- ✅ 更新存储配置说明
- ✅ 添加 `CHROMA_PATH` 文档

## 💡 最佳实践

1. **备份重要数据**: 定期备份 `storage/` 目录
2. **版本控制**: 在 `.gitignore` 中添加 `storage/`
3. **监控磁盘**: 向量数据可能占用较多空间
4. **定期清理**: 清理过期的记忆数据

## ⚠️ 注意事项

1. **路径一致性**: 确保所有路径配置使用相对路径
2. **权限问题**: 确保应用有读写 `storage/` 的权限
3. **数据迁移**: 升级时注意数据迁移
4. **备份策略**: 生产环境建议配置自动备份

## 🎯 测试存储功能

```bash
# 1. 导入测试数据
python -m scripts.ingest

# 2. 验证数据已持久化
ls -la storage/vectordb/

# 3. 重启服务
uvicorn app.main:app --reload

# 4. 查询数据（应该还在）
curl -H "Authorization: Bearer changeme" -X POST http://127.0.0.1:8000/tools/vdb/query -H 'Content-Type: application/json' -d '{"query":"federated learning","top_k":3}'
```

数据应该在服务重启后依然存在！✅

