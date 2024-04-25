# -*- coding: utf-8 -*-
# Time       : 2024/4/20 19:32
# Author     : QIN2DIM
# GitHub     : https://github.com/QIN2DIM
# Description:
import os
import random
import sys
from contextlib import suppress
from pathlib import Path
from typing import Set

import dotenv
from loguru import logger

__all__ = ["KEYWORDS", "init_log"]

dotenv.load_dotenv()


def init_log(**sink_channel):
    event_logger_format = "<g>{time:YYYY-MM-DD HH:mm:ss}</g> | <lvl>{level}</lvl> - {message}"
    persistent_format = (
        "<g>{time:YYYY-MM-DD HH:mm:ss}</g> | "
        "<lvl>{level}</lvl>    | "
        "<c><u>{name}</u></c>:{function}:{line} | "
        "{message} - "
        "{extra}"
    )
    serialize_format = event_logger_format + " - {extra}"
    logger.remove()
    logger.add(
        sink=sys.stdout, colorize=True, level="DEBUG", format=serialize_format, diagnose=False
    )
    if sink_channel.get("error"):
        logger.add(
            sink=sink_channel.get("error"),
            level="ERROR",
            rotation="1 week",
            encoding="utf8",
            diagnose=False,
            format=persistent_format,
        )
    if sink_channel.get("runtime"):
        logger.add(
            sink=sink_channel.get("runtime"),
            level="DEBUG",
            rotation="20 MB",
            retention="20 days",
            encoding="utf8",
            diagnose=False,
            format=persistent_format,
        )
    if sink_channel.get("serialize"):
        logger.add(
            sink=sink_channel.get("serialize"),
            level="DEBUG",
            format=persistent_format,
            encoding="utf8",
            diagnose=False,
            serialize=True,
        )
    return logger


def load_keywords(fp: Path = Path("./keywords.txt")) -> Set[str] | None:
    if kws_env := os.getenv("SEARCH_KEYWORDS", ""):
        kws_list = kws_env.strip().split(",")
    elif fp.is_file():
        kws_list = fp.read_text(encoding="utf8").strip().split("\n")
    else:
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text("", encoding="utf8")
        return

    kws_list = [i.strip() for i in kws_list]
    random.shuffle(kws_list)

    qs_ = len(kws_list)
    with suppress(Exception):
        if qsize := os.getenv("KEYWORD_LIMIT"):
            if qsize != "all" and qsize.isdigit():
                if 0 < (qsize_int := int(qsize)) < len(kws_list) + 1:
                    qs_ = qsize_int

    kws_list = kws_list[:qs_]
    kws = set(kws_list)

    return kws


if not (KEYWORDS := load_keywords()):
    logger.info("No keywords")
    sys.exit()
 