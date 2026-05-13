"""Pydantic shapes that mirror the frontend `types.ts` exactly.

If you change one side, change the other. The /api/graph and /api/rank
responses are the boundary contract — anything that diverges will
break the React app.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Coord = tuple[float, float]  # [lng, lat] — keep this order, GeoJSON convention
EdgeKind = Literal["SAME_DISH", "SAME_CUISINE", "SAME_VIBE", "SAME_AREA"]


class Venue(BaseModel):
    id: str
    name: str
    area: str
    dishes: list[str]
    cuisine: list[str]
    vibe: list[str]
    loc: Coord
    dist: float = 0.0


class Anchor(Venue):
    searchCount: int = Field(0, alias="searchCount")
    saves: int = 0
    directions: int = 0

    model_config = {"populate_by_name": True}


class User(BaseModel):
    id: str
    name: str
    center: Coord


class Weights(BaseModel):
    SAME_DISH: float = 3.0
    SAME_CUISINE: float = 1.5
    SAME_VIBE: float = 1.0
    SAME_AREA: float = 1.2
    DISTANCE_PENALTY: float = 0.15


class GraphResponse(BaseModel):
    user: User
    anchors: dict[str, Anchor]
    venues: dict[str, Venue]
    weights: Weights


class BreakdownItem(BaseModel):
    anchor: str
    kind: EdgeKind
    item: str
    score: float


class RankRequest(BaseModel):
    query: str


class RankedCandidate(BaseModel):
    id: str
    venue: Venue
    score: float
    breakdown: list[BreakdownItem]
