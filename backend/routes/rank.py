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
MATCH (u:User {id: $user_id})

CALL (u) {
  // Branch 1: property-shared edges (dish/cuisine/vibe/area)
  MATCH (u)-[:ANCHORED_TO]->(anchor:Venue)-[r1]->(prop)<-[r2]-(candidate:Venue)
  WHERE candidate <> anchor
    AND NOT EXISTS { MATCH (u)-[:ANCHORED_TO]->(candidate) }
    AND type(r1) IN ['SERVES','HAS_CUISINE','HAS_VIBE','IN_AREA']
    AND type(r1) = type(r2)
  WITH candidate, anchor, type(r1) AS et, prop,
       coalesce($boosts[anchor.id], 1.0) AS b
  WITH candidate, anchor, et, prop,
       CASE et
         WHEN 'SERVES'       THEN $w_dish
         WHEN 'HAS_CUISINE'  THEN $w_cuisine
         WHEN 'HAS_VIBE'     THEN $w_vibe
         WHEN 'IN_AREA'      THEN $w_area
         ELSE 0.0
       END * b *
       CASE
         WHEN et = 'SERVES'      AND prop.name IN $tag_dishes   THEN 2.5
         WHEN et = 'HAS_CUISINE' AND prop.name IN $tag_cuisines THEN 2.5
         WHEN et = 'HAS_VIBE'    AND prop.name IN $tag_vibes    THEN 2.0
         WHEN et = 'IN_AREA'     AND prop.name IN $tag_areas    THEN 2.0
         // When the LLM extracted tags for a dimension but this prop isn't
         // in them, attenuate hard. The user said "curry"; don't reward
         // SAME_DISH:salt_beef_bagel just because the edge happens to exist.
         WHEN et = 'SERVES'      AND size($tag_dishes)   > 0 THEN 0.15
         WHEN et = 'HAS_CUISINE' AND size($tag_cuisines) > 0 THEN 0.15
         ELSE 1.0
       END AS edge_score
  RETURN candidate,
         {
           anchor: anchor.id,
           kind:
             CASE et
               WHEN 'SERVES'      THEN 'SAME_DISH'
               WHEN 'HAS_CUISINE' THEN 'SAME_CUISINE'
               WHEN 'HAS_VIBE'    THEN 'SAME_VIBE'
               WHEN 'IN_AREA'     THEN 'SAME_AREA'
             END,
           item: prop.name,
           score: edge_score
         } AS item,
         edge_score AS partial

  UNION ALL

  // Branch 2: :SIMILAR_TO direct edges
  MATCH (u)-[:ANCHORED_TO]->(anchor:Venue)-[s:SIMILAR_TO]->(candidate:Venue)
  WHERE NOT EXISTS { MATCH (u)-[:ANCHORED_TO]->(candidate) }
  WITH candidate, anchor,
       coalesce(s.score, 0.0) * $w_similar * coalesce($boosts[anchor.id], 1.0) AS sim_score
  RETURN candidate,
         {
           anchor: anchor.id,
           kind: 'SIMILAR_OVERALL',
           item: 'similar to ' + anchor.name,
           score: sim_score
         } AS item,
         sim_score AS partial
}

WITH candidate, collect(item) AS breakdown, sum(partial) AS raw
WITH candidate, breakdown, raw - candidate.dist * $w_distance_penalty AS score
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
                w_similar=2.5,
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
