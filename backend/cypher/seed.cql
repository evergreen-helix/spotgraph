// Seed data — mirrors frontend/src/data/graph.ts exactly.
// Coords are point({longitude, latitude}) with WGS-84 implied.

// ─── User
MERGE (u:User {id: 'u_alex'})
SET u.name = 'Alex Chen',
    u.center = point({longitude: -0.0726, latitude: 51.5225});

// ─── Areas
UNWIND [
  'brick_lane','shoreditch','regents_canal','spitalfields','highbury',
  'broadway_mkt','borough_mkt','marylebone','hackney','bethnal_green',
  'whitechapel','smithfield','clerkenwell','haggerston','hackney_road',
  'soho'
] AS area
MERGE (:Area {name: area});

// ─── Anchor venues (visited)
UNWIND [
  {id:'beigel',  name:'Beigel Bake',  area:'brick_lane',    lng:-0.0716, lat:51.5227,
   dishes:['salt_beef_bagel','cream_cheese_bagel'], cuisine:['jewish','east_european'],
   vibe:['no_frills','late_night','counter_service','cheap_eats'],
   sc:14, sv:6, dr:9},
  {id:'dishoom', name:'Dishoom', area:'shoreditch', lng:-0.0779, lat:51.5258,
   dishes:['bacon_naan','black_daal'], cuisine:['indian','bombay'],
   vibe:['bustling','all_day','atmospheric'],
   sc:11, sv:4, dr:7},
  {id:'towpath', name:'Towpath Café', area:'regents_canal', lng:-0.0759, lat:51.5395,
   dishes:['sourdough_toast','cardamom_bun'], cuisine:['modern_european','cafe'],
   vibe:['outdoor','seasonal','local_favourite','weekend_brunch'],
   sc:8, sv:3, dr:5},
  {id:'e_pellicci', name:'E Pellicci', area:'bethnal_green', lng:-0.0686, lat:51.526,
   dishes:['full_english','spaghetti_bolognese'], cuisine:['italian','british','caff'],
   vibe:['family_run','no_frills','cheap_eats','all_day'],
   sc:9, sv:4, dr:6},
  {id:'lahore_kebab', name:'Lahore Kebab House', area:'whitechapel', lng:-0.063, lat:51.515,
   dishes:['seekh_kebab','lamb_chops','karahi_gosht'], cuisine:['pakistani','indian'],
   vibe:['late_night','bustling','cheap_eats','no_frills'],
   sc:7, sv:3, dr:5},
  {id:'st_john', name:'St. John', area:'smithfield', lng:-0.103, lat:51.521,
   dishes:['bone_marrow','roast_pork','welsh_rarebit'], cuisine:['british','modern_british'],
   vibe:['minimal','seasonal','quiet','cult_favourite'],
   sc:6, sv:5, dr:4},
  {id:'caravan_exmouth', name:'Caravan', area:'clerkenwell', lng:-0.108, lat:51.524,
   dishes:['cornbread','shakshuka','flat_white'], cuisine:['antipodean','cafe','all_day_brunch'],
   vibe:['weekend_brunch','bustling','bright'],
   sc:7, sv:3, dr:5}
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

// ─── Candidate venues (suggested)
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
   vibe:['weekend_brunch','queue','local_favourite'], dist:2.8},
  {id:'smokestak', name:'Smokestak', area:'shoreditch', lng:-0.072, lat:51.524,
   dishes:['brisket','pulled_pork','ox_cheek'], cuisine:['bbq','modern_european'],
   vibe:['loud','bustling','atmospheric'], dist:0.4},
  {id:'padella', name:'Padella', area:'borough_mkt', lng:-0.091, lat:51.506,
   dishes:['pici_cacio_pepe','pappardelle_ragu'], cuisine:['italian','pasta'],
   vibe:['counter_service','queue','cheap_eats','bustling'], dist:5.5},
  {id:'hoppers', name:'Hoppers', area:'soho', lng:-0.131, lat:51.514,
   dishes:['hoppers','kothu_roti','bone_marrow_varuval'], cuisine:['sri_lankan','south_indian'],
   vibe:['bustling','small_plates','atmospheric'], dist:5.1},
  {id:'berber_q', name:'Berber & Q', area:'haggerston', lng:-0.072, lat:51.539,
   dishes:['lamb_shawarma','cauliflower_shawarma'], cuisine:['middle_eastern','grill'],
   vibe:['loud','music','atmospheric'], dist:1.5},
  {id:'marksman', name:'The Marksman', area:'hackney_road', lng:-0.069, lat:51.53,
   dishes:['beef_barley_bun','sunday_roast'], cuisine:['british','gastropub'],
   vibe:['pub','seasonal','local_favourite'], dist:0.9},
  {id:'som_saa', name:'Som Saa', area:'spitalfields', lng:-0.073, lat:51.519,
   dishes:['nahm_dtok','gaeng_hung_lay'], cuisine:['thai','northern_thai'],
   vibe:['small_plates','atmospheric','loud'], dist:0.4},
  {id:'brat', name:'Brat', area:'shoreditch', lng:-0.077, lat:51.525,
   dishes:['whole_turbot','grilled_lamb'], cuisine:['basque','modern_european'],
   vibe:['seasonal','atmospheric','cult_favourite'], dist:0.5},
  {id:'smoking_goat', name:'Smoking Goat', area:'shoreditch', lng:-0.077, lat:51.524,
   dishes:['fish_sauce_wings','lardo_pad_thai'], cuisine:['thai','modern_thai'],
   vibe:['loud','music','bustling'], dist:0.4},
  {id:'bistrotheque', name:'Bistrotheque', area:'bethnal_green', lng:-0.06, lat:51.532,
   dishes:['steak_frites','weekend_brunch'], cuisine:['french','bistro'],
   vibe:['weekend_brunch','design_y','atmospheric'], dist:1.5},
  {id:'quality_chop', name:'Quality Chop House', area:'clerkenwell', lng:-0.108, lat:51.523,
   dishes:['confit_potatoes','mince_on_toast'], cuisine:['british','modern_british'],
   vibe:['seasonal','atmospheric','cult_favourite'], dist:2.6},
  {id:'bao_soho', name:'Bao', area:'soho', lng:-0.135, lat:51.512,
   dishes:['classic_bao','fried_chicken_bao'], cuisine:['taiwanese'],
   vibe:['counter_service','queue','small_plates'], dist:5.3},
  {id:'tayyabs', name:'Tayyabs', area:'whitechapel', lng:-0.064, lat:51.516,
   dishes:['lamb_chops','karahi_gosht','seekh_kebab'], cuisine:['pakistani','punjabi'],
   vibe:['loud','bustling','cheap_eats','bring_your_own'], dist:0.7}
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
