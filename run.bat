@echo off
title Jarvis Lite: The Windows Assistant
cd /d "%~dp0"

echo ========================================================
echo       Starting Jarvis Lite: The Windows Assistant
echo ========================================================

set "PY_EXE="
if exist "venv\Scripts\python.exe" set "PY_EXE=venv\Scripts\python.exe"
if not defined PY_EXE if exist ".venv\Scripts\python.exe" set "PY_EXE=.venv\Scripts\python.exe"

if not defined PY_EXE (
    echo [ERROR] Virtual environment 'venv' or '.venv' not found.
    echo Please make sure the venv is created.
    pause
    exit /b 1
)

:: Launch assistant using project virtual environment
%PY_EXE% main.py %*

if %ERRORLEVEL% neq 0 (
    echo.
    echo Assistant exited with error code %ERRORLEVEL%.
    pause
)
