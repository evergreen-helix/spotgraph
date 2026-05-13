import type { Graph } from "../types";

/**
 * Mock graph that mirrors what we expect Neo4j to return.
 *
 * In production the shape is identical — `GET /api/graph` returns
 * { user, anchors, venues, weights } and `POST /api/rank { query }`
 * returns a ranked candidate list with breakdown[] (the literal Cypher
 * path that produced the score).
 *
 * Coordinates are real London lat/lngs.
 */
export const GRAPH: Graph = {
  user: {
    id: "u_alex",
    name: "Alex Chen",
    // Centered roughly on Brick Lane / Spitalfields
    center: [-0.0726, 51.5225],
  },

  // anchor venues — places Alex has searched for repeatedly
  anchors: {
    beigel: {
      id: "beigel",
      name: "Beigel Bake",
      area: "brick_lane",
      dishes: ["salt_beef_bagel", "cream_cheese_bagel"],
      cuisine: ["jewish", "east_european"],
      vibe: ["no_frills", "late_night", "counter_service", "cheap_eats"],
      loc: [-0.0716, 51.5227],
      dist: 0,
      searchCount: 14,
      saves: 6,
      directions: 9,
    },
    dishoom: {
      id: "dishoom",
      name: "Dishoom",
      area: "shoreditch",
      dishes: ["bacon_naan", "black_daal"],
      cuisine: ["indian", "bombay"],
      vibe: ["bustling", "all_day", "atmospheric"],
      loc: [-0.0779, 51.5258],
      dist: 0,
      searchCount: 11,
      saves: 4,
      directions: 7,
    },
    towpath: {
      id: "towpath",
      name: "Towpath Café",
      area: "regents_canal",
      dishes: ["sourdough_toast", "cardamom_bun"],
      cuisine: ["modern_european", "cafe"],
      vibe: ["outdoor", "seasonal", "local_favourite", "weekend_brunch"],
      loc: [-0.0759, 51.5395],
      dist: 0,
      searchCount: 8,
      saves: 3,
      directions: 5,
    },
  },

  // candidate universe
  venues: {
    brick_lane_bagel: {
      id: "brick_lane_bagel",
      name: "Brick Lane Bagel Co.",
      area: "brick_lane",
      dishes: ["salt_beef_bagel", "cream_cheese_bagel"],
      cuisine: ["jewish", "east_european"],
      vibe: ["no_frills", "late_night", "counter_service", "cheap_eats"],
      loc: [-0.0717, 51.5225],
      dist: 0.05,
    },
    poppies: {
      id: "poppies",
      name: "Poppies Fish & Chips",
      area: "spitalfields",
      dishes: ["fish_chips", "jellied_eels"],
      cuisine: ["british", "east_end"],
      vibe: ["nostalgic", "counter_service", "cheap_eats"],
      loc: [-0.0723, 51.5208],
      dist: 0.3,
    },
    ottolenghi: {
      id: "ottolenghi",
      name: "Ottolenghi",
      area: "spitalfields",
      dishes: ["aubergine", "challah", "babka"],
      cuisine: ["middle_eastern", "jewish"],
      vibe: ["bright", "brunch", "queue"],
      loc: [-0.076, 51.5179],
      dist: 0.4,
    },
    black_axe: {
      id: "black_axe",
      name: "Black Axe Mangal",
      area: "highbury",
      dishes: ["lamb_flatbread", "squid_flatbread"],
      cuisine: ["turkish_inspired", "modern_european"],
      vibe: ["loud", "music", "cult_favourite", "intense"],
      loc: [-0.098, 51.545],
      dist: 4.2,
    },
    climpsons: {
      id: "climpsons",
      name: "Climpson & Sons",
      area: "broadway_mkt",
      dishes: ["flat_white", "sourdough_toast"],
      cuisine: ["cafe", "specialty_coffee"],
      vibe: ["weekend_brunch", "outdoor", "local_favourite"],
      loc: [-0.0598, 51.5378],
      dist: 1.6,
    },
    gunpowder: {
      id: "gunpowder",
      name: "Gunpowder",
      area: "spitalfields",
      dishes: ["chettinad_duck", "rasam"],
      cuisine: ["indian", "south_indian"],
      vibe: ["bustling", "small_plates", "atmospheric"],
      loc: [-0.075, 51.5187],
      dist: 0.3,
    },
    kappacasein: {
      id: "kappacasein",
      name: "Kappacasein",
      area: "borough_mkt",
      dishes: ["raclette", "grilled_cheese"],
      cuisine: ["british", "cheese"],
      vibe: ["counter_service", "cheap_eats", "queue", "market"],
      loc: [-0.0911, 51.5054],
      dist: 5.8,
    },
    monocle: {
      id: "monocle",
      name: "Monocle Café",
      area: "marylebone",
      dishes: ["pastries", "matcha"],
      cuisine: ["cafe", "japanese_leaning"],
      vibe: ["bright", "quiet", "design_y"],
      loc: [-0.1527, 51.5188],
      dist: 6.4,
    },
    lyles: {
      id: "lyles",
      name: "Lyle's",
      area: "shoreditch",
      dishes: ["tasting_menu", "seasonal"],
      cuisine: ["modern_british"],
      vibe: ["minimal", "seasonal", "quiet"],
      loc: [-0.0784, 51.5237],
      dist: 0.6,
    },
    pophams: {
      id: "pophams",
      name: "Pophams Bakery",
      area: "hackney",
      dishes: ["pastries", "laminated_dough"],
      cuisine: ["bakery", "modern_european"],
      vibe: ["weekend_brunch", "queue", "local_favourite"],
      loc: [-0.057, 51.543],
      dist: 2.8,
    },
  },

  weights: {
    SAME_DISH: 3.0,
    SAME_CUISINE: 1.5,
    SAME_VIBE: 1.0,
    SAME_AREA: 1.2,
    DISTANCE_PENALTY: 0.15,
  },
};

export const HOOD_LABELS: { name: string; loc: [number, number] }[] = [
  { name: "Shoreditch", loc: [-0.078, 51.527] },
  { name: "Spitalfields", loc: [-0.074, 51.519] },
  { name: "Whitechapel", loc: [-0.064, 51.516] },
  { name: "Bethnal Green", loc: [-0.054, 51.527] },
  { name: "Clerkenwell", loc: [-0.105, 51.523] },
  { name: "Hackney", loc: [-0.057, 51.547] },
  { name: "Broadway Market", loc: [-0.06, 51.538] },
  { name: "Brick Lane", loc: [-0.072, 51.522] },
];
