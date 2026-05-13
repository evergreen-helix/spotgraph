/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_MAPBOX_TOKEN: string;
  readonly VITE_USE_BACKEND: string;
  readonly VITE_USE_OSM: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
