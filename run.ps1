# =====================================================================
# AI Dubbing Studio - Run Script (Virtual Environment .venv)
# =====================================================================

Write-Host "Starting AI Dubbing Studio in .venv..." -ForegroundColor Cyan

# Check if .venv exists
if (Test-Path ".venv\Scripts\python.exe") {
    Write-Host "[OK] Using virtual environment .venv (Python + CUDA 12.4)" -ForegroundColor Green
    & ".venv\Scripts\python.exe" main.py
} elseif (Test-Path "dist\AIDubbingStudio\AIDubbingStudio.exe") {
    Write-Host "Running packaged application from dist..." -ForegroundColor Green
    & "dist\AIDubbingStudio\AIDubbingStudio.exe"
} else {
    Write-Host "Running from global Python..." -ForegroundColor Yellow
    python main.py
}


