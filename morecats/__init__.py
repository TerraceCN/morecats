# -*- coding: utf-8 -*-
import os
import re
import imghdr
import time
from io import BytesIO
from typing import Literal, Tuple
from datetime import datetime

from nonebot import on_message, get_driver
from nonebot.adapters import Event
from nonebot.adapters.onebot.v11 import Bot as OneBotV11Bot
from nonebot.log import logger

from httpx import AsyncClient
from PIL import Image as PILImage

from .models import CatOrNot, NeuralHash
from .config import Config
from .database import ImageTB, db
from . import deduplication

driver = get_driver()
conf = Config.parse_obj(driver.config)

cat_model = CatOrNot("./models/resnext50_32x4d.onnx")
hash_model = NeuralHash(
    "./models/neuralhash.onnx", "./models/neuralhash_128x96_seed1.dat"
)

ImageExt = Literal["gif", "jpeg", "png", "bmp"]

matcher = on_message()


async def read_image(url: str) -> Tuple[ImageExt, BytesIO]:
    """
    Read image from url

    :params url: image url
    :return: image extension, PIL Image object
    """
    async with AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()

    image = BytesIO(resp.content)
    ext = imghdr.what(image)
    if ext not in ("gif", "jpeg", "png", "bmp"):
        raise ValueError(f"Unsupported image format {ext}")

    image.seek(0)
    return ext, PILImage.open(image)


def save_image(image: PILImage.Image, filename: str) -> None:
    """
    Save PIL Image object to file

    :params image: PIL Image object
    :params filename: filename
    """
    if not conf.cat_image_dir:
        return

    if not os.path.exists(conf.cat_image_dir):
        os.makedirs(conf.cat_image_dir)
    
    image_path = os.path.join(conf.cat_image_dir, filename)
    image.save(image_path)


@driver.on_startup
async def initialize():
    await deduplication.load_hashes()


@matcher.handle()
async def handle_image(event: Event, bot: OneBotV11Bot):
    probs = [] # Probabilities of image being a cat
    output_prob = False # Whether to output probability

    for segment in event.get_message(): # Iterate over all message segments
        if segment.type == "text":
            if re.match(f"^/cat_prob$", segment.data["text"].strip()):
                output_prob = True # Enable probability output

        if segment.type == "image":
            url: str = segment.data["url"]
            filename: str = segment.data["file"]

            try:
                ext, image = await read_image(url)
                static_image = image.convert("RGB") # Convert GIF image to static image (1st frame)
            except Exception as e:
                logger.error(f"Failed to read image: {e}")
                return
            filename = ".".join(filename.rsplit(".", 1)[:-1] + [ext]) # Replace extension with actual extension

            try:
                stime = time.time()
                prob = cat_model.predict_prob(static_image)[0] # Predict probability of image being a cat
                etime = time.time()
                probs.append(prob)
            except Exception as e:
                logger.error(f"Failed to predict: {e}")
                probs.append(-1)
                return
            
            if prob < 0.6: # If the image doesn't contain any cat
                image.close()
                continue

            logger.info(f"Cat[{prob:.4f}]({int((etime - stime) * 1000)}ms): {filename}")

            record = await db.fetch_one(
                ImageTB
                .select()
                .where(ImageTB.c.filename == filename)
            )

            if record: # If the image has been recorded
                await db.execute( # Record count increases
                    ImageTB
                    .update()
                    .where(ImageTB.c.filename == filename)
                    .values(count=record.count + 1)
                )
            else: # New image
                session_id = event.get_session_id() # type_groupid_userid
                user_id = event.get_user_id()

                stime = time.time()
                nhash_bits = hash_model.calc_bits(static_image) # Calc neural hash bits
                similarity = await deduplication.has_similar(nhash_bits) # Find similar images
                etime = time.time()

                if similarity >= 0.9: # If the image is similar to a recorded image
                    logger.info(f"Duplicate cat[{similarity:.4f}]({int((etime - stime) * 1000)}ms): {filename}")
                    image.close()
                    continue

                await db.execute( # Add new image to database
                    ImageTB.insert().values(
                        url=url,
                        filename=filename,
                        nhash=NeuralHash.bits2hex(nhash_bits),
                        group_id=session_id.split("_")[1] if session_id != user_id else None,
                        user_id=user_id,
                        time=datetime.fromtimestamp(event.time),
                        count=1
                    )
                )
                save_image(image, filename)
                await deduplication.add_hash(nhash_bits)

    if output_prob:
        await matcher.finish(
            "猫猫概率:\n"
            + "\n".join(f"[{i + 1}] {p:.4f}" for i, p in enumerate(probs))
        )
    