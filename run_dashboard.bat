@echo off
cd /d "%~dp0"
echo.
echo  GreineQ Dashboard
echo  ====================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python not found. Install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)

for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8501" ^| findstr "LISTENING"') do (
    echo  Stopping existing server on port 8501 ^(PID %%a^)...
    taskkill /F /PID %%a >nul 2>&1
)

echo  Starting server at http://localhost:8501
echo  Keep this window open. Press Ctrl+C to stop.
echo.
start "" cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8501"
python -m streamlit run dashboard\app.py
if errorlevel 1 (
    echo.
    echo  Failed to start. Try:
    echo    pip install -r requirements.txt
    echo    python -m streamlit run dashboard\app.py
    pause
)
