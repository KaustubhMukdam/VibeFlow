import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
import os

load_dotenv()
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="Asia/Kolkata")


def _daily_recommendation_job():
    """Runs at 8:00 AM IST every day."""
    logger.info("Running daily recommendation job...")
    try:
        from models.hybrid import get_daily_recommendation
        result = get_daily_recommendation()
        if result:
            logger.info(f"Daily pick: {result['title']} by {result['artist']}")
        else:
            logger.warning("No daily recommendation generated")
    except Exception as e:
        logger.error(f"Daily job failed: {e}", exc_info=True)


def _weekend_playlist_job():
    """Runs at 7:00 PM IST every Friday."""
    logger.info("Running weekend playlist job...")
    try:
        from models.weekend_playlist import generate_weekend_playlist
        playlist = generate_weekend_playlist()
        logger.info(f"Weekend playlist: {len(playlist)} songs")
    except Exception as e:
        logger.error(f"Weekend playlist job failed: {e}", exc_info=True)


def _retrain_als_job():
    """Retrains ALS + LSTM models weekly (Sunday midnight) as history grows."""
    logger.info("Retraining models...")
    try:
        from models.collaborative import train_als
        train_als()
        logger.info("ALS model retrained")
    except Exception as e:
        logger.error(f"ALS retrain failed: {e}", exc_info=True)

    try:
        from models.sequential import train_sequential
        success = train_sequential()
        if success:
            logger.info("LSTM sequential model retrained")
        else:
            logger.info("LSTM training skipped (insufficient sessions)")
    except Exception as e:
        logger.error(f"LSTM retrain failed: {e}", exc_info=True)


def start_scheduler():
    daily_time   = os.getenv("DAILY_REC_TIME", "08:00").split(":")
    weekend_time = os.getenv("WEEKEND_PLAYLIST_TIME", "19:00").split(":")

    scheduler.add_job(
        _daily_recommendation_job,
        CronTrigger(hour=int(daily_time[0]), minute=int(daily_time[1])),
        id="daily_recommendation",
        replace_existing=True,
    )
    scheduler.add_job(
        _weekend_playlist_job,
        CronTrigger(day_of_week="fri",
                    hour=int(weekend_time[0]),
                    minute=int(weekend_time[1])),
        id="weekend_playlist",
        replace_existing=True,
    )
    scheduler.add_job(
        _retrain_als_job,
        CronTrigger(day_of_week="sun", hour=0, minute=0),
        id="als_retrain",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started — daily @ 08:00 IST | weekend playlist @ Fri 19:00 IST")
    return scheduler


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
