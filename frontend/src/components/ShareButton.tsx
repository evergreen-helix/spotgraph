import { useMemo } from "react";
import type { Anchor, Graph } from "../types";
import { useGraph } from "../contexts/GraphContext";
import { pretty } from "../lib/rank";

function weighted(map: Map<string, number>, limit: number) {
  return [...map.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit);
}

function bar(value: number, max: number, width = 12) {
  const filled = Math.round((value / max) * width);
  return "█".repeat(filled) + "░".repeat(width - filled);
}

function buildProfile(graph: Graph) {
  const anchors = Object.values(graph.anchors).sort(
    (a, b) => b.searchCount - a.searchCount
  );
  const venues = Object.values(graph.venues);
  const allVenues = [...anchors, ...venues];

  const cuisineWeight = new Map<string, number>();
  const vibeWeight = new Map<string, number>();
  const dishWeight = new Map<string, number>();
  const areaWeight = new Map<string, number>();

  for (const a of anchors) {
    const w = a.searchCount + a.directions * 1.5 + a.saves * 2;
    for (const c of a.cuisine) cuisineWeight.set(c, (cuisineWeight.get(c) ?? 0) + w);
    for (const v of a.vibe) vibeWeight.set(v, (vibeWeight.get(v) ?? 0) + w);
    for (const d of a.dishes) dishWeight.set(d, (dishWeight.get(d) ?? 0) + w);
    areaWeight.set(a.area, (areaWeight.get(a.area) ?? 0) + w);
  }

  const totalSearches = anchors.reduce((s, a) => s + a.searchCount, 0);
  const totalDirs = anchors.reduce((s, a) => s + a.directions, 0);
  const totalSaves = anchors.reduce((s, a) => s + a.saves, 0);
  const totalSignals = totalSearches + totalDirs + totalSaves;

  const uniqueCuisines = new Set(allVenues.flatMap((v) => v.cuisine));
  const uniqueVibes = new Set(allVenues.flatMap((v) => v.vibe));
  const uniqueDishes = new Set(allVenues.flatMap((v) => v.dishes));
  const uniqueAreas = new Set(allVenues.map((v) => v.area));

  let edgeCount = 0;
  for (const v of allVenues) {
    edgeCount += v.dishes.length + v.cuisine.length + v.vibe.length + 1;
  }
  edgeCount += anchors.length;

  const propertyNodes = new Set<string>();
  for (const v of allVenues) {
    v.dishes.forEach((d) => propertyNodes.add(d));
    v.cuisine.forEach((c) => propertyNodes.add(c));
    v.vibe.forEach((vb) => propertyNodes.add(vb));
    propertyNodes.add(v.area);
  }
  const nodeCount = 1 + anchors.length + venues.length + propertyNodes.size;

  const overlapMatrix: { a1: string; a2: string; shared: string[] }[] = [];
  for (let i = 0; i < anchors.length; i++) {
    for (let j = i + 1; j < anchors.length; j++) {
      const a1 = anchors[i], a2 = anchors[j];
      const tags1 = new Set([...a1.dishes, ...a1.cuisine, ...a1.vibe, a1.area]);
      const tags2 = new Set([...a2.dishes, ...a2.cuisine, ...a2.vibe, a2.area]);
      const shared = [...tags1].filter((t) => tags2.has(t));
      if (shared.length > 0) {
        overlapMatrix.push({ a1: a1.name, a2: a2.name, shared });
      }
    }
  }
  overlapMatrix.sort((a, b) => b.shared.length - a.shared.length);

  const candidateReach = new Map<string, number>();
  for (const a of anchors) {
    const tags = new Set([...a.dishes, ...a.cuisine, ...a.vibe, a.area]);
    let reach = 0;
    for (const v of venues) {
      const vTags = [...v.dishes, ...v.cuisine, ...v.vibe, v.area];
      if (vTags.some((t) => tags.has(t))) reach++;
    }
    candidateReach.set(a.id, reach);
  }

  const distances = venues.map((v) => v.dist).filter((d) => d > 0);
  const maxDist = distances.length ? Math.max(...distances) : 0;
  const avgDist = distances.length
    ? distances.reduce((s, d) => s + d, 0) / distances.length
    : 0;

  const diversityScore = Math.min(100, Math.round(
    (uniqueCuisines.size / 5) * 25 +
    (uniqueAreas.size / 5) * 25 +
    (anchors.length / 5) * 25 +
    (uniqueVibes.size / 8) * 25
  ));

  return {
    anchors, venues, nodeCount, edgeCount,
    cuisineWeight, vibeWeight, dishWeight, areaWeight,
    totalSearches, totalDirs, totalSaves, totalSignals,
    uniqueCuisines, uniqueVibes, uniqueDishes, uniqueAreas,
    overlapMatrix, candidateReach,
    maxDist, avgDist, diversityScore,
  };
}

