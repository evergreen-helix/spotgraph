"""Embedding helpers — single-shot async embed, batch sync embed, cosine.

The profile text template is shared by every embedding consumer: query
understanding embeds anchors with it, build_similar_edges.py embeds every
venue with it. Keep it identical so the two systems agree on geometry.
"""

from __future__ import annotations

from typing import Any, Iterable

import numpy as np

from llm.client import async_client, openai_settings, sync_client


Vec = np.ndarray


def profile_text(name: str, dishes: list[str], cuisine: list[str], vibe: list[str], area: str) -> str:
    """The canonical "what is this venue" string we embed.

    Shared by anchor embedding cache and :SIMILAR_TO offline build. If you
    change this you must rebuild every artifact that used it.
    """
    def fmt(items: list[str]) -> str:
        return ", ".join(i.replace("_", " ") for i in items) if items else "none"
    return (
        f"{name}. "
        f"Serves: {fmt(dishes)}. "
        f"Cuisine: {fmt(cuisine)}. "
        f"Vibe: {fmt(vibe)}. "
        f"Area: {area.replace('_', ' ')}."
    )


async def embed_async(text: str) -> Vec:
    resp = await async_client().embeddings.create(
        model=openai_settings().openai_embed_model,
        input=text,
    )
    return np.asarray(resp.data[0].embedding, dtype=np.float32)


def embed_batch(texts: Iterable[str], batch_size: int = 256) -> list[Vec]:
    """Batch sync — used by offline scripts. OpenAI accepts arrays of input."""
    texts = list(texts)
    out: list[Vec] = []
    client = sync_client()
    model = openai_settings().openai_embed_model
    for i in range(0, len(texts), batch_size):
        chunk = texts[i : i + batch_size]
        resp = client.embeddings.create(model=model, input=chunk)
        out.extend(np.asarray(d.embedding, dtype=np.float32) for d in resp.data)
    return out


def cosine(a: Vec, b: Vec) -> float:
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def cosine_matrix(query: Vec, mat: np.ndarray) -> np.ndarray:
    """Cosine similarity between a single vector and rows of a matrix."""
    qn = float(np.linalg.norm(query))
    if qn == 0.0:
        return np.zeros(mat.shape[0], dtype=np.float32)
    norms = np.linalg.norm(mat, axis=1)
    norms[norms == 0.0] = 1.0
    return (mat @ query) / (norms * qn)


def venue_profile_text(v: dict[str, Any]) -> str:
    """Convenience for callers that already have a dict in the seed.json shape."""
    return profile_text(
        name=v.get("name", ""),
        dishes=v.get("dishes", []),
        cuisine=v.get("cuisine", []),
        vibe=v.get("vibe", []),
        area=v.get("area", ""),
    )
