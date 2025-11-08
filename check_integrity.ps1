# File Integrity Check Script
# Checks for empty files and validates Python imports

Write-Host "🔍 Checking File Integrity..." -ForegroundColor Cyan
Write-Host ""

# 1. Check for empty Python files
Write-Host "📁 Checking for empty files..." -ForegroundColor Yellow
$emptyFiles = Get-ChildItem -Recurse -Include *.py -Path app | Where-Object { 
    $_.Length -eq 0 -or (Get-Content $_.FullName -ErrorAction SilentlyContinue | Measure-Object -Line).Lines -eq 0 
}

if ($emptyFiles.Count -eq 0) {
    Write-Host "  ✅ No empty files found" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Found $($emptyFiles.Count) empty file(s):" -ForegroundColor Red
    $emptyFiles | ForEach-Object { Write-Host "    - $($_.FullName)" -ForegroundColor Red }
    exit 1
}

Write-Host ""

# 2. Check critical agent files
Write-Host "📊 Checking agent module files..." -ForegroundColor Yellow
$agentFiles = @(
    @{File="app\agent\core.py"; MinLines=500},
    @{File="app\agent\intent.py"; MinLines=200},
    @{File="app\agent\memory.py"; MinLines=30},
    @{File="app\agent\planning.py"; MinLines=15},
    @{File="app\agent\toolkit.py"; MinLines=30}
)

foreach ($fileInfo in $agentFiles) {
    $lines = (Get-Content $fileInfo.File | Measure-Object -Line).Lines
    $fileName = Split-Path $fileInfo.File -Leaf
    
    if ($lines -ge $fileInfo.MinLines) {
        Write-Host "  ✅ $fileName : $lines lines" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ $fileName : $lines lines (expected >= $($fileInfo.MinLines))" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""

# 3. Test Python imports
Write-Host "🐍 Testing Python imports..." -ForegroundColor Yellow

$venvPython = "..\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    $venvPython = "python"
    Write-Host "  ℹ Using system Python (venv not found)" -ForegroundColor Yellow
}

$testScript = @"
import sys
try:
    from app.agent.intent import Intent, IntentRecognizer
    from app.agent.planning import Step
    from app.agent.memory import ShortTermMemory, SessionMemory
    from app.agent.toolkit import ToolRegistry
    from app.agent.core import Agent
    from app.main import app
    print('SUCCESS')
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
"@

$result = & $venvPython -c $testScript 2>&1
if ($result -match "SUCCESS") {
    Write-Host "  ✅ All modules import successfully" -ForegroundColor Green
} else {
    Write-Host "  ❌ Import failed: $result" -ForegroundColor Red
    exit 1
}

Write-Host ""

# 4. Summary
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "✅ ALL CHECKS PASSED" -ForegroundColor Green -BackgroundColor Black
Write-Host "   - No empty files" -ForegroundColor Green
Write-Host "   - All critical files present and valid" -ForegroundColor Green
Write-Host "   - All Python modules import correctly" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""
Write-Host "🚀 Ready to start server with: .\start_server.ps1" -ForegroundColor Cyan

