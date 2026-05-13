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
         WHEN et = 'SERVES'      AND prop.name IN $tag_dishes   THEN 1.5
         WHEN et = 'HAS_CUISINE' AND prop.name IN $tag_cuisines THEN 1.5
         WHEN et = 'HAS_VIBE'    AND prop.name IN $tag_vibes    THEN 1.5
         WHEN et = 'IN_AREA'     AND prop.name IN $tag_areas    THEN 1.5
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
LIMIT 12;
