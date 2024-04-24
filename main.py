from __future__ import annotations

import asyncio
import random
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import dotenv
from playwright.async_api import async_playwright
from muk.const import IS_DISPLAY, PROXY, ENABLE_RECORD_VIDEO, LOOP_THE_KEYWORD, LOOP_LIMIT
from muk import Malenia, AgentV
from utils import KEYWORDS, init_log

dotenv.load_dotenv()

init_log(
    runtime=Path("tmp_dir/logs/{time:YYYY-MM-DD-HH-mm-ss}/runtime.log"),
    error=Path("tmp_dir/logs/{time:YYYY-MM-DD-HH-mm-ss}/error.log"),
    serialize=Path("tmp_dir/logs/{time:YYYY-MM-DD-HH-mm-ss}/serialize.log"),
)


async def shuffle_devices():
    device_list = [
        "iPhone 13",
        "iPhone 13 Pro",
        "iPhone 13 Pro Max",
        "iPhone 14",
        "iPhone 14 Plus",
        "iPhone 14 Pro",
        "iPhone 14 Pro Max",
        "Desktop Firefox",
        "Desktop Edge",
        "Desktop Chrome",
        "Desktop Safari",
    ]
    random.shuffle(device_list)
    return device_list[-1]


async def main(headless: bool = False):
    if "linux" in sys.platform and not IS_DISPLAY:
        headless = True

    fmt = "%Y-%d-%m-%H-%M-%S"
    now_ = datetime.now(timezone(timedelta(hours=8))).strftime(fmt)

    record_video_dir = None
    if ENABLE_RECORD_VIDEO:
        record_video_dir = Path(f"tmp_dir/record_videos/{now_}")

    kw = LOOP_THE_KEYWORD

    async with async_playwright() as p:
        # shuffled_device = p.devices[shuffle_devices()]
        # browser = await p.chromium.launch(headless=headless, proxy=proxy)
        # context = await browser.new_context(**shuffled_device, locale="zh-CN", record_video_dir=record_video_dir)
        browser = await p.chromium.launch(headless=headless, proxy=PROXY)
        context = await browser.new_context(locale="zh-CN", record_video_dir=record_video_dir)
        await Malenia.apply_stealth(context)

        page = await context.new_page()
        agent = AgentV.into_solver(page, tmp_dir=Path("tmp_dir"))

        if isinstance(kw, str):
            await agent.loop_one_search(keyword=kw, limit=LOOP_LIMIT)
        else:
            await agent.wait_for_search(keywords=KEYWORDS)
            await agent.tumble_related_questions(step=3)

        await context.close()


if __name__ == "__main__":
    encrypted_resp = asyncio.run(main(headless=False))
