"""Scheduler for running market analysis at fixed times"""
import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from test_integrated_analysis import run_integrated_analysis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_market_analysis():
    """Run the market analysis task"""
    try:
        logger.info(f"Running scheduled market analysis at {datetime.now()}")
        success, result = await run_integrated_analysis()

        if success:
            logger.info("✅ Market analysis completed successfully")
            if isinstance(result, dict):
                logger.info(f"Analysis content:\n{result['analysis']}")
        else:
            logger.error(f"❌ Market analysis failed: {result}")
    except Exception as e:
        logger.error(f"❌ Error in market analysis: {str(e)}")

async def main():
    """Main scheduler function"""
    try:
        scheduler = AsyncIOScheduler()
        central_tz = pytz.timezone('America/Chicago')

        # Schedule for 9 AM CST
        scheduler.add_job(
            run_market_analysis,
            CronTrigger(hour=9, minute=0, timezone=central_tz),
            name='morning_analysis'
        )

        # Schedule for 6 PM CST
        scheduler.add_job(
            run_market_analysis,
            CronTrigger(hour=18, minute=0, timezone=central_tz),
            name='evening_analysis'
        )

        scheduler.start()
        logger.info("✅ Market analysis scheduler started")
        logger.info("Scheduled times (CST):")
        logger.info("- Morning analysis: 9:00 AM")
        logger.info("- Evening analysis: 6:00 PM")

        # Keep the script running
        while True:
            await asyncio.sleep(60)

    except KeyboardInterrupt:
        logger.info("👋 Scheduler stopped by user")
    except Exception as e:
        logger.error(f"❌ Scheduler error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())