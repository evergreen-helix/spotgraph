"""Lifetime-of-process cache: anchor embeddings + tag vocabularies.

Populated once in the FastAPI lifespan hook. Both are derived from the
graph state at boot — restart the server when the seed changes.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from db.neo4j_client import session, settings
from llm.client import has_key
from llm.embeddings import Vec, embed_async, profile_text
from llm.query_understanding import Vocab


log = logging.getLogger(__name__)


SEED_FALLBACK = Path(__file__).parent.parent / "data" / "seed.json"


@dataclass
class AnchorCache:
    """In-memory, mutable, swapped wholesale at warm-time."""

    embeddings: dict[str, Vec] = field(default_factory=dict)
    vocab: Vocab = field(default_factory=Vocab)
    ready: bool = False


_cache = AnchorCache()


def cache() -> AnchorCache:
    return _cache


# ─── Loaders

def _load_from_neo4j() -> tuple[dict[str, dict], Vocab]:
    """Pull anchors with their property tags and the full label vocabularies."""
    s = settings()
    with session() as sess:
        anchor_rows = sess.run(
            """
            MATCH (u:User {id: $uid})-[:ANCHORED_TO]->(a:Venue)
            OPTIONAL MATCH (a)-[:SERVES]->(d:Dish)
            OPTIONAL MATCH (a)-[:HAS_CUISINE]->(c:Cuisine)
            OPTIONAL MATCH (a)-[:HAS_VIBE]->(v:Vibe)
            OPTIONAL MATCH (a)-[:IN_AREA]->(ar:Area)
            RETURN a.id AS id, a.name AS name,
                   collect(DISTINCT d.name) AS dishes,
                   collect(DISTINCT c.name) AS cuisine,
                   collect(DISTINCT v.name) AS vibe,
                   head(collect(DISTINCT ar.name)) AS area
            """,
            uid=s.user_id,
        ).data()

        vocab_row = sess.run(
            """
            MATCH (d:Dish)    WITH collect(DISTINCT d.name) AS dishes
            MATCH (c:Cuisine) WITH dishes, collect(DISTINCT c.name) AS cuisines
            MATCH (v:Vibe)    WITH dishes, cuisines, collect(DISTINCT v.name) AS vibes
            MATCH (a:Area)    RETURN dishes, cuisines, vibes,
                                      collect(DISTINCT a.name) AS areas
            """
        ).single() or {}

    vocab = Vocab(
        dishes=sorted(vocab_row.get("dishes") or []),
        cuisines=sorted(vocab_row.get("cuisines") or []),
        vibes=sorted(vocab_row.get("vibes") or []),
        areas=sorted(vocab_row.get("areas") or []),
    )
    anchors = {r["id"]: r for r in anchor_rows}
    return anchors, vocab


def _load_from_seed_json() -> tuple[dict[str, dict], Vocab]:
    if not SEED_FALLBACK.exists():
        return {}, Vocab()
    data = json.loads(SEED_FALLBACK.read_text())
    anchors_raw = data.get("anchors") or {}
    all_venues = list(anchors_raw.values()) + list((data.get("venues") or {}).values())
    dishes, cuisines, vibes, areas = set(), set(), set(), set()
    for v in all_venues:
        dishes.update(v.get("dishes", []))
        cuisines.update(v.get("cuisine", []))
        vibes.update(v.get("vibe", []))
        if v.get("area"):
            areas.add(v["area"])
    vocab = Vocab(
        dishes=sorted(dishes),
        cuisines=sorted(cuisines),
        vibes=sorted(vibes),
        areas=sorted(areas),
    )
    anchors = {aid: {**a, "cuisine": a.get("cuisine", [])} for aid, a in anchors_raw.items()}
    return anchors, vocab


async def warm() -> None:
    """Called from FastAPI lifespan on startup.

    Fills the global cache. Failure to talk to Neo4j is non-fatal: we fall
    back to seed.json so the demo still boots when Aura is down.
    Failure to embed (no OPENAI_API_KEY, network out) leaves the cache empty
    — /api/rank then runs with neutral boosts but still returns results.
    """
    try:
        anchors, vocab = _load_from_neo4j()
        log.info("anchor cache: loaded %d anchors from Neo4j", len(anchors))
    except Exception as e:
        log.warning("Neo4j unreachable at startup (%s), falling back to seed.json", e)
        anchors, vocab = _load_from_seed_json()
        log.info("anchor cache: loaded %d anchors from seed.json", len(anchors))

    _cache.vocab = vocab

    if not anchors or not has_key():
        _cache.embeddings = {}
        _cache.ready = True
        log.info("anchor cache: ready (no embeddings — %s)",
                 "no anchors" if not anchors else "no OPENAI_API_KEY")
        return

    tasks = [
        embed_async(
            profile_text(
                name=a.get("name", ""),
                dishes=a.get("dishes", []),
                cuisine=a.get("cuisine", []),
                vibe=a.get("vibe", []),
                area=a.get("area", "") or "",
            )
        )
        for a in anchors.values()
    ]
    try:
        vecs = await asyncio.gather(*tasks)
    except Exception as e:
        log.warning("anchor embedding failed: %s", e)
        _cache.embeddings = {}
        _cache.ready = True
        return

    _cache.embeddings = {aid: vec for aid, vec in zip(anchors.keys(), vecs)}
    _cache.ready = True
    log.info("anchor cache: %d anchors embedded", len(_cache.embeddings))
