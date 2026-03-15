@echo off
REM Diamond Fincorp Loan Management System - Quick Start Script (Windows)

echo ============================================================
echo      DIAMOND FINCORP LOAN MANAGEMENT SYSTEM
echo                  Quick Start Script
echo ============================================================
echo.

REM Check Python installation
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [X] Python is not installed. Please install Python 3.8 or higher.
    pause
    exit /b 1
)
echo [OK] Python found

REM Install dependencies
echo.
echo [2/5] Installing Python dependencies...
cd backend
pip install -r requirements.txt --quiet --disable-pip-version-check
if errorlevel 1 (
    echo [X] Failed to install dependencies
    pause
    exit /b 1
)
echo [OK] Dependencies installed successfully
cd ..

REM Check database
echo.
echo [3/5] Checking database...
if exist "excel_schema\LoanManagement_DB.xlsx" (
    echo [OK] Database found: excel_schema\LoanManagement_DB.xlsx
) else (
    echo [!] Database not found. Creating new database...
    cd excel_schema
    python create_database.py
    cd ..
)

REM Create directories
echo.
echo [4/5] Setting up directories...
if not exist "excel_schema\backups" mkdir excel_schema\backups
if not exist "logs" mkdir logs
echo [OK] Directories created

REM Start server
echo.
echo [5/5] Starting backend server...
echo.
echo ============================================================
echo STARTING APPLICATION
echo ============================================================
echo.
echo Backend API will start on: http://localhost:8000
echo API Documentation: http://localhost:8000/docs
echo.
echo To open the frontend, open this file in your browser:
echo frontend\index.html
echo.
echo Press Ctrl+C to stop the server
echo.
echo ============================================================
echo.

REM Set environment variable
set EXCEL_DB_PATH=%CD%\excel_schema\LoanManagement_DB.xlsx

REM Start server
cd backend
python main.py
