export type VenueId = string;

export interface Venue {
  id: VenueId;
  name: string;
  area: string;
  dishes: string[];
  cuisine: string[];
  vibe: string[];
  loc: [number, number]; // [lng, lat]
  dist: number; // km from a notional centroid — used as a soft penalty
  searchCount?: number;
  saves?: number;
  directions?: number;
}

export interface Anchor extends Venue {
  searchCount: number;
  saves: number;
  directions: number;
}

export interface User {
  id: string;
  name: string;
  center: [number, number]; // [lng, lat]
}

export interface BreakdownItem {
  anchor: VenueId;
  kind: "SAME_DISH" | "SAME_CUISINE" | "SAME_VIBE" | "SAME_AREA";
  item: string;
  score: number;
}

export interface RankedCandidate {
  id: VenueId;
  venue: Venue;
  score: number;
  breakdown: BreakdownItem[];
}

export interface Graph {
  user: User;
  anchors: Record<VenueId, Anchor>;
  venues: Record<VenueId, Venue>;
  weights: {
    SAME_DISH: number;
    SAME_CUISINE: number;
    SAME_VIBE: number;
    SAME_AREA: number;
    DISTANCE_PENALTY: number;
  };
}
