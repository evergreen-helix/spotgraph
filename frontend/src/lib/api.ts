import { GRAPH } from "../data/graph";
import { rank as localRank } from "./rank";
import type { Graph, RankedCandidate } from "../types";

const USE_BACKEND = import.meta.env.VITE_USE_BACKEND === "true";

/**
 * Thin transport layer. Either:
 *   - returns the local mock (USE_BACKEND=false, default)
 *   - calls the FastAPI backend at /api/graph and /api/rank (USE_BACKEND=true)
 *
 * The backend response shapes are identical to the local mock,
 * so consumers don't care which mode is active.
 */
export async function fetchGraph(): Promise<Graph> {
  if (!USE_BACKEND) return GRAPH;
  const res = await fetch("/api/graph");
  if (!res.ok) throw new Error(`fetchGraph failed: ${res.status}`);
  return res.json();
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
