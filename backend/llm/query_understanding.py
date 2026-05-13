"""Parse a free-text restaurant query into two signals:

  1. anchor_boosts  — per-anchor continuous boost in [1.0, 3.5] from cosine
                      similarity between query and anchor profile embeddings.
  2. query_tags     — structured tags (dishes, cuisines, vibes, areas)
                      extracted via gpt-4o-mini against a controlled vocab,
                      then snapped to the closest vocab item per dimension.

Both fire in parallel via asyncio.gather. On any OpenAI failure the function
returns neutral boosts ({} → Cypher uses 1.0 for all anchors) and empty
tags — the downstream Cypher still runs, just without the OpenAI signal.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Iterable

from pydantic import BaseModel, Field

from llm.client import async_client, openai_settings
from llm.embeddings import Vec, cosine_matrix, embed_async


log = logging.getLogger(__name__)


class QueryTags(BaseModel):
    dishes: list[str] = Field(default_factory=list)
    cuisines: list[str] = Field(default_factory=list)
    vibes: list[str] = Field(default_factory=list)
    areas: list[str] = Field(default_factory=list)


class Vocab(BaseModel):
    """Per-label vocabulary used both in the GPT system prompt and to snap
    free-form GPT output back onto the canonical token set."""

    dishes: list[str] = Field(default_factory=list)
    cuisines: list[str] = Field(default_factory=list)
    vibes: list[str] = Field(default_factory=list)
    areas: list[str] = Field(default_factory=list)


TAG_SYSTEM = """You map a casual restaurant search query to structured tags
from a fixed vocabulary. Return JSON exactly matching this schema:

  {{ "dishes": string[], "cuisines": string[], "vibes": string[], "areas": string[] }}

Rules:
- Use tokens from the vocabularies below. Underscored spelling (e.g. "salt_beef_bagel").
- Empty arrays are correct when a dimension does not apply.
- Do not infer anything not implied by the query.
- Max 4 items per array.

Vocabularies:
- dishes: {dishes}
- cuisines: {cuisines}
- vibes: {vibes}
- areas: {areas}
"""


async def _extract_tags(query: str, vocab: Vocab) -> QueryTags:
    """One gpt-4o-mini call, JSON mode, temp=0. Snap output to vocab."""
    s = openai_settings()
    sys_prompt = TAG_SYSTEM.format(
        dishes=", ".join(vocab.dishes),
        cuisines=", ".join(vocab.cuisines),
        vibes=", ".join(vocab.vibes),
        areas=", ".join(vocab.areas),
    )
    try:
        resp = await async_client().chat.completions.create(
            model=s.openai_chat_model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": query},
            ],
        )
        raw = json.loads(resp.choices[0].message.content or "{}")
    except Exception as e:
        log.warning("tag extraction failed: %s", e)
        return QueryTags()

    return QueryTags(
        dishes=_snap(raw.get("dishes", []), vocab.dishes),
        cuisines=_snap(raw.get("cuisines", []), vocab.cuisines),
        vibes=_snap(raw.get("vibes", []), vocab.vibes),
        areas=_snap(raw.get("areas", []), vocab.areas),
    )


def _snap(items: Iterable, allowed: list[str]) -> list[str]:
    """Drop anything not in the vocab — GPT occasionally invents tokens."""
    if not allowed:
        return []
    allowed_set = set(allowed)
    out: list[str] = []
    for item in items:
        if not isinstance(item, str):
            continue
        token = item.strip().lower().replace(" ", "_").replace("-", "_")
        if token in allowed_set:
            out.append(token)
    return out[:4]


def _boosts_from_similarity(
    q_vec: Vec, anchor_vecs: dict[str, Vec]
) -> dict[str, float]:
    """Map cosine similarity → continuous boost in [1.0, 3.5].

    A perfectly orthogonal anchor gets 1.0 (i.e. no boost, falls back to the
    default in Cypher). A perfectly aligned anchor gets 3.5 — replicates the
    old binary 3.0 boost ceiling with a smooth gradient underneath.
    """
    if not anchor_vecs:
        return {}
    ids = list(anchor_vecs.keys())
    import numpy as np

    mat = np.stack([anchor_vecs[i] for i in ids])
    sims = cosine_matrix(q_vec, mat)
    sims = np.clip(sims, 0.0, 1.0)
    boosts = 1.0 + 2.5 * sims
    return {aid: float(b) for aid, b in zip(ids, boosts)}


async def understand(
    query: str,
    anchor_embeddings: dict[str, Vec],
    vocab: Vocab,
) -> tuple[dict[str, float], QueryTags]:
    """Two OpenAI calls in parallel: embed(query) + extract_tags(query).

    On embed failure: anchor_boosts is empty (Cypher uses default 1.0).
    On extract failure: tags is empty (Cypher tag-match bonus is no-op).
    """
    embed_task = asyncio.create_task(_safe_embed(query))
    tags_task = asyncio.create_task(_extract_tags(query, vocab))
    q_vec, tags = await asyncio.gather(embed_task, tags_task)
    boosts = _boosts_from_similarity(q_vec, anchor_embeddings) if q_vec is not None else {}
    return boosts, tags


async def _safe_embed(query: str) -> Vec | None:
    try:
        return await embed_async(query)
    except Exception as e:
        log.warning("query embed failed: %s", e)
        return None
