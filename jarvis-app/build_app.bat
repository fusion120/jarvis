@echo off
cd /d %~dp0..
set "PY=python"
if exist "backend\.venv\Scripts\python.exe" set "PY=backend\.venv\Scripts\python.exe"
echo j11 app build (python: %PY%)
%PY% jarvis-app\build_app.py
if errorlevel 1 (
  echo.
  echo Build failed - see the errors above.
  pause
)
