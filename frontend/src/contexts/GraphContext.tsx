import { createContext, useContext } from "react";
import type { Graph } from "../types";

const GraphContext = createContext<Graph | null>(null);

export const GraphProvider = GraphContext.Provider;

export function useGraph(): Graph {
  const ctx = useContext(GraphContext);
  if (!ctx) throw new Error("useGraph must be used inside <GraphProvider>");
  return ctx;
}
