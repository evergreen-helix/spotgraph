import type { Graph, VenueId } from "../types";
import { pretty } from "../lib/rank";

interface Props {
  graph: Graph;
  onFocus: (id: VenueId) => void;
}

export default function ProfileCard({ graph, onFocus }: Props) {
  const totalSearches = Object.values(graph.anchors).reduce(
    (s, a) => s + a.searchCount,
    0
  );
  const totalDir = Object.values(graph.anchors).reduce(
    (s, a) => s + a.directions,
    0
  );
  const totalSaves = Object.values(graph.anchors).reduce(
    (s, a) => s + a.saves,
    0
  );

  return (
    <div className="profile">
      <h4>
        Your anchor venues
        <br />— inferred from search history
      </h4>
      <div className="name">{graph.user.name}</div>
      <div className="loved-list">
        {Object.values(graph.anchors).map((a) => (
          <div
            key={a.id}
            className="loved-item"
            onClick={() => onFocus(a.id)}
          >
            <span className="heart">♥</span>
            <span className="place">{a.name}</span>
            <span className="area">— {pretty(a.area)}</span>
          </div>
        ))}
      </div>
      <div className="source">
        From {totalSearches}× searches · {totalDir}× direction requests ·{" "}
        {totalSaves}× saves
      </div>
    </div>
  );
}
