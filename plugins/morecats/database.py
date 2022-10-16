# -*- coding: utf-8 -*-
import sqlalchemy as sa

metadata = sa.MetaData()

ImageTable = sa.Table(
    "cat_images", metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("url", sa.String(256), unique=True, nullable=False, comment="url"),
    sa.Column("filename", sa.String(64), unique=True, nullable=False, comment="文件名"),
    sa.Column("nhash", sa.String(64), nullable=True, comment="neural hash"),
    sa.Column("group_id", sa.String(32), index=True, nullable=True, comment="群号"),
    sa.Column("user_id", sa.String(32), index=True, nullable=False, comment="用户id"),
    sa.Column("time", sa.DateTime, nullable=False, comment="时间"),
    sa.Column("count", sa.Integer, nullable=False, default=1, comment="次数"),
)
