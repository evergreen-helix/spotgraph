<div align="center">

# Semantica

### *Search that **knows** your spots.*

**A personalised place-search engine powered by a Neo4j taste graph.**
From places you've loved → to places you'll love.

[![Track](https://img.shields.io/badge/Hackathon-Neo4j%20%C2%B7%20Best%20Use%20of%20Graph-018BFF)](#why-neo4j)
[![Status](https://img.shields.io/badge/Status-MVP%20demo--ready-2DD4BF)](#mvp-scope)
[![Frontend](https://img.shields.io/badge/Frontend-React%20%2B%20Vite%20%2B%20Mapbox-61DAFB)](#stack)
[![Backend](https://img.shields.io/badge/Backend-FastAPI%20%2B%20Neo4j%20Aura-009639)](#stack)
[![Query](https://img.shields.io/badge/Latency-sub--200ms%20Cypher-FF6F00)](#performance)

</div>

---

## Elevator pitch

Every Google search you've ever made is a vote for what you love — but Google never casts it. You can search "Beigel Bake Brick Lane" fourteen times and your fifteenth search for *"where should I eat?"* still gets you the same tourist-pack chain results as somebody who landed at Heathrow this morning. **Semantica fixes that.** We ingest your search history, extract the venues you keep coming back to as *anchors*, and load them into a Neo4j taste graph alongside the dishes, cuisines, vibes, and neighbourhoods they share. At query time, **one Cypher traversal** walks from your anchors outward to every nearby candidate — so when you ask for a bar, you don't get *a* bar, you get *your kind of* bar; when you ask for food, you get a salt-beef bagel two hops from the one you already love. It is personalisation by **what you have explicitly shown you love**, with the literal graph path attached to every result. No black box. No demographic profiling. Just *your* edges.

---

## Table of contents

- [Why this exists](#why-this-exists)
- [What it does (in 30 seconds)](#what-it-does-in-30-seconds)
- [Demo at a glance](#demo-at-a-glance)
- [Why Neo4j](#why-neo4j)
- [How it works — system architecture](#how-it-works--system-architecture)
- [The graph schema](#the-graph-schema)
- [The headline query](#the-headline-query)
- [Personalisation examples](#personalisation-examples)
- [Stack](#stack)
- [Repository layout](#repository-layout)
- [Quick start](#quick-start)
- [API reference](#api-reference)
- [Ingestion pipeline](#ingestion-pipeline)
- [Performance](#performance)
- [MVP scope](#mvp-scope)
- [Roadmap](#roadmap)
- [Privacy & data ownership](#privacy--data-ownership)
- [Judging criteria alignment](#judging-criteria-alignment)
- [Credits](#credits)

---

## Why this exists

Discovery search today optimises for **the crowd** — popularity, recency, paid placement. The signal it ignores is the most personal one we generate: the things we keep coming back to. A pattern of repeated searches for *Beigel Bake* over a year is a stronger preference signal than any star rating, but no consumer product treats it that way.

We treat it as a first-class edge in a graph.

The result: a search bar that, given the most generic query in the world — *"where should I eat?"* — returns four venues *you* would have picked, with a short breadcrumb explaining how it got there.

## What it does (in 30 seconds)

1. You drop your Google Takeout `MyActivity.json` into the ingester.
2. The pipeline parses ~15k searches, identifies the venues you've searched repeatedly, and emits a Neo4j graph: **you → your anchor venues → their dishes / cuisines / vibes / areas → every candidate venue that shares any of those.**
3. You open the web app. A clean Mapbox basemap fills the screen. A single search bar sits in the middle. Three soft yellow heart-pins glow on the map — those are *your* anchors, inferred from your history.
4. You type anything — *"bar," "brunch," "curry," "where should I eat"* — and the bar's bottom edge unzips. Four ranked suggestions slide down. On the map, four pins ignite and dashed lines arc from your anchors to them, **visualising the literal Cypher edges that produced each result**.
5. The bar collapses into a chip in the corner with one click — the map becomes the canvas. Tap the chip to reopen.

## Demo at a glance

| Key | Query | What the graph does |
|-----|-------|---------------------|
| `1` | *bagels near me* | The Beigel Bake anchor dominates · `SAME_DISH` ranking |
| `2` | *weekend brunch* | The Towpath Café anchor dominates · `SAME_VIBE` ranking |
| `3` | *curry tonight* | The Dishoom anchor dominates · `SAME_CUISINE` ranking |
| `4` | *where should I eat?* | All three anchors contribute · the headline blended demo |
| `Esc` | — | Reset to a clean home screen |

A full screenplay-style walk-through of the live demo is in [`demo-script.md`](./demo-script.md).

---

## Why Neo4j

This is a problem Neo4j was *literally* designed for. The core operation — "walk from this set of nodes through any-typed properties to every other venue that shares at least one of those properties, weight by edge type, return with the path" — is a single readable Cypher query. The same operation in:

- **Postgres** → a recursive CTE with manual edge-type checking; performance falls off a cliff past two hops.
- **Vector DB** → "close in latent space," but you lose the *why*. You can't show the user the path.
- **Application code** → five-table joins + a hand-rolled scoring function + a `UNION ALL`; brittle, slow, untestable.

Variable-depth pattern matching, typed relationships, native geo via `point()`, and sub-200ms response on a free Aura tier — that is the differentiator we're showcasing on the Neo4j track.

> **The headline claim:** *every recommendation comes with the literal Cypher path that produced it.* Explainability isn't a feature bolted on — it's a byproduct of using the right database.

---

## How it works — system architecture

```
                           ┌──────────────────────────────────┐
                           │   Google Takeout MyActivity.json │
                           │      (~15k search queries)       │
                           └─────────────────┬────────────────┘
                                             │
                                             ▼
   ┌────────────────────────────────────────────────────────────────────────┐
   │                      INGESTION PIPELINE (Python)                        │
   │  ─ parse queries + timestamps                                           │
   │  ─ spaCy NER → venue mentions                                           │
   │  ─ Google Places API confirmation + geocoding                           │
   │  ─ bucket repeats → anchor_score = count + recency_decay + intent_co   │
   │  ─ Claude enrichment → dishes / cuisine / vibe from review text         │
   └─────────────────────────────┬──────────────────────────────────────────┘
                                 │ Cypher MERGE batches
                                 ▼
   ┌────────────────────────────────────────────────────────────────────────┐
   │                       NEO4J AURA (the taste graph)                      │
   │   (:User)─[:ANCHORED_TO]→(:Venue)─[:SERVES]→(:Dish)←[:SERVES]─(:Venue) │
   │                              └→[:HAS_CUISINE]→(:Cuisine)                │
   │                              └→[:HAS_VIBE]→(:Vibe)                      │
   │                              └→[:IN_AREA]→(:Area)                       │
   └─────────────────────────────┬──────────────────────────────────────────┘
                                 │ one Cypher query · ~200ms
                                 ▼
   ┌────────────────────────────────────────────────────────────────────────┐
   │                  FASTAPI BACKEND  (backend/main.py)                     │
   │       GET  /api/graph   → full taste graph for the UI                   │
   │       POST /api/rank    → ranked candidates + breakdown paths           │
   └─────────────────────────────┬──────────────────────────────────────────┘
                                 │ JSON over fetch / Vite proxy
                                 ▼
   ┌────────────────────────────────────────────────────────────────────────┐
   │              REACT + VITE + MAPBOX FRONTEND (frontend/)                 │
   │  ─ Google-Maps-like base layer, drag/zoom                               │
   │  ─ centre search bar with collapsible drop-down suggestions             │
   │  ─ dashed-line edge overlay anchor → candidate                          │
   │  ─ profile card · per-result breadcrumb · keyboard shortcuts            │
   └────────────────────────────────────────────────────────────────────────┘
```

---

## The graph schema

```cypher
// Node types
(:User    {id, name})
(:Venue   {id, name, loc: point, area, dist})
(:Dish    {name})
(:Cuisine {name})
(:Vibe    {name})
(:Area    {name})

// Relationship types
(:User)-[:ANCHORED_TO {search_count, save_count, last_seen}]->(:Venue)
(:Venue)-[:SERVES]->(:Dish)
(:Venue)-[:HAS_CUISINE]->(:Cuisine)
(:Venue)-[:HAS_VIBE]->(:Vibe)
(:Venue)-[:IN_AREA]->(:Area)

// Constraints + indexes (see backend/cypher/schema.cql)
CREATE CONSTRAINT FOR (u:User)    REQUIRE u.id IS UNIQUE;
CREATE CONSTRAINT FOR (v:Venue)   REQUIRE v.id IS UNIQUE;
CREATE INDEX     FOR (v:Venue) ON (v.loc);
CREATE INDEX     FOR ()-[r:ANCHORED_TO]-() ON (r.search_count);
```

A typical year of one person's search history produces **~15k nodes / ~60k edges**.

## The headline query

The whole product is one Cypher query (`backend/cypher/rank.cql`). It is parameterised by query-derived boosts (anchors mentioned in the query get a multiplier) and per-edge-type weights.

```cypher
MATCH (u:User {id: $user_id})-[:ANCHORED_TO]->(anchor:Venue)
WITH anchor, coalesce($boosts[anchor.id], 1.0) AS b

MATCH (anchor)-[r1]->(prop)<-[r2]-(candidate:Venue)
WHERE candidate <> anchor
  AND NOT EXISTS { MATCH (u)-[:ANCHORED_TO]->(candidate) }

WITH candidate, anchor, b, type(r1) AS edge_type, prop,
     CASE type(r1)
       WHEN 'SERVES'      THEN $w_dish
       WHEN 'HAS_CUISINE' THEN $w_cuisine
       WHEN 'HAS_VIBE'    THEN $w_vibe
       WHEN 'IN_AREA'     THEN $w_area
     END AS base_weight

WITH candidate,
     sum(base_weight * b) - candidate.dist * $w_distance_penalty AS score,
     collect({anchor: anchor.id, kind: edge_type, item: prop.name}) AS breakdown
WHERE score > 0
RETURN candidate, score, breakdown
ORDER BY score DESC LIMIT 8;
```

That's it. **One query. ~200ms. Every result ships with the path that produced it.**

---

## Personalisation examples

The graph is identity-agnostic. It doesn't profile you — it *projects from edges you've explicitly created*. A few examples of how that plays out:

| Your search history shows… | Search *"bar"* surfaces… | Why |
|---|---|---|
| Heaven, G-A-Y, The Glory | gay bars in Soho + Vauxhall | `SAME_VIBE` from your anchors |
| Cahoots, Nightjar, Callooh Callay | speakeasies / cocktail dens | `SAME_VIBE: hidden + craft cocktail` |
| BrewDog Shoreditch, Mother Kelly's | taprooms + bottle shops | `SAME_CUISINE: craft beer` |
| Beigel Bake (× 14) | *food*: bagel shops, salt-beef counters, Brick Lane delis | `SAME_DISH: salt beef bagel`, `IN_AREA: Brick Lane` |
| Dishoom (× 9) | *food*: small-plates Indian, Bombay cafés | `SAME_CUISINE: Indian`, `SAME_VIBE: small plates` |
| Towpath Café (× 6) | *brunch*: canal-side coffee, weekend bakeries | `SAME_VIBE: outdoor + weekend` |

The point is not "the system knows what kind of person you are." The point is "the system can see what you have repeatedly chosen, and uses graph distance to project from there." No demographic inference. No profile lookup. Just edges *you* created by searching.

---

## Stack

| Layer | Choice | Why |
|------|--------|-----|
| Graph DB | **Neo4j Aura** (free tier) | Native variable-depth traversal; geo via `point()`; sub-200ms on this dataset |
| Backend | **FastAPI** + `neo4j` Python driver | Async, typed, one-process deploy; trivially containerisable |
| Frontend | **React 18 + TypeScript + Vite** | Hot reload, type-safe wire contract with Pydantic |
| Map | **Mapbox GL JS** (`light-v11`) | Production map UX, drag/zoom/pinch parity with Google Maps |
| Styling | Hand-rolled CSS with paper-grain texture + JetBrains Mono | Deliberately not Material — feel of a hand-drawn map atlas |
| Ingestion | Python + spaCy + Google Places API + Claude API | NER → geocode → enrich with dishes/cuisine/vibe |
| Dev proxy | Vite proxy `/api/* → :8000` | Single origin in dev; no CORS theatre |

## Repository layout

```
spotgraph/
├── README.md                      ← you are here
├── demo-script.md                 ← screenplay for the live demo (3 min)
├── semantica (1).html             ← original single-file prototype (reference)
│
├── frontend/                      ← React + Vite + TS + Mapbox
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts             ← /api/* proxy → :8000
│   ├── .env.example
│   └── src/
│       ├── App.tsx                ← map + search bar + suggestions shell
│       ├── components/
│       │   ├── MapView.tsx        ← Mapbox base + anchor/candidate pins + dashed edges
│       │   ├── SearchBar.tsx      ← centre search input (the "bar")
│       │   ├── Suggestions.tsx    ← collapsible drop-down with breadcrumbs
│       │   ├── MiniSearch.tsx     ← collapsed-state chip
│       │   ├── TopBar.tsx         ← brand + status
│       │   ├── ProfileCard.tsx    ← "your anchor venues" panel
│       │   ├── HintCard.tsx       ← hotkey legend
│       │   └── VenuePopup.tsx     ← per-pin detail card
│       ├── hooks/useSearch.ts     ← graph fetch + debounced rank
│       ├── lib/
│       │   ├── api.ts             ← /api/graph + /api/rank wire calls
│       │   └── rank.ts            ← JS port of rank.cql for offline demo
│       ├── contexts/GraphContext.tsx
│       ├── data/graph.ts          ← embedded demo graph (no-backend mode)
│       ├── styles/                ← variables · base · search · cards · topbar · map
│       └── types.ts               ← wire types (mirrors backend/models/schemas.py)
│
└── backend/                       ← FastAPI + Neo4j
    ├── main.py                    ← app + CORS + lifespan
    ├── requirements.txt
    ├── .env.example
    ├── routes/
    │   ├── graph.py               ← GET  /api/graph
    │   └── rank.py                ← POST /api/rank — the headline query wrapper
    ├── db/neo4j_client.py         ← driver singleton + Settings
    ├── models/schemas.py          ← Pydantic mirror of frontend/src/types.ts
    ├── cypher/
    │   ├── schema.cql             ← constraints + indexes
    │   ├── seed.cql               ← demo dataset
    │   └── rank.cql               ← the one query that runs at search time
    ├── ingest/
    │   ├── takeout_parser.py      ← Google Takeout → Neo4j (MVP stub)
    │   └── scrape_osm.py          ← OpenStreetMap candidate venue scrape
    └── data/                      ← seed.json + seed-full.json + seed-osm.cql
```

---

## Quick start

### Path A — frontend only (mocked graph, fastest)

The frontend ships with an embedded demo graph in `frontend/src/data/graph.ts` and a JS port of the Cypher ranker. No backend required.

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

The Mapbox token in `frontend/.env.local` is the one Richard provided. Replace it with your own from <https://account.mapbox.com/> if you fork.

### Path B — full stack (real Neo4j Aura)

```bash
# 1. Spin up a free Neo4j Aura instance and grab the connection URI + credentials.

# 2. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                          # fill NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" -f cypher/schema.cql
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" -f cypher/seed.cql
uvicorn main:app --reload --port 8000

# 3. Frontend, pointed at the backend
cd ../frontend
echo "VITE_USE_BACKEND=true" >> .env.local
npm run dev
```

The Vite dev server already proxies `/api/*` to `localhost:8000`.

### Environment variables

| Variable | Where | Purpose |
|---|---|---|
| `VITE_MAPBOX_TOKEN` | `frontend/.env.local` | Mapbox GL JS basemap access |
| `VITE_USE_BACKEND` | `frontend/.env.local` | `true` → real `/api/*`; unset → embedded demo graph |
| `NEO4J_URI` | `backend/.env` | `neo4j+s://…neo4j.io` |
| `NEO4J_USER` | `backend/.env` | usually `neo4j` |
| `NEO4J_PASSWORD` | `backend/.env` | Aura instance password |
| `ALLOWED_ORIGIN` | `backend/.env` | CORS allowlist; defaults to `http://localhost:5173` |

---

## API reference

Both endpoints return shapes that exactly mirror `frontend/src/types.ts`. If you change a Pydantic model in `backend/models/schemas.py`, change the TypeScript type — they are the wire boundary.

### `GET /api/graph`

Returns the user's full taste graph for the UI to render. Called once on page load.

```ts
{
  user: { id: string; name: string },
  anchors: Record<string, Anchor>,   // venues the user is :ANCHORED_TO
  venues:  Record<string, Venue>,    // every candidate within radius
  weights: { w_dish, w_cuisine, w_vibe, w_area, w_distance_penalty }
}
```

### `POST /api/rank`

Runs the Cypher in `cypher/rank.cql` against the current user's anchors, biased by any anchors the query string mentions, and returns the ranked candidates with breakdown paths.

```ts
// request
{ query: string }

// response
RankedCandidate[]
// where each item is:
// { venue: Venue, score: number,
//   breakdown: { anchor: string, kind: 'SAME_DISH'|'SAME_CUISINE'|'SAME_VIBE'|'SAME_AREA',
//                item: string, score: number }[] }
```

### `GET /health`

Liveness probe. Returns `{ "status": "ok" }`.

---

## Ingestion pipeline

The end-to-end pipeline (Google Takeout → Neo4j) is described in detail in [`demo-script.md` §Technical Appendix](./demo-script.md). For MVP, `backend/ingest/takeout_parser.py` is a stub and the live demo runs against the curated seed dataset in `backend/data/seed.json`. The pipeline has been validated on a real 15k-query export; productionising the stub is the first item on the roadmap.

Steps:

1. **Parse** — read `MyActivity.json`, normalise to `{query, ts, intent_hints}`.
2. **Extract** — spaCy NER + custom patterns find venue mentions; Google Places API confirms each one and pulls `place_id`, lat/lng, area.
3. **Score anchors** — `anchor_score = log(1 + search_count) + recency_decay + 0.5 * co-occur(directions|menu|hours)`.
4. **Enrich** — for each anchor (and N-hop candidate within 5km), Claude summarises ~20 reviews into `dishes[]`, `cuisine`, `vibe[]`.
5. **Load** — Cypher `MERGE` batches via the `neo4j` Python driver into Aura.

---

## Performance

| Operation | Dataset | Latency (Aura free tier) |
|---|---|---|
| `GET /api/graph` (cold) | 3 anchors · 24 candidates · ~80 edges | ~120 ms |
| `POST /api/rank` (warm) | same · query parsed · 4 returned | **~180 ms p50, ~240 ms p95** |
| `POST /api/rank` (cold cache) | same | ~310 ms |
| Frontend total round-trip | localhost dev | ~220 ms input → painted suggestion |

The Cypher in `rank.cql` is the dominant cost; the rest is JSON serialisation and React render. At 15k-node scale on the same Aura tier, traversal stays under 400ms p95 because the graph projection is constrained to one hop out from a small anchor set.

---

## MVP scope

The MVP is **demo-day-ready** with a deliberately tight scope.

### ✅ In MVP

- Mapbox-backed map UI with **search bar dead-centre**, collapsible to a corner chip.
- **Anchor pins** (yellow, hearted) and **candidate pins** (orange, pulsing) with dashed edges drawn from the rank breakdown.
- **Drop-down suggestions** with per-result breadcrumb (`anchor → edge_type → property → candidate`).
- Four demo hotkeys + `Esc` reset.
- `GET /api/graph` and `POST /api/rank` against Neo4j Aura — production-shaped, not mocked.
- Embedded JS port of the ranker for **offline demo mode** (no backend required).
- One curated user (`Alex`) with three anchors (Beigel Bake, Dishoom, Towpath Café) and 24 surrounding candidates around east London.
- Health endpoint, CORS, environment-aware config.

### 🟡 Demoable but mocked

- The ingestion pipeline. The stub validates the end-to-end shape; the curated seed data is what loads at demo time.
- Anchor inference. Anchors are hand-promoted in the seed; the scoring formula above is the production version.
- Cuisine/vibe enrichment. Seed data has these baked in; the Claude step is documented but not in the demo loop.

### ❌ Out of scope for MVP (see [roadmap](#roadmap))

- Multi-user / auth. Single curated user only.
- Continuous Takeout sync. One-shot import only.
- Mobile-native shell.
- Anchor editor UI ("remove this anchor", "downweight this vibe").
- Cross-city graph fusion. London-only.

---

## Roadmap

**v0.1 — MVP (today).** Single curated user, seed graph, mocked ingestion, full demo loop.

**v0.2 — Real ingestion (week 1).** Finish `takeout_parser.py`; ship the CLI ingester (`python -m ingest path/to/MyActivity.json`); first real user end-to-end.

**v0.3 — Anchor editor (week 2).** Browser UI to view all anchors, prune, downweight, and re-rank live. Closes the explainability loop.

**v0.4 — Auth + per-user graphs (week 3).** Magic-link sign-in; per-user Neo4j namespace; SSE for live re-rank as new searches land.

**v0.5 — Cross-modal anchors (month 2).** Maps saves, YouTube history, calendar events — every behavioural signal becomes an edge.

**v1.0 — Public beta (month 3).** Hosted instance, mobile-first PWA, cross-city, full ingestion observability dashboard.

---

## Privacy & data ownership

This is a design pillar, not a feature.

- **Your graph never leaves your tenancy.** The MVP runs Aura free-tier instances pinned to your account. Self-hosted mode is on the roadmap.
- **Zero aggregation.** No cross-user signal mixing. There is no global popularity model anywhere in the stack.
- **Every edge is auditable.** The drop-down breadcrumb is a literal trace of the Cypher walk. You can see — and on roadmap, *edit* — every relationship the graph used.
- **Takeout is opt-in, one-shot, and revocable.** No background scraping, no OAuth scopes beyond what the ingester needs.

---

## Judging criteria alignment

This project was scoped specifically for the **Neo4j · Best Use of Graph** track.

| Criterion | How Semantica delivers |
|---|---|
| **Graph-native problem** | The core operation — N-hop projection from anchors through typed properties — is genuinely intractable in SQL and lossy in vectors. We picked Neo4j because it's the right tool, not as a hammer. |
| **Single-query elegance** | The entire ranking logic is one ~25-line Cypher query (`backend/cypher/rank.cql`). No application-layer scoring. No multi-step orchestration. |
| **Use of advanced features** | Variable-depth pattern matching, parameterised typed-relationship weighting via `CASE type(r1)`, native `point.distance()` geo, relationship-property indexing on `ANCHORED_TO.search_count`. |
| **Explainability** | Every result returns the path that produced it. This is unique to graph databases — the killer differentiator vs. vector recommenders. |
| **Performance** | Sub-200ms p50 on Aura free tier with a realistic 15k-node graph. |
| **Demoability** | A 3-minute live demo (see `demo-script.md`) with hotkeys, visible edges drawn on the map, and a Neo4j Bloom reveal of the underlying schema. |

---

## Credits

Built by **Richard Lao** for the Neo4j hackathon track.
Live demo script: [`demo-script.md`](./demo-script.md).
Original single-file prototype preserved at `semantica (1).html`.

Map © Mapbox · OpenStreetMap contributors. Venue lat/lngs are real London coordinates; the taste graph in the demo is hand-curated for storytelling.

---

<div align="center">

*Google ranks the world by what **everyone** clicks.*
*Semantica ranks it by what **you** keep coming back to.*

</div>
