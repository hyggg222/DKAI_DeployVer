@echo off
title DKAI Demo Runner
cd /d "%~dp0"

echo ============================================================
echo           DKAI SYSTEM - DEMO & TEST RUNNER
echo ============================================================
echo.
echo [1/3] Starting AI Backend Test Server (Port 8001)...
start "DKAI AI Server" cmd /k "cd /d "%~dp0" && "D:\DK_AI\venv\Scripts\python.exe" ai_server_test.py"

echo [2/3] Waiting for server to initialize...
timeout /t 3 /nobreak >nul

echo [3/3] Opening Web Dashboard in browser...
start http://localhost:8001

echo.
echo ============================================================
echo Server is running at: http://localhost:8001
echo.
echo Options for Mobile App:
echo   1. Press [M] to start Mobile App in Chrome (Web Mode)
echo   2. Press [T] to trigger a simulated Vehicle Event
echo   3. Press [Q] to exit this runner
echo ============================================================

:menu
set /p choice="Select an option (M/T/Q): "
if /i "%choice%"=="M" goto run_mobile
if /i "%choice%"=="T" goto trigger_test
if /i "%choice%"=="Q" goto end
goto menu

:run_mobile
echo.
echo Freeing port 5000 if previously occupied...
powershell -Command "Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"
echo Starting Flutter Mobile App in Chrome on http://localhost:5000...
start "DKAI Mobile App" cmd /k "cd /d "%~dp0mobile_flutter" && flutter run -d chrome --web-port=5000"
goto menu

:trigger_test
echo.
echo Sending test vehicle event trigger...
powershell -Command "try { Invoke-RestMethod -Uri 'http://localhost:8001/api/test/trigger' -Method Post | Out-Null; Write-Host 'Event triggered successfully!' -ForegroundColor Green } catch { Write-Host 'Server not responding yet.' -ForegroundColor Red }"
goto menu

:end
echo Exiting...
