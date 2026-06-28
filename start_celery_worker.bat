@echo off
title GLRMS — Celery Worker
echo ============================================================
echo  GLRMS — Celery Worker (Background Task Processor)
echo ============================================================
cd /d "%~dp0"

IF EXIST "..\venv\Scripts\activate.bat" (
    call ..\venv\Scripts\activate.bat
) ELSE IF EXIST "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

echo Starting Celery worker...
python -m celery -A glrms worker --loglevel=info --concurrency=2 -P solo
pause
