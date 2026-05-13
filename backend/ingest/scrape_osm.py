"""Scrape East London restaurants / cafes / pubs from OpenStreetMap.

Free, no API key. Uses the Overpass API.

Outputs three artifacts:
  - backend/data/seed.json          → full graph JSON (user, anchors, venues, weights)
  - frontend/public/seed.json       → same file copied for the frontend to fetch()
  - backend/data/seed-osm.cql       → Cypher MERGE statements for Neo4j Aura

Anchor selection: from venues within ~1km of the user centre, take up to 7
distinct primary cuisines and synthesise plausible search-history counts.
Everything else becomes a candidate.

Run:
    python -m ingest.scrape_osm
"""

from __future__ import annotations

import json
import math
import random
import urllib.parse
import urllib.request
from pathlib import Path

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# (south, west, north, east) — Shoreditch / Spitalfields / Hackney / Whitechapel / parts of City
BBOX = (51.495, -0.135, 51.555, -0.030)

USER_CENTER = (-0.0726, 51.5225)  # near Brick Lane

# Neighborhood centroids — closest one becomes the venue's area.
NEIGHBORHOODS = {
    "shoreditch":     (-0.078, 51.527),
    "spitalfields":   (-0.074, 51.519),
    "whitechapel":    (-0.064, 51.5165),
    "bethnal_green":  (-0.054, 51.527),
    "clerkenwell":    (-0.105, 51.523),
    "hackney":        (-0.057, 51.547),
    "broadway_mkt":   (-0.060, 51.538),
    "brick_lane":     (-0.072, 51.522),
    "smithfield":     (-0.100, 51.519),
    "borough_mkt":    (-0.090, 51.503),
    "soho":           (-0.133, 51.513),
    "haggerston":     (-0.075, 51.541),
    "highbury":       (-0.098, 51.545),
    "marylebone":     (-0.153, 51.519),
    "regents_canal":  (-0.076, 51.540),
    "old_street":     (-0.087, 51.526),
    "barbican":       (-0.094, 51.520),
    "london_fields":  (-0.062, 51.541),
    "dalston":        (-0.075, 51.546),
    "city":           (-0.085, 51.515),
    "hoxton":         (-0.080, 51.532),
}


def overpass_query() -> str:
    s, w, n, e = BBOX
    return (
        f"[out:json][timeout:120];"
        f"("
        f'  node["amenity"~"^(restaurant|cafe|fast_food|pub|bar|food_court|ice_cream)$"]({s},{w},{n},{e});'
        f'  way["amenity"~"^(restaurant|cafe|fast_food|pub|bar|food_court|ice_cream)$"]({s},{w},{n},{e});'
        f");"
        f"out center tags;"
    )


