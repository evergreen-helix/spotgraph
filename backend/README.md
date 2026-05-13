# Semantica — Backend

FastAPI + Neo4j. Single `/api/rank` endpoint that runs one Cypher
query to walk from a user's anchor venues to candidate venues along
shared dish / cuisine / vibe / area edges.

## Quick start

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# fill in your Neo4j Aura credentials in .env

# load schema and seed
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" -f cypher/schema.cql
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" -f cypher/seed.cql

uvicorn main:app --reload --port 8000
```

Frontend Vite dev server proxies `/api/*` to port 8000, so flip
`VITE_USE_BACKEND=true` in `frontend/.env.local` and you're wired.

## Layout

```
backend/
├── main.py                # FastAPI app + CORS + lifespan
├── routes/
│   ├── graph.py           # GET /api/graph
│   └── rank.py            # POST /api/rank — the headline query
├── db/neo4j_client.py     # driver singleton + Settings
├── models/schemas.py      # Pydantic mirror of frontend types.ts
├── cypher/
│   ├── schema.cql         # constraints + indexes
│   ├── seed.cql           # demo dataset
│   └── rank.cql           # standalone copy of the rank query
└── ingest/
    └── takeout_parser.py  # Google Takeout → Neo4j (stub)
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
