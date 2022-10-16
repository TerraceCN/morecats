# -*- coding: utf-8 -*-
import sqlalchemy as sa

metadata = sa.MetaData()

MessageTable = sa.Table(
    "worldcloud_message", metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("group_id", sa.String(32), index=True, nullable=True, comment="群号"),
    sa.Column("user_id", sa.String(32), index=True, nullable=False, comment="用户id"),
    sa.Column("time", sa.DateTime, nullable=False, comment="时间"),
    sa.Column("text", sa.Text, nullable=False, comment="文字内容"),
)
