// The one query that runs at search time.
//
// Parameters:
//   $user_id              : the user
//   $boosts               : map<anchor_id, multiplier> from cosine(query, anchor)
//   $tag_dishes,
//   $tag_cuisines,
//   $tag_vibes,
//   $tag_areas            : extracted tags from LLM; property matches get 1.5x
//   $w_dish, $w_cuisine,
//   $w_vibe, $w_area,
//   $w_similar,           : SIMILAR_TO branch weight
//   $w_distance_penalty   : edge-type weights
//
// Two branches: property-shared edges, and :SIMILAR_TO direct edges
// (built offline by scripts/build_similar_edges.py).
//
// See backend/routes/rank.py for the Python wrapper that invokes this.

MATCH (u:User {id: $user_id})-[:ANCHORED_TO]->(anchor:Venue)
WITH u, anchor, coalesce($boosts[anchor.id], 1.0) AS b

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
LIMIT 12;
