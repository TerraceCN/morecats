# -*- coding: utf-8 -*-
from nonebot import get_driver

import sqlalchemy as sa
from databases import Database

from .config import Config

conf = Config.parse_obj(get_driver().config)

db_url = f"sqlite:///{conf.cat_image_sqlite}"

db = Database(db_url)
metadata = sa.MetaData()

ImageTB = sa.Table(
    "images", metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("url", sa.String(256), unique=True, nullable=False, comment="url"),
    sa.Column("filename", sa.String(64), unique=True, nullable=False, comment="文件名"),
    sa.Column("nhash", sa.String(64), nullable=True, comment="neural hash"),
    sa.Column("group_id", sa.String(32), index=True, nullable=True, comment="群号"),
    sa.Column("user_id", sa.String(32), index=True, nullable=False, comment="用户id"),
    sa.Column("time", sa.DateTime, nullable=False, comment="时间"),
    sa.Column("count", sa.Integer, nullable=False, default=1, comment="次数"),
)

engine = sa.create_engine(db_url)
metadata.create_all(engine)
