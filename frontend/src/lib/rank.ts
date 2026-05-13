import type { BreakdownItem, Graph, RankedCandidate } from "../types";

/**
 * JS port of the Cypher ranking query.
 *
 * In production this is replaced by a POST /api/rank that runs the
 * single Cypher MATCH described in demo-script.md §SCENE 4.
 * Keeping the shape identical means the swap is one fetch call.
 */
export function rank(graph: Graph, query: string): RankedCandidate[] {
  const q = query.toLowerCase().trim();

  // The query nudges which anchor matters most.
  // In production this is a vector similarity step:
  //   query embedding × anchor embedding → boost.
  const boost: Record<string, number> = {
    beigel: 1,
    dishoom: 1,
    towpath: 1,
  };
  if (/\b(bagel|beigel|salt beef|sandwich|bread)\b/.test(q)) boost.beigel = 3;
  if (/\b(curry|indian|naan|biryani|daal|spice)\b/.test(q)) boost.dishoom = 3;
  if (/\b(brunch|coffee|cafe|breakfast|outdoor|canal)\b/.test(q)) boost.towpath = 3;

  const W = graph.weights;

  const candidates: RankedCandidate[] = Object.entries(graph.venues)
    .map(([id, v]) => {
      const breakdown: BreakdownItem[] = [];
      let score = 0;

      for (const [aId, anchor] of Object.entries(graph.anchors)) {
        const b = boost[aId] ?? 1;

        const dishOverlap = anchor.dishes.filter((d) => v.dishes.includes(d));
        const cuisineOverlap = anchor.cuisine.filter((c) => v.cuisine.includes(c));
        const vibeOverlap = anchor.vibe.filter((vb) => v.vibe.includes(vb));
        const sameArea = anchor.area === v.area;

        if (dishOverlap.length) {
          const s = dishOverlap.length * W.SAME_DISH * b;
          score += s;
          breakdown.push({ anchor: aId, kind: "SAME_DISH", item: dishOverlap[0], score: s });
        }
        if (cuisineOverlap.length) {
          const s = cuisineOverlap.length * W.SAME_CUISINE * b;
          score += s;
          breakdown.push({ anchor: aId, kind: "SAME_CUISINE", item: cuisineOverlap[0], score: s });
        }
        if (vibeOverlap.length) {
          const s = vibeOverlap.length * W.SAME_VIBE * b;
          score += s;
          breakdown.push({ anchor: aId, kind: "SAME_VIBE", item: vibeOverlap[0], score: s });
        }
        if (sameArea) {
          const s = W.SAME_AREA * b;
          score += s;
          breakdown.push({ anchor: aId, kind: "SAME_AREA", item: v.area, score: s });
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
