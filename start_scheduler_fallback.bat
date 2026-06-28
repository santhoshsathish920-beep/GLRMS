@echo off
title GLRMS — APScheduler Fallback (No Redis Needed)
echo ============================================================
echo  GLRMS — Background Scheduler (APScheduler Fallback)
echo  Use this if Redis is NOT installed on this machine.
echo  Monitoring scan runs every 6 hours automatically.
echo ============================================================
cd /d "%~dp0"
call venv\Scripts\activate.bat
pip install apscheduler --quiet
echo.
echo Starting APScheduler background monitor...
python scheduler.py
pause
