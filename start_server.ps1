# Start Agentic AI Server with Virtual Environment
# This script ensures the correct Python environment is used

Write-Host "🚀 Starting Agentic AI Server..." -ForegroundColor Green

# Use virtual environment Python directly
$venvPython = "..\.venv\Scripts\python.exe"

if (Test-Path $venvPython) {
    Write-Host "✓ Using virtual environment Python" -ForegroundColor Green
    & $venvPython -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
} else {
    Write-Host "⚠ Virtual environment not found, using system Python" -ForegroundColor Yellow
    python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
}

