"""GET /api/graph — returns the user, their anchors, candidate venues, weights.

The frontend calls this once at boot to render every pin on the map.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from db.neo4j_client import session, settings
from models.schemas import Anchor, GraphResponse, User, Venue, Weights

router = APIRouter()


GRAPH_QUERY = """
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

// Render a digestible subset: hand-curated venues first (non-'osm_' ids),
// then OSM by ascending distance. Cap at 600 — denser map for visual
// richness, traded against a heavier Mapbox marker load. The rank endpoint
// still queries the full graph.
MATCH (v:Venue)
WHERE NOT (u)-[:ANCHORED_TO]->(v)
WITH u, anchors, v,
     CASE WHEN v.id STARTS WITH 'osm_' THEN 1 ELSE 0 END AS is_osm
ORDER BY is_osm ASC, v.dist ASC
LIMIT 600

OPTIONAL MATCH (v)-[:SERVES]->(d:Dish)
OPTIONAL MATCH (v)-[:HAS_CUISINE]->(c:Cuisine)
OPTIONAL MATCH (v)-[:HAS_VIBE]->(vb:Vibe)
OPTIONAL MATCH (v)-[:IN_AREA]->(area:Area)
WITH u, anchors, v,
     collect(DISTINCT d.name) AS dishes,
     collect(DISTINCT c.name) AS cuisine,
     collect(DISTINCT vb.name) AS vibe,
     head(collect(DISTINCT area.name)) AS area
RETURN
  { id: u.id, name: u.name, center: [u.center.x, u.center.y] } AS user,
  anchors,
  collect({
    id: v.id, name: v.name, area: area,
    dishes: dishes, cuisine: cuisine, vibe: vibe,
    loc: [v.loc.x, v.loc.y], dist: v.dist
  }) AS venues
"""


@router.get("/api/graph", response_model=GraphResponse)
def get_graph() -> GraphResponse:
    s = settings()
    try:
        with session() as sess:
            rec = sess.run(GRAPH_QUERY, user_id=s.user_id).single()
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
