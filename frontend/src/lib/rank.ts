import type { Anchor, BreakdownItem, Graph, RankedCandidate } from "../types";

function computeBoosts(
  anchors: Record<string, Anchor>,
  query: string
): Record<string, number> {
  const tokens = query
    .toLowerCase()
    .split(/\s+/)
    .filter((t) => t.length > 2);
  const boosts: Record<string, number> = {};

  for (const [id, anchor] of Object.entries(anchors)) {
    boosts[id] = 1;
    if (!tokens.length) continue;

    const searchable = [
      anchor.name.toLowerCase(),
      ...anchor.dishes.map((d) => d.replace(/_/g, " ")),
      ...anchor.cuisine.map((c) => c.replace(/_/g, " ")),
      ...anchor.vibe.map((v) => v.replace(/_/g, " ")),
      anchor.area.replace(/_/g, " "),
    ];

    for (const token of tokens) {
      if (searchable.some((s) => s.includes(token))) {
        boosts[id] = 3;
        break;
      }
    }
  }

  return boosts;
}

export function rank(graph: Graph, query: string): RankedCandidate[] {
  const boost = computeBoosts(graph.anchors, query);
  const W = graph.weights;

  const candidates: RankedCandidate[] = Object.entries(graph.venues)
    .map(([id, v]) => {
      const breakdown: BreakdownItem[] = [];
      let score = 0;

      for (const [aId, anchor] of Object.entries(graph.anchors)) {
        const b = boost[aId] ?? 1;

        const dishOverlap = anchor.dishes.filter((d) => v.dishes.includes(d));
        const cuisineOverlap = anchor.cuisine.filter((c) =>
          v.cuisine.includes(c)
        );
        const vibeOverlap = anchor.vibe.filter((vb) => v.vibe.includes(vb));
        const sameArea = anchor.area === v.area;

        if (dishOverlap.length) {
          const s = dishOverlap.length * W.SAME_DISH * b;
          score += s;
          breakdown.push({
            anchor: aId,
            kind: "SAME_DISH",
            item: dishOverlap[0],
            score: s,
          });
        }
        if (cuisineOverlap.length) {
          const s = cuisineOverlap.length * W.SAME_CUISINE * b;
          score += s;
          breakdown.push({
            anchor: aId,
            kind: "SAME_CUISINE",
            item: cuisineOverlap[0],
            score: s,
          });
        }
        if (vibeOverlap.length) {
          const s = vibeOverlap.length * W.SAME_VIBE * b;
          score += s;
          breakdown.push({
            anchor: aId,
            kind: "SAME_VIBE",
            item: vibeOverlap[0],
            score: s,
          });
        }
        if (sameArea) {
          const s = W.SAME_AREA * b;
          score += s;
          breakdown.push({
            anchor: aId,
            kind: "SAME_AREA",
            item: v.area,
            score: s,
          });
        }
      }

      score -= v.dist * W.DISTANCE_PENALTY;
      breakdown.sort((a, b) => b.score - a.score);

      return { id, venue: v, score: Math.max(0, score), breakdown };
    })
    .filter((c) => c.score > 0)
    .sort((a, b) => b.score - a.score);

  return candidates;
}

export const pretty = (s: string) => s.replace(/_/g, " ");
