// Schema for the Semantica graph.
// Run once against a fresh Neo4j Aura instance before seeding.

CREATE CONSTRAINT user_id      IF NOT EXISTS FOR (u:User)    REQUIRE u.id IS UNIQUE;
CREATE CONSTRAINT venue_id     IF NOT EXISTS FOR (v:Venue)   REQUIRE v.id IS UNIQUE;
CREATE CONSTRAINT dish_name    IF NOT EXISTS FOR (d:Dish)    REQUIRE d.name IS UNIQUE;
CREATE CONSTRAINT cuisine_name IF NOT EXISTS FOR (c:Cuisine) REQUIRE c.name IS UNIQUE;
CREATE CONSTRAINT vibe_name    IF NOT EXISTS FOR (v:Vibe)    REQUIRE v.name IS UNIQUE;
CREATE CONSTRAINT area_name    IF NOT EXISTS FOR (a:Area)    REQUIRE a.name IS UNIQUE;

CREATE INDEX venue_loc         IF NOT EXISTS FOR (v:Venue) ON (v.loc);
CREATE INDEX anchored_to_count IF NOT EXISTS FOR ()-[r:ANCHORED_TO]-() ON (r.search_count);
CREATE INDEX similar_to_score  IF NOT EXISTS FOR ()-[r:SIMILAR_TO]-() ON (r.score);
