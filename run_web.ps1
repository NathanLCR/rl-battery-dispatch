# Start GréineQ Web Twin (FastAPI) on http://localhost:8080
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$existing = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Port 8080 already in use (PID $($existing.OwningProcess)). Open http://localhost:8080"
    Start-Process "http://localhost:8080"
    exit 0
}

Write-Host "Starting GréineQ Web Twin at http://localhost:8080"
Start-Job { Start-Sleep -Seconds 2; Start-Process "http://localhost:8080" } | Out-Null
python -m uvicorn webapp.main:app --host 127.0.0.1 --port 8080 --reload
