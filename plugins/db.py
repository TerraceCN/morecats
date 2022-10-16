# -*- coding: utf-8 -*-
from nonebot import get_driver

import sqlalchemy as sa
from databases import Database

from .config import Config

conf = Config.parse_obj(get_driver().config)

db = Database(conf.db_url)
engine = sa.create_engine(conf.db_url)
