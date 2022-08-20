# -*- coding: utf-8 -*-
from typing import Optional
from pydantic import BaseModel, Extra


class Config(BaseModel, extra=Extra.ignore):
    cat_image_dir: Optional[str]
