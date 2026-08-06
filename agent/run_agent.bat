@echo off
title Jarvis Desktop Agent
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python not found. Install it from python.org and tick "Add to PATH".
  pause
  exit /b 1
)
echo Checking dependencies (requests, Pillow)...
python -c "import requests, PIL" 2>nul
if errorlevel 1 (
  echo Installing dependencies...
  python -m pip install -r requirements.txt
)
python jarvis_agent.py
pause
