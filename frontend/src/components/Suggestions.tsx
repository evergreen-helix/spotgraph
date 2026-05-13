import { useState } from "react";
import type { RankedCandidate, VenueId } from "../types";
import { useGraph } from "../contexts/GraphContext";
import { pretty } from "../lib/rank";

interface Props {
  results: RankedCandidate[];
  query: string;
  isLoading: boolean;
  hasMore: boolean;
  onShowMore: () => void;
  onSelect: (id: VenueId) => void;
}

export default function Suggestions({
  results,
  query,
  isLoading,
  hasMore,
  onShowMore,
  onSelect,
}: Props) {
  const graph = useGraph();
  const [feedback, setFeedback] = useState<Record<string, "up" | "down">>({});

  const toggleFeedback = (id: string, dir: "up" | "down") => {
    setFeedback((prev) => ({
      ...prev,
      [id]: prev[id] === dir ? undefined! : dir,
    }));
  };

  if (isLoading) {
    return (
      <div className="loading-bar">
        <div className="loading-dots">
          <span />
          <span />
          <span />
        </div>
      </div>
    );
  }

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
  const anchorName = graph.anchors[tb.anchor]?.name ?? tb.anchor;

  return (
    <>
      <div className="drop-head">
        <h3>Suggestions · projected from your anchors</h3>
        <span className="you">your taste graph →</span>
      </div>

      <div>
        {results.map((c, i) => {
          const top2 = c.breakdown.slice(0, 2);
          const fb = feedback[c.id];
          return (
            <div
              key={c.id}
              className={`sugg ${i === 0 ? "top" : ""}`}
              onClick={() => onSelect(c.id)}
            >
              <div className="sugg-rank">
                {String(i + 1).padStart(2, "0")}
              </div>
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
                      <span className="anchor">
                        {graph.anchors[b.anchor]?.name ?? b.anchor}
                      </span>{" "}
                      &mdash;{" "}
                      <span className="edge">
                        {b.kind.replace(/_/g, " ").toLowerCase()}:{" "}
                        {pretty(b.item)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="sugg-actions">
                <button
                  className={`sugg-action up ${fb === "up" ? "active" : ""}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleFeedback(c.id, "up");
                  }}
                  title="Good match"
                  aria-label="Good match"
                >
                  ↑
                </button>
                <button
                  className={`sugg-action down ${fb === "down" ? "active" : ""}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleFeedback(c.id, "down");
                  }}
                  title="Not relevant"
                  aria-label="Not relevant"
                >
                  ↓
                </button>
              </div>
              <div className="sugg-score">{c.score.toFixed(2)}</div>
            </div>
          );
        })}
      </div>

      {hasMore && (
        <div className="show-more">
          <button onClick={onShowMore}>show more</button>
        </div>
      )}

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
