"""Offline Google Takeout -> Neo4j ingest pipeline.

This implementation stays deterministic and local:

1. Parse `MyActivity.json` into SearchEvent rows.
2. Normalize queries and infer venue hits from the seeded demo catalog.
3. Score anchors from frequency, recency, and intent.
4. Reuse catalog metadata for dishes/cuisine/vibe enrichment.
5. Write the resulting graph into Neo4j using the existing schema.

It is not a replacement for a full Places/LLM ingest path, but it is
useful today and exercises the real graph model end to end.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

SEED_PATH = Path(__file__).resolve().parents[1] / "cypher" / "seed.cql"
MAX_ANCHORS = 7

INTENT_PATTERNS: dict[str, re.Pattern[str]] = {
    "directions": re.compile(r"\b(directions|route|how to get|navigate)\b", re.I),
    "menu": re.compile(r"\b(menu)\b", re.I),
    "hours": re.compile(r"\b(hours|opening times|open now|closing time)\b", re.I),
    "save": re.compile(r"\b(save|bookmark|favourite|favorite)\b", re.I),
}

ALIAS_OVERRIDES: dict[str, set[str]] = {
    "beigel": {"beigel bake", "beigel", "beigel bake brick lane"},
    "dishoom": {"dishoom"},
    "towpath": {"towpath", "towpath cafe"},
    "e_pellicci": {"e pellicci", "pellicci", "e pellicci bethnal green"},
    "lahore_kebab": {"lahore kebab house", "lahore kebab"},
    "st_john": {"st john", "st. john"},
    "caravan_exmouth": {"caravan", "caravan exmouth", "caravan exmouth market"},
    "brick_lane_bagel": {"brick lane bagel co", "brick lane bagel"},
    "smokestak": {"smokestak", "smoke stak"},
    "bao_soho": {"bao", "bao soho"},
    "tayyabs": {"tayyabs", "tayyab"},
}


@dataclass
class SearchEvent:
    query: str
    timestamp: str  # ISO8601
    intent: str | None = None  # e.g. "directions", "menu", "hours", None


@dataclass
class VenueRecord:
    id: str
    name: str
    place_id: str | None
    lat: float | None
    lng: float | None
    area: str | None
    dishes: list[str]
    cuisine: list[str]
    vibe: list[str]
    search_count: int
    saves: int
    directions: int
    dist: float = 0.0


@dataclass(frozen=True)
class CatalogVenue:
    id: str
    name: str
    area: str
    lat: float
    lng: float
    dishes: tuple[str, ...]
    cuisine: tuple[str, ...]
    vibe: tuple[str, ...]
    dist: float
    search_count: int = 0
    saves: int = 0
    directions: int = 0


def _normalize(text: str) -> str:
    text = text.casefold().replace("café", "cafe")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(
        r"\b(near me|in london|london|restaurant|restaurants|best|review|reviews)\b",
        " ",
        text,
    )
    return re.sub(r"\s+", " ", text).strip()


def _infer_intent(query: str) -> str | None:
    for intent, pattern in INTENT_PATTERNS.items():
        if pattern.search(query):
            return intent
    return None


def _parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def _recency_bonus(value: str, now: datetime | None = None) -> int:
    ts = _parse_timestamp(value)
    if ts is None:
        return 0
    reference = now or datetime.now(UTC)
    age_days = (reference - ts).days
    if age_days <= 30:
        return 2
    if age_days <= 180:
        return 1
    return 0


def _split_list(raw: str) -> tuple[str, ...]:
    if not raw.strip():
        return ()
    return tuple(item.strip().strip("'") for item in raw.split(",") if item.strip())


def _extract_rows(seed_text: str) -> list[str]:
    rows: list[str] = []
    depth = 0
    start = -1
    for idx, char in enumerate(seed_text):
        if char == "{":
            if depth == 0:
                start = idx
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                rows.append(seed_text[start : idx + 1])
    return rows


def _parse_catalog(seed_path: Path = SEED_PATH) -> dict[str, CatalogVenue]:
    text = seed_path.read_text(encoding="utf-8")
    catalog: dict[str, CatalogVenue] = {}
    for row in _extract_rows(text):
        if "name:" not in row or "lng:" not in row or "lat:" not in row:
            continue
        match = re.search(
            r"id:'(?P<id>[^']+)'.*?"
            r"name:(?P<quote>['\"])(?P<name>.*?)(?P=quote).*?"
            r"area:'(?P<area>[^']+)'.*?"
            r"lng:(?P<lng>-?\d+(?:\.\d+)?), lat:(?P<lat>-?\d+(?:\.\d+)?).*?"
            r"dishes:\[(?P<dishes>[^\]]*)\], cuisine:\[(?P<cuisine>[^\]]*)\].*?"
            r"vibe:\[(?P<vibe>[^\]]*)\](?:, dist:(?P<dist>-?\d+(?:\.\d+)?))?"
            r"(?:,?\s*sc:(?P<sc>\d+), sv:(?P<sv>\d+), dr:(?P<dr>\d+))?",
            row,
            re.S,
        )
        if not match:
            continue
        catalog[match["id"]] = CatalogVenue(
            id=match["id"],
            name=match["name"],
            area=match["area"],
            lng=float(match["lng"]),
            lat=float(match["lat"]),
            dishes=_split_list(match["dishes"]),
            cuisine=_split_list(match["cuisine"]),
            vibe=_split_list(match["vibe"]),
            dist=float(match["dist"] or 0.0),
            search_count=int(match["sc"] or 0),
            saves=int(match["sv"] or 0),
            directions=int(match["dr"] or 0),
        )
    if not catalog:
        raise RuntimeError(f"could not parse any venues from {seed_path}")
    return catalog


def _catalog_aliases(catalog: dict[str, CatalogVenue]) -> dict[str, set[str]]:
    aliases: dict[str, set[str]] = {}
    for venue_id, venue in catalog.items():
        base = _normalize(venue.name)
        venue_aliases = {base}
        venue_aliases.update(ALIAS_OVERRIDES.get(venue_id, set()))
        if base.startswith("the "):
            venue_aliases.add(base.removeprefix("the "))
        aliases[venue_id] = {_normalize(alias) for alias in venue_aliases if alias}
    return aliases


def _match_venue(query: str, aliases: dict[str, set[str]]) -> str | None:
    normalized = _normalize(query)
    matches: list[tuple[int, str]] = []
    for venue_id, venue_aliases in aliases.items():
        for alias in venue_aliases:
            if alias and alias in normalized:
                matches.append((len(alias), venue_id))
    if not matches:
        return None
    matches.sort(reverse=True)
    return matches[0][1]


def parse_takeout(path: Path) -> list[SearchEvent]:
    """Read MyActivity.json and emit SearchEvent rows."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    events: list[SearchEvent] = []
    for item in raw:
        title = item.get("title", "")
        if item.get("header") != "Search" and not title.startswith("Searched for "):
            continue
        query = title.removeprefix("Searched for ").strip()
        timestamp = item.get("time", "")
        events.append(SearchEvent(query=query, timestamp=timestamp, intent=_infer_intent(query)))
    return events


