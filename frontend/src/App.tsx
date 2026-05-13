import { useCallback, useEffect, useRef, useState } from "react";
import MapView from "./components/MapView";
import TopBar from "./components/TopBar";
import SearchBar from "./components/SearchBar";
import Suggestions from "./components/Suggestions";
import ProfileCard from "./components/ProfileCard";
import HintCard from "./components/HintCard";
import MiniSearch from "./components/MiniSearch";
import SponsorBadge from "./components/SponsorBadge";
import { GraphProvider } from "./contexts/GraphContext";
import { useSearch } from "./hooks/useSearch";

const HOTKEYS: Record<string, string> = {
  "1": "bagels near me",
  "2": "weekend brunch",
  "3": "curry tonight",
  "4": "where should I eat?",
};

export default function App() {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const {
    graph,
    graphError,
    query,
    setQuery,
    results,
    showMore,
    hasMore,
    isLoading,
    isOpen,
    close,
    focusedId,
    setFocusedId,
  } = useSearch();
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    if (graph && !collapsed) inputRef.current?.focus();
  }, [graph, collapsed]);

  const expand = useCallback(() => {
    setCollapsed(false);
    requestAnimationFrame(() => inputRef.current?.focus());
  }, []);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const isInput =
        (e.target as HTMLElement | null)?.tagName === "INPUT" ||
        (e.target as HTMLElement | null)?.tagName === "TEXTAREA";

      if (e.key === "Escape") {
        if (focusedId) {
          setFocusedId(null);
          return;
        }
        setQuery("");
        close();
        inputRef.current?.blur();
        return;
      }

      const preset = HOTKEYS[e.key];
      if (preset) {
        // Hotkeys 1–4 override even when the input has focus — they're the
        // primary demo interaction. preventDefault keeps the digit from being
        // typed into the input alongside the preset.
        if (isInput) e.preventDefault();
        if (collapsed) setCollapsed(false);
        setQuery(preset);
        if (inputRef.current) inputRef.current.value = preset;
        return;
      }

      if (isInput) return;
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [close, setQuery, focusedId, setFocusedId, collapsed]);

  if (graphError) {
    return (
      <div
        style={{
          position: "fixed",
          inset: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "column",
          gap: 8,
          fontFamily: "JetBrains Mono, monospace",
          fontSize: 11,
          letterSpacing: "0.15em",
          textTransform: "uppercase" as const,
          opacity: 0.55,
        }}
      >
        <span style={{ color: "#c4452d" }}>failed to load graph</span>
        <span style={{ fontSize: 9, opacity: 0.7 }}>{graphError}</span>
      </div>
    );
  }

  if (!graph) {
    return (
      <div
        style={{
          position: "fixed",
          inset: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "JetBrains Mono, monospace",
          fontSize: 11,
          letterSpacing: "0.15em",
          textTransform: "uppercase" as const,
          opacity: 0.55,
        }}
      >
        loading graph...
      </div>
    );
  }

  return (
    <GraphProvider value={graph}>
      <MapView
        results={results}
        focusedId={focusedId}
        onPinClick={(id) => setFocusedId(id)}
        onPopupClose={() => setFocusedId(null)}
      />
      <div className="grain" />
      <div className="paper-tint" />

      <TopBar />

      <div className={`stage ${collapsed ? "collapsed" : ""}`}>
        <div className="composer">
          <button
            className="collapse-btn"
            onClick={() => setCollapsed(true)}
            title="Hide search — use the map"
            aria-label="Collapse search"
          >
            ⌃
          </button>
          <h1 className="tagline">
            Search that <em>knows</em> your spots.
            <span className="sub">
              — from places you love, to places you'll love —
            </span>
          </h1>
          <SearchBar
            ref={inputRef}
            value={query}
            onChange={setQuery}
            onSubmit={() => {
              if (!query.trim()) setQuery("where should I eat?");
            }}
            isOpen={isOpen}
          />
          <div className={`drop ${isOpen ? "open" : ""}`}>
            <div className="drop-inner">
              <Suggestions
                results={results}
                query={query}
                isLoading={isLoading}
                hasMore={hasMore}
                onShowMore={showMore}
                onSelect={(id) => setFocusedId(id)}
              />
            </div>
          </div>
        </div>
      </div>

      <MiniSearch show={collapsed} query={query} onExpand={expand} />

      <ProfileCard onFocus={(id) => setFocusedId(id)} />
      <HintCard />
      <SponsorBadge />
    </GraphProvider>
  );
}
