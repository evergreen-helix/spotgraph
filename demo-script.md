# SEMANTICA — Hackathon Demo Script

**Track:** Neo4j · Best Use of Graph
**Format:** ~3-minute live demo (screenplay style)
**Pitch line:** *"Google ranks by what's popular. We rank by what you've already loved."*

---

## THE CORE IDEA, IN ONE PARAGRAPH

Every Google search you've ever made is a vote for what you like. Search "Beigel Bake Brick Lane" fourteen times and Google still doesn't *do* anything with that — your fifteenth search for "where to eat" gets you the same top-of-funnel results as a tourist. **Semantica ingests your search history, identifies the venues you keep coming back to (your "anchors"), and uses Neo4j to project from those anchors outward — same dish, same cuisine, same neighbourhood, same vibe.** When you search "where should I eat," it knows that a Brick Lane Bagel Co. is two hops from Beigel Bake (same dish: salt beef bagel), that Poppies Fish & Chips is two hops (same vibe: counter service, cheap eats, east end). It's not personalisation by demographics. It's personalisation by **what you've already shown you love**.

---

## SETUP (before stage)

- Browser fullscreen on `semantica.html`, cursor in the search bar.
- Second tab with Neo4j Bloom (or a screenshot of the schema) ready for the technical reveal.
- Demo hotkeys: `1` bagels · `2` brunch · `3` curry · `4` generic · `Esc` reset.

---

## SCENE 1 — THE PROBLEM (0:00 – 0:25)

**[Screen: vintage-paper map of east London. A search bar dead-center. Lower-left, a card labelled "Your anchor venues" lists Beigel Bake, Dishoom, Towpath Café — each with a heart. On the map, three yellow heart-pinned dots glow softly.]**

**SPEAKER**
Quick question. How many times have you Googled the *same* restaurant before finally going there?

*(pause)*

Yeah. I've searched "Beigel Bake Brick Lane" fourteen times in the last year. Fourteen. And the next time I open Google and type "where should I eat" — it has no idea. I get the same top-of-funnel chain restaurants as somebody who landed at Heathrow this morning.

That's the problem we're solving. We call it **Semantica**.

Watch the bottom-left of the screen. Those three hearted spots — Beigel Bake, Dishoom, Towpath Café — those aren't favourites I clicked. We **inferred** them from my search history. Fourteen searches, nine direction requests, six saves. That's an anchor.

---

## SCENE 2 — THE MAGIC MOMENT (0:25 – 1:10)

