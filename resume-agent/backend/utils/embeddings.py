"""
Embedding utilities — generate and compare vectors for resume-job matching.
"""
import math
from typing import List
from openai import AsyncOpenAI
from api.config import get_settings

settings = get_settings()
_client = None


def get_openai_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def embed_text(text: str) -> List[float]:
    """Generate an embedding vector for a text string."""
    client = get_openai_client()
    response = await client.embeddings.create(
        input=text[:8000],  # token limit safety
        model=settings.embedding_model
    )
    return response.data[0].embedding


async def embed_resume(resume_text: str) -> List[float]:
    """Embed a full resume for matching against job descriptions."""
    return await embed_text(resume_text)


async def embed_job_description(jd_text: str) -> List[float]:
    """Embed a job description for matching."""
    return await embed_text(jd_text)


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute cosine similarity between two vectors. Returns 0.0–1.0."""
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = math.sqrt(sum(a * a for a in vec_a))
    mag_b = math.sqrt(sum(b * b for b in vec_b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def match_score_to_label(score: float) -> str:
    """Convert 0-100 score to human label."""
    if score >= 85:
        return "Excellent match"
    elif score >= 70:
        return "Good match"
    elif score >= 55:
        return "Moderate match"
    elif score >= 40:
        return "Weak match"
    else:
        return "Poor match"
