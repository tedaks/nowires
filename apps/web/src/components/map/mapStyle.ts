import type maplibregl from "maplibre-gl";

export function getMapStyle() {
  return {
    version: 8 as const,
    sources: {
      hillshade: {
        type: "raster" as const,
        tiles: [
          "https://server.arcgisonline.com/ArcGIS/rest/services/Elevation/World_Hillshade/MapServer/tile/{z}/{y}/{x}",
        ],
        tileSize: 256,
        attribution: "© Esri World Hillshade",
      },
      osm: {
        type: "raster" as const,
        tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
        tileSize: 256,
        attribution: "© OpenStreetMap contributors",
      },
    },
    layers: [
      { id: "hillshade", type: "raster" as const, source: "hillshade" },
      { id: "osm", type: "raster" as const, source: "osm", paint: { "raster-opacity": 0.55 } },
    ],
  };
}

export function addInitialSourcesAndLayers(map: maplibregl.Map) {
  map.addSource("path-line", {
    type: "geojson",
    data: { type: "FeatureCollection", features: [] },
  });
  map.addLayer({
    id: "path-line-layer",
    type: "line",
    source: "path-line",
    paint: { "line-color": "#22d3ee", "line-width": 3 },
  });
  map.addSource("horizons", {
    type: "geojson",
    data: { type: "FeatureCollection", features: [] },
  });
  map.addLayer({
    id: "horizons-layer",
    type: "circle",
    source: "horizons",
    paint: {
      "circle-radius": 6,
      "circle-color": "#f59e0b",
      "circle-stroke-color": "#0b0b0b",
      "circle-stroke-width": 2,
    },
  });
}