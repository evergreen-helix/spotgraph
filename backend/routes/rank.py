"""POST /api/rank — the single Cypher query that powers the demo.

In: { "query": "where should I eat?" }
Out: list of RankedCandidate, sorted DESC by score.

Query understanding (parallel):
  - embed(query) → cosine vs anchor profile embeddings → continuous boost
  - gpt-4o-mini → structured tags (dishes/cuisines/vibes/areas)

Both feed the Cypher:
  - $boosts maps anchor.id → continuous multiplier in [1.0, 3.5]
  - $tag_* are the extracted tags; a property match adds a 1.5x bonus on
    top of the base edge weight × anchor boost.
  - :SIMILAR_TO is a 5th edge type: direct anchor→candidate edges built
    offline by scripts/build_similar_edges.py.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from db.neo4j_client import session, settings
from llm import anchor_cache
from llm.query_understanding import understand
from models.schemas import BreakdownItem, RankRequest, RankedCandidate, Venue


log = logging.getLogger(__name__)

router = APIRouter()


RANK_QUERY = """
MATCH (u:User {id: $user_id})-[:ANCHORED_TO]->(anchor:Venue)
WITH u, anchor, coalesce($boosts[anchor.id], 1.0) AS b

// --- Branch 1: property-shared edges (dish/cuisine/vibe/area)
CALL {
  WITH u, anchor, b
  MATCH (anchor)-[r1]->(prop)<-[r2]-(candidate:Venue)
  WHERE candidate <> anchor
    AND NOT EXISTS { MATCH (u)-[:ANCHORED_TO]->(candidate) }
    AND type(r1) IN ['SERVES','HAS_CUISINE','HAS_VIBE','IN_AREA']
    AND type(r1) = type(r2)
  WITH candidate, anchor, b, type(r1) AS edge_type, prop,
       CASE type(r1)
         WHEN 'SERVES'       THEN $w_dish
         WHEN 'HAS_CUISINE'  THEN $w_cuisine
         WHEN 'HAS_VIBE'     THEN $w_vibe
         WHEN 'IN_AREA'      THEN $w_area
         ELSE 0.0
       END AS base_weight,
       CASE
         WHEN type(r1) = 'SERVES'      AND prop.name IN $tag_dishes   THEN 1.5
         WHEN type(r1) = 'HAS_CUISINE' AND prop.name IN $tag_cuisines THEN 1.5
         WHEN type(r1) = 'HAS_VIBE'    AND prop.name IN $tag_vibes    THEN 1.5
         WHEN type(r1) = 'IN_AREA'     AND prop.name IN $tag_areas    THEN 1.5
         ELSE 1.0
       END AS tag_match
  WITH candidate, anchor, edge_type, prop, base_weight * b * tag_match AS edge_score
  RETURN candidate AS c, anchor AS a, edge_type, prop.name AS item, edge_score
}

WITH u, c AS candidate, a AS anchor, edge_type, item, edge_score
WITH candidate,
     sum(edge_score) - candidate.dist * $w_distance_penalty AS prop_score,
     collect({
       anchor: anchor.id,
       kind:
         CASE edge_type
           WHEN 'SERVES'      THEN 'SAME_DISH'
           WHEN 'HAS_CUISINE' THEN 'SAME_CUISINE'
           WHEN 'HAS_VIBE'    THEN 'SAME_VIBE'
           WHEN 'IN_AREA'     THEN 'SAME_AREA'
         END,
       item: item,
       score: edge_score
     }) AS prop_breakdown

// --- Branch 2: :SIMILAR_TO direct edges (only present if build_similar_edges has run)
OPTIONAL MATCH (u_:User {id: $user_id})-[:ANCHORED_TO]->(anc:Venue)-[s:SIMILAR_TO]->(candidate)
WITH candidate, prop_score, prop_breakdown,
     collect(DISTINCT CASE WHEN anc IS NULL THEN NULL ELSE {
       anchor: anc.id,
       kind: 'SIMILAR_OVERALL',
       item: 'similar to ' + anc.name,
       score: coalesce(s.score, 0.0) * $w_similar * coalesce($boosts[anc.id], 1.0)
     } END) AS sim_breakdown_raw
WITH candidate, prop_score, prop_breakdown,
     [item IN sim_breakdown_raw WHERE item IS NOT NULL] AS sim_breakdown

WITH candidate,
     prop_score + reduce(s = 0.0, item IN sim_breakdown | s + item.score) AS score,
     prop_breakdown + sim_breakdown AS breakdown
WHERE score > 0

OPTIONAL MATCH (candidate)-[:SERVES]->(d:Dish)
OPTIONAL MATCH (candidate)-[:HAS_CUISINE]->(c:Cuisine)
OPTIONAL MATCH (candidate)-[:HAS_VIBE]->(vb:Vibe)
OPTIONAL MATCH (candidate)-[:IN_AREA]->(area:Area)
WITH candidate, score, breakdown,
     collect(DISTINCT d.name) AS dishes,
     collect(DISTINCT c.name) AS cuisine,
     collect(DISTINCT vb.name) AS vibe,
     head(collect(DISTINCT area.name)) AS area
RETURN
  candidate.id AS id,
  {
    id: candidate.id, name: candidate.name, area: area,
    dishes: dishes, cuisine: cuisine, vibe: vibe,
    loc: [candidate.loc.x, candidate.loc.y], dist: candidate.dist
  } AS venue,
  score,
  breakdown
ORDER BY score DESC
LIMIT 12
"""


@router.post("/api/rank", response_model=list[RankedCandidate])
async def post_rank(req: RankRequest) -> list[RankedCandidate]:
    s = settings()
    cache = anchor_cache.cache()

    query = req.query.strip()
    if not query:
        return []

    boosts, tags = await understand(query, cache.embeddings, cache.vocab)
    log.info(
        "rank query=%r boosts=%s tags=dishes:%d cuisines:%d vibes:%d areas:%d",
        query, {k: round(v, 2) for k, v in boosts.items()},
        len(tags.dishes), len(tags.cuisines), len(tags.vibes), len(tags.areas),
    )

    try:
        with session() as sess:
            records = sess.run(
                RANK_QUERY,
                user_id=s.user_id,
                boosts=boosts,
                tag_dishes=tags.dishes,
                tag_cuisines=tags.cuisines,
                tag_vibes=tags.vibes,
                tag_areas=tags.areas,
                w_dish=3.0,
                w_cuisine=1.5,
                w_vibe=1.0,
                w_area=1.2,
                w_similar=4.0,
                w_distance_penalty=0.15,
            ).data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"neo4j error: {e}") from e

    results: list[RankedCandidate] = []
    for r in records:
        r["breakdown"].sort(key=lambda b: b["score"], reverse=True)
        results.append(
            RankedCandidate(
                id=r["id"],
                venue=Venue(**r["venue"]),
                score=r["score"],
                breakdown=[BreakdownItem(**b) for b in r["breakdown"]],
            )
        )
    return results
