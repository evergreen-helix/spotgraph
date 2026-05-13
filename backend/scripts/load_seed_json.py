"""Wipe Neo4j and reload from a seed.json file (7 anchors + N candidates).

Usage:
    python -m scripts.load_seed_json [path/to/seed.json]

Defaults to backend/data/seed.json — the demo-quality 400-venue subset.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from db.neo4j_client import session


DEFAULT = Path(__file__).parent.parent / "data" / "seed.json"


def main(path: Path) -> int:
    data = json.loads(path.read_text())
    user = data["user"]
    anchors = list(data["anchors"].values())
    candidates = list(data["venues"].values())

    print(f"loading {path.name}: user={user['name']} anchors={len(anchors)} candidates={len(candidates)}")

    with session() as sess:
        # Wipe everything except User node (which we'll MERGE anyway)
        sess.run("MATCH (n) WHERE NOT n:User DETACH DELETE n")
        sess.run("MATCH (u:User) DETACH DELETE u")

        # User
        sess.run(
            "MERGE (u:User {id: $id}) SET u.name = $name, "
            "u.center = point({longitude: $lng, latitude: $lat})",
            id=user["id"], name=user["name"],
            lng=user["center"][0], lat=user["center"][1],
        )

        # Anchors
        sess.run(
            """
            UNWIND $rows AS row
            MERGE (v:Venue {id: row.id})
            SET v.name = row.name,
                v.loc = point({longitude: row.lng, latitude: row.lat}),
                v.dist = 0.0
            WITH v, row
            MATCH (u:User {id: $uid})
            MERGE (u)-[a:ANCHORED_TO]->(v)
            SET a.search_count = row.sc, a.saves = row.sv, a.directions = row.dr
            WITH v, row
            MERGE (area:Area {name: row.area})
            MERGE (v)-[:IN_AREA]->(area)
            FOREACH (d IN row.dishes  | MERGE (x:Dish    {name: d}) MERGE (v)-[:SERVES]->(x))
            FOREACH (c IN row.cuisine | MERGE (x:Cuisine {name: c}) MERGE (v)-[:HAS_CUISINE]->(x))
            FOREACH (vb IN row.vibe   | MERGE (x:Vibe    {name: vb}) MERGE (v)-[:HAS_VIBE]->(x))
            """,
            uid=user["id"],
            rows=[
                {
                    "id": a["id"], "name": a["name"], "area": a["area"],
                    "lng": a["loc"][0], "lat": a["loc"][1],
                    "dishes": a["dishes"], "cuisine": a["cuisine"], "vibe": a["vibe"],
                    "sc": a.get("searchCount", 0),
                    "sv": a.get("saves", 0),
                    "dr": a.get("directions", 0),
                }
                for a in anchors
            ],
        )

        # Candidates
        sess.run(
            """
            UNWIND $rows AS row
            MERGE (v:Venue {id: row.id})
            SET v.name = row.name,
                v.loc = point({longitude: row.lng, latitude: row.lat}),
                v.dist = row.dist
            WITH v, row
            MERGE (area:Area {name: row.area})
            MERGE (v)-[:IN_AREA]->(area)
            FOREACH (d IN row.dishes  | MERGE (x:Dish    {name: d}) MERGE (v)-[:SERVES]->(x))
            FOREACH (c IN row.cuisine | MERGE (x:Cuisine {name: c}) MERGE (v)-[:HAS_CUISINE]->(x))
            FOREACH (vb IN row.vibe   | MERGE (x:Vibe    {name: vb}) MERGE (v)-[:HAS_VIBE]->(x))
            """,
            rows=[
                {
                    "id": c["id"], "name": c["name"], "area": c["area"],
                    "lng": c["loc"][0], "lat": c["loc"][1], "dist": c.get("dist", 0.0),
                    "dishes": c["dishes"], "cuisine": c["cuisine"], "vibe": c["vibe"],
                }
                for c in candidates
            ],
        )

    print("done")
    return 0


if __name__ == "__main__":
    p = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    sys.exit(main(p))
