"""Google Takeout → Neo4j ingest pipeline.

Pipeline:
  1. Parse `MyActivity.json` (Google Takeout) into (query, timestamp) rows.
  2. Bucket repeated searches per venue and compute an anchor score:
       score = search_count + recency_decay + signal_co_occurrence
     where signal_co_occurrence boosts queries that fire alongside
     "directions to", "hours", "menu" — strong intent signals.
  3. Entity-extract venue mentions with spaCy NER, then confirm each
     against Google Places API to attach a canonical place_id, address,
     and lat/lng.
  4. Enrich every venue with dishes/cuisine/vibe via Claude on top of
     scraped review text.
  5. Write nodes and relationships into Neo4j.

This file is a stub — the structure is here, the inner per-step logic
is left as TODOs. None of the demo code paths depend on this running.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class SearchEvent:
    query: str
    timestamp: str  # ISO8601
    intent: str | None = None  # e.g. "directions", "menu", "hours", None


@dataclass
class VenueRecord:
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


def parse_takeout(path: Path) -> list[SearchEvent]:
    """Read MyActivity.json and emit SearchEvent rows."""
    raw = json.loads(path.read_text())
    events: list[SearchEvent] = []
    for item in raw:
        if item.get("header") != "Search":
            continue
        q = item.get("title", "").removeprefix("Searched for ")
        ts = item.get("time", "")
        events.append(SearchEvent(query=q, timestamp=ts))
    return events


def compute_anchor_scores(events: Iterable[SearchEvent]) -> Counter[str]:
    """Bucket events by inferred venue name and compute a heat score.

    TODO:
      - normalise queries (lowercase, strip "near me", trailing punctuation)
      - apply recency decay (events older than 6mo count for less)
      - boost when co-occurring with "directions"/"hours"/"menu" intents
    """
    counts: Counter[str] = Counter()
    for ev in events:
        counts[ev.query.strip().lower()] += 1
    return counts


def extract_venues(events: Iterable[SearchEvent]) -> list[VenueRecord]:
    """spaCy NER → Google Places confirmation.

    TODO:
      - load `en_core_web_trf` for high-accuracy NER
      - filter entities to (ORG, FAC, GPE) likely to be venues
      - resolve each candidate to a Google Places place_id
      - drop anything Google can't confirm with a lat/lng
    """
    raise NotImplementedError


def enrich_with_claude(venues: list[VenueRecord]) -> None:
    """Pull review text per venue and ask Claude to tag dishes/cuisine/vibe.

    TODO:
      - fetch top 10 reviews from Google Places (or scraped fallback)
      - prompt: "extract up to 4 signature dishes, 2 cuisine tags,
        and 4 vibe tags from these reviews. Return JSON."
      - validate JSON schema, dedupe across the corpus
    """
    raise NotImplementedError


def write_to_neo4j(user_id: str, venues: list[VenueRecord], anchors: set[str]) -> None:
    """Single transaction MERGE for nodes + relationships.

    TODO:
      - open a session against the configured Neo4j URI
      - UNWIND venues, MERGE each Venue and its property nodes
      - for each venue in `anchors`, MERGE the :ANCHORED_TO edge with
        search_count/saves/directions from VenueRecord
    """
    raise NotImplementedError


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit("ingest pipeline not yet wired — see TODOs above")
