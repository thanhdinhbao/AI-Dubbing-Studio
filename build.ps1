# =====================================================================
# AI Dubbing Studio - Windows PowerShell Build Script
# =====================================================================

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "   BUILDING AI DUBBING STUDIO WINDOWS EXECUTABLE      " -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

# 1. Check Python
$pythonVer = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Python is not installed or not in PATH." -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Detected: $pythonVer" -ForegroundColor Green

# 2. Check FFmpeg
$ffmpegVer = ffmpeg -version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARNING] FFmpeg not found in PATH. Make sure FFmpeg is installed or bundled." -ForegroundColor Yellow
} else {
    Write-Host "[OK] Detected FFmpeg" -ForegroundColor Green
}

# 3. Check / Install dependencies
Write-Host "[INFO] Checking dependencies from requirements.txt..." -ForegroundColor Cyan
pip install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to install requirements." -ForegroundColor Red
    exit 1
}

# 4. Run Core Tests
Write-Host "[INFO] Running automated test suite before packaging..." -ForegroundColor Cyan
pytest -v
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Tests failed! Aborting build to ensure package stability." -ForegroundColor Red
    exit 1
}
Write-Host "[OK] All unit and integration tests passed successfully." -ForegroundColor Green

# 5. Clean Previous Builds
Write-Host "[INFO] Cleaning previous dist and build folders..." -ForegroundColor Cyan
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }

# 6. Execute PyInstaller Build
Write-Host "[INFO] Building onedir executable with PyInstaller..." -ForegroundColor Cyan
pyinstaller --clean pyinstaller.spec

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] PyInstaller build failed with exit code $LASTEXITCODE." -ForegroundColor Red
    exit $LASTEXITCODE
}

$exePath = "dist\AIDubbingStudio\AIDubbingStudio.exe"
if (Test-Path $exePath) {
    Write-Host "=====================================================" -ForegroundColor Green
    Write-Host "   BUILD SUCCESSFUL!                                 " -ForegroundColor Green
    Write-Host "   Executable location: $exePath                     " -ForegroundColor Green
    Write-Host "=====================================================" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Build finished but executable was not found at $exePath" -ForegroundColor Red
    exit 1
}

