"""POST /api/rank — the single Cypher query that powers the demo.

In: { "query": "where should I eat?" }
Out: list of RankedCandidate, sorted DESC by score.

The Cypher walks User → AnchorVenue → shared property → CandidateVenue
and collects the path for every match. Edge-type weights and a
query-driven anchor boost let one query serve "bagels near me"
and "weekend brunch" without separate code paths.
"""

from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException

from db.neo4j_client import session, settings
from models.schemas import BreakdownItem, RankRequest, RankedCandidate, Venue

router = APIRouter()


# Mirrors frontend/src/lib/rank.ts — keyword → anchor boost.
# In production this is replaced by a vector-similarity step:
#   query embedding × anchor embedding → continuous boost vector.
ANCHOR_BOOSTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(bagel|beigel|salt beef|sandwich|bread)\b", re.I), "beigel"),
    (re.compile(r"\b(curry|indian|naan|biryani|daal|spice|tikka|masala)\b", re.I), "dishoom"),
    (re.compile(r"\b(brunch|coffee|cafe|breakfast|outdoor|canal|sourdough)\b", re.I), "towpath"),
    (re.compile(r"\b(brunch|coffee|cafe|breakfast|shakshuka|antipodean)\b", re.I), "caravan_exmouth"),
    (re.compile(r"\b(kebab|pakistani|lamb|punjabi|tandoor)\b", re.I), "lahore_kebab"),
    (re.compile(r"\b(roast|sunday|nose[ -]to[ -]tail|seasonal|modern british)\b", re.I), "st_john"),
    (re.compile(r"\b(caff|full english|fry[ -]?up|italian|cheap)\b", re.I), "e_pellicci"),
]


RANK_QUERY = """
// Boosts are passed in as a map: { anchor_id: weight }
MATCH (u:User {id: $user_id})-[:ANCHORED_TO]->(anchor:Venue)
WITH anchor, coalesce($boosts[anchor.id], 1.0) AS b

// Walk anchor -> shared property <- candidate, one relationship-type at a time
MATCH (anchor)-[r1]->(prop)<-[r2]-(candidate:Venue)
WHERE candidate <> anchor
  AND NOT EXISTS { MATCH (u)-[:ANCHORED_TO]->(candidate) }
WITH candidate, anchor, b, type(r1) AS edge_type, prop,
     CASE type(r1)
       WHEN 'SERVES'       THEN $w_dish
       WHEN 'HAS_CUISINE'  THEN $w_cuisine
       WHEN 'HAS_VIBE'     THEN $w_vibe
       WHEN 'IN_AREA'      THEN $w_area
       ELSE 0.0
     END AS base_weight

WITH candidate, anchor, edge_type, prop, base_weight * b AS edge_score
WITH candidate,
     sum(edge_score) - candidate.dist * $w_distance_penalty AS score,
     collect({
       anchor: anchor.id,
       kind:
         CASE edge_type
           WHEN 'SERVES'      THEN 'SAME_DISH'
           WHEN 'HAS_CUISINE' THEN 'SAME_CUISINE'
           WHEN 'HAS_VIBE'    THEN 'SAME_VIBE'
           WHEN 'IN_AREA'     THEN 'SAME_AREA'
         END,
       item: prop.name,
       score: edge_score
     }) AS breakdown
WHERE score > 0

// Strip property nodes from breakdown, re-sort, return
WITH candidate, score, breakdown
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
LIMIT 8
"""


def _compute_boosts(query: str) -> dict[str, float]:
    boosts: dict[str, float] = {}
    for pattern, anchor_id in ANCHOR_BOOSTS:
        if pattern.search(query):
            boosts[anchor_id] = 3.0
    return boosts


@router.post("/api/rank", response_model=list[RankedCandidate])
def post_rank(req: RankRequest) -> list[RankedCandidate]:
    s = settings()
    boosts = _compute_boosts(req.query)
    try:
        with session() as sess:
            records = sess.run(
                RANK_QUERY,
                user_id=s.user_id,
                boosts=boosts,
                w_dish=3.0,
                w_cuisine=1.5,
                w_vibe=1.0,
                w_area=1.2,
                w_distance_penalty=0.15,
            ).data()
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"neo4j error: {e}") from e
