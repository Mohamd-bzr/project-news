@echo off
REM MOHMD NEWS — one-click GitHub push
REM Double-click me. The first time, a browser window opens for the
REM one-time GitHub login (Git Credential Manager); after that it just pushes.
cd /d "%~dp0"
echo.
echo === MOHMD NEWS — push to GitHub ===
echo.
git remote -v | findstr origin >nul 2>&1
if errorlevel 1 (
    echo No remote configured yet.
    set /p REPO="Paste your repo URL (https://github.com/USER/mohmd-news.git): "
    git remote add origin %REPO%
)
git push -u origin main
echo.
pause
