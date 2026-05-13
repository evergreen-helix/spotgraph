// Seed data — mirrors frontend/src/data/graph.ts exactly.
// Coords are point({longitude, latitude}) with WGS-84 implied.

// User
MERGE (u:User {id: 'u_alex'})
SET u.name = 'Alex Chen',
    u.center = point({longitude: -0.0726, latitude: 51.5225});

// Areas
UNWIND [
  'brick_lane','shoreditch','regents_canal','spitalfields','highbury',
  'broadway_mkt','borough_mkt','marylebone','hackney'
] AS area
MERGE (:Area {name: area});

// ─── Anchor venues
UNWIND [
  {id:'beigel',  name:'Beigel Bake',  area:'brick_lane',    lng:-0.0716, lat:51.5227,
   dishes:['salt_beef_bagel','cream_cheese_bagel'], cuisine:['jewish','east_european'],
   vibe:['no_frills','late_night','counter_service','cheap_eats'],
   sc:14, sv:6, dr:9},
  {id:'dishoom', name:'Dishoom',      area:'shoreditch',    lng:-0.0779, lat:51.5258,
   dishes:['bacon_naan','black_daal'], cuisine:['indian','bombay'],
   vibe:['bustling','all_day','atmospheric'],
   sc:11, sv:4, dr:7},
  {id:'towpath', name:'Towpath Café', area:'regents_canal', lng:-0.0759, lat:51.5395,
   dishes:['sourdough_toast','cardamom_bun'], cuisine:['modern_european','cafe'],
   vibe:['outdoor','seasonal','local_favourite','weekend_brunch'],
   sc:8, sv:3, dr:5}
] AS row
MERGE (v:Venue {id: row.id})
SET v.name = row.name,
    v.loc  = point({longitude: row.lng, latitude: row.lat}),
    v.dist = 0.0
WITH v, row
MATCH (u:User {id: 'u_alex'})
MERGE (u)-[a:ANCHORED_TO]->(v)
SET a.search_count = row.sc, a.saves = row.sv, a.directions = row.dr
WITH v, row
MATCH (area:Area {name: row.area}) MERGE (v)-[:IN_AREA]->(area)
FOREACH (d IN row.dishes  | MERGE (x:Dish    {name: d}) MERGE (v)-[:SERVES]->(x))
FOREACH (c IN row.cuisine | MERGE (x:Cuisine {name: c}) MERGE (v)-[:HAS_CUISINE]->(x))
FOREACH (vb IN row.vibe   | MERGE (x:Vibe    {name: vb}) MERGE (v)-[:HAS_VIBE]->(x));

// ─── Candidate venues
UNWIND [
  {id:'brick_lane_bagel', name:'Brick Lane Bagel Co.', area:'brick_lane',   lng:-0.0717, lat:51.5225,
   dishes:['salt_beef_bagel','cream_cheese_bagel'], cuisine:['jewish','east_european'],
   vibe:['no_frills','late_night','counter_service','cheap_eats'], dist:0.05},
  {id:'poppies', name:'Poppies Fish & Chips', area:'spitalfields', lng:-0.0723, lat:51.5208,
   dishes:['fish_chips','jellied_eels'], cuisine:['british','east_end'],
   vibe:['nostalgic','counter_service','cheap_eats'], dist:0.3},
  {id:'ottolenghi', name:'Ottolenghi', area:'spitalfields', lng:-0.076, lat:51.5179,
   dishes:['aubergine','challah','babka'], cuisine:['middle_eastern','jewish'],
   vibe:['bright','brunch','queue'], dist:0.4},
  {id:'black_axe', name:'Black Axe Mangal', area:'highbury', lng:-0.098, lat:51.545,
   dishes:['lamb_flatbread','squid_flatbread'], cuisine:['turkish_inspired','modern_european'],
   vibe:['loud','music','cult_favourite','intense'], dist:4.2},
  {id:'climpsons', name:'Climpson & Sons', area:'broadway_mkt', lng:-0.0598, lat:51.5378,
   dishes:['flat_white','sourdough_toast'], cuisine:['cafe','specialty_coffee'],
   vibe:['weekend_brunch','outdoor','local_favourite'], dist:1.6},
  {id:'gunpowder', name:'Gunpowder', area:'spitalfields', lng:-0.075, lat:51.5187,
   dishes:['chettinad_duck','rasam'], cuisine:['indian','south_indian'],
   vibe:['bustling','small_plates','atmospheric'], dist:0.3},
  {id:'kappacasein', name:'Kappacasein', area:'borough_mkt', lng:-0.0911, lat:51.5054,
   dishes:['raclette','grilled_cheese'], cuisine:['british','cheese'],
   vibe:['counter_service','cheap_eats','queue','market'], dist:5.8},
  {id:'monocle', name:'Monocle Café', area:'marylebone', lng:-0.1527, lat:51.5188,
   dishes:['pastries','matcha'], cuisine:['cafe','japanese_leaning'],
   vibe:['bright','quiet','design_y'], dist:6.4},
  {id:'lyles', name:"Lyle's", area:'shoreditch', lng:-0.0784, lat:51.5237,
   dishes:['tasting_menu','seasonal'], cuisine:['modern_british'],
   vibe:['minimal','seasonal','quiet'], dist:0.6},
  {id:'pophams', name:'Pophams Bakery', area:'hackney', lng:-0.057, lat:51.543,
   dishes:['pastries','laminated_dough'], cuisine:['bakery','modern_european'],
   vibe:['weekend_brunch','queue','local_favourite'], dist:2.8}
] AS row
MERGE (v:Venue {id: row.id})
SET v.name = row.name,
    v.loc  = point({longitude: row.lng, latitude: row.lat}),
    v.dist = row.dist
WITH v, row
MATCH (area:Area {name: row.area}) MERGE (v)-[:IN_AREA]->(area)
FOREACH (d IN row.dishes  | MERGE (x:Dish    {name: d}) MERGE (v)-[:SERVES]->(x))
FOREACH (c IN row.cuisine | MERGE (x:Cuisine {name: c}) MERGE (v)-[:HAS_CUISINE]->(x))
FOREACH (vb IN row.vibe   | MERGE (x:Vibe    {name: vb}) MERGE (v)-[:HAS_VIBE]->(x));
