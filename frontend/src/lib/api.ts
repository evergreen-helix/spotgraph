import { GRAPH } from "../data/graph";
import { rank as localRank } from "./rank";
import type { Graph, RankedCandidate } from "../types";

const USE_BACKEND = import.meta.env.VITE_USE_BACKEND === "true";
const USE_OSM = import.meta.env.VITE_USE_OSM === "true";

/**
 * Thin transport layer. Three modes:
 *   - VITE_USE_BACKEND=true  → call FastAPI at /api/graph and /api/rank
 *   - VITE_USE_OSM=true      → fetch the OSM-scraped seed at /seed.json,
 *                              rank locally (good demo, no backend needed)
 *   - default                → use the hand-curated GRAPH constant + localRank
 *
 * All three return identical shapes, so consumers don't care which one ran.
 */
export async function fetchGraph(): Promise<Graph> {
  if (USE_BACKEND) {
    const res = await fetch("/api/graph");
    if (!res.ok) throw new Error(`fetchGraph failed: ${res.status}`);
    return res.json();
  }
  if (USE_OSM) {
    const res = await fetch("/seed.json");
    if (!res.ok) throw new Error(`fetchGraph(/seed.json) failed: ${res.status}`);
    return res.json();
  }
  return GRAPH;
}

export async function rank(graph: Graph, query: string): Promise<RankedCandidate[]> {
  if (!USE_BACKEND) return localRank(graph, query);
  const res = await fetch("/api/rank", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  if (!res.ok) throw new Error(`rank failed: ${res.status}`);
  return res.json();
}
