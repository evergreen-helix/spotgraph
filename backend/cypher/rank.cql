// The one query that runs at search time.
//
// Parameters:
//   $user_id            : the user
//   $boosts             : map<anchor_id, multiplier> from query parsing
//   $w_dish, $w_cuisine,
//   $w_vibe, $w_area,
//   $w_distance_penalty : edge-type weights
//
// See backend/routes/rank.py for the Python wrapper that invokes this.

MATCH (u:User {id: $user_id})-[:ANCHORED_TO]->(anchor:Venue)
WITH anchor, coalesce($boosts[anchor.id], 1.0) AS b

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
LIMIT 8;
