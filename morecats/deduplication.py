# -*- coding: utf-8 -*-
import sqlalchemy as sa
import numpy as np

from .models import NeuralHash
from .database import ImageTB, db

HASHES = []


async def load_hashes():
    last_id = 0
    while True:
        records = await db.fetch_all(
            sa.select(
                ImageTB.c.id,
                ImageTB.c.nhash,
            )
            .where(sa.and_(ImageTB.c.nhash != None, ImageTB.c.id > last_id))
            .order_by(ImageTB.c.id.asc())
            .limit(10000)
        )
        last_id = records[-1].id
        HASHES.append(np.array([NeuralHash.hex2bits(i.nhash) for i in records if i.nhash is not None], dtype=bool))
        if len(records) < 10000:
            break


async def has_similar(bits: np.ndarray) -> float:
    max_similarity = 0
    for i in HASHES:
        similarity = np.bitwise_xor(~bits, i).sum(1).max() / i.shape[1]
        if similarity > max_similarity:
            max_similarity = similarity
    return max_similarity


async def add_hash(bits: np.ndarray):
    if len(HASHES) == 0 or HASHES[-1].shape[0] >= 10000:
        HASHES.append(np.expand_dims(bits, 0))
    else:
        HASHES[-1] = np.append(HASHES[-1], np.expand_dims(bits, 0), axis=0)
