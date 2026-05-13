import { useCallback, useEffect, useState } from "react";
import type { Graph, RankedCandidate } from "../types";
import { fetchGraph, rank } from "../lib/api";

interface UseSearchResult {
  graph: Graph | null;
  query: string;
  setQuery: (q: string) => void;
  results: RankedCandidate[];
  isOpen: boolean;
  open: () => void;
  close: () => void;
  focusedId: string | null;
  setFocusedId: (id: string | null) => void;
}

export function useSearch(): UseSearchResult {
  const [graph, setGraph] = useState<Graph | null>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<RankedCandidate[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [focusedId, setFocusedId] = useState<string | null>(null);

  useEffect(() => {
    fetchGraph().then(setGraph);
  }, []);

  useEffect(() => {
    if (!graph) return;
    if (!query.trim()) {
      setResults([]);
      setIsOpen(false);
      setFocusedId(null);
      return;
    }
    let cancelled = false;
    rank(graph, query).then((r) => {
      if (cancelled) return;
      setResults(r.slice(0, 4));
      setIsOpen(true);
    });
    return () => {
      cancelled = true;
    };
  }, [graph, query]);

  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => {
    setIsOpen(false);
    setFocusedId(null);
  }, []);

  return {
    graph,
    query,
    setQuery,
    results,
    isOpen,
    open,
    close,
    focusedId,
    setFocusedId,
  };
}
