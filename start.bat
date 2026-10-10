@echo off
title Persian Market News Dashboard
cd /d "%~dp0"
echo ==========================================
echo   داشبورد خبری بازار - کریپتو، طلا و نقره
echo ==========================================
echo.
if not exist ".venv\Scripts\python.exe" (
    echo [setup] creating virtual environment...
    python -m venv .venv
    .venv\Scripts\python -m pip install --quiet --upgrade pip
    .venv\Scripts\python -m pip install --quiet -r requirements.txt
)
echo Starting dashboard on http://localhost:5055 ...
echo (first cycle takes about a minute: 194 sources + translation + reports)
start "" http://localhost:5055
.venv\Scripts\python app.py --port 5055
pause