**[SPEAKER hits `4`. Text types into the bar: "where should I eat?" The bar's bottom edge unzips. Four ranked suggestions slide down. On the map, four pins ignite orange and pulse — and dashed lines visibly arc from the three yellow heart-pins to the orange ones, showing the projection.]**

**SPEAKER**
I type the most generic query possible — "where should I eat" — and look at what comes back.

*(beat, pointing)*

**Brick Lane Bagel Co.** Number one. Why? Because the graph walks: Alex → ♥ Beigel Bake → **same dish: salt beef bagel** → Brick Lane Bagel Co. Two hops. Score 23.4.

**Poppies Fish & Chips.** Number two. Different walk: ♥ Beigel Bake → **same vibe: counter service, cheap eats** → Poppies.

**Ottolenghi Spitalfields.** Three hops: ♥ Beigel Bake → **same cuisine: Jewish** → Ottolenghi.

**[SPEAKER points at the dashed lines on the map.]**

And see those dashed lines on the map? Each one is a **literal Cypher edge**. The yellow heart-pins are my anchors. The orange ones are the recommendations. The lines are the graph relationships that connect them.

No popularity ranking. No "people who liked X also liked Y." Just: *Alex liked this specific thing, here are places one or two graph hops away*.

---

## SCENE 3 — DIFFERENT QUERIES, DIFFERENT ANCHORS (1:10 – 1:50)

**[SPEAKER hits `Esc`, then `1`. Query: "bagels near me". The map redraws: only the Beigel Bake heart-pin lights up; lines from it to Brick Lane Bagel Co. and Ottolenghi.]**

**SPEAKER**
Now watch what happens when the query is specific.

*(taps `1`)*

"Bagels near me." The graph re-weights — Beigel Bake becomes the dominant anchor. The Dishoom and Towpath signals fade. We only project from the relevant part of the taste graph.

*(taps `3`)*

"Curry tonight." Different anchor now — Dishoom lights up. Gunpowder appears. Small plates, atmospheric, Indian. The bagel signal is silent.

*(taps `2`)*

"Weekend brunch." Now Towpath Café is doing the work. Climpsons. Pophams. Outdoor, local favourite, weekend energy.

**[SPEAKER taps `Esc`. The dropdown collapses. The map returns to its quiet state.]**

Same person, three different anchors, three different traversals. The bar collapses cleanly. No clutter.

---

## SCENE 4 — THE NEO4J REVEAL (1:50 – 2:35)

**[SPEAKER switches to the Neo4j Bloom tab. A graph: User node at center, three Anchor venues, then radiating outward — Dish nodes, Cuisine nodes, Vibe nodes, Area nodes, then Candidate venues at the perimeter.]**

**SPEAKER**
Here's why this is a Neo4j problem.

We ingest Google search history through Takeout — roughly 15,000 queries for me. We extract venue mentions, count repeats, and write nodes:

- `(:User)` — me
- `(:Venue)` — every place I've searched for
- `(:Dish)` — salt beef bagel, bacon naan, cardamom bun
- `(:Cuisine)`, `(:Vibe)`, `(:Area)`

Anchors are venues with a high search-repeat score:

```cypher
(:User)-[:ANCHORED_TO {searches: 14, saves: 6}]->(:Venue)
```

And venues connect to their properties:

```cypher
(:Venue)-[:SERVES]->(:Dish)
(:Venue)-[:HAS_CUISINE]->(:Cuisine)
(:Venue)-[:HAS_VIBE]->(:Vibe)
(:Venue)-[:IN_AREA]->(:Area)
```

At search time, **one Cypher query** does the whole projection:

```cypher
MATCH (u:User {id: $me})-[:ANCHORED_TO]->(anchor:Venue)
MATCH (anchor)-[r1]->(prop)<-[r2]-(candidate:Venue)
WHERE candidate <> anchor
  AND point.distance(candidate.loc, $here) < 5000
WITH candidate, anchor, type(r1) AS edge_type, prop,
     CASE type(r1)
       WHEN 'SERVES'      THEN 3.0
       WHEN 'HAS_CUISINE' THEN 1.5
       WHEN 'HAS_VIBE'    THEN 1.0
       WHEN 'IN_AREA'     THEN 1.2
     END AS weight
RETURN candidate.name,
       sum(weight) AS score,
       collect({anchor: anchor.name, via: prop.name, edge: edge_type}) AS path
ORDER BY score DESC
LIMIT 4
```

**One query. ~200 milliseconds. Every result comes with the path that produced it.**

This is exactly what graph databases were built for. A relational DB would need a self-join across five tables with a `UNION ALL` and a manual scoring function in application code. A vector DB could *kind of* do "similar to my favourites," but you'd lose the **explainability** — that little breadcrumb at the bottom of the dropdown is a literal trace of which edges Cypher walked. I can show you exactly why we recommended Poppies. A vector model can only show you a cosine similarity.

---

## SCENE 5 — WHY IT'S DEFENSIBLE (2:35 – 2:55)

**[SPEAKER back at the demo. Dropdown is open. Breadcrumb visible.]**

**SPEAKER**
Three things make this real:

**One — your data, your graph.** The whole thing lives on your account. We don't aggregate, we don't sell. Every edge is one of your decisions.

**Two — explainability by construction.** Every rank shows its path. No black box. Hover, see the Cypher trace.

**Three — it compounds.** Every search adds an edge. Every direction request strengthens an anchor. Every save promotes a venue. The graph gets better while you use it — and you can *see* it getting better, because the paths get richer.

Built in 36 hours. Neo4j Aura free tier, sub-200ms queries the whole time.

---

## SCENE 6 — CLOSE (2:55 – 3:00)

**[SPEAKER hits `Esc` one last time. Clean search bar. Cursor blinking.]**

**SPEAKER**
Google ranks the world by what *everyone* clicks.

Semantica ranks it by what *you* keep coming back to.

*(beat)*

Thanks.

**[END]**

---

## TECHNICAL APPENDIX

### Schema (Cypher)

```cypher
// Constraints
CREATE CONSTRAINT FOR (u:User)   REQUIRE u.id IS UNIQUE;
CREATE CONSTRAINT FOR (v:Venue)  REQUIRE v.id IS UNIQUE;
CREATE CONSTRAINT FOR (d:Dish)   REQUIRE d.name IS UNIQUE;
CREATE CONSTRAINT FOR (c:Cuisine) REQUIRE c.name IS UNIQUE;
CREATE CONSTRAINT FOR (vb:Vibe)  REQUIRE vb.name IS UNIQUE;
CREATE CONSTRAINT FOR (a:Area)   REQUIRE a.name IS UNIQUE;

// Indexes for hot paths
CREATE INDEX FOR (v:Venue) ON (v.loc);
CREATE INDEX FOR ()-[r:ANCHORED_TO]-() ON (r.search_count);
```

### Ingestion (high level)

1. User uploads Google Takeout `MyActivity.json`.
2. Python pipeline (~150 lines):
   - Parse search queries with timestamps.
   - Entity-extract venue names via spaCy NER + Google Places API confirmation.
   - Bucket repeated searches → compute anchor score (search_count + recency decay + co-occurrence with "directions to", "hours", "menu").
   - Enrich each venue with dishes/cuisine/vibe via Claude API on top of review text.
3. Write to Neo4j Aura: ~15k nodes, ~60k edges for a typical year of search history.

### What's mocked in this demo

- The `GRAPH` constant in the HTML is the entire Neo4j response, embedded. In production, `GRAPH.rank()` is replaced by `fetch('/api/rank?q=...')` which runs the Cypher above.
- Pin positions on the map are hand-placed for visual storytelling. Real geo would come from `point({latitude, longitude})` and a Mapbox/Leaflet basemap.
- The dashed lines between anchor pins and recommended pins are drawn client-side from the breakdown returned by `rank()` — in production, the same data, just streamed from Cypher.

### Q&A — likely judge questions

- *"How is this different from a recommender?"*
  → Recommenders rank by latent similarity. We rank by **explicit graph path**. You can ask "why" and get an answer in plain English: "because you love Beigel Bake and this place serves the same dish."

- *"Why not just embeddings?"*
  → Embeddings give you "close in vector space" — opaque. The graph gives you "close *through this specific relationship*." That's the difference between a suggestion and an explanation. Also, embeddings can't easily encode "same neighbourhood" without geo-aware loss functions; the graph does it natively with `:IN_AREA`.

- *"Cold start?"*
  → After ~50 queries we have one anchor. After ~500 we have three or four and the projection is rich. Before that, we fall back to popularity-ranked results — same as Google — but with an honest banner that says "still learning your taste."

- *"What about bias / filter bubbles?"*
  → Every edge is auditable. You can see the graph, prune anchors you don't want, downweight a vibe. Compare that to Google's ranking model, which you have zero visibility into.

- *"Why Neo4j specifically, not just a graph in Postgres?"*
  → Variable-depth pattern matching. The query `(:User)-[:ANCHORED_TO]->(:Venue)-[*1..2]-(:Venue)` is one line in Cypher. In SQL it's a recursive CTE with manual edge-type checking. Performance falls off a cliff past two hops.

### Repo structure

```
semantica/
├── semantica.html       ← demo UI (this file)
├── ingest.py            ← Google Takeout → Neo4j
├── server.js            ← thin Express layer, single /api/rank endpoint
├── cypher/
│   ├── schema.cql
│   ├── seed.cql
│   └── rank.cql         ← the one query that runs at search time
└── README.md
```

---

## DEMO HOTKEYS

| Key | Query | What it shows |
|-----|-------|---------------|
| `1` | "bagels near me" | Beigel Bake anchor dominates · same dish ranking |
| `2` | "weekend brunch" | Towpath anchor dominates · same vibe ranking |
| `3` | "curry tonight" | Dishoom anchor dominates · same cuisine ranking |
| `4` | "where should I eat?" | All three anchors contribute · the headline demo |
| `Esc` | — | Reset to clean home screen |

Click any suggestion card to isolate its pin and visualise just the edges feeding that recommendation.
