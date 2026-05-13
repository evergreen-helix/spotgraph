import { useEffect, useRef } from "react";
import MapView from "./components/MapView";
import TopBar from "./components/TopBar";
import SearchBar from "./components/SearchBar";
import Suggestions from "./components/Suggestions";
import ProfileCard from "./components/ProfileCard";
import HintCard from "./components/HintCard";
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
    query,
    setQuery,
    results,
    isOpen,
    close,
    focusedId,
    setFocusedId,
  } = useSearch();

  useEffect(() => {
    inputRef.current?.focus();
  }, [graph]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const isInput =
        (e.target as HTMLElement | null)?.tagName === "INPUT" ||
        (e.target as HTMLElement | null)?.tagName === "TEXTAREA";
      // Escape always works
      if (e.key === "Escape") {
        setQuery("");
        close();
        inputRef.current?.blur();
        return;
      }
      // Hotkeys 1-4 only when not typing into the input
      if (isInput) return;
      const preset = HOTKEYS[e.key];
      if (preset) {
        setQuery(preset);
        if (inputRef.current) inputRef.current.value = preset;
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [close, setQuery]);

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
          textTransform: "uppercase",
          opacity: 0.55,
        }}
      >
        loading graph…
      </div>
    );
  }

  return (
    <>
      <MapView
        graph={graph}
        results={results}
        focusedId={focusedId}
        onPinClick={(id) => setFocusedId(id)}
      />
      <div className="grain" />
      <div className="paper-tint" />

      <TopBar />

      <div className="stage">
        <div className="composer">
          <h1 className="tagline">
            Search that <em>knows</em> your spots.
            <span className="sub">— from places you love, to places you'll love —</span>
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
                graph={graph}
                results={results}
                query={query}
                onSelect={(id) => setFocusedId(id)}
              />
            </div>
          </div>
        </div>
      </div>

      <ProfileCard graph={graph} onFocus={(id) => setFocusedId(id)} />
      <HintCard />
    </>
  );
}
