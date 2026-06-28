@echo off
title GLRMS — Django Web Server
echo ============================================================
echo  GLRMS Government Land Monitoring System — Web Server
echo ============================================================
echo.
echo  Access at: http://127.0.0.1:8000/
echo  Login:     http://127.0.0.1:8000/login/
echo  Admin:     http://127.0.0.1:8000/dashboard/admin/
echo.
cd /d "%~dp0"

REM Try outer venv first (user's activated environment)
IF EXIST "..\venv\Scripts\activate.bat" (
    call ..\venv\Scripts\activate.bat
) ELSE IF EXIST "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

python manage.py runserver 0.0.0.0:8000
pause