def fetch_osm() -> dict:
    body = urllib.parse.urlencode({"data": overpass_query()}).encode()
    req = urllib.request.Request(
        OVERPASS_URL,
        data=body,
        method="POST",
        headers={
            # Overpass blocks the bare urllib UA with 406 — give it a real one.
            "User-Agent": "spotgraph-osm-scraper/0.1 (hackathon; richard@seractech.co.uk)",
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read())


def nearest_area(lon: float, lat: float) -> str:
    return min(
        NEIGHBORHOODS,
        key=lambda n: math.hypot(NEIGHBORHOODS[n][0] - lon, NEIGHBORHOODS[n][1] - lat),
    )


def km_distance(lon: float, lat: float) -> float:
    dx = (lon - USER_CENTER[0]) * 111.0 * math.cos(math.radians(lat))
    dy = (lat - USER_CENTER[1]) * 111.0
    return math.hypot(dx, dy)


# Cuisine → likely dish keywords. Hand-tuned for London street food / restaurant scene.
CUISINE_DISHES: dict[str, list[str]] = {
    "indian":          ["curry", "naan", "biryani", "daal"],
    "pakistani":       ["karahi_gosht", "biryani", "seekh_kebab", "lamb_chops"],
    "bangladeshi":     ["curry", "naan", "biryani"],
    "south_indian":    ["dosa", "rasam", "chettinad_duck"],
    "chinese":         ["dim_sum", "noodles", "char_siu"],
    "japanese":        ["sushi", "ramen", "katsu"],
    "korean":          ["bibimbap", "kimchi", "korean_bbq"],
    "vietnamese":      ["pho", "banh_mi", "spring_rolls"],
    "thai":            ["pad_thai", "green_curry", "som_tam"],
    "malaysian":       ["nasi_lemak", "laksa"],
    "indonesian":      ["nasi_goreng", "satay"],
    "italian":         ["pasta", "pizza", "gnocchi"],
    "pizza":           ["pizza", "neapolitan_pizza"],
    "french":          ["steak_frites", "moules", "croque_monsieur"],
    "spanish":         ["tapas", "paella", "jamon"],
    "portuguese":      ["bacalhau", "pastel_de_nata"],
    "turkish":         ["kebab", "meze", "lahmacun"],
    "greek":           ["souvlaki", "moussaka", "halloumi"],
    "lebanese":        ["hummus", "shawarma", "tabbouleh"],
    "middle_eastern":  ["hummus", "shawarma", "babaganoush"],
    "persian":         ["chelo_kebab", "saffron_rice"],
    "ethiopian":       ["injera", "tibs", "doro_wat"],
    "mexican":         ["tacos", "burrito", "quesadilla"],
    "argentinian":     ["steak", "empanadas"],
    "peruvian":        ["ceviche", "lomo_saltado"],
    "brazilian":       ["feijoada", "picanha"],
    "american":        ["burger", "fries", "buffalo_wings"],
    "burger":          ["burger", "fries"],
    "bbq":             ["brisket", "ribs", "pulled_pork"],
    "british":         ["fish_chips", "sunday_roast", "bangers_mash"],
    "modern_british":  ["seasonal", "tasting_menu", "bone_marrow"],
    "fish_and_chips":  ["fish_chips", "mushy_peas"],
    "pub":             ["sunday_roast", "fish_chips", "pub_burger"],
    "gastropub":       ["sunday_roast", "seasonal"],
    "seafood":         ["oysters", "fish_chips"],
    "sushi":           ["sushi", "sashimi"],
    "ramen":           ["ramen", "gyoza"],
    "noodle":          ["noodles", "udon"],
    "dumpling":        ["dumplings", "xiao_long_bao"],
    "sandwich":        ["sandwich", "panini"],
    "salad":           ["salad", "grain_bowl"],
    "bagel":           ["salt_beef_bagel", "cream_cheese_bagel"],
    "bakery":          ["pastries", "sourdough", "laminated_dough"],
    "coffee_shop":     ["flat_white", "espresso", "pastries"],
    "cafe":            ["flat_white", "sourdough_toast", "pastries"],
    "ice_cream":       ["gelato", "sorbet"],
    "tea":             ["matcha", "afternoon_tea"],
    "vegan":           ["vegan_bowl", "jackfruit_bao"],
    "vegetarian":      ["veg_curry", "halloumi"],
    "kosher":          ["challah", "babka"],
    "jewish":          ["salt_beef_bagel", "challah", "babka"],
    "mediterranean":   ["mezze", "grilled_lamb", "hummus"],
    "asian":           ["noodles", "dumplings"],
    "international":   ["seasonal_menu"],
    "fast_food":       ["burger", "fries"],
    "chicken":         ["fried_chicken", "wings"],
    "regional":        ["seasonal"],
}


def derive_dishes(cuisine: list[str]) -> list[str]:
    dishes: list[str] = []
    for c in cuisine:
        dishes.extend(CUISINE_DISHES.get(c, []))
    seen: set[str] = set()
    out: list[str] = []
    for d in dishes:
        if d in seen:
            continue
        seen.add(d)
        out.append(d)
    return out[:5]


def derive_vibe(tags: dict, amenity: str) -> list[str]:
    v: list[str] = []
    if amenity == "cafe":      v.extend(["cafe", "bright"])
    if amenity == "fast_food": v.extend(["counter_service", "cheap_eats", "takeaway"])
    if amenity == "pub":       v.extend(["pub"])
    if amenity == "bar":       v.extend(["loud", "atmospheric"])
    if amenity == "food_court":v.extend(["bustling", "counter_service"])
    if amenity == "ice_cream": v.append("counter_service")

    if tags.get("outdoor_seating") in ("yes", "seasonal"): v.append("outdoor")
    if tags.get("takeaway") == "yes":                      v.append("takeaway")
    if tags.get("delivery") == "yes":                      v.append("delivery")
    if tags.get("internet_access") in ("wlan", "yes"):     v.append("design_y")
    if tags.get("smoking") in ("outside", "no"):           pass
    if tags.get("reservation") in ("no", "not_required"):  v.append("no_frills")
    if tags.get("organic") == "yes":                       v.append("local_favourite")

    oh = (tags.get("opening_hours") or "").lower()
    if "24/7" in oh or "03:" in oh or "04:" in oh:         v.append("late_night")

    # Dedupe, cap at 5
    seen: set[str] = set()
    out: list[str] = []
    for vb in v:
        if vb in seen:
            continue
        seen.add(vb)
        out.append(vb)
    return out[:5]


def derive_cuisine(tags: dict, amenity: str) -> list[str]:
    raw = (tags.get("cuisine") or "").lower()
    if raw:
        out = [
            c.strip().replace(" ", "_").replace("-", "_")
            for c in raw.replace(",", ";").split(";")
            if c.strip()
        ]
        return out[:4]
    # Fallback by amenity
    if amenity == "cafe":      return ["cafe"]
    if amenity == "pub":       return ["british", "pub"]
    if amenity == "bar":       return ["bar"]
    if amenity == "fast_food": return ["fast_food"]
    if amenity == "ice_cream": return ["ice_cream"]
    return ["misc"]


def process(osm: dict) -> list[dict]:
    out: list[dict] = []
    for el in osm.get("elements", []):
        tags = el.get("tags") or {}
        name = tags.get("name")
        if not name:
            continue
        lon = el.get("lon")
        lat = el.get("lat")
        if lon is None or lat is None:
            c = el.get("center") or {}
            lon, lat = c.get("lon"), c.get("lat")
        if lon is None or lat is None:
            continue
        amenity = tags.get("amenity") or ""
        cuisine = derive_cuisine(tags, amenity)
        dishes = derive_dishes(cuisine)
        if not dishes:
            dishes = ["seasonal_menu"]
        out.append(
            {
                "id": f"osm_{el['type']}_{el['id']}",
                "name": name,
                "area": nearest_area(lon, lat),
                "loc": [round(lon, 6), round(lat, 6)],
                "dishes": dishes,
                "cuisine": cuisine,
                "vibe": derive_vibe(tags, amenity),
                "dist": round(km_distance(lon, lat), 2),
            }
        )
    # Dedupe by (lower name + rough loc)
    seen: set[tuple] = set()
    unique: list[dict] = []
    for v in out:
        key = (v["name"].lower(), round(v["loc"][0], 4), round(v["loc"][1], 4))
        if key in seen:
            continue
        seen.add(key)
        unique.append(v)
    return unique


# Iconic East London venues to use as anchors when they appear in the OSM
# scrape. These give the demo a recognisable storyline ("I love Beigel Bake")
# instead of whatever happens to score highest algorithmically.
# Iconic East London venues to use as anchors when they appear in the OSM
# scrape. Order matters — first match wins, so put the most-wanted first.
# Each entry: (search_needle, hint) where hint helps disambiguate among
# multiple candidates (e.g. "st john" matches several things; we want the
# restaurant in Smithfield, not a street or a bar).
ICONIC_ANCHORS: list[tuple[str, dict]] = [
    ("beigel bake", {}),
    ("dishoom", {}),
    ("towpath", {}),
    ("e pellicci", {}),
    ("lahore kebab", {}),
    ("st john", {"area": "smithfield"}),  # restaurant in Smithfield specifically
    ("caravan", {"area_in": {"clerkenwell"}}),
    ("ottolenghi", {}),
    ("lyle's", {}),
    ("pophams", {}),
    ("climpson", {}),
    ("smokestak", {}),
    ("padella", {}),
    ("brat", {}),
    ("som saa", {}),
    ("the marksman", {}),
]

# Words in a name that suggest it's actually a street/road, not a venue.
STREET_WORDS = {"street", "road", "lane", "avenue", "place", "court"}


def _name_match(name: str, needle: str) -> bool:
    name_clean = name.lower().replace(".", "").replace(",", "").strip()
    needle_clean = needle.replace(".", "").strip()
    # Reject obvious street names that happen to share the needle
    tokens = name_clean.split()
    if STREET_WORDS & set(tokens):
        return False
    return needle_clean in name_clean


def pick_anchors(venues: list[dict], n: int = 7) -> tuple[list[dict], list[dict]]:
    """Pick iconic anchors first (by name match), then fill remaining slots
    algorithmically with distinct-cuisine, well-tagged, close-to-centre venues."""
    anchors: list[dict] = []
    anchor_ids: set[str] = set()
    cuisines_seen: set[str] = set()

    def add(v: dict) -> None:
        rng = random.Random(hash(v["id"]) & 0xFFFFFFFF)
        anchors.append(
            {
                **v,
                "dist": 0,
                "searchCount": rng.randint(6, 18),
                "saves": rng.randint(2, 7),
                "directions": rng.randint(3, 11),
            }
        )
        anchor_ids.add(v["id"])
        if v["cuisine"]:
            cuisines_seen.add(v["cuisine"][0])

    # 1) Iconic-name pass — prefer hinted-area match if available, else any
    for needle, hint in ICONIC_ANCHORS:
        if len(anchors) >= n:
            break
        matches = [
            v
            for v in venues
            if v["id"] not in anchor_ids and _name_match(v["name"], needle)
        ]
        if not matches:
            continue
        # Apply hint filters
        if "area" in hint:
            preferred = [v for v in matches if v["area"] == hint["area"]]
            if preferred:
                matches = preferred
        if "area_in" in hint:
            preferred = [v for v in matches if v["area"] in hint["area_in"]]
            if preferred:
                matches = preferred
        # Prefer the one with the richest tag coverage
        matches.sort(
            key=lambda v: -(len(v["cuisine"]) + len(v["vibe"]) + len(v["dishes"]))
        )
        add(matches[0])

    # 2) Algorithmic fill — closest, best-tagged, distinct primary cuisine
    def score(v: dict) -> float:
        return (
            v["dist"]
            - 0.4 * len(v["cuisine"])
            - 0.3 * len(v["vibe"])
            - 0.4 * len(v["dishes"])
        )

    for v in sorted(venues, key=score):
        if len(anchors) >= n:
            break
        if v["id"] in anchor_ids:
            continue
        if v["cuisine"] in ([], ["misc"]):
            continue
        primary = v["cuisine"][0] if v["cuisine"] else None
        if primary in cuisines_seen:
            continue
        add(v)

    remaining = [v for v in venues if v["id"] not in anchor_ids]
    return anchors, remaining


def to_seed_json(anchors: list[dict], venues: list[dict]) -> dict:
    return {
        "user": {"id": "u_alex", "name": "Alex Chen", "center": list(USER_CENTER)},
        "anchors": {a["id"]: a for a in anchors},
        "venues": {v["id"]: v for v in venues},
        "weights": {
            "SAME_DISH": 3.0,
            "SAME_CUISINE": 1.5,
            "SAME_VIBE": 1.0,
            "SAME_AREA": 1.2,
            "DISTANCE_PENALTY": 0.15,
        },
    }


def cypher_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'")


def to_cypher(seed: dict) -> str:
    """Emit MERGE statements that load this dataset into Neo4j."""
    lines: list[str] = [
        "// Auto-generated from OSM Overpass scrape — do not hand-edit.",
        "",
        f"MERGE (u:User {{id: '{seed['user']['id']}'}})",
        f"SET u.name = '{cypher_escape(seed['user']['name'])}',",
        f"    u.center = point({{longitude: {seed['user']['center'][0]}, latitude: {seed['user']['center'][1]}}});",
        "",
    ]
    # Build the area set
    areas = {v["area"] for v in seed["venues"].values()} | {
        a["area"] for a in seed["anchors"].values()
    }
    areas_list = ",".join(f"'{a}'" for a in sorted(areas))
    lines += [
        f"UNWIND [{areas_list}] AS area MERGE (:Area {{name: area}});",
        "",
    ]

    def emit_venue(v: dict, anchor: bool) -> list[str]:
        dishes = ",".join(f"'{cypher_escape(d)}'" for d in v["dishes"])
        cuisine = ",".join(f"'{cypher_escape(c)}'" for c in v["cuisine"])
        vibe = ",".join(f"'{cypher_escape(vb)}'" for vb in v["vibe"])
        sub: list[str] = [
            f"MERGE (v:Venue {{id: '{cypher_escape(v['id'])}'}})",
            f"SET v.name = '{cypher_escape(v['name'])}',",
            f"    v.loc  = point({{longitude: {v['loc'][0]}, latitude: {v['loc'][1]}}}),",
            f"    v.dist = {v['dist']}",
            "WITH v",
        ]
        if anchor:
            sub.append(
                f"MATCH (u:User {{id: '{seed['user']['id']}'}}) "
                f"MERGE (u)-[a:ANCHORED_TO]->(v) "
                f"SET a.search_count = {v.get('searchCount', 0)}, "
                f"a.saves = {v.get('saves', 0)}, a.directions = {v.get('directions', 0)}"
            )
            sub.append("WITH v")
        sub.append(
            f"MATCH (area:Area {{name: '{v['area']}'}}) MERGE (v)-[:IN_AREA]->(area)"
        )
        if dishes:
            sub.append(
                f"FOREACH (d IN [{dishes}] | MERGE (x:Dish {{name: d}}) MERGE (v)-[:SERVES]->(x))"
            )
        if cuisine:
            sub.append(
                f"FOREACH (c IN [{cuisine}] | MERGE (x:Cuisine {{name: c}}) MERGE (v)-[:HAS_CUISINE]->(x))"
            )
        if vibe:
            sub.append(
                f"FOREACH (vb IN [{vibe}] | MERGE (x:Vibe {{name: vb}}) MERGE (v)-[:HAS_VIBE]->(x))"
            )
        sub[-1] = sub[-1] + ";"
        return sub

    for a in seed["anchors"].values():
        lines += emit_venue(a, anchor=True) + [""]
    for v in seed["venues"].values():
        lines += emit_venue(v, anchor=False) + [""]
    return "\n".join(lines)


def is_demo_quality(v: dict) -> bool:
    """Curated subset filter — keep only well-tagged, semantically rich venues
    for the frontend demo. The full scrape still goes to Neo4j."""
    if v["cuisine"] in ([], ["misc"]):
        return False
    if len(v["vibe"]) < 2:
        return False
    if v["dist"] > 3.5:
        return False
    return True


def main() -> None:
    here = Path(__file__).resolve().parent.parent  # backend/
    repo = here.parent
    data_dir = here / "data"
    public_dir = repo / "frontend" / "public"
    data_dir.mkdir(parents=True, exist_ok=True)
    public_dir.mkdir(parents=True, exist_ok=True)

    print("Querying OSM Overpass…")
    osm = fetch_osm()
    print(f"  fetched {len(osm.get('elements', []))} raw elements")

    venues = process(osm)
    print(f"  kept {len(venues)} named, located venues")

    random.seed(42)
    full_anchors, full_remaining = pick_anchors(venues, n=7)
    print(
        f"  FULL: {len(full_anchors)} anchors, {len(full_remaining)} candidates "
        f"(for Neo4j load)"
    )

    full_seed = to_seed_json(full_anchors, full_remaining)
    full_json = json.dumps(full_seed, indent=2)
    (data_dir / "seed-full.json").write_text(full_json)
    (data_dir / "seed-osm.cql").write_text(to_cypher(full_seed))

    # Curated demo subset
    demo_candidates = [v for v in full_remaining if is_demo_quality(v)]
    # If still too large, take the N closest-to-centre with best tag coverage
    demo_candidates.sort(
        key=lambda v: (v["dist"], -len(v["cuisine"]) - len(v["vibe"]) - len(v["dishes"]))
    )
    demo_candidates = demo_candidates[:400]
    print(f"  DEMO: {len(full_anchors)} anchors, {len(demo_candidates)} candidates "
          f"(for frontend)")

    demo_seed = to_seed_json(full_anchors, demo_candidates)
    demo_json = json.dumps(demo_seed, indent=2)
    (data_dir / "seed.json").write_text(demo_json)
    (public_dir / "seed.json").write_text(demo_json)

    print(f"  → {data_dir / 'seed.json'}            ({len(demo_json) // 1024} KB)")
    print(f"  → {public_dir / 'seed.json'}          ({len(demo_json) // 1024} KB)")
    print(f"  → {data_dir / 'seed-full.json'}        ({len(full_json) // 1024} KB)")
    print(f"  → {data_dir / 'seed-osm.cql'}")
    print("done.")


if __name__ == "__main__":
    main()
