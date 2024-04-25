import asyncio
import logging
import sys
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from main import main as run_task
from muk.const import END_DAYS, INTERVAL_SECONDS
from loguru import logger

logging.basicConfig(
    level=logging.INFO, stream=sys.stdout, format="%(asctime)s - %(levelname)s - %(message)s"
)


async def main():
    scheduler = AsyncIOScheduler()

    now_ = datetime.now(timezone(timedelta(hours=8)))
    end_date_ = now_ + timedelta(days=END_DAYS)
    trigger = IntervalTrigger(seconds=INTERVAL_SECONDS, end_date=end_date_)

    scheduler.add_job(
        run_task, trigger=trigger, kwargs={"headless": True}, max_instances=2, next_run_time=now_
    )

    logger.debug(
        "Applying jobs",
        interval=INTERVAL_SECONDS,
        end_date=end_date_.date(),
        next_run_time=now_.date(),
    )

    try:
        scheduler.start()
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
