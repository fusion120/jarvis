@echo off
title Jarvis Companion
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python not found. Install it from python.org and tick "Add to PATH".
  pause
  exit /b 1
)
echo Checking dependencies (requests, Pillow, pystray)...
python -c "import requests, PIL, pystray" 2>nul
if errorlevel 1 (
  echo Installing dependencies...
  python -m pip install -r requirements.txt
)
echo Starting Jarvis agent (tray icon lives in the taskbar)...
start "Jarvis Agent" python jarvis_agent.py
timeout /t 3 /nobreak >nul
echo Opening the Companion window...
start "" "http://localhost:8765/companion"
