"""GET /api/graph — returns the user, their anchors, candidate venues, weights.

The frontend calls this once at boot to render every pin on the map.

We CAP the candidate set so Mapbox stays smooth. The full graph remains
in Neo4j and feeds /api/rank — only what gets *drawn* on the map is
trimmed. Filter mirrors the OSM scraper's demo-quality rules:
  - within ~3.5km of user centre
  - has a non-misc cuisine
  - has at least 2 vibe tags
  - sorted by (distance ASC, tag_coverage DESC)
  - capped at GRAPH_RENDER_LIMIT (default 300)
"""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException

from db.neo4j_client import session, settings
from models.schemas import Anchor, GraphResponse, User, Venue, Weights

router = APIRouter()


GRAPH_RENDER_LIMIT = int(os.getenv("GRAPH_RENDER_LIMIT", "300"))
GRAPH_RENDER_RADIUS_KM = float(os.getenv("GRAPH_RENDER_RADIUS_KM", "3.5"))


GRAPH_QUERY = """
// Anchors: venues with an :ANCHORED_TO edge from the user
MATCH (u:User {id: $user_id})
OPTIONAL MATCH (u)-[anc:ANCHORED_TO]->(a:Venue)
OPTIONAL MATCH (a)-[:SERVES]->(ad:Dish)
OPTIONAL MATCH (a)-[:HAS_CUISINE]->(ac:Cuisine)
OPTIONAL MATCH (a)-[:HAS_VIBE]->(av:Vibe)
OPTIONAL MATCH (a)-[:IN_AREA]->(aarea:Area)
WITH u, a, anc,
     collect(DISTINCT ad.name) AS a_dishes,
     collect(DISTINCT ac.name) AS a_cuisine,
     collect(DISTINCT av.name) AS a_vibe,
     head(collect(DISTINCT aarea.name)) AS a_area
WITH u, collect({
  id: a.id, name: a.name, area: a_area,
  dishes: a_dishes, cuisine: a_cuisine, vibe: a_vibe,
  loc: [a.loc.x, a.loc.y], dist: 0.0,
  searchCount: anc.search_count, saves: anc.saves, directions: anc.directions
}) AS anchors

// Candidate venues — filter to demo-quality subset for fast map rendering
MATCH (v:Venue)
WHERE NOT (u)-[:ANCHORED_TO]->(v)
  AND v.dist < $radius_km
OPTIONAL MATCH (v)-[:SERVES]->(d:Dish)
OPTIONAL MATCH (v)-[:HAS_CUISINE]->(c:Cuisine)
OPTIONAL MATCH (v)-[:HAS_VIBE]->(vb:Vibe)
OPTIONAL MATCH (v)-[:IN_AREA]->(area:Area)
WITH u, anchors, v,
     collect(DISTINCT d.name) AS dishes,
     collect(DISTINCT c.name) AS cuisine,
     collect(DISTINCT vb.name) AS vibe,
     head(collect(DISTINCT area.name)) AS area
WHERE size(cuisine) > 0
  AND NOT (size(cuisine) = 1 AND cuisine[0] = 'misc')
  AND size(vibe) >= 2
WITH u, anchors, v, dishes, cuisine, vibe, area,
     (size(dishes) + size(cuisine) + size(vibe)) AS tag_coverage
ORDER BY v.dist ASC, tag_coverage DESC
LIMIT $limit

WITH u, anchors,
     collect({
       id: v.id, name: v.name, area: area,
       dishes: dishes, cuisine: cuisine, vibe: vibe,
       loc: [v.loc.x, v.loc.y], dist: v.dist
     }) AS venues
RETURN
  { id: u.id, name: u.name, center: [u.center.x, u.center.y] } AS user,
  anchors,
  venues
"""


@router.get("/api/graph", response_model=GraphResponse)
def get_graph() -> GraphResponse:
    s = settings()
    try:
        with session() as sess:
            rec = sess.run(
                GRAPH_QUERY,
                user_id=s.user_id,
                limit=GRAPH_RENDER_LIMIT,
                radius_km=GRAPH_RENDER_RADIUS_KM,
            ).single()
            if not rec:
                raise HTTPException(status_code=404, detail="user not found")
            user = User(**rec["user"])
            anchors = {a["id"]: Anchor(**a) for a in rec["anchors"] if a["id"]}
            venues = {v["id"]: Venue(**v) for v in rec["venues"] if v["id"]}
            return GraphResponse(
                user=user,
                anchors=anchors,
                venues=venues,
                weights=Weights(),
            )
    except HTTPException:
        raise
    except Exception as e:
        # Surface driver/connection errors as 500 with the underlying message
        raise HTTPException(status_code=500, detail=f"neo4j error: {e}") from e