function anchorBlock(a: Anchor, reach: number, maxSearch: number) {
  return [
    `  ♥ ${a.name}`,
    `    ${pretty(a.area)} · ${a.searchCount}× searched · ${a.directions}× directions · ${a.saves}× saved`,
    `    engagement  ${bar(a.searchCount, maxSearch)}`,
    `    dishes      ${a.dishes.map(pretty).join(", ")}`,
    `    cuisine     ${a.cuisine.map(pretty).join(", ")}`,
    `    vibe        ${a.vibe.map(pretty).join(", ")}`,
    `    reaches → ${reach} candidate venues`,
  ];
}

export default function ShareButton() {
  const graph = useGraph();

  const profile = useMemo(() => buildProfile(graph), [graph]);

  const handleShare = async () => {
    const p = profile;
    const maxSearch = p.anchors[0]?.searchCount ?? 1;

    const lines = [
      `╔══════════════════════════════════════════════════════╗`,
      `║         ${graph.user.name.toUpperCase()}'S TASTE GRAPH              ║`,
      `║         semantica — search that knows your spots     ║`,
      `╚══════════════════════════════════════════════════════╝`,
      ``,
      `── GRAPH OVERVIEW ──────────────────────────────────────`,
      `  ${p.nodeCount.toLocaleString()} nodes · ${p.edgeCount.toLocaleString()} edges`,
      `  ${p.anchors.length} anchors · ${p.venues.length} candidates`,
      `  ${p.uniqueCuisines.size} cuisines · ${p.uniqueDishes.size} dishes · ${p.uniqueVibes.size} vibes · ${p.uniqueAreas.size} areas`,
      `  diversity score: ${p.diversityScore}/100`,
      ``,
      `── ENGAGEMENT SIGNALS ──────────────────────────────────`,
      `  ${p.totalSignals} total signals from Google search history`,
      `  ${p.totalSearches}× searches · ${p.totalDirs}× direction requests · ${p.totalSaves}× saves`,
      ``,
      `── ANCHOR VENUES (ranked by engagement) ────────────────`,
      ``,
      ...p.anchors.flatMap((a) => [
        ...anchorBlock(a, p.candidateReach.get(a.id) ?? 0, maxSearch),
        ``,
      ]),
      `── TASTE FINGERPRINT ───────────────────────────────────`,
      ``,
      `  CUISINE DISTRIBUTION`,
      ...weighted(p.cuisineWeight, 6).map(([k, v]) =>
        `    ${pretty(k).padEnd(20)} ${bar(v, weighted(p.cuisineWeight, 1)[0][1])} ${v.toFixed(0)}`
      ),
      ``,
      `  VIBE PROFILE`,
      ...weighted(p.vibeWeight, 6).map(([k, v]) =>
        `    ${pretty(k).padEnd(20)} ${bar(v, weighted(p.vibeWeight, 1)[0][1])} ${v.toFixed(0)}`
      ),
      ``,
      `  SIGNATURE DISHES`,
      ...weighted(p.dishWeight, 6).map(([k, v]) =>
        `    ${pretty(k).padEnd(20)} ${bar(v, weighted(p.dishWeight, 1)[0][1])} ${v.toFixed(0)}`
      ),
      ``,
      `  NEIGHBORHOOD MAP`,
      ...weighted(p.areaWeight, 8).map(([k, v]) =>
        `    ${pretty(k).padEnd(20)} ${bar(v, weighted(p.areaWeight, 1)[0][1])} ${v.toFixed(0)}`
      ),
      ``,
      `── ANCHOR CONNECTIONS ──────────────────────────────────`,
      `  (shared tags between your anchor venues)`,
      ``,
      ...p.overlapMatrix.slice(0, 6).map(
        (o) => `  ${o.a1} ↔ ${o.a2}: ${o.shared.map(pretty).join(", ")}`
      ),
      ``,
      `── GEOGRAPHIC RANGE ───────────────────────────────────`,
      `  avg candidate distance: ${p.avgDist.toFixed(1)} km`,
      `  max candidate distance: ${p.maxDist.toFixed(1)} km`,
      `  center: [${graph.user.center[0].toFixed(4)}, ${graph.user.center[1].toFixed(4)}]`,
      ``,
      `══════════════════════════════════════════════════════`,
      `  built with Neo4j · Tessl · Kimchi · HackerSquad`,
      `  hackersquad.dev`,
    ];

    const text = lines.join("\n");

    if (navigator.share) {
      await navigator.share({ title: `${graph.user.name}'s Taste Graph`, text });
    } else {
      await navigator.clipboard.writeText(text);
      const btn = document.querySelector(".share-btn") as HTMLElement;
      if (btn) {
        btn.textContent = "copied!";
        setTimeout(() => (btn.textContent = "share graph"), 1500);
      }
    }
  };

  return (
    <button className="share-btn" onClick={handleShare}>
      share graph
    </button>
  );
}
