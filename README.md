# Semantica

> Google ranks by what's popular. We rank by what you've already loved.

Personalized venue search backed by a Neo4j taste graph. The user
profile is inferred from search history — repeated searches become
"anchor" venues — and `/api/rank` walks one Cypher query from
those anchors to every candidate venue along shared dish, cuisine,
vibe and area edges. Every recommendation comes with the literal
graph path that produced it.

See [`demo-script.md`](./demo-script.md) for the full pitch and
the headline Cypher query.

## Layout

```
spotgraph/
├── frontend/     # React + Vite + TS, Mapbox GL JS map
├── backend/      # FastAPI + neo4j Python driver
├── demo-script.md
└── semantica (1).html   # original hand-written prototype (reference)
```

## Run the demo (frontend only, mock graph)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The graph is embedded — no backend required.

The Mapbox token in `frontend/.env.local` is the one Richard provided.
Replace it with your own from https://account.mapbox.com if you fork.

## Run the full stack (Neo4j Aura backed)

1. Spin up a free Neo4j Aura instance.
2. Backend:
   ```bash
   cd backend
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env             # fill NEO4J_* values
   cypher-shell -f cypher/schema.cql
   cypher-shell -f cypher/seed.cql
   uvicorn main:app --reload --port 8000
   ```
3. Flip the frontend onto the backend:
   ```bash
   # in frontend/.env.local
   VITE_USE_BACKEND=true
   ```
4. `npm run dev` again.

The Vite dev server proxies `/api/*` to `localhost:8000` already.

## Demo hotkeys

| Key | Query |
|-----|-------|
| `1` | bagels near me |
| `2` | weekend brunch |
| `3` | curry tonight |
| `4` | where should I eat? |
| `Esc` | reset |

## What's mocked vs real

- The Mapbox basemap is real (light-v11 style, scrollable and
  zoomable like Google Maps).
- Venue lat/lngs are real London coordinates.
- The graph itself is mocked in `frontend/src/data/graph.ts` for the
  no-backend demo. The same shape is what `/api/graph` returns in
  production.
- The Cypher query in `backend/cypher/rank.cql` is the real query —
  the JS port in `frontend/src/lib/rank.ts` exists so the frontend
  works offline.
- `backend/ingest/takeout_parser.py` is a stub. The real ingest
  pipeline (Google Takeout → spaCy NER → Places API → Claude
  enrichment → Neo4j) is described in `demo-script.md` §Technical
  Appendix.
