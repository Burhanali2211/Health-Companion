@echo off
REM ═══════════════════════════════════════════════════════════════
REM Health Companion — Windows Client Kiosk Launcher
REM ═══════════════════════════════════════════════════════════════

set CONFIG_FILE=%~dp0.pc_server_config

if not "%~1" == "" (
    set SERVER_IP=%~1
    echo %~1 > "%CONFIG_FILE%"
    echo Saved new server IP: %~1
    goto launch
)

if exist "%CONFIG_FILE%" (
    set /p SERVER_IP=<"%CONFIG_FILE%"
)

REM Clean up any corrupted or empty config values
if "%SERVER_IP%" == "ECHO is off. " set SERVER_IP=
if "%SERVER_IP%" == "ECHO is off." set SERVER_IP=

if "%SERVER_IP%" == "" (
    set /p SERVER_IP="Enter Server IP Address [Default: localhost]: "
)

if "%SERVER_IP%" == "" (
    set SERVER_IP=localhost
)

REM Strip trailing spaces
set SERVER_IP=%SERVER_IP: =%

echo %SERVER_IP% > "%CONFIG_FILE%"

echo ==================================================
echo  Saved Server IP: %SERVER_IP%
echo  To change this, run: .\run_pc_client.bat ^<new_ip^>
echo ==================================================

:launch
echo Launching Health Companion UI connected to http://%SERVER_IP%:8000...
"%~dp0backend\venv\Scripts\python.exe" "%~dp0native_app\main_window.py" --server http://%SERVER_IP%:8000
