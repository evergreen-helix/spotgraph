import type { Anchor, BreakdownItem, Graph, RankedCandidate } from "../types";

// Tokens are noisy — "bagels" / "bagel" / "bagelry" should all hit the same
// anchor. We strip a single trailing 's' and require ≥4 chars on the stem so
// "the" / "and" don't collapse into prefixes of unrelated cuisines.
function stem(token: string): string {
  return token.endsWith("s") && token.length > 4 ? token.slice(0, -1) : token;
}

function tokenMatches(token: string, haystack: string): boolean {
  if (haystack.includes(token)) return true;
  const t = stem(token);
  if (t.length >= 4 && haystack.includes(t)) return true;
  return false;
}

// When any anchor matches the query, unmatched anchors are damped so their
// "background" signal doesn't drown out the explicit one. This is what the
// demo-script means by "the Dishoom and Towpath signals fade" — without
// dampening, two cafe anchors × 3 dish overlaps still beats one bagel anchor
// × 2 dish overlaps even with a 3x boost on the bagel anchor.
const BOOST_MATCH = 3.0;
const BOOST_UNMATCHED_WHEN_OTHERS_MATCH = 0.35;
const BOOST_DEFAULT = 1.0;

function computeBoosts(
  anchors: Record<string, Anchor>,
  query: string
): Record<string, number> {
  const tokens = query
    .toLowerCase()
    .split(/\s+/)
    .filter((t) => t.length > 2);
  const boosts: Record<string, number> = {};

  // First pass — flag which anchors match any token
  const matched: Record<string, boolean> = {};
  for (const [id, anchor] of Object.entries(anchors)) {
    if (!tokens.length) {
      matched[id] = false;
      continue;
    }
    const searchable = [
      anchor.name.toLowerCase(),
      ...anchor.dishes.map((d) => d.replace(/_/g, " ")),
      ...anchor.cuisine.map((c) => c.replace(/_/g, " ")),
      ...anchor.vibe.map((v) => v.replace(/_/g, " ")),
      anchor.area.replace(/_/g, " "),
    ];
    matched[id] = tokens.some((t) =>
      searchable.some((s) => tokenMatches(t, s))
    );
  }

  const anyMatched = Object.values(matched).some(Boolean);

  // Second pass — assign weights
  for (const id of Object.keys(anchors)) {
    if (matched[id]) boosts[id] = BOOST_MATCH;
    else if (anyMatched) boosts[id] = BOOST_UNMATCHED_WHEN_OTHERS_MATCH;
    else boosts[id] = BOOST_DEFAULT;
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
