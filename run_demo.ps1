# DKAI System - Demo & Test Runner
Set-Location $PSScriptRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "           DKAI SYSTEM - DEMO & TEST RUNNER" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Start Server
Write-Host "[1/3] Starting AI Backend Test Server (Port 8001)..." -ForegroundColor Yellow
Start-Process -FilePath "cmd.exe" -ArgumentList "/k cd /d `"$PSScriptRoot`" && `"D:\DK_AI\venv\Scripts\python.exe`" ai_server_test.py"

# 2. Wait
Write-Host "[2/3] Waiting for server initialization..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# 3. Open Browser
Write-Host "[3/3] Opening Web Dashboard in browser..." -ForegroundColor Green
Start-Process "http://localhost:8001"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Server is running at http://localhost:8001" -ForegroundColor Cyan
Write-Host "Commands:"
Write-Host "  M -> Launch Mobile App on Chrome (http://localhost:5000)"
Write-Host "  T -> Send a simulated vehicle detection event"
Write-Host "  Q -> Quit"
Write-Host "============================================================" -ForegroundColor Cyan

while ($true) {
    $key = (Read-Host "Choose option (M/T/Q)").Trim().ToUpper()
    if ($key -eq "M") {
        Write-Host "Starting Mobile App on Chrome..." -ForegroundColor Yellow
        Start-Process -FilePath "cmd.exe" -ArgumentList "/k cd /d `"$PSScriptRoot\mobile_flutter`" && flutter run -d chrome --web-port=5000"
    } elseif ($key -eq "T") {
        Write-Host "Sending test trigger..." -ForegroundColor Yellow
        try {
            $resp = Invoke-RestMethod -Uri "http://localhost:8001/api/test/trigger" -Method Post
            Write-Host "Test trigger success: $($resp.message)" -ForegroundColor Green
        } catch {
            Write-Host "Error sending trigger: $_" -ForegroundColor Red
        }
    } elseif ($key -eq "Q") {
        break
    }
}
