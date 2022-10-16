# -*- coding: utf-8 -*-
from typing import Optional
from pydantic import BaseModel, Extra


class Config(BaseModel, extra=Extra.ignore):
    catimage_dir: Optional[str]
    