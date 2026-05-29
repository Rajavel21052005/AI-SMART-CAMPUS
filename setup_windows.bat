@echo off
REM ============================================================
REM Smart Campus AI System — Windows Setup Script
REM Run this once after extracting the project.
REM Usage: Double-click or run from Command Prompt as Admin
REM ============================================================

echo.
echo ============================================================
echo   Smart Campus AI System — Windows Setup
echo ============================================================
echo.

REM Check Python version
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo ERROR: Python not found. Install Python 3.12+ from python.org
    pause & exit /b 1
)

REM Create virtual environment
echo [1/6] Creating virtual environment...
python -m venv venv
IF ERRORLEVEL 1 (echo ERROR: venv creation failed & pause & exit /b 1)

REM Activate venv
echo [2/6] Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo [3/6] Upgrading pip...
python -m pip install --upgrade pip

REM Install requirements
echo [4/6] Installing dependencies (this may take 5-10 minutes)...
pip install -r requirements.txt
IF ERRORLEVEL 1 (
    echo.
    echo TIP: If dlib fails, install CMake first: https://cmake.org/download/
    echo Then run: pip install dlib
    echo.
)

REM Copy .env file
echo [5/6] Creating .env file...
IF NOT EXIST .env (
    copy .env.example .env
    echo .env file created. Please edit it with your MySQL password and email settings.
) ELSE (
    echo .env already exists, skipping.
)

REM Create directories
echo [6/6] Creating required directories...
if not exist logs mkdir logs
if not exist ai_models mkdir ai_models
if not exist app\static\images\uploads mkdir app\static\images\uploads
if not exist app\static\images\security mkdir app\static\images\security

echo.
echo ============================================================
echo   Setup complete!
echo ============================================================
echo.
echo NEXT STEPS:
echo.
echo 1. Install MySQL 8.0 if not already installed:
echo    https://dev.mysql.com/downloads/installer/
echo.
echo 2. Open MySQL and create the database:
echo    CREATE DATABASE smart_campus_db CHARACTER SET utf8mb4;
echo.
echo 3. Edit .env and set your DB_PASSWORD and SECRET_KEY
echo.
echo 4. Initialize the database:
echo    flask init-db
echo.
echo 5. Seed demo data (optional):
echo    python database/seed_data.py
echo.
echo 6. Run the application:
echo    python run.py
echo.
echo 7. Open browser: http://localhost:5000
echo    Admin login:   admin / Admin@1234
echo.
pause
