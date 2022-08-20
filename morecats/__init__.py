# -*- coding: utf-8 -*-
import os
import re
import imghdr
import time
from io import BytesIO
from typing import Literal, Tuple

from nonebot import on_message, get_driver
from nonebot.adapters import Event
from nonebot.adapters.onebot.v11 import Bot as OneBotV11Bot
from nonebot.log import logger

import numpy as np
from httpx import AsyncClient
from PIL import Image

from .model import CatOrNot
from .config import Config

conf = Config.parse_obj(get_driver().config)
cat_model = CatOrNot(os.path.join(os.path.dirname(__file__), "resnext50_32x4d.onnx"))

ImageExt = Literal["gif", "jpeg", "png", "bmp"]

matcher = on_message()


async def read_image(url: str) -> Tuple[ImageExt, BytesIO]:
    async with AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()

    image = BytesIO(resp.content)
    ext = imghdr.what(image)
    if ext not in ("gif", "jpeg", "png", "bmp"):
        raise ValueError(f"Unsupported image format {ext}")

    image.seek(0)
    return ext, image


def predict_image(data: BytesIO) -> np.ndarray:
    with Image.open(data) as img:
        prob = cat_model.predict_prob(img.convert("RGB"))
        return prob


def save_image(image: BytesIO, filename: str) -> None:
    if not conf.cat_image_dir:
        return

    if not os.path.exists(conf.cat_image_dir):
        os.makedirs(conf.cat_image_dir)
    
    image_path = os.path.join(conf.cat_image_dir, filename)
    with open(image_path, "wb") as f:
        image.seek(0)
        f.write(image.read())


@matcher.handle()
async def handle_image(event: Event, bot: OneBotV11Bot):
    probs = []
    output_prob = False

    for segment in event.get_message():
        if segment.type == "text":
            if re.match(f"^/cat_prob$", segment.data["text"].strip()):
                output_prob = True
        if segment.type == "image":
            url: str = segment.data["url"]
            filename: str = segment.data["file"]

            try:
                ext, image = await read_image(url)
            except Exception as e:
                logger.error(f"Failed to read image: {e}")
                return
            filename = ".".join(filename.rsplit(".", 1)[:-1] + [ext])

            try:
                stime = time.time()
                prob = predict_image(image)[0]
                etime = time.time()
                probs.append(prob)
            except Exception as e:
                logger.error(f"Failed to predict: {e}")
                probs.append(-1)
                return
            
            if prob >= 0.6:
                logger.info(f"Cat[{prob:.4f}]({int((etime - stime) * 1000)}ms): {filename}")
                save_image(image, filename)

    if output_prob:
        await matcher.finish(
            "猫猫概率:\n"
            + "\n".join(f"[{i + 1}] {p:.4f}" for i, p in enumerate(probs))
        )
    