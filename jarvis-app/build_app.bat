@echo off
setlocal
set ROOT=%~dp0..
cd /d "%ROOT%"
echo.
echo === Jarvis - Windows app build ===
echo Building from: %cd%
echo.

REM Prefer the repo venv so requests/robot_bridge/pywebview are all present.
set "PY=python"
if exist "backend\.venv\Scripts\python.exe" set "PY=backend\.venv\Scripts\python.exe"
%PY% --version

%PY% -c "import PyInstaller" >nul 2>nul || (echo Installing PyInstaller... & %PY% -m pip install --quiet pyinstaller)
%PY% -c "import webview" >nul 2>nul || (echo Installing pywebview... & %PY% -m pip install --quiet pywebview)

echo.
echo [1/4] Building the desktop agent (agent.exe)...
%PY% -m PyInstaller --noconfirm --clean --noconsole ^
  --distpath dist\Jarvis\agent --workpath build\agent ^
  --name agent --paths agent ^
  agent\jarvis_agent.py
if errorlevel 1 exit /b 1

echo.
echo [2/4] Copying companion page, config, extension and app page...
copy /y agent\companion.html dist\Jarvis\agent\companion.html >nul
if exist agent\agent_config.json copy /y agent\agent_config.json dist\Jarvis\agent\agent_config.json >nul
if not exist dist\Jarvis\extension mkdir dist\Jarvis\extension
xcopy /e /i /y extension dist\Jarvis\extension >nul
copy /y jarvis-app\app.html dist\Jarvis\app.html >nul

echo.
echo [3/4] Building the launcher (Jarvis.exe)...
%PY% -m PyInstaller --noconfirm --clean --noconsole ^
  --distpath dist\Jarvis --workpath build\main ^
  --name Jarvis ^
  jarvis-app\main.py
if errorlevel 1 exit /b 1

echo.
echo [4/4] Zipping for download...
powershell -NoProfile -Command "Compress-Archive -Path 'dist\Jarvis' -DestinationPath 'dist\Jarvis.zip' -Force"
if errorlevel 1 echo (zip skipped - dist\Jarvis\ is ready to copy)

echo.
echo === Done ===
echo   Run: dist\Jarvis\Jarvis.exe
echo   Zip: dist\Jarvis.zip
echo.
endlocal
