"""Augment the hand-curated graph with N additional OSM candidates.

Picks the N closest-to-centre OSM venues from seed-full.json that have a
real cuisine (not 'misc') and at least one dish tag, skips IDs that
already exist, and MERGEs them as candidate venues.

Usage:
    python -m scripts.augment_candidates [N]   # default 1000
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from db.neo4j_client import session


SEED_FULL = Path(__file__).parent.parent / "data" / "seed-full.json"


def main(n: int) -> int:
    data = json.loads(SEED_FULL.read_text())
    all_candidates = list(data["venues"].values())

    # Filter to demo-quality: real cuisine, at least one dish
    filtered = [
        c for c in all_candidates
        if c.get("cuisine") and c["cuisine"] not in (["misc"], [])
        and c.get("dishes")
    ]
    filtered.sort(key=lambda c: c.get("dist", 999.0))
    picks = filtered[:n]

    print(f"loaded {len(all_candidates)} from seed-full.json; "
          f"{len(filtered)} pass quality filter; taking top {len(picks)} by distance")

    with session() as sess:
        # Get IDs already in the graph so we don't duplicate
        existing = {
            r["id"] for r in sess.run("MATCH (v:Venue) RETURN v.id AS id").data()
        }
        new = [c for c in picks if c["id"] not in existing]
        print(f"{len(new)} new (skipping {len(picks) - len(new)} already in graph)")

        if not new:
            return 0

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
                    "dishes": c["dishes"], "cuisine": c["cuisine"], "vibe": c.get("vibe", []),
                }
                for c in new
            ],
        )

        total = sess.run("MATCH (v:Venue) RETURN count(v) AS n").single()["n"]
        print(f"done — graph now has {total} venues total")

    return 0


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    sys.exit(main(n))
