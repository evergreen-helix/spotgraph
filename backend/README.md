# Semantica — Backend

FastAPI + Neo4j + OpenAI. `/api/rank` walks a Neo4j taste graph from
the user's anchor venues to candidates along five edge types
(`SERVES`, `HAS_CUISINE`, `HAS_VIBE`, `IN_AREA`, `SIMILAR_TO`). OpenAI
sits in front for query understanding — embeddings for continuous
anchor boosts, plus structured tag extraction.

## Quick start

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# fill: NEO4J_*, OPENAI_API_KEY

# load schema + the 6,320-venue OSM scrape
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" -f cypher/schema.cql
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" -f data/seed-osm.cql

# build :SIMILAR_TO edges (top-5 per anchor)
python -m scripts.build_similar_edges

uvicorn main:app --reload --port 8000
```

Frontend: `VITE_USE_BACKEND=true` in `frontend/.env.local`.

## Layout

```
backend/
├── main.py                       # FastAPI app + CORS + lifespan (warms anchor cache)
├── llm/
│   ├── client.py                 # OpenAI sync + async singletons
│   ├── embeddings.py             # text-embedding-3-small + cosine
│   ├── query_understanding.py    # embed(query) + extract_tags() in parallel
│   └── anchor_cache.py           # warm at startup: anchor embeddings + vocab
├── routes/
│   ├── graph.py                  # GET /api/graph
│   └── rank.py                   # POST /api/rank — Cypher + LLM
├── scripts/
│   └── build_similar_edges.py    # offline: embed venues, MERGE top-5 :SIMILAR_TO
├── middleware/observability.py   # Kimchi/Cast AI — /api/metrics
├── cypher/
│   ├── schema.cql                # constraints + indexes (incl. SIMILAR_TO)
│   └── rank.cql                  # the 2-branch query (property + similar)
├── ingest/
│   ├── scrape_osm.py             # Overpass → seed.json + seed-osm.cql
│   └── takeout_parser.py         # stub — superseded by OSM ingest
├── data/
│   ├── seed.json                 # 7 anchors + 400 curated (frontend offline mode)
│   ├── seed-full.json            # 7 anchors + 6,313 candidates
│   └── seed-osm.cql              # MERGE statements for the full set
├── db/neo4j_client.py            # driver singleton + Settings
└── models/schemas.py             # Pydantic mirror of frontend types.ts
```

## How a query flows

```
POST /api/rank  query="something like dishoom"
        │
        ├─► embed(query)              ──► cosine vs 7 anchor embeddings
        │                                  → boosts = {dishoom: 2.84, beigel: 1.42, ...}
        ├─► gpt-4o-mini structured    ──► tags = {cuisines:['indian'], vibes:[]}
        │                                  (snapped to controlled vocab)
        │                                  asyncio.gather — both fire in parallel
        ▼
   one Cypher with two branches:
     1. anchor→prop←candidate  (dish/cuisine/vibe/area), tag-match adds 1.5x
     2. anchor-[:SIMILAR_TO]→candidate (cosine baked offline)
   results carry breakdown[] of literal edges → frontend shows the path.
```

## Contracts

Both endpoints return shapes that exactly match
`frontend/src/types.ts`. If you change a Pydantic model, change the
TS type — they are the wire boundary.

### GET /api/graph
```ts
{ user, anchors: Record<id, Anchor>, venues: Record<id, Venue>, weights }
```

### POST /api/rank
```ts
// request
{ query: string }
// response
RankedCandidate[]
```
