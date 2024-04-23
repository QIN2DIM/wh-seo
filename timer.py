import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from main import main as run_task

logging.basicConfig(
    level=logging.INFO, stream=sys.stdout, format="%(asctime)s - %(levelname)s - %(message)s"
)


async def main():
    scheduler = AsyncIOScheduler()

    now_ = datetime.now(timezone(timedelta(hours=8)))

    # 设定结束时间，防止任务被遗忘后一直运行下去
    end_date_ = now_ + timedelta(days=30)

    # Default to 1onc /10min
    seconds_ = 60 * 10
    if (interval_seconds := os.getenv("INTERVAL_SECONDS")) and interval_seconds.isdigit():
        seconds_ = int(interval_seconds)

    trigger = IntervalTrigger(seconds=seconds_, end_date=end_date_)

    scheduler.add_job(run_task, trigger=trigger, kwargs={"headless": False}, max_instances=2, next_run_time=now_)

    try:
        scheduler.start()
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


if __name__ == '__main__':
    asyncio.run(main())