def compute_anchor_scores(events: Iterable[SearchEvent]) -> Counter[str]:
    """Bucket events by inferred venue id and compute a simple anchor heat score."""
    catalog = _parse_catalog()
    aliases = _catalog_aliases(catalog)
    counts: Counter[str] = Counter()
    for event in events:
        venue_id = _match_venue(event.query, aliases)
        if not venue_id:
            continue
        score = 1 + _recency_bonus(event.timestamp)
        if event.intent == "directions":
            score += 2
        elif event.intent in {"menu", "hours", "save"}:
            score += 1
        counts[venue_id] += score
    return counts


def extract_venues(events: Iterable[SearchEvent]) -> list[VenueRecord]:
    """Match search events onto the seeded venue catalog and aggregate metrics."""
    catalog = _parse_catalog()
    aliases = _catalog_aliases(catalog)
    metrics: dict[str, dict[str, int]] = {}

    for event in events:
        venue_id = _match_venue(event.query, aliases)
        if not venue_id:
            continue
        stats = metrics.setdefault(venue_id, {"search_count": 0, "saves": 0, "directions": 0})
        stats["search_count"] += 1
        if event.intent == "save":
            stats["saves"] += 1
        if event.intent == "directions":
            stats["directions"] += 1

    venues: list[VenueRecord] = []
    for venue_id, stats in metrics.items():
        seeded = catalog[venue_id]
        venues.append(
            VenueRecord(
                id=seeded.id,
                name=seeded.name,
                place_id=f"seed:{seeded.id}",
                lat=seeded.lat,
                lng=seeded.lng,
                area=seeded.area,
                dishes=list(seeded.dishes),
                cuisine=list(seeded.cuisine),
                vibe=list(seeded.vibe),
                search_count=stats["search_count"],
                saves=stats["saves"],
                directions=stats["directions"],
                dist=seeded.dist,
            )
        )
    venues.sort(key=lambda venue: (venue.search_count, venue.directions, venue.saves), reverse=True)
    return venues


