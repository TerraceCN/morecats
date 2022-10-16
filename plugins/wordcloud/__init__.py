# -*- coding: utf-8 -*-
import os
import re
from datetime import datetime, timedelta
from typing import List, Set
from collections import Counter
from io import BytesIO

from nonebot import get_driver, on_message
from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment, GROUP_ADMIN
from nonebot.params import EventPlainText
from nonebot.utils import run_sync
from sqlalchemy import select, and_, between
import jieba
import wordcloud

from .database import MessageTable, metadata
from ..db import db, engine

driver = get_driver()

stopword_list: Set[str] = set()


@driver.on_startup
async def initialize():
    metadata.create_all(engine)
    stopword_dir = os.path.join(os.path.dirname(__file__), "stopwords")
    for i in os.listdir(stopword_dir):
        if not i.endswith(".txt"):
            continue
        with open(os.path.join(stopword_dir, i), 'r', encoding='utf-8') as file:
            for word in file.readlines():
                stopword_list.add(word.strip())
    jieba.initialize()


def has_text(event: MessageEvent) -> bool:
    segment: MessageSegment
    for segment in event.get_message():
        if segment.type == "text":
            return True
    return False


def query_rule(event: MessageEvent) -> bool:
    for prefix in driver.config.command_start:
        if event.get_plaintext().startswith(f"{prefix}今日成分"):
            return True
        elif event.get_plaintext().startswith(f"{prefix}昨日成分"):
            return True
    return False


matcher = on_message(rule=has_text, priority=2)
query = on_message(rule=query_rule, priority=1, block=True, permission=GROUP_ADMIN)


@matcher.handle()
async def handle_text(event: MessageEvent, text: str = EventPlainText()):
    session_id = event.get_session_id()
    user_id = event.get_user_id()

    await db.execute(MessageTable.insert().values(
        group_id=session_id.split("_")[1] if session_id != user_id else None,
        user_id=user_id,
        time=datetime.fromtimestamp(event.time),
        text=text,
    ))


@run_sync
def generate_wordcloud(texts: List[str]) -> BytesIO:
    words: List[str] = []
    for text in texts:
        for word in jieba.cut(text, HMM=True):
            w = word.strip()
            if w and w in stopword_list:
                continue
            words.append(w)
    word_counter = Counter(words)
    wc = wordcloud.WordCloud(
        width=1000,
        height=700,
        background_color="white",
        font_path=os.path.join(os.path.dirname(__file__), "msyh.ttc")
    )
    word_len = len(words)
    wc_image = wc.generate_from_frequencies({day: v / word_len for day,v in word_counter.items()})
    bio = BytesIO()
    wc_image.to_image().save(bio, format="PNG")
    bio.seek(0)
    return bio


@query.handle()
async def handle_query(event: MessageEvent):
    message = event.get_message()

    session_id = event.get_session_id()
    user_id = event.get_user_id()
    group_id = session_id.split("_")[1] if session_id != user_id else None

    if group_id is None:
        return await query.finish("请在群聊中使用本功能")


    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)

    if re.search(r"今日成分", event.get_plaintext()) is not None:
        pass
    elif re.search(r"昨日成分", event.get_plaintext()) is not None:
        start_date = start_date - timedelta(days=1)
        end_date = end_date - timedelta(days=1)
    else:
        pass

    if len(message) == 1:
        if event.to_me:
            return await query.finish("无法查询机器人的成分")
        else:
            conditions = and_(
                MessageTable.c.group_id == group_id,
                between(MessageTable.c.time, start_date, end_date),
            )
    elif len(message) == 2 and message[1].type == "at":
        conditions = and_(
            MessageTable.c.group_id == group_id,
            MessageTable.c.user_id == message[1].data["qq"],
            between(MessageTable.c.time, start_date, end_date),
        )
    else:
        return await query.finish("参数错误")

    texts = await db.fetch_all(
        select(MessageTable.c.text).where(conditions)
    )
    
    if len(texts) == 0:
        return await query.finish("没有找到相关消息")
    
    image = await generate_wordcloud([text.text for text in texts])
    await query.finish(MessageSegment.image(image))
