import { useMemo } from "react";
import { useGraph } from "../contexts/GraphContext";

export default function TopBar() {
  const graph = useGraph();

  const { nodes, edges } = useMemo(() => {
    const anchorCount = Object.keys(graph.anchors).length;
    const venueCount = Object.keys(graph.venues).length;
    const allVenues = { ...graph.anchors, ...graph.venues };

    let edgeCount = 0;
    for (const v of Object.values(allVenues)) {
      edgeCount += v.dishes.length + v.cuisine.length + v.vibe.length + 1;
    }
    edgeCount += anchorCount;

    const propertySet = new Set<string>();
    for (const v of Object.values(allVenues)) {
      v.dishes.forEach((d) => propertySet.add(`dish:${d}`));
      v.cuisine.forEach((c) => propertySet.add(`cuisine:${c}`));
      v.vibe.forEach((vb) => propertySet.add(`vibe:${vb}`));
      propertySet.add(`area:${v.area}`);
    }

    const nodeCount = 1 + anchorCount + venueCount + propertySet.size;
    return { nodes: nodeCount, edges: edgeCount };
  }, [graph]);

  const fmt = (n: number) => n.toLocaleString();

  return (
    <header className="topbar">
      <div className="brand">
        semantica<span>.</span>
      </div>
      <div className="meta">
        graph · <b>{fmt(nodes)} nodes</b> · <b>{fmt(edges)} edges</b>
      </div>
    </header>
  );
}
