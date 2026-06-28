import logging

logger = logging.getLogger(__name__)

# Guard against celery not being installed
try:
    from celery import shared_task

    @shared_task(name="lands.tasks.scheduled_land_monitoring")
    def scheduled_land_monitoring():
        """
        Celery task: runs the full automated GEE real-time monitoring scan.
        Scheduled via CELERY_BEAT_SCHEDULE (every 7 days by default).
        """
        logger.info("Celery: Starting scheduled REAL-TIME land monitoring task (GEE)...")
        try:
            from detection.realtime_processor import run_real_time_scan
            results = run_real_time_scan()
            if results.get('status') == 'success':
                logger.info(f"Celery: Scheduled scan completed. Alerts created: {results.get('alerts_created')}")
            else:
                logger.warning(f"Celery: Scheduled scan issue — {results.get('message')}")
        except Exception as e:
            logger.error(f"Celery: Scan error — {e}", exc_info=True)

except ImportError:
    # Celery not installed — define a plain function as a no-op placeholder
    def scheduled_land_monitoring():
        """Fallback no-op when Celery is not installed."""
        logger.warning(
            "Celery is not installed. Run: pip install celery redis\n"
            "Or use 'python scheduler.py' as a fallback."
        )
