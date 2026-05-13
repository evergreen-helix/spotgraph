"""Offline: embed every venue, MERGE top-5 :SIMILAR_TO edges per anchor.

Run after seed.cql / seed-osm.cql has been loaded. Edges are directional
anchor → candidate. Score = cosine similarity in [0, 1].

    cd backend
    python -m scripts.build_similar_edges

Cost: ~$0.001 per 1000 venues (text-embedding-3-small). On 6,320 venues
the whole script costs about $0.007 and takes ~30s.

The rank Cypher walks these as a 5th edge type alongside the four
property edges; weight is $w_similar in routes/rank.py.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import numpy as np

from db.neo4j_client import driver, session, settings
from llm.client import has_key
from llm.embeddings import embed_batch, profile_text


log = logging.getLogger(__name__)


TOP_K = 5


def fetch_venues() -> tuple[list[dict[str, Any]], list[str]]:
    """Pull every venue with its property tags. Returns (rows, anchor_ids)."""
    s = settings()
    with session() as sess:
        rows = sess.run(
            """
            MATCH (v:Venue)
            OPTIONAL MATCH (v)-[:SERVES]->(d:Dish)
            OPTIONAL MATCH (v)-[:HAS_CUISINE]->(c:Cuisine)
            OPTIONAL MATCH (v)-[:HAS_VIBE]->(vb:Vibe)
            OPTIONAL MATCH (v)-[:IN_AREA]->(ar:Area)
            RETURN v.id AS id, v.name AS name,
                   collect(DISTINCT d.name)  AS dishes,
                   collect(DISTINCT c.name)  AS cuisine,
                   collect(DISTINCT vb.name) AS vibe,
                   head(collect(DISTINCT ar.name)) AS area
            """
        ).data()
        anchor_ids = [
            r["id"] for r in sess.run(
                "MATCH (u:User {id: $uid})-[:ANCHORED_TO]->(v:Venue) RETURN v.id AS id",
                uid=s.user_id,
            ).data()
        ]
    return rows, anchor_ids


def write_edges(anchor_id: str, neighbors: list[tuple[str, float]]) -> None:
    """Replace the anchor's existing :SIMILAR_TO edges atomically."""
    with session() as sess:
        sess.run(
            "MATCH (a:Venue {id: $aid})-[r:SIMILAR_TO]->() DELETE r",
            aid=anchor_id,
        )
        sess.run(
            """
            UNWIND $rows AS row
            MATCH (a:Venue {id: $aid})
            MATCH (c:Venue {id: row.id})
            MERGE (a)-[r:SIMILAR_TO]->(c)
            SET r.score = row.score
            """,
            aid=anchor_id,
            rows=[{"id": cid, "score": float(score)} for cid, score in neighbors],
        )


def main() -> int:
    if not has_key():
        log.error("OPENAI_API_KEY missing — set it in backend/.env first")
        return 1

    rows, anchor_ids = fetch_venues()
    if not rows:
        log.error("no venues in Neo4j — load seed.cql or seed-osm.cql first")
        return 1
    if not anchor_ids:
        log.error("no anchors for user — check USER_ID and ANCHORED_TO edges")
        return 1

    log.info("embedding %d venues...", len(rows))
    texts = [
        profile_text(
            name=r["name"] or "",
            dishes=r["dishes"] or [],
            cuisine=r["cuisine"] or [],
            vibe=r["vibe"] or [],
            area=r["area"] or "",
        )
        for r in rows
    ]
    vecs = embed_batch(texts)

    mat = np.stack(vecs).astype(np.float32)
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    normed = mat / norms
    # NaN/Inf can leak in from degenerate inputs; cosine of a zero vector is 0
    normed = np.nan_to_num(normed, nan=0.0, posinf=0.0, neginf=0.0)

    id_index = {r["id"]: i for i, r in enumerate(rows)}
    anchor_set = set(anchor_ids)

    for anchor_id in anchor_ids:
        if anchor_id not in id_index:
            log.warning("anchor %s missing from venue scan, skipping", anchor_id)
            continue
        ai = id_index[anchor_id]
        sims = normed @ normed[ai]
        # Filter out self and other anchors so :SIMILAR_TO points at candidates
        sims[ai] = -1.0
        for other_aid in anchor_set:
            j = id_index.get(other_aid)
            if j is not None:
                sims[j] = -1.0
        top = np.argpartition(-sims, TOP_K)[:TOP_K]
        top_sorted = top[np.argsort(-sims[top])]
        neighbors = [(rows[int(i)]["id"], float(sims[int(i)])) for i in top_sorted if sims[int(i)] > 0]
        write_edges(anchor_id, neighbors)
        log.info("anchor %-30s -> top-%d %s", anchor_id, TOP_K,
                 [(rows[int(i)]["name"], round(float(sims[int(i)]), 3)) for i in top_sorted])

    driver().close()
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    sys.exit(main())
