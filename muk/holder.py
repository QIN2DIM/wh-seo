# -*- coding: utf-8 -*-
# Time       : 2024/4/20 19:24
# Author     : QIN2DIM
# GitHub     : https://github.com/QIN2DIM
# Description:
import json
import random
import time
from asyncio import Queue
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Set, List, Dict
from venv import logger

from loguru import logger
from playwright.async_api import Page, Response, expect

from muk.const import (
    INTO_DEPTH_PAGE_TIMES,
    PAGES_PER_KEYWORD,
    TIME_SPENT_ON_EACH_PAGE,
    BLACKLIST_CONTENT,
    WHITELIST_CONTENT,
    TUMBLE_RELATED_KEYWORD,
)


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
class Sample:
    nth: int
    title_text: str
    content: str


@dataclass
class AgentV:
    tmp_dir: Path
    page: Page | None = None

    blacklist_content: Set[str] = field(default_factory=set)
    whitelist_content: Set[str] = field(default_factory=set)

    _keywords: Set[str] = field(default_factory=set)
    sug_queue: Queue[Suggestion] = field(default_factory=Queue)

    _viewed_page_binder: Set[str] = field(default_factory=set)
    _into_depth_page_times: int = INTO_DEPTH_PAGE_TIMES
    _pages_per_keyword: int = PAGES_PER_KEYWORD
    _time_spent_on_each_page: int = TIME_SPENT_ON_EACH_PAGE
    _tumble_kw: str = "暴跌"

    def __post_init__(self):
        self.blacklist_content = BLACKLIST_CONTENT
        self.whitelist_content = WHITELIST_CONTENT

        self.whitelist_ful = {"进化论"}

        self.page.on("response", self.task_handler)

        logger.debug(
            "Load settings",
            blacklist=self.blacklist_content,
            whitelist=self.whitelist_content,
            wh_ful=self.whitelist_ful,
        )

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

    def is_irrelevant(self, content: str):
        for i in self.blacklist_content:
            if i in content:
                return True

    def is_highly_relevant(self, content: str):
        for k in self.whitelist_content:
            if k in content:
                return True

        clay = "".join(self.whitelist_ful)
        clay = "".join(set(clay))
        for i in clay:
            if i not in content:
                return False

    async def _recall_keyword(self, kw: str, *, tumble: bool = False):
        self._this_kw = kw

        await self.page.goto("https://www.baidu.com/")

        input_field = self.page.locator("//input")

        ful_co = "进化论资产"
        if not kw.startswith(ful_co):
            await input_field.first.type(kw, delay=50)
        else:
            await input_field.first.type(ful_co, delay=50)
            await self.page.wait_for_timeout(1000)
            await input_field.first.type(kw.replace(ful_co, ""), delay=75)

        # wait for video captrue
        await self.page.wait_for_timeout(1000)

        # Click on related suggestion
        await self.page.keyboard.press("Enter")

    async def _tumble_related_questions(self, kw: str, *, selection: str = ""):
        await self.page.goto("https://www.baidu.com/")

        input_field = self.page.locator("//input[@id='kw']")
        await input_field.type(kw, delay=50)

        # wait for video captrue
        await self.page.wait_for_timeout(1000)

        sug_list = self.page.locator("//ul[@id='normalSugSearchUl']//li")
        count = await sug_list.count()
        tumble_id = count - 1

        pending_list = []
        for i in range(count):
            sug_item = sug_list.nth(i)
            related_question = await sug_item.get_attribute("data-key")
            pending_list.append([sug_item, related_question])
            if self._tumble_kw in related_question:
                tumble_id = i + 1
            if (
                selection
                and (selection in related_question)
                and (self._tumble_kw not in related_question)
            ):
                await sug_item.click()
                return

        if 0 < tumble_id <= count - 1:
            return pending_list[tumble_id:]
        return pending_list

    async def _fil_depth_page(self) -> List[Sample]:
        await self.page.wait_for_load_state(state="networkidle")
        title_tags = self.page.locator(
            "//div[@id='content_left']//div[contains(@class, 'result ')]"
        )
        # 当前词条无搜索结果
        await expect(title_tags.first).to_be_visible()
        count = await title_tags.count()
        pending_samples = []

        for i in range(count):
            tag = title_tags.nth(i)
            content = await tag.text_content()
            content = content.strip()
            title = self.page.locator("//h3").nth(i)
            title_text = await title.text_content()
            binder = title_text + content
            # 过滤已访问过的链接
            if binder in self._viewed_page_binder:
                continue
            # [白名单规则优先]过滤不在白名单内的索引
            if self.is_highly_relevant(binder):
                self._viewed_page_binder.add(binder)
                sample = Sample(nth=i, title_text=title_text, content=content)
                pending_samples.append(sample)
                print(f"add sample {title_text}")
                continue
            # [黑名单规则]过滤异常的追踪器
            if self.is_irrelevant(binder):
                continue
            # [无害内容]
            sample = Sample(nth=i, title_text=title_text, content=content)
            pending_samples.append(sample)
            print(f"add sample {title_text}")

        return pending_samples

    async def _is_select_title_visible(self, sample: Sample):
        title = self.page.locator("//h3").nth(sample.nth)
        title_text = await title.text_content()
        if title_text in sample.title_text:
            return True

    async def _drop_depth_page(self, sample: Sample):
        await self.page.wait_for_timeout(random.randint(300, 1000))
        title = self.page.locator("//h3").nth(sample.nth)
        await title.click()
        await self.page.wait_for_timeout(random.randint(3000, 5000))

        logger.debug(
            "Page jump",
            url=self.page.context.pages[-1].url,
            title=sample.title_text,
            content=sample.content,
        )

    async def _scroll_page(self):
        t0 = time.perf_counter()

        pending_samples = await self._fil_depth_page()
        random.shuffle(pending_samples)
        samples = pending_samples[: self._into_depth_page_times]
        print(f"{len(samples)=}")

        for sample in samples:
            while not await self._is_select_title_visible(sample):
                await self.page.wait_for_timeout(random.choice([300, 400]))
                for _ in range(random.randint(1, 2)):
                    await self.page.mouse.wheel(0, 20)
            await self._drop_depth_page(sample)
            await self.page.bring_to_front()
            if len(samples) > 1:
                await self.page.wait_for_timeout(300)
                await self.page.keyboard.press("Home")
            else:
                for _ in range(3):
                    for _ in range(random.randint(3, 5)):
                        await self.page.mouse.wheel(0, 50)
                        await self.page.wait_for_timeout(400)
                    await self.page.wait_for_timeout(random.choice([500, 800]))
                await self.page.wait_for_timeout(1000)

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
        await self._scroll_page()

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

    async def tumble_related_questions(self, kw_: str = "", step: int = 10):
        kw_ = kw_ or TUMBLE_RELATED_KEYWORD
        if not kw_:
            logger.success("Invoke down", reason="Tumble related keywords not set")
            return

        kws = await self._tumble_related_questions(kw_)
        random.shuffle(kws)
        step = min(len(kws), step)
        logger.debug("tumble related questions", kw=kw_, related=[i for i in kws[:step]])

        for sug_item, related_question in kws[:step]:
            logger.debug("Invoke task", selection=related_question)
            await self._tumble_related_questions(kw_, selection=related_question)
            await self._action(related_question, revoke=self._pages_per_keyword)
        logger.success("Invoke down", trigger=self.__class__.__name__)

    async def loop_one_search(self, keyword: str, limit: int = 100):
        self._keywords = {keyword} if isinstance(keyword, str) else keyword
        self._pages_per_keyword = 1
        self._into_depth_page_times = 1

        logger.info("[LOOP] keywords", keywords=self._keywords)
        logger.debug(
            "Apply configuration",
            PAGES_PER_KEYWORD=self._pages_per_keyword,
            TIME_SPENT_ON_EACH_PAGE=f"{self._time_spent_on_each_page}ms",
        )

        for i in range(limit):
            try:
                logger.debug("Loop task", progress=f"[{i + 1}/{limit}]")
                await self._recall_keyword(keyword)
                await self._action(keyword, revoke=self._pages_per_keyword)
                self._viewed_page_binder = set()
            except Exception as err:
                logger.error(err)
                await self.page.wait_for_timeout(3000)
