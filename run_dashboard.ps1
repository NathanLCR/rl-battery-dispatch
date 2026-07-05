Set-Location $PSScriptRoot
Write-Host ""
Write-Host "GréineQ Dashboard" -ForegroundColor Cyan
Write-Host "Open http://localhost:8501 in your browser after the server starts."
Write-Host "Press Ctrl+C to stop.`n"
Start-Job { Start-Sleep -Seconds 4; Start-Process "http://localhost:8501" } | Out-Null
python -m streamlit run dashboard\app.py
