@echo off
echo Starting Health Wellness Companion App...
call "%~dp0backend\venv\Scripts\activate.bat"
cd "%~dp0native_app"
python main_window.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo The application crashed or failed to start.
    echo Check crash.log for details.
    pause
)
