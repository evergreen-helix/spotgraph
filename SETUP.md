# Semantica — From Zero to a Working Demo

End-to-end setup. Copy-paste each block, check the expected output before
moving on. Total time on a clean machine: ~10 minutes.

──────────────────────────────────────────────────────────────────────
PREREQUISITES
──────────────────────────────────────────────────────────────────────

You need:
  - Python 3.10+
  - Node 18+ and npm
  - Docker (for local Neo4j)  — OR a Neo4j Aura account
  - An OpenAI API key (the existing one in backend/.env works)

Check:
    python3 --version   # 3.10+
    node --version      # 18+
    docker --version    # any recent

──────────────────────────────────────────────────────────────────────
STEP 1 — Start Neo4j
──────────────────────────────────────────────────────────────────────

Option A (local, recommended for the demo):

First check whether a previous run already left a container behind:

    docker ps -a --filter name=spotgraph-neo4j --format "{{.Names}} {{.Status}}"

If you see "spotgraph-neo4j Up ...", it's already running — skip to
Step 2 and reuse it (data is preserved unless you destroy the
container).  If you see "spotgraph-neo4j Exited ...", remove it first:

    docker rm spotgraph-neo4j

Then start it:

    docker run -d --rm --name spotgraph-neo4j \
      -p 7687:7687 -p 7474:7474 \
      -e NEO4J_AUTH=neo4j/testpassword \
      neo4j:5-community

Wait ~10 seconds for it to boot, then verify:

    until docker exec spotgraph-neo4j cypher-shell \
      -u neo4j -p testpassword "RETURN 1;" >/dev/null 2>&1; do
      sleep 2
    done
    echo "neo4j ready"

Option B (Aura): create a free instance at https://console.neo4j.io,
then put your bolt URL / user / password into backend/.env (NEO4J_URI,
NEO4J_USER, NEO4J_PASSWORD).

──────────────────────────────────────────────────────────────────────
STEP 2 — Backend env
──────────────────────────────────────────────────────────────────────

    cd backend
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

The .env is already populated with the working OPENAI_API_KEY and
points NEO4J_URI at bolt://localhost:7687. If you switched to Aura in
Step 1, edit backend/.env now and update the four NEO4J_* fields.

──────────────────────────────────────────────────────────────────────
STEP 3 — Load schema + the 6,320-venue OSM scrape
──────────────────────────────────────────────────────────────────────

For local Docker Neo4j:

    docker cp cypher/schema.cql      spotgraph-neo4j:/tmp/
    docker cp data/seed-osm.cql      spotgraph-neo4j:/tmp/
    docker exec spotgraph-neo4j cypher-shell -u neo4j -p testpassword \
      -f /tmp/schema.cql
    docker exec spotgraph-neo4j cypher-shell -u neo4j -p testpassword \
      -f /tmp/seed-osm.cql

For Aura (cypher-shell must be installed locally):

    cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
      -f cypher/schema.cql
    cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
      -f data/seed-osm.cql

Verify (should print 6320 / 7 / 95 / 192 / 15 / 20):

    docker exec spotgraph-neo4j cypher-shell -u neo4j -p testpassword "
      MATCH (v:Venue) RETURN count(v) AS venues;
      MATCH (u:User)-[r:ANCHORED_TO]->() RETURN count(r) AS anchors;
      MATCH (d:Dish) RETURN count(d) AS dishes;
      MATCH (c:Cuisine) RETURN count(c) AS cuisines;
      MATCH (vb:Vibe) RETURN count(vb) AS vibes;
      MATCH (a:Area) RETURN count(a) AS areas;
    "

──────────────────────────────────────────────────────────────────────
STEP 4 — Build the :SIMILAR_TO edges
──────────────────────────────────────────────────────────────────────

This is the offline step that embeds all 6,320 venues with OpenAI and
writes top-5 :SIMILAR_TO edges per anchor. One-time, ~30s, ~$0.007.

    cd backend                # if not already
    source .venv/bin/activate # if not already
    python -m scripts.build_similar_edges

