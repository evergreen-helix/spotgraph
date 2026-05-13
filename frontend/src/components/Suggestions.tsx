import type { Graph, RankedCandidate, VenueId } from "../types";
import { pretty } from "../lib/rank";

interface Props {
  graph: Graph;
  results: RankedCandidate[];
  query: string;
  onSelect: (id: VenueId) => void;
}

export default function Suggestions({ graph, results, query, onSelect }: Props) {
  if (!results.length) {
    return (
      <div
        style={{
          padding: 28,
          textAlign: "center",
          opacity: 0.55,
          fontFamily: "Fraunces, serif",
          fontStyle: "italic",
        }}
      >
        No graph paths from your anchors to "{query}". Try something broader.
      </div>
    );
  }

  const topC = results[0];
  const tb = topC.breakdown[0];
  const anchorName = graph.anchors[tb.anchor].name;

  return (
    <>
      <div className="drop-head">
        <h3>Suggestions · projected from your anchors</h3>
        <span className="you">your taste graph →</span>
      </div>

      <div>
        {results.map((c, i) => {
          const top2 = c.breakdown.slice(0, 2);
          return (
            <div
              key={c.id}
              className={`sugg ${i === 0 ? "top" : ""}`}
              onClick={() => onSelect(c.id)}
            >
              <div className="sugg-rank">0{i + 1}</div>
              <div className="sugg-body">
                <div className="sugg-name">
                  {c.venue.name}{" "}
                  <span className="dist">
                    {c.venue.dist.toFixed(1)} km · {pretty(c.venue.area)}
                  </span>
                </div>
                <div className="sugg-why">
                  {top2.map((b, idx) => (
                    <div key={idx}>
                      <span className="anchor">{graph.anchors[b.anchor].name}</span>{" "}
                      &mdash;{" "}
                      <span className="edge">
                        {b.kind.replace(/_/g, " ").toLowerCase()}: {pretty(b.item)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="sugg-score">{c.score.toFixed(2)}</div>
            </div>
          );
        })}
      </div>

      <div className="breadcrumb">
        <b>cypher path:</b>{" "}
        <span className="node">User: {graph.user.name.split(" ")[0]}</span> →{" "}
        <span className="node love">♥ {anchorName}</span> →{" "}
        <span className="node">[:{tb.kind}]</span> →{" "}
        <span className="node">{pretty(tb.item)}</span> →{" "}
        <span className="node">{topC.venue.name}</span> &nbsp;
        <b>(score {topC.score.toFixed(2)})</b>
      </div>
    </>
  );
}
