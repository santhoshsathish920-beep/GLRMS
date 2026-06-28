@echo off
title GLRMS — Celery Beat Scheduler
echo ============================================================
echo  GLRMS — Celery Beat (Auto Scan every 6 hours)
echo ============================================================
cd /d "%~dp0"

IF EXIST "..\venv\Scripts\activate.bat" (
    call ..\venv\Scripts\activate.bat
) ELSE IF EXIST "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

echo Starting Celery Beat scheduler...
python -m celery -A glrms beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
pause
