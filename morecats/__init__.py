# -*- coding: utf-8 -*-
import os
import re
import time
from datetime import datetime

from nonebot import get_driver, on_message, on_command
from nonebot.adapters import Event
from nonebot.adapters.onebot.v11 import Bot as OneBotV11Bot
from nonebot.adapters.onebot.v11.message import Message, MessageSegment
from nonebot.log import logger

import sqlalchemy as sa
from PIL import Image

from .models import CatOrNot, NeuralHash
from .database import ImageTB, db
from .deduplication import has_similar, add_hash
from .image_utils import read_image, save_image
from .config import Config

driver = get_driver()
conf = Config.parse_obj(driver.config)

cat_model = CatOrNot("./models/resnext50_32x4d.onnx")
hash_model = NeuralHash(
    "./models/neuralhash.onnx", "./models/neuralhash_128x96_seed1.dat"
)

matcher = on_message()
random_cat = on_command("random_cat")
maomao = on_command("猫猫")


@driver.on_startup
async def initialize():
    await deduplication.load_hashes()


@matcher.handle()
async def handle_images(event: Event, bot: OneBotV11Bot):
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
                static_image = Image.open(image).convert("RGB") # Convert GIF image to static image (1st frame)
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
                similarity = await has_similar(nhash_bits) # Find similar images
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
                await add_hash(nhash_bits)

    if output_prob:
        await matcher.finish(
            "猫猫概率:\n"
            + "\n".join(f"[{i + 1}] {p:.4f}" for i, p in enumerate(probs))
        )



@random_cat.handle()
@maomao.handle()
async def get_random_cat():
    record = await db.fetch_one(
        ImageTB
        .select()
        .order_by(sa.sql.expression.func.random())
        .limit(1)
    )

    if not record:
        await matcher.finish("没有发现猫猫")
    elif not conf.cat_image_dir:
        await matcher.finish("没有配置图片目录")
    else:
        with open(os.path.join(conf.cat_image_dir, record.filename), "rb") as f:
            image = MessageSegment.image(f.read())
        await matcher.finish(Message(image))
