"""
Scheduler — runs the scraper on a configurable interval using APScheduler.
Default interval: every 15 minutes.
"""
import logging
import os
import signal
import sys

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from scraper.engine import run_scraper

logger = logging.getLogger(__name__)

REFRESH_INTERVAL_MINUTES = int(os.environ.get("NEWSR0_REFRESH_MINUTES", "15"))


def scraper_job():
    logger.info("Scheduled scraper job starting...")
    try:
        run_ids = run_scraper()
        logger.info("Scheduled scraper job complete. Run IDs: %s", run_ids)
    except Exception as exc:
        logger.error("Scheduled scraper job failed: %s", exc, exc_info=True)


def start_scheduler():
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        scraper_job,
        trigger=IntervalTrigger(minutes=REFRESH_INTERVAL_MINUTES),
        id="scraper",
        name="newsR0 scraper",
        replace_existing=True,
        max_instances=1,
    )

    def _shutdown(signum, frame):
        logger.info("Shutdown signal received. Stopping scheduler...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    logger.info(
        "Scheduler started. Scraper will run every %d minutes.", REFRESH_INTERVAL_MINUTES
    )
    # Run once immediately on startup
    scraper_job()
    scheduler.start()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/scraper.log"),
        ],
    )
    start_scheduler()
