@echo off
setlocal enabledelayedexpansion

echo.
echo ==========================================
echo Cloud File Sharing System - Setup
echo ==========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org
    exit /b 1
)

echo [1/5] Creating virtual environment...
if not exist .venv (
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo Error: Failed to create virtual environment
        exit /b 1
    )
    echo Created .venv
) else (
    echo .venv already exists
)

echo [2/5] Activating virtual environment...
call .venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo Error: Failed to activate virtual environment
    exit /b 1
)

echo [3/5] Installing dependencies...
pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Error: Failed to install dependencies
    exit /b 1
)

echo [4/5] Setting up database...
if not exist cloud.db (
    python create_db.py
    if %errorlevel% neq 0 (
        echo Warning: Database creation had issues, but continuing...
    )
) else (
    echo cloud.db already exists
    echo Running migration to add new columns...
    python migrate_db.py
    if %errorlevel% neq 0 (
        echo Warning: Migration had issues, but continuing...
    )
)

echo [5/5] Checking configuration...
if not exist .env (
    echo Copying .env.example to .env...
    if exist .env.example (
        copy .env.example .env >nul
        echo Created .env file - please edit with your settings
        echo Press Enter to open .env in notepad...
        pause
        notepad .env
    ) else (
        echo Warning: .env.example not found
    )
) else (
    echo .env already exists
)

echo.
echo ==========================================
echo Setup Complete!
echo ==========================================
echo.
echo To start the application, run:
echo   python app.py
echo.
echo Then open your browser to:
echo   http://127.0.0.1:5000
echo.
echo Features:
echo   - File storage up to 1GB
echo   - Auto MIME type detection
echo   - Media duration extraction (audio/video)
echo   - Multi-cloud support (Local, GCS, S3, Azure)
echo   - OTP-based authentication
echo.
echo For more information, see:
echo   - README.md (Quick start and setup)
echo   - FEATURES.md (Detailed features)
echo   - IMPLEMENTATION_SUMMARY.md (What's new)
echo.
pause
