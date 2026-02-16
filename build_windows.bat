@echo off
REM ============================================
REM ShareLink Extractor - Windows Build Script
REM ============================================
REM 
REM This batch file will build the ShareLink Extractor
REM application into a standalone Windows executable.
REM 
REM Prerequisites:
REM   - Python 3.9 or higher
REM   - pip install -r requirements.txt
REM 
REM Usage:
REM   build_windows.bat         - Build with console (debug)
REM   build_windows.bat release - Build without console (production)
REM ============================================

echo.
echo ============================================
echo ShareLink Extractor - Build Script
echo ============================================
echo.

REM Check Python
python --version
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Install dependencies if needed
echo.
echo Checking dependencies...
pip install -r requirements.txt --quiet

REM Build
if "%1"=="release" (
    echo.
    echo Building RELEASE version...
    python build.py --release
) else (
    echo.
    echo Building DEBUG version...
    python build.py
)

echo.
echo ============================================
echo Build complete!
echo Check the 'dist' folder for the executable.
echo ============================================
echo.
pause
