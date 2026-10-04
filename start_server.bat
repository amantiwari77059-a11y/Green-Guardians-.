@echo off
title Green Guardians Campus Portal - Server
color 0A
cd /d "%~dp0"

echo ================================================================
echo           GREEN GUARDIANS - SWACHH CAMPUS SOCIETY
echo       Frontend, Backend, and Database Launcher
echo ================================================================
echo.
echo [1/3] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo [ERROR] Python is not found in PATH!
    echo Please install Python 3.9+ from https://www.python.org/
    pause
    exit /b 1
)

echo [2/3] Checking dependencies (FastAPI, Uvicorn)...
python -c "import fastapi, uvicorn" >nul 2>&1
if errorlevel 1 (
    echo Installing missing requirements...
    pip install fastapi uvicorn
)

echo [3/3] Starting backend server at http://localhost:8000 ...
echo Database connected: campus.db (SQLite)
echo.
echo Opening browser to http://localhost:8000 ...
start "" "http://localhost:8000"

echo Server is LIVE. Press Ctrl+C in this window to stop.
echo ================================================================
python server.py
pause
