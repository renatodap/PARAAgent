@echo off
REM Setup script for Windows

echo Setting up PARA Autopilot Backend...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH. Please install Python 3.11+
    exit /b 1
)

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Create .env from example if it doesn't exist
if not exist .env (
    echo Creating .env file from example...
    copy ..\..env.example .env
    echo Please edit .env with your actual credentials
)

echo.
echo Setup complete!
echo.
echo Next steps:
echo 1. Edit .env with your API keys and credentials
echo 2. Run the SQL schema in backend/schema.sql in your Supabase project
echo 3. Start the server: uvicorn main:app --reload
echo.
pause
