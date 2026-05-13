import { Popup } from "react-map-gl/mapbox";
import type { Anchor, RankedCandidate, Venue, VenueId } from "../types";
import { useGraph } from "../contexts/GraphContext";
import { pretty } from "../lib/rank";

interface Props {
  venueId: VenueId | null;
  results: RankedCandidate[];
  onClose: () => void;
}

function Tags({ label, items }: { label: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <div className="popup-row">
      <span className="popup-row-label">{label}</span>
      <span className="popup-tags">
        {items.map((t) => (
          <span className="popup-tag" key={t}>
            {pretty(t)}
          </span>
        ))}
      </span>
    </div>
  );
}

export default function VenuePopup({ venueId, results, onClose }: Props) {
  const graph = useGraph();

  if (!venueId) return null;
  const anchor = graph.anchors[venueId] as Anchor | undefined;
  const candidate = anchor ? undefined : (graph.venues[venueId] as Venue | undefined);
  const venue: Venue | Anchor | undefined = anchor ?? candidate;
  if (!venue) return null;

  const ranked = results.find((r) => r.id === venueId);
  const isAnchor = !!anchor;

  return (
    <Popup
      longitude={venue.loc[0]}
      latitude={venue.loc[1]}
      anchor="bottom"
      offset={22}
      closeButton={true}
      closeOnClick={false}
      onClose={onClose}
      maxWidth="320px"
      className="venue-popup"
    >
      <div className={`popup ${isAnchor ? "anchor" : "candidate"}`}>
        <div className="popup-head">
          {isAnchor && <span className="popup-heart">♥</span>}
          <h3 className="popup-name">{venue.name}</h3>
        </div>
        <div className="popup-sub">
          {isAnchor ? "visited venue" : "suggestion"} · {pretty(venue.area)}
          {!isAnchor && ` · ${venue.dist.toFixed(1)} km`}
        </div>

        {isAnchor && anchor && (
          <div className="popup-stats">
            <span>
              <b>{anchor.searchCount}×</b> searches
            </span>
            <span>
              <b>{anchor.directions}×</b> directions
            </span>
            <span>
              <b>{anchor.saves}×</b> saves
            </span>
          </div>
        )}

        {ranked && !isAnchor && (
          <div className="popup-why">
            <div className="popup-why-head">Why this matches your taste</div>
            {ranked.breakdown.slice(0, 3).map((b, i) => (
              <div className="popup-why-row" key={i}>
                <span className="popup-why-anchor">
                  ♥ {graph.anchors[b.anchor]?.name ?? b.anchor}
                </span>
                <span className="popup-why-edge">
                  {b.kind.replace(/_/g, " ").toLowerCase()}: {pretty(b.item)}
                </span>
              </div>
            ))}
          </div>
        )}

        <div className="popup-body">
          <Tags label="Dishes" items={venue.dishes} />
          <Tags label="Cuisine" items={venue.cuisine} />
          <Tags label="Vibe" items={venue.vibe} />
        </div>

        <div className="popup-foot">
          {isAnchor
            ? "graph anchor — defines your taste"
            : ranked
              ? `score ${ranked.score.toFixed(2)} · ${ranked.breakdown.length} edges`
              : "search to see how this connects to your anchors"}
        </div>
      </div>
    </Popup>
  );
}
