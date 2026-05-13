import { useCallback, useEffect, useState } from "react";
import type { Graph, RankedCandidate } from "../types";
import { fetchGraph, rank } from "../lib/api";

const INITIAL_COUNT = 4;
const PAGE_SIZE = 4;

interface UseSearchResult {
  graph: Graph | null;
  graphError: string | null;
  query: string;
  setQuery: (q: string) => void;
  results: RankedCandidate[];
  visibleCount: number;
  showMore: () => void;
  hasMore: boolean;
  isLoading: boolean;
  isOpen: boolean;
  open: () => void;
  close: () => void;
  focusedId: string | null;
  setFocusedId: (id: string | null) => void;
}

export function useSearch(): UseSearchResult {
  const [graph, setGraph] = useState<Graph | null>(null);
  const [graphError, setGraphError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [allResults, setAllResults] = useState<RankedCandidate[]>([]);
  const [visibleCount, setVisibleCount] = useState(INITIAL_COUNT);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [focusedId, setFocusedId] = useState<string | null>(null);

  useEffect(() => {
    fetchGraph()
      .then(setGraph)
      .catch((e) => setGraphError(e.message ?? "Failed to load graph"));
  }, []);

  useEffect(() => {
    if (!graph) return;
    if (!query.trim()) {
      setAllResults([]);
      setVisibleCount(INITIAL_COUNT);
      setIsOpen(false);
      setFocusedId(null);
      return;
    }
    let cancelled = false;
    setIsLoading(true);
    rank(graph, query).then((r) => {
      if (cancelled) return;
      setAllResults(r);
      setVisibleCount(INITIAL_COUNT);
      setIsOpen(true);
      setIsLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [graph, query]);

  const results = allResults.slice(0, visibleCount);
  const hasMore = visibleCount < allResults.length;

  const showMore = useCallback(() => {
    setVisibleCount((c) => c + PAGE_SIZE);
  }, []);

  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => {
    setIsOpen(false);
    setFocusedId(null);
  }, []);

  return {
    graph,
    graphError,
    query,
    setQuery,
    results,
    visibleCount,
    showMore,
    hasMore,
    isLoading,
    isOpen,
    open,
    close,
    focusedId,
    setFocusedId,
  };
}
