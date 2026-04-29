import math

from app.services.ai_router import embed_text

EMBEDDING_DIM = 1536
MAX_CHARS = 8000


async def generate_embedding(text: str) -> list[float]:
    return await embed_text(text[:MAX_CHARS])


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    dot = sum(a * b for a, b in zip(vec1, vec2))
    mag1 = math.sqrt(sum(a * a for a in vec1))
    mag2 = math.sqrt(sum(b * b for b in vec2))
    if mag1 == 0.0 or mag2 == 0.0:
        return 0.0
    return dot / (mag1 * mag2)
