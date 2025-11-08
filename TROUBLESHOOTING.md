# Troubleshooting Guide

## Issue: ImportError - cannot import name 'ShortTermMemory' from 'app.agent.memory'

### Problem
```
ImportError: cannot import name 'ShortTermMemory' from 'app.agent.memory'
```

### Root Cause
The `app/agent/memory.py` file was corrupted or empty (0 bytes) on disk, even though it showed correct content in the editor.

### Solution Steps

#### 1. Clear Python Bytecode Cache
```powershell
# Remove all __pycache__ directories
Get-ChildItem -Path agentic_ai_artc -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force

# Remove all .pyc files
Get-ChildItem -Path agentic_ai_artc -Recurse -Filter "*.pyc" | Remove-Item -Force
```

#### 2. Verify File Content
```powershell
# Check file size
Get-Content app\agent\memory.py | Measure-Object -Line
```

If the file is empty or incomplete, restore it with the correct content (see below).

#### 3. Restore memory.py
The file should contain:
- `ShortTermMemory` class (in-memory conversation buffer)
- `SessionMemory` class (persistent session storage)

#### 4. Install Dependencies
```powershell
# Use virtual environment if available
..\.venv\Scripts\python.exe -m pip install -r requirements.txt

# Or system Python
python -m pip install -r requirements.txt
```

Key dependencies:
- `pydantic-settings==2.5.2`
- `python-dotenv==1.0.1`
- `fastapi`
- `uvicorn`

#### 5. Verify Import
```powershell
..\.venv\Scripts\python.exe -c "from app.agent.memory import ShortTermMemory, SessionMemory; print('✓ Success!')"
```

---

## Virtual Environment Usage

### Location
The virtual environment is located at `D:\AI_Learning\LLM\.venv` (parent directory of project).

### Activation (if execution policy allows)
```powershell
..\.venv\Scripts\Activate.ps1
```

### Direct Usage (recommended)
```powershell
# Run Python commands
..\.venv\Scripts\python.exe -c "import app"

# Start server
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload

# Or use the provided script
.\start_server.ps1
```

---

## Common Issues

### 1. ModuleNotFoundError: No module named 'pydantic_settings'
**Solution**: Install `pydantic-settings`
```powershell
..\.venv\Scripts\python.exe -m pip install pydantic-settings==2.5.2
```

### 2. ModuleNotFoundError: No module named 'fastapi'
**Solution**: Install all dependencies
```powershell
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. PowerShell Execution Policy Error
**Error**: `Activate.ps1 cannot be loaded because running scripts is disabled`

**Solution**: Use Python directly without activating
```powershell
..\.venv\Scripts\python.exe <your_command>
```

Or temporarily change execution policy (admin required):
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 4. File Corruption Issues
**Symptoms**:
- Editor shows correct content
- `Get-Content` shows empty file
- Import errors

**Solution**:
1. Delete the problematic file
2. Recreate it with correct content
3. Clear Python cache
4. Verify with `Get-Content`

---

## Quick Start Server

### Method 1: Using Start Script (Recommended)
```powershell
cd agentic_ai_artc
.\start_server.ps1
```

### Method 2: Direct Command
```powershell
cd agentic_ai_artc
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

### Method 3: With Activated Environment
```powershell
cd agentic_ai_artc
..\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

---

## Verification Checklist

✅ **All Python cache cleared**
```powershell
Get-ChildItem -Recurse -Filter "__pycache__" | Measure-Object
# Should show 0 items
```

✅ **memory.py file is not empty**
```powershell
(Get-Content app\agent\memory.py).Length -gt 0
```

✅ **Can import ShortTermMemory**
```powershell
..\.venv\Scripts\python.exe -c "from app.agent.memory import ShortTermMemory"
```

✅ **Can load FastAPI app**
```powershell
..\.venv\Scripts\python.exe -c "from app.main import app"
```

✅ **Server starts without errors**
```powershell
.\start_server.ps1
# Should see: "Application startup complete"
```

---

## Maintenance

### Clean Cache Regularly
```powershell
# Create a cleanup script
@"
Get-ChildItem -Recurse -Filter '__pycache__' | Remove-Item -Recurse -Force
Get-ChildItem -Recurse -Filter '*.pyc' | Remove-Item -Force
Write-Host 'Cache cleaned!'
"@ | Out-File clean_cache.ps1
```

### Update Dependencies
```powershell
..\.venv\Scripts\python.exe -m pip install --upgrade -r requirements.txt
```

### Check for Missing Dependencies
```powershell
..\.venv\Scripts\python.exe -m pip check
```

---

## Contact

For persistent issues, check:
1. `design_doc.md` - Project architecture
2. `AGENT_IMPLEMENTATION_SUMMARY.md` - Implementation details
3. `TOOLS_OPTIMIZATION_SUMMARY.md` - Tool specifications
4. `README.md` - General documentation

**Status**: ✅ All issues resolved as of 2025-11-08

