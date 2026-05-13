import { useMemo } from "react";
import { useGraph } from "../contexts/GraphContext";
import { pretty } from "../lib/rank";

export default function ShareButton() {
  const graph = useGraph();

  const profile = useMemo(() => {
    const anchors = Object.values(graph.anchors);
    const venueCount = Object.keys(graph.venues).length;

    const allCuisines = new Map<string, number>();
    const allVibes = new Map<string, number>();
    const allDishes = new Map<string, number>();
    const areas = new Set<string>();

    for (const a of anchors) {
      areas.add(a.area);
      for (const c of a.cuisine) allCuisines.set(c, (allCuisines.get(c) ?? 0) + a.searchCount);
      for (const v of a.vibe) allVibes.set(v, (allVibes.get(v) ?? 0) + a.searchCount);
      for (const d of a.dishes) allDishes.set(d, (allDishes.get(d) ?? 0) + a.searchCount);
    }

    const topCuisines = [...allCuisines.entries()].sort((a, b) => b[1] - a[1]).slice(0, 4).map(([k]) => k);
    const topVibes = [...allVibes.entries()].sort((a, b) => b[1] - a[1]).slice(0, 4).map(([k]) => k);
    const topDishes = [...allDishes.entries()].sort((a, b) => b[1] - a[1]).slice(0, 3).map(([k]) => k);

    const totalSearches = anchors.reduce((s, a) => s + a.searchCount, 0);
    const totalDirs = anchors.reduce((s, a) => s + a.directions, 0);

    const topAnchor = anchors.sort((a, b) => b.searchCount - a.searchCount)[0];

    return { anchors, venueCount, topCuisines, topVibes, topDishes, areas, totalSearches, totalDirs, topAnchor };
  }, [graph]);

  const handleShare = async () => {
    const { anchors, venueCount, topCuisines, topVibes, topDishes, areas, totalSearches, totalDirs, topAnchor } = profile;

    const lines = [
      `┌─── ${graph.user.name}'s Taste Graph ───`,
      `│`,
      `│  ${anchors.length} anchor venues · ${venueCount} candidates`,
      `│  ${totalSearches} searches · ${totalDirs} direction requests`,
      `│  ${areas.size} neighborhoods explored`,
      `│`,
      `│  ANCHOR VENUES`,
      ...anchors.map((a) =>
        `│  ♥ ${a.name} — ${pretty(a.area)} (${a.searchCount}× searched)`
      ),
      `│`,
      `│  TOP CUISINES: ${topCuisines.map(pretty).join(", ")}`,
      `│  SIGNATURE DISHES: ${topDishes.map(pretty).join(", ")}`,
      `│  YOUR VIBE: ${topVibes.map(pretty).join(", ")}`,
      `│`,
      `│  #1 spot: ${topAnchor.name} (${topAnchor.searchCount} searches, ${topAnchor.directions} directions)`,
      `│`,
      `└─── semantica · powered by Neo4j ───`,
      `     hackersquad.dev`,
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
