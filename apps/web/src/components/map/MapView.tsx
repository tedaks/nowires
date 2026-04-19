"use client";

import { useEffect, useRef, useImperativeHandle, forwardRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { LatLng, CoverageResponse, Horizon } from "@/lib/types";
import type { CoverageSite } from "@/lib/site";

export interface MapViewHandle {
  drawPath(tx: LatLng, rx: LatLng): void;
  drawHorizons(horizons: Horizon[], tx: LatLng, rx: LatLng, totalDistM: number): void;
  addCoverageOverlay(result: CoverageResponse): void;
  removeCoverageOverlay(): void;
  setOverlayOpacity(opacity: number): void;
  addSiteLayer(site: CoverageSite): void;
  removeSiteLayer(siteId: number): void;
  setSiteVisibility(siteId: number, visible: boolean): void;
  setSiteOpacity(siteId: number, opacity: number): void;
  setTxMarker(lngLat: LatLng | null): void;
  setRxMarker(lngLat: LatLng | null): void;
  setCovMarker(lngLat: LatLng | null): void;
  resize(): void;
}

interface Props { onMapClick: (lngLat: LatLng) => void; }

const MAP_STYLE = {
  version: 8 as const,
  sources: {
    hillshade: { type: "raster" as const, tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/Elevation/World_Hillshade/MapServer/tile/{z}/{y}/{x}"], tileSize: 256, attribution: "© Esri World Hillshade" },
    osm: { type: "raster" as const, tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], tileSize: 256, attribution: "© OpenStreetMap contributors" },
  },
  layers: [
    { id: "hillshade", type: "raster" as const, source: "hillshade" },
    { id: "osm", type: "raster" as const, source: "osm", paint: { "raster-opacity": 0.55 } },
  ],
};

const _txMarker = () => new maplibregl.Marker({ color: "#22c55e" });
const _rxMarker = () => new maplibregl.Marker({ color: "#ef4444" });

function _geojsonSrc(data: GeoJSON.FeatureCollection) { return { type: "geojson" as const, data }; }
function _imageSrc(url: string, coords: [[number, number], [number, number], [number, number], [number, number]]) {
  return { type: "image" as const, url, coordinates: coords };
}

function _setupLayers(map: maplibregl.Map) {
  map.addSource("path-line", _geojsonSrc({ type: "FeatureCollection", features: [] }));
  map.addLayer({ id: "path-line-layer", type: "line", source: "path-line", paint: { "line-color": "#22d3ee", "line-width": 3 } });
  map.addSource("horizons", _geojsonSrc({ type: "FeatureCollection", features: [] }));
  map.addLayer({ id: "horizons-layer", type: "circle", source: "horizons", paint: { "circle-radius": 6, "circle-color": "#f59e0b", "circle-stroke-color": "#0b0b0b", "circle-stroke-width": 2 } });
}

function _boundsToCoords(bounds: [[number, number], [number, number]]): [[number, number], [number, number], [number, number], [number, number]] {
  const [[minLat, minLon], [maxLat, maxLon]] = bounds;
  return [[minLon, maxLat], [maxLon, maxLat], [maxLon, minLat], [minLon, minLat]];
}

function _updateGeoJSON(map: maplibregl.Map, source: string, features: GeoJSON.Feature[]) {
  (map.getSource(source) as maplibregl.GeoJSONSource)?.setData({ type: "FeatureCollection", features });
}

function _removeOverlay(map: maplibregl.Map, layer: string, source: string) {
  try { if (map.getLayer(layer)) map.removeLayer(layer); if (map.getSource(source)) map.removeSource(source); } catch {}
}

const MapView = forwardRef<MapViewHandle, Props>(function MapView({ onMapClick }, ref) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const onMapClickRef = useRef(onMapClick);
  onMapClickRef.current = onMapClick;

  const txMarkerRef = useRef<maplibregl.Marker | null>(null);
  const rxMarkerRef = useRef<maplibregl.Marker | null>(null);
  const covMarkerRef = useRef<maplibregl.Marker | null>(null);

  useImperativeHandle(ref, () => ({
    drawPath(tx, rx) {
      const m = mapRef.current;
      if (!m) return;
      _updateGeoJSON(m, "path-line", [{ type: "Feature", geometry: { type: "LineString", coordinates: [[tx.lng, tx.lat], [rx.lng, rx.lat]] }, properties: {} }]);
    },

    drawHorizons(horizons, tx, rx, totalDistM) {
      const m = mapRef.current;
      if (!m) return;
      const features = horizons.map((h) => {
        const t = h.d_m / totalDistM;
        return { type: "Feature" as const, geometry: { type: "Point" as const, coordinates: [tx.lng + t * (rx.lng - tx.lng), tx.lat + t * (rx.lat - tx.lat)] }, properties: { role: h.role } };
      });
      _updateGeoJSON(m, "horizons", features);
    },

    addCoverageOverlay(result) {
      const m = mapRef.current;
      if (!m) return;
      _removeOverlay(m, "coverage-overlay-layer", "coverage-overlay");
      m.addSource("coverage-overlay", _imageSrc("data:image/png;base64," + result.png_base64, _boundsToCoords(result.bounds)));
      m.addLayer({ id: "coverage-overlay-layer", type: "raster", source: "coverage-overlay", paint: { "raster-opacity": 0.75 } }, "path-line-layer");
    },

    removeCoverageOverlay() { const m = mapRef.current; if (m) _removeOverlay(m, "coverage-overlay-layer", "coverage-overlay"); },

    setOverlayOpacity(opacity) {
      const m = mapRef.current;
      if (m?.getLayer("coverage-overlay-layer")) m.setPaintProperty("coverage-overlay-layer", "raster-opacity", opacity);
    },

    addSiteLayer(site) {
      const m = mapRef.current;
      if (!m) return;
      const { png_base64, bounds } = site.coverage_data;
      const srcId = `site-source-${site.id}`;
      const layerId = `site-coverage-${site.id}`;
      m.addSource(srcId, _imageSrc(`data:image/png;base64,${png_base64}`, _boundsToCoords(bounds)));
      m.addLayer({ id: layerId, type: "raster", source: srcId, paint: { "raster-opacity": site.opacity } }, "path-line-layer");
    },

    removeSiteLayer(siteId) {
      const m = mapRef.current;
      if (!m) return;
      const layerId = `site-coverage-${siteId}`;
      const srcId = `site-source-${siteId}`;
      if (m.getLayer(layerId)) m.removeLayer(layerId);
      if (m.getSource(srcId)) m.removeSource(srcId);
    },

    setSiteVisibility(siteId, visible) {
      const m = mapRef.current;
      const layerId = `site-coverage-${siteId}`;
      if (m?.getLayer(layerId)) m.setLayoutProperty(layerId, "visibility", visible ? "visible" : "none");
    },

    setSiteOpacity(siteId, opacity) {
      const m = mapRef.current;
      const layerId = `site-coverage-${siteId}`;
      if (m?.getLayer(layerId)) m.setPaintProperty(layerId, "raster-opacity", opacity);
    },

    setTxMarker(lngLat) {
      txMarkerRef.current?.remove();
      txMarkerRef.current = null;
      if (lngLat && mapRef.current) txMarkerRef.current = _txMarker().setLngLat([lngLat.lng, lngLat.lat]).addTo(mapRef.current);
    },

    setRxMarker(lngLat) {
      rxMarkerRef.current?.remove();
      rxMarkerRef.current = null;
      if (lngLat && mapRef.current) rxMarkerRef.current = _rxMarker().setLngLat([lngLat.lng, lngLat.lat]).addTo(mapRef.current);
    },

    setCovMarker(lngLat) {
      covMarkerRef.current?.remove();
      covMarkerRef.current = null;
      if (lngLat && mapRef.current) covMarkerRef.current = _txMarker().setLngLat([lngLat.lng, lngLat.lat]).addTo(mapRef.current);
    },

    resize() { mapRef.current?.resize(); },
  }));

  useEffect(() => {
    if (!containerRef.current) return;
    const map = new maplibregl.Map({ container: containerRef.current, style: MAP_STYLE, center: [121.0, 12.0], zoom: 6 });
    map.on("error", (e) => console.error("MapLibre error:", e.error));
    map.on("load", () => _setupLayers(map));
    map.on("click", (e) => onMapClickRef.current(e.lngLat));
    mapRef.current = map;
    return () => { map.remove(); mapRef.current = null; };
  }, []);

  return <div ref={containerRef} className="w-full h-full min-h-[400px]" />;
});

export default MapView;