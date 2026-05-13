import { useEffect, useMemo, useRef } from "react";
import Map, {
  Marker,
  NavigationControl,
  Source,
  Layer,
  type MapRef,
} from "react-map-gl/mapbox";
import type { FeatureCollection, LineString } from "geojson";
import "mapbox-gl/dist/mapbox-gl.css";
import { HOOD_LABELS } from "../data/graph";
import type { Graph, RankedCandidate, VenueId } from "../types";
import VenuePopup from "./VenuePopup";

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN;

interface Props {
  graph: Graph | null;
  results: RankedCandidate[];
  focusedId: VenueId | null;
  onPinClick: (id: VenueId) => void;
  onPopupClose: () => void;
}

/**
 * Build a GeoJSON FeatureCollection of arched lines from each anchor
 * to each candidate. Curves are drawn by sampling a quadratic bezier
 * with a midpoint offset perpendicular to the chord — purely cosmetic,
 * gives the lines that "thread on a map" feel.
 */
function buildEdgeCollection(
  graph: Graph,
  results: RankedCandidate[]
): FeatureCollection<LineString> {
  const features: FeatureCollection<LineString>["features"] = [];

  for (const c of results) {
    const cPos = graph.venues[c.id]?.loc;
    if (!cPos) continue;
    const anchors = new Set(c.breakdown.slice(0, 2).map((b) => b.anchor));
    for (const aId of anchors) {
      const aPos = graph.anchors[aId]?.loc;
      if (!aPos) continue;
      features.push({
        type: "Feature",
        geometry: {
          type: "LineString",
          coordinates: bezierArc(aPos, cPos, 24),
        },
        properties: { anchor: aId, candidate: c.id },
      });
    }
  }

  return { type: "FeatureCollection", features };
}

function bezierArc(
  a: [number, number],
  b: [number, number],
  steps: number
): [number, number][] {
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const len = Math.hypot(dx, dy);
  const offset = len * 0.25;
  const px = -dy / (len || 1);
  const py = dx / (len || 1);
  const mx = (a[0] + b[0]) / 2 + px * offset;
  const my = (a[1] + b[1]) / 2 + py * offset;

  const pts: [number, number][] = [];
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    const x = (1 - t) * (1 - t) * a[0] + 2 * (1 - t) * t * mx + t * t * b[0];
    const y = (1 - t) * (1 - t) * a[1] + 2 * (1 - t) * t * my + t * t * b[1];
    pts.push([x, y]);
  }
  return pts;
}

export default function MapView({
  graph,
  results,
  focusedId,
  onPinClick,
  onPopupClose,
}: Props) {
  const mapRef = useRef<MapRef | null>(null);

  const matchIds = useMemo(() => new Set(results.map((r) => r.id)), [results]);
  const edges = useMemo(() => {
    if (!graph || results.length === 0) {
      return { type: "FeatureCollection" as const, features: [] };
    }
    const filtered = focusedId
      ? results.filter((r) => r.id === focusedId)
      : results;
    return buildEdgeCollection(graph, filtered);
  }, [graph, results, focusedId]);

  // When focus changes, fly to that pin
  useEffect(() => {
    if (!focusedId || !graph) return;
    const v = graph.venues[focusedId] ?? graph.anchors[focusedId];
    if (!v || !mapRef.current) return;
    mapRef.current.flyTo({
      center: v.loc,
      zoom: 14.5,
      duration: 900,
      essential: true,
    });
  }, [focusedId, graph]);

  // When new results arrive, fit them in view
  useEffect(() => {
    if (!graph || results.length === 0 || !mapRef.current) return;
    const pts: [number, number][] = [];
    for (const a of Object.values(graph.anchors)) pts.push(a.loc);
    for (const r of results) pts.push(graph.venues[r.id].loc);
    if (pts.length < 2) return;
    const lngs = pts.map((p) => p[0]);
    const lats = pts.map((p) => p[1]);
    mapRef.current.fitBounds(
      [
        [Math.min(...lngs), Math.min(...lats)],
        [Math.max(...lngs), Math.max(...lats)],
      ],
      { padding: { top: 220, bottom: 220, left: 80, right: 80 }, duration: 900 }
    );
  }, [results, graph]);

  if (!graph) return <div className="mapwrap" />;

  return (
    <div className="mapwrap">
      <Map
        ref={mapRef}
        mapboxAccessToken={MAPBOX_TOKEN}
        initialViewState={{
          longitude: graph.user.center[0],
          latitude: graph.user.center[1],
          zoom: 13.4,
        }}
        mapStyle="mapbox://styles/mapbox/light-v11"
        attributionControl={true}
      >
        <NavigationControl position="top-right" showCompass={false} />

        {/* Edges: arcs between anchor and candidate pins */}
        <Source id="edges" type="geojson" data={edges}>
          <Layer
            id="edges-line"
            type="line"
            paint={{
              "line-color": "#c4452d",
              "line-width": 1.6,
              "line-dasharray": [2, 2],
              "line-opacity": 0.7,
            }}
          />
        </Source>

        {/* Anchor (loved) markers */}
        {Object.values(graph.anchors).map((a) => {
          const isFocused = focusedId === a.id;
          return (
            <Marker
              key={a.id}
              longitude={a.loc[0]}
              latitude={a.loc[1]}
              anchor="center"
              onClick={(e) => {
                e.originalEvent.stopPropagation();
                onPinClick(a.id);
              }}
            >
              <div className={`pin loved ${isFocused ? "focused" : ""}`}>
                <span className="label">♥ {a.name}</span>
              </div>
            </Marker>
          );
        })}

        {/* Candidate markers */}
        {Object.values(graph.venues).map((v) => {
          const isMatch = matchIds.has(v.id);
          const isDim = matchIds.size > 0 && !isMatch;
          const isFocused = focusedId === v.id;
          let cls = "pin candidate";
          if (isMatch) cls += " match";
          if (isFocused) cls += " match focused";
          if (isDim && !isFocused) cls += " dim";
          return (
            <Marker
              key={v.id}
              longitude={v.loc[0]}
              latitude={v.loc[1]}
              anchor="center"
              onClick={(e) => {
                e.originalEvent.stopPropagation();
                onPinClick(v.id);
              }}
            >
              <div className={cls}>
                <span className="label">{v.name}</span>
              </div>
            </Marker>
          );
        })}

        {/* Neighborhood labels */}
        {HOOD_LABELS.map((h) => (
          <Marker
            key={h.name}
            longitude={h.loc[0]}
            latitude={h.loc[1]}
            anchor="center"
          >
            <div className="hood-label">{h.name}</div>
          </Marker>
        ))}

        {/* Click-to-describe popup */}
        <VenuePopup
          graph={graph}
          venueId={focusedId}
          results={results}
          onClose={onPopupClose}
        />
      </Map>
    </div>
  );
}
