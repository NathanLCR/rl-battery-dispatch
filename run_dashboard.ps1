Set-Location $PSScriptRoot
Write-Host ""
Write-Host "GreineQ Dashboard" -ForegroundColor Cyan
Write-Host "==================" -ForegroundColor Cyan
Write-Host ""

try {
    python --version | Out-Null
} catch {
    Write-Host "ERROR: Python not found in PATH." -ForegroundColor Red
    exit 1
}

$existing = Get-NetTCPConnection -LocalPort 8501 -State Listen -ErrorAction SilentlyContinue
foreach ($conn in $existing) {
    Write-Host "Stopping existing server on port 8501 (PID $($conn.OwningProcess))..."
    Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
}

Write-Host "Starting server at http://localhost:8501"
Write-Host "Keep this window open. Press Ctrl+C to stop.`n"
Start-Job { Start-Sleep -Seconds 3; Start-Process "http://localhost:8501" } | Out-Null
python -m streamlit run dashboard\app.py
