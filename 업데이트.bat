@echo off
cd /d "%~dp0"
python scripts/update_program.py
if errorlevel 1 (
    echo.
    echo Update failed. Python is required. Please run the installer script.
    pause
)
