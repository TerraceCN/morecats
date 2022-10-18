# -*- coding: utf-8 -*-
import os
import imghdr
from io import BytesIO
from typing import Literal, Tuple

from nonebot import get_driver

from httpx import AsyncClient

from .config import Config

ImageExt = Literal["gif", "jpeg", "png", "bmp"]

driver = get_driver()
conf = Config.parse_obj(driver.config)


async def download_image(url: str) -> Tuple[ImageExt, BytesIO]:
    """
    Read image from url

    :params url: image url
    :return: image extension, BytesIO
    """
    async with AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()

    image = BytesIO(resp.content)
    ext = imghdr.what(image)
    if ext not in ("gif", "jpeg", "png", "bmp"):
        raise ValueError(f"Unsupported image format {ext}")

    image.seek(0)
    return ext, image


def save_image(image: BytesIO, filename: str) -> None:
    """
    Save PIL Image object to file

    :params image: BytesIO
    :params filename: filename
    """
    if not conf.catimage_dir:
        return

    if not os.path.exists(conf.catimage_dir):
        os.makedirs(conf.catimage_dir)
    
    image_path = os.path.join(conf.catimage_dir, filename)
    image.seek(0)
    with open(image_path, "wb") as f:
        f.write(image.read())