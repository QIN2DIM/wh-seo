from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import dotenv
from playwright.async_api import async_playwright

from muk import Malenia, AgentV
from utils import KEYWORDS, init_log

dotenv.load_dotenv()

init_log(
    runtime=Path("tmp_dir/logs/{time:YYYY-MM-DD-HH-mm-ss}/runtime.log"),
    error=Path("tmp_dir/logs/{time:YYYY-MM-DD-HH-mm-ss}/error.log"),
    serialize=Path("tmp_dir/logs/{time:YYYY-MM-DD-HH-mm-ss}/serialize.log"),
)


async def main(headless: bool = False):
    if "linux" in sys.platform and "DISPLAY" not in os.environ:
        headless = True

    proxy = None
    if proxy_server := os.getenv("HTTPS_PROXY"):
        proxy = {"server": proxy_server}

    fmt = "%Y-%d-%m-%H-%M-%S"
    now_ = datetime.now(timezone(timedelta(hours=8))).strftime(fmt)
    record_video_dir = Path(f"tmp_dir/record_videos/{now_}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, proxy=proxy)
        context = await browser.new_context(locale="zh-CN", record_video_dir=record_video_dir)
        await Malenia.apply_stealth(context)

        page = await context.new_page()
        agent = AgentV.into_solver(page, tmp_dir=Path("tmp_dir"))

        await agent.wait_for_search(keywords=KEYWORDS)
        await agent.tumble_related_questions(step=1)

        await context.close()


if __name__ == "__main__":
    encrypted_resp = asyncio.run(main(headless=False))