You should see lines like:

    anchor osm_way_271641402   -> top-5 [('Beigel Shop', 0.947),
                                         ('Bagel Factory', 0.803), ...]
    anchor osm_node_3501612811 -> top-5 [('Dishoom', 0.963), ...]

──────────────────────────────────────────────────────────────────────
STEP 5 — Start the backend
──────────────────────────────────────────────────────────────────────

    cd backend
    source .venv/bin/activate
    uvicorn main:app --reload --port 8000

You should see in the logs:

    INFO llm.anchor_cache: anchor cache: loaded 7 anchors from Neo4j
    INFO llm.anchor_cache: anchor cache: 7 anchors embedded
    INFO uvicorn: Application startup complete.

Smoke test from another tab:

    curl http://localhost:8000/health
    # {"status":"ok"}

    curl http://localhost:8000/api/graph | head -c 200
    # JSON starting with {"user":{"id":"u_alex",...},"anchors":{...

    curl -X POST http://localhost:8000/api/rank \
         -H "Content-Type: application/json" \
         -d '{"query":"something like dishoom"}' | python3 -m json.tool | head -40
    # 12 results; top one should be Sagar or Dishoom or Daily Dose
    # breakdown[] contains entries with kind:'SIMILAR_OVERALL' alongside
    # SAME_DISH / SAME_CUISINE / SAME_VIBE / SAME_AREA.

    curl http://localhost:8000/api/metrics | python3 -m json.tool
    # Shows the Kimchi/Cast AI observability stats.

──────────────────────────────────────────────────────────────────────
STEP 6 — Wire the frontend
──────────────────────────────────────────────────────────────────────

Open a third tab.

    cd frontend
    npm install
    # frontend/.env.local already has VITE_MAPBOX_TOKEN.
    # By default it serves the offline OSM seed. To use the live backend:
    #   change VITE_USE_BACKEND=false  ->  VITE_USE_BACKEND=true
    npm run dev

Open http://localhost:5173. Hotkeys:

    1   bagels near me
    2   weekend brunch
    3   curry tonight
    4   where should I eat?
    Esc reset

──────────────────────────────────────────────────────────────────────
WHAT YOU SHOULD SEE IN A SUCCESSFUL DEMO
──────────────────────────────────────────────────────────────────────

For "something like dishoom" the breakdown for each result should show
one of:

    SAME_DISH:curry / SAME_CUISINE:indian / SAME_VIBE:bustling / SAME_AREA
    SIMILAR_OVERALL "similar to Dishoom" — this is new and matters

For "weekend brunch outdoor" the LLM extracts vibe:weekend_brunch +
vibe:outdoor and Cypher boosts candidates that match those tags 1.5x.

──────────────────────────────────────────────────────────────────────
TROUBLESHOOTING
──────────────────────────────────────────────────────────────────────

Symptom: backend logs "anchor cache: ready (no embeddings — no OPENAI_API_KEY)"
  Fix: backend/.env is missing OPENAI_API_KEY. Check the file.

Symptom: /api/rank returns [] for everything.
  Cause 1: Neo4j wasn't loaded with data. Re-run Step 3.
  Cause 2: USER_ID in .env doesn't match any User in Neo4j.
           Should be USER_ID=u_alex.

Symptom: /api/rank works but no SIMILAR_OVERALL breakdown items.
  Fix: build_similar_edges.py hasn't been run. See Step 4.

Symptom: /api/rank returns 500 with "neo4j error".
  Cause: Neo4j unreachable. Check `docker ps` and that the URI in
         backend/.env matches the running instance.

Symptom: openai 401.
  Cause: OPENAI_API_KEY is set but invalid. Get a fresh key.

Symptom: frontend shows "loading graph…" forever.
  Cause: VITE_USE_BACKEND=true but backend isn't running, OR proxy
         misconfigured. Check that uvicorn is up on port 8000.

──────────────────────────────────────────────────────────────────────
TEAR-DOWN
──────────────────────────────────────────────────────────────────────

    docker stop spotgraph-neo4j     # stops Neo4j (data lost — it's --rm)
    # ctrl-c the uvicorn and vite processes
