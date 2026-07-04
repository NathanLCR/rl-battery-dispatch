@echo off
cd /d "%~dp0"
echo.
echo  GreineGrid_Qagent Dashboard
echo  ====================
echo  Starting server... browser will open at http://localhost:8501
echo  Press Ctrl+C in this window to stop.
echo.
start "" cmd /c "timeout /t 4 /nobreak >nul && start http://localhost:8501"
python -m streamlit run dashboard\app.py
if errorlevel 1 (
    echo.
    echo  Failed to start. Try: pip install -r requirements.txt
    pause
)
