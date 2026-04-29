from __future__ import annotations

import asyncio
import logging
import math
from typing import List

from fastembed import TextEmbedding

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 384
MAX_CHARS = 8000

_model: TextEmbedding | None = None


def get_embedding_model() -> TextEmbedding:
    global _model
    if _model is None:
        logger.info("Loading fastembed model (all-MiniLM-L6-v2)...")
        _model = TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
        logger.info("Embedding model loaded.")
    return _model


def get_embedding(text: str) -> List[float]:
    model = get_embedding_model()
    embeddings = list(model.embed([text]))
    return embeddings[0].tolist()


async def generate_embedding(text: str) -> List[float]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, get_embedding, text[:MAX_CHARS])


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    dot = sum(a * b for a, b in zip(vec1, vec2))
    mag1 = math.sqrt(sum(a * a for a in vec1))
    mag2 = math.sqrt(sum(b * b for b in vec2))
    if mag1 == 0.0 or mag2 == 0.0:
        return 0.0
    return dot / (mag1 * mag2)
