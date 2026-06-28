"""
APScheduler-based fallback scheduler.
Use this if you do NOT have Redis/Celery set up.

HOW TO USE:
  In settings.py, set: USE_CELERY = False
  In glrms/__init__.py, import this instead of celery.

Run this file directly:
  python scheduler.py
"""

import os
import sys
import django
import logging

# Setup Django env
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'glrms.settings')
django.setup()

from apscheduler.schedulers.background import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def run_monitoring_job():
    """Job that runs the land monitoring pipeline."""
    from lands.services import run_automated_monitoring
    logger.info('==================================================')
    logger.info('SCHEDULED SCAN: Starting land monitoring...')
    try:
        success = run_automated_monitoring()
        if success:
            logger.info('SCHEDULED SCAN: Completed successfully.')
        else:
            logger.warning('SCHEDULED SCAN: Failed or returned no data.')
    except Exception as e:
        logger.error(f'SCHEDULED SCAN ERROR: {e}')
    logger.info('==================================================')


if __name__ == '__main__':
    scheduler = BlockingScheduler(timezone='Asia/Kolkata')

    # Run every 6 hours
    scheduler.add_job(
        run_monitoring_job,
        trigger=IntervalTrigger(hours=6),
        id='land_monitoring',
        name='Land Monitoring Scan',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )

    logger.info('╔══════════════════════════════════════════╗')
    logger.info('║  GLRMS Background Scheduler Started      ║')
    logger.info('║  Monitoring scan: every 6 hours          ║')
    logger.info('╚══════════════════════════════════════════╝')

    # Run immediately on startup
    run_monitoring_job()

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info('Scheduler stopped.')