def enrich_with_claude(venues: list[VenueRecord]) -> None:
    """Local fallback enrichment using the seeded venue catalog metadata."""
    catalog = _parse_catalog()
    for venue in venues:
        seeded = catalog.get(venue.id)
        if not seeded:
            continue
        if not venue.dishes:
            venue.dishes = list(seeded.dishes)
        if not venue.cuisine:
            venue.cuisine = list(seeded.cuisine)
        if not venue.vibe:
            venue.vibe = list(seeded.vibe)
        if venue.area is None:
            venue.area = seeded.area
        if venue.lat is None:
            venue.lat = seeded.lat
        if venue.lng is None:
            venue.lng = seeded.lng


def build_ingest_payload(path: Path, top_anchors: int = MAX_ANCHORS) -> tuple[list[VenueRecord], set[str]]:
    events = parse_takeout(path)
    scores = compute_anchor_scores(events)
    venues = extract_venues(events)
    enrich_with_claude(venues)
    ordered = sorted(venues, key=lambda venue: scores.get(venue.id, 0), reverse=True)
    anchors = {venue.id for venue in ordered[:top_anchors]}
    return venues, anchors


WRITE_QUERY = """
MERGE (u:User {id: $user_id})
SET u.name = coalesce($user_name, u.name, 'Imported User'),
    u.center = point({longitude: $center_lng, latitude: $center_lat})
WITH u
OPTIONAL MATCH (u)-[old:ANCHORED_TO]->(:Venue)
DELETE old
WITH u
UNWIND $venues AS row
MERGE (v:Venue {id: row.id})
SET v.name = row.name,
    v.loc = point({longitude: row.lng, latitude: row.lat}),
    v.dist = row.dist
MERGE (area:Area {name: row.area})
MERGE (v)-[:IN_AREA]->(area)
FOREACH (dish IN row.dishes |
  MERGE (d:Dish {name: dish})
  MERGE (v)-[:SERVES]->(d)
)
FOREACH (cuisine IN row.cuisine |
  MERGE (c:Cuisine {name: cuisine})
  MERGE (v)-[:HAS_CUISINE]->(c)
)
FOREACH (vibe IN row.vibe |
  MERGE (vb:Vibe {name: vibe})
  MERGE (v)-[:HAS_VIBE]->(vb)
)
FOREACH (_ IN CASE WHEN row.is_anchor THEN [1] ELSE [] END |
  MERGE (u)-[a:ANCHORED_TO]->(v)
  SET a.search_count = row.search_count,
      a.saves = row.saves,
      a.directions = row.directions
)
"""


def write_to_neo4j(user_id: str, venues: list[VenueRecord], anchors: set[str]) -> None:
    """Write Venue nodes, property nodes, and ANCHORED_TO edges to Neo4j."""
    from db.neo4j_client import session

    if not venues:
        raise ValueError("no venues extracted from takeout")

    locs = [(venue.lng, venue.lat) for venue in venues if venue.lng is not None and venue.lat is not None]
    if not locs:
        raise ValueError("no venue coordinates available for user center")
    center_lng = sum(lng for lng, _ in locs) / len(locs)
    center_lat = sum(lat for _, lat in locs) / len(locs)

    payload = [
        {
            "id": venue.id,
            "name": venue.name,
            "lng": venue.lng,
            "lat": venue.lat,
            "area": venue.area,
            "dishes": venue.dishes,
            "cuisine": venue.cuisine,
            "vibe": venue.vibe,
            "dist": venue.dist,
            "search_count": venue.search_count,
            "saves": venue.saves,
            "directions": venue.directions,
            "is_anchor": venue.id in anchors,
        }
        for venue in venues
        if venue.lng is not None and venue.lat is not None and venue.area is not None
    ]

    with session() as sess:
        sess.run(
            WRITE_QUERY,
            user_id=user_id,
            user_name=user_id.replace("_", " ").title(),
            center_lng=center_lng,
            center_lat=center_lat,
            venues=payload,
        ).consume()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest Google Takeout search history into Neo4j.")
    parser.add_argument("takeout", type=Path, help="Path to MyActivity.json")
    parser.add_argument("--user-id", default="u_takeout", help="User id to write into Neo4j")
    parser.add_argument(
        "--top-anchors",
        type=int,
        default=MAX_ANCHORS,
        help="How many top venues to treat as anchors",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write the extracted graph into Neo4j instead of only printing a summary",
    )
    args = parser.parse_args(argv)

    venues, anchors = build_ingest_payload(args.takeout, top_anchors=args.top_anchors)
    print(f"events -> venues: {len(venues)}")
    print(f"anchors: {', '.join(sorted(anchors)) if anchors else '(none)'}")
    for venue in venues[:10]:
        anchor_marker = " *" if venue.id in anchors else ""
        print(
            f"- {venue.id}{anchor_marker}: "
            f"{venue.search_count} searches, {venue.directions} directions, {venue.saves} saves"
        )

    if args.write:
        write_to_neo4j(args.user_id, venues, anchors)
        print(f"wrote {len(venues)} venues for {args.user_id}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
