# -*- coding: utf-8 -*-
# Time       : 2024/4/20 19:24
# Author     : QIN2DIM
# GitHub     : https://github.com/QIN2DIM
# Description:
import json
import os
import random
import time
from asyncio import Queue
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Set, List, Dict
from venv import logger

from loguru import logger
from playwright.async_api import Page, Response


def _fil_jquery(response_txt: str) -> dict:
    start_index = response_txt.index("{")
    end_index = response_txt.rindex("}")
    json_string = response_txt[start_index : end_index + 1]
    qr_data = json.loads(json_string)
    return qr_data


def _now(fmt: str = "%Y-%m-%d %H:%M:%S"):
    fmt = fmt or "%Y-%m-%d %H:%M:%S"
    return datetime.now(timezone(timedelta(hours=8))).strftime(fmt)


@dataclass
class Suggestion:
    q: str
    p: bool
    g: List[Dict[str, str]]
    slid: str
    queryid: str
    date: str | None = None

    def __post_init__(self):
        self.date = self.date or _now()


@dataclass
class AgentV:
    tmp_dir: Path
    page: Page | None = None

    _keywords: Set[str] = field(default_factory=set)
    sug_queue: Queue[Suggestion] = field(default_factory=Queue)

    _viewed_page_content: Set[str] = field(default_factory=set)
    _into_depth_page_times: int = 1
    _pages_per_keyword: int = 3
    _time_spent_on_each_page: int = 5000

    def __post_init__(self):
        if (pt := os.getenv("INTO_DEPTH_PAGE_TIMES")) and pt.isdigit():
            self._into_depth_page_times = int(pt)
        if (revoke := os.getenv("PAGES_PER_KEYWORD")) and revoke.isdigit():
            self._pages_per_keyword = int(revoke)
        if (ts := os.getenv("TIME_SPENT_ON_EACH_PAGE")) and ts.isdigit():
            self._time_spent_on_each_page = int(ts)

        self.page.on("response", self.task_handler)

    @logger.catch
    async def task_handler(self, response: Response):
        if "www.baidu.com/sugrec" in response.url and response.request.method == "GET":
            response_text = await response.text()
            qr_data = _fil_jquery(response_text)
            if (q := qr_data.get("q")) in self._keywords:
                logger.info(f"query ->> {q}", suggestion=qr_data)
                self.sug_queue.put_nowait(Suggestion(**qr_data))

    @classmethod
    def into_solver(cls, page: Page, tmp_dir: Path = Path("tmp_dir")):
        return cls(page=page, tmp_dir=tmp_dir)

    @staticmethod
    def is_blacklist_content(content: str):
        inv = {"知乎"}
        for i in inv:
            if i in content:
                return True

    async def _recall_keyword(self, kw: str):
        self._this_kw = kw

        await self.page.goto("https://www.baidu.com/")

        input_field = self.page.locator("//input[@id='kw']")
        await input_field.type(kw, delay=50)

        # wait for video captrue
        await self.page.wait_for_timeout(1000)
        await self.page.keyboard.press("Enter")

    async def _fall_into_depth_page(self, is_first_page: bool = True):
        title_tags = self.page.locator("//h3")
        count = await title_tags.count()
        pending_samples = []

        for i in range(count):
            # 防止被投毒
            if is_first_page and i == 0:
                continue
            tag = title_tags.nth(i)
            # 元素在当前视界内
            if await tag.is_visible():
                content = await tag.text_content()
                # 过滤已访问过的链接，过滤异常的追踪器
                if content in self._viewed_page_content or self.is_blacklist_content(content):
                    continue
                self._viewed_page_content.add(content)
                pending_samples.append((tag, content))

        if pending_samples:
            random.shuffle(pending_samples)
            tag, content = pending_samples[0]
            await self.page.wait_for_timeout(random.randint(300, 1000))
            await tag.click(no_wait_after=True)
            await self.page.wait_for_timeout(random.randint(3000, 5000))
            logger.debug("Page jump", content=content, url=self.page.context.pages[-1].url)

    async def _scroll_page(self, revoke):
        t0 = time.perf_counter()

        click_count = 0

        # Let each page stay longer than 5 seconds
        for j in range(2):
            if click_count >= self._into_depth_page_times:
                break
            # Process top-ranked terms
            if revoke != 1 and random.uniform(0, 1) > 0.7:
                click_count += 1
                await self._fall_into_depth_page()
                await self.page.bring_to_front()
            # Move the screen randomly
            for _ in range(random.randint(2, 3)):
                for _ in range(random.randint(3, 8)):
                    await self.page.mouse.wheel(0, 30)
                await self.page.wait_for_timeout(random.choice([500, 600]))
            # Process end-of-page entries
            if click_count < self._into_depth_page_times:
                click_count += 1
                await self._fall_into_depth_page()
                await self.page.bring_to_front()
            if j == 0:
                for _ in range(random.randint(5, 7)):
                    await self.page.mouse.wheel(0, -40)

        # Make the next page button is_visible
        await self.page.bring_to_front()
        await self.page.keyboard.press("End")
        te = time.perf_counter()
        time_left = self._time_spent_on_each_page - ((te - t0) * 1000)
        if time_left > 0:
            await self.page.wait_for_timeout(time_left)

    @logger.catch
    async def _action(self, kw: str, *, revoke: int = 3):
        """once trigger"""
        await self._scroll_page(revoke)

        # Release cache
        if len(self.page.context.pages) > 1:
            for p in self.page.context.pages[1:]:
                await p.close()

        # Claim 3 pages
        if not revoke:
            return

        # Special keywords. The browser has reached the last page
        next_page_btn = self.page.locator("//a[@class='n']").last
        if not await next_page_btn.is_visible():
            return

        # Next page
        await next_page_btn.click()
        await self.page.wait_for_load_state(state="networkidle")

        return await self._action(kw, revoke=revoke - 1)

    async def wait_for_search(self, keywords: Set[str]):
        self._keywords = keywords

        logger.debug("loaded keywords", keywords=keywords)
        logger.debug(
            "Apply configuration",
            PAGES_PER_KEYWORD=self._pages_per_keyword,
            TIME_SPENT_ON_EACH_PAGE=f"{self._time_spent_on_each_page}ms",
        )

        for i, kw in enumerate(keywords):
            logger.debug("Invoke task", progress=f"[{i + 1}/{len(keywords)}]")
            await self._recall_keyword(kw)
            await self._action(kw, revoke=self._pages_per_keyword)

        logger.success("Invoke down", trigger=self.__class__.__name__)
