import os
from typing import Set

import dotenv

dotenv.load_dotenv()

__all__ = [
    "END_DAYS",
    "INTERVAL_SECONDS",
    "ENABLE_RECORD_VIDEO",
    "IS_DISPLAY",
    "PROXY",
    "LOOP_LIMIT",
    "LOOP_THE_KEYWORD",
    "INTO_DEPTH_PAGE_TIMES",
    "PAGES_PER_KEYWORD",
    "TIME_SPENT_ON_EACH_PAGE",
    "BLACKLIST_CONTENT",
    "WHITELIST_CONTENT",
    "TUMBLE_RELATED_KEYWORD",
    "SEARCH_KEYWORDS_ENV",
    "KEYWORD_LIMIT"
]

# ===================================================================
# TIMER
# ===================================================================
# 设定结束时间，防止任务被遗忘后一直运行下去
END_DAYS: int = 3
if (end_days := os.getenv("HANG_AFTER_N_DAYS")) and end_days.isdigit():
    END_DAYS = int(end_days)

# Default to 1onc /10min
INTERVAL_SECONDS: int = 60 * 10
if (interval_seconds := os.getenv("INTERVAL_SECONDS")) and interval_seconds.isdigit():
    seconds_ = int(interval_seconds)

# ===================================================================
# ASYNC_PLAYWRIGHT
# ===================================================================
# 浏览器无头设置
IS_DISPLAY = "DISPLAY" in os.environ

# 浏览器代理
PROXY = None
if proxy_server_ := os.getenv("HTTPS_PROXY"):
    PROXY = {"server": proxy_server_}

# 浏览器是否录屏
ENABLE_RECORD_VIDEO = os.getenv("ENABLE_RECORD_VIDEO")

# ===================================================================
# AgentV
# ===================================================================
# 单字循环任务
LOOP_THE_KEYWORD: str | None = os.getenv("LOOP_THE_KEYWORD")

# 单字循环轮次
_loop_limit = os.getenv("LOOP_LIMIT", 10)
if isinstance(_loop_limit, str) and _loop_limit.isdigit():
    _loop_limit = int(_loop_limit)
else:
    _loop_limit = 10
LOOP_LIMIT: int = _loop_limit

# 每个页面至多点击几个词条（进入多少个深度页面）
INTO_DEPTH_PAGE_TIMES: int = 1
if (pt := os.getenv("INTO_DEPTH_PAGE_TIMES")) and pt.isdigit():
    INTO_DEPTH_PAGE_TIMES = int(pt)

# 每个关键词访问几页
PAGES_PER_KEYWORD = 2
if (revoke := os.getenv("PAGES_PER_KEYWORD")) and revoke.isdigit():
    PAGES_PER_KEYWORD = int(revoke)

# 每个页面至少停留的时间（ms）
TIME_SPENT_ON_EACH_PAGE = 6000
if (ts := os.getenv("TIME_SPENT_ON_EACH_PAGE")) and ts.isdigit():
    TIME_SPENT_ON_EACH_PAGE = int(ts)

# 拒绝点入body包含如下关键词的页面
BLACKLIST_CONTENT: Set[str] = {"知乎", "倒闭", "暴跌", "广告", "美女", "公务员"}
if bc := os.getenv("BLACKLIST_CONTENT"):
    bc = set([i.strip() for i in bc.strip().split(",")])
    BLACKLIST_CONTENT.update(bc)

# 拒绝点入body不含如下关键词的页面（全文匹配）
WHITELIST_CONTENT: Set[str] = {"资产"}
if trk := os.getenv("TUMBLE_RELATED_KEYWORD"):
    trk = set([i.strip() for i in trk.strip().split(",")])
    WHITELIST_CONTENT.update(trk)

# 关注的轮动主体词
TUMBLE_RELATED_KEYWORD: str | None = os.getenv("TUMBLE_RELATED_KEYWORD")

# ===================================================================
# UTILS
# ===================================================================

# 覆盖掉 keywords.txt 优先级更高的检索词列表，以英文半角逗号分开，不需要空格
SEARCH_KEYWORDS_ENV: str | None = os.getenv("SEARCH_KEYWORDS", "")

# 一共阅览多少个关键词，可选项 Literal["all", "0 < IsDigit < Max"]
KEYWORD_LIMIT: str | None = os.getenv("KEYWORD_LIMIT")
