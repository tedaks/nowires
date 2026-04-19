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

interface Props {
  onMapClick: (lngLat: LatLng) => void;
}

const MapView = forwardRef<MapViewHandle, Props>(function MapView(
  { onMapClick },
  ref
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const onMapClickRef = useRef(onMapClick);
  onMapClickRef.current = onMapClick;

  const txMarkerRef = useRef<maplibregl.Marker | null>(null);
  const rxMarkerRef = useRef<maplibregl.Marker | null>(null);
  const covMarkerRef = useRef<maplibregl.Marker | null>(null);

  useImperativeHandle(ref, () => ({
    drawPath(tx, rx) {
      const map = mapRef.current;
      if (!map) return;
      (map.getSource("path-line") as maplibregl.GeoJSONSource)?.setData({
        type: "FeatureCollection",
        features: [
          {
            type: "Feature",
            geometry: {
              type: "LineString",
              coordinates: [[tx.lng, tx.lat], [rx.lng, rx.lat]],
            },
            properties: {},
          },
        ],
      });
    },

    drawHorizons(horizons, tx, rx, totalDistM) {
      const map = mapRef.current;
      if (!map) return;
      const features = horizons.map((h) => {
        const t = h.d_m / totalDistM;
        const lng = tx.lng + t * (rx.lng - tx.lng);
        const lat = tx.lat + t * (rx.lat - tx.lat);
        return {
          type: "Feature" as const,
          geometry: { type: "Point" as const, coordinates: [lng, lat] },
          properties: { role: h.role },
        };
      });
      (map.getSource("horizons") as maplibregl.GeoJSONSource)?.setData({
        type: "FeatureCollection",
        features,
      });
    },

    addCoverageOverlay(result) {
      const map = mapRef.current;
      if (!map) return;
      const { png_base64, bounds } = result;
      const [minLat, minLon] = bounds[0];
      const [maxLat, maxLon] = bounds[1];
      const coordinates: [[number, number], [number, number], [number, number], [number, number]] = [
        [minLon, maxLat],
        [maxLon, maxLat],
        [maxLon, minLat],
        [minLon, minLat],
      ];
      try {
        if (map.getLayer("coverage-overlay-layer")) {
          map.removeLayer("coverage-overlay-layer");
        }
        if (map.getSource("coverage-overlay")) {
          map.removeSource("coverage-overlay");
        }
      } catch {
        // may not exist yet
      }
      map.addSource("coverage-overlay", {
        type: "image",
        url: "data:image/png;base64," + png_base64,
        coordinates,
      });
      map.addLayer(
        {
          id: "coverage-overlay-layer",
          type: "raster",
          source: "coverage-overlay",
          paint: { "raster-opacity": 0.75 },
        },
        "path-line-layer"
      );
    },

    removeCoverageOverlay() {
      const map = mapRef.current;
      if (!map) return;
      try {
        if (map.getLayer("coverage-overlay-layer")) {
          map.removeLayer("coverage-overlay-layer");
        }
        if (map.getSource("coverage-overlay")) {
          map.removeSource("coverage-overlay");
        }
      } catch {
        // Layer/source may not exist
      }
    },

    setOverlayOpacity(opacity) {
      const map = mapRef.current;
      if (!map) return;
      if (map.getLayer("coverage-overlay-layer")) {
        map.setPaintProperty("coverage-overlay-layer", "raster-opacity", opacity);
      }
    },

    addSiteLayer(site) {
      const map = mapRef.current;
      if (!map) return;
      const layerId = `site-coverage-${site.id}`;
      const sourceId = `site-source-${site.id}`;
      const { png_base64, bounds } = site.coverage_data;
      const [minLat, minLon] = bounds[0];
      const [maxLat, maxLon] = bounds[1];
      map.addSource(sourceId, {
        type: "image",
        url: `data:image/png;base64,${png_base64}`,
        coordinates: [
          [minLon, maxLat],
          [maxLon, maxLat],
          [maxLon, minLat],
          [minLon, minLat],
        ],
      });
      map.addLayer(
        { id: layerId, type: "raster", source: sourceId, paint: { "raster-opacity": site.opacity } },
        "path-line-layer"
      );
    },

    removeSiteLayer(siteId) {
      const map = mapRef.current;
      if (!map) return;
      const layerId = `site-coverage-${siteId}`;
      const sourceId = `site-source-${siteId}`;
      if (map.getLayer(layerId)) map.removeLayer(layerId);
      if (map.getSource(sourceId)) map.removeSource(sourceId);
    },

    setSiteVisibility(siteId, visible) {
      const map = mapRef.current;
      if (!map) return;
      const layerId = `site-coverage-${siteId}`;
      if (map.getLayer(layerId))
        map.setLayoutProperty(layerId, "visibility", visible ? "visible" : "none");
    },

    setSiteOpacity(siteId, opacity) {
      const map = mapRef.current;
      if (!map) return;
      const layerId = `site-coverage-${siteId}`;
      if (map.getLayer(layerId))
        map.setPaintProperty(layerId, "raster-opacity", opacity);
    },

    setTxMarker(lngLat) {
      txMarkerRef.current?.remove();
      txMarkerRef.current = null;
      if (lngLat && mapRef.current) {
        txMarkerRef.current = new maplibregl.Marker({ color: "#22c55e" })
          .setLngLat([lngLat.lng, lngLat.lat])
          .addTo(mapRef.current);
      }
    },

    setRxMarker(lngLat) {
      rxMarkerRef.current?.remove();
      rxMarkerRef.current = null;
      if (lngLat && mapRef.current) {
        rxMarkerRef.current = new maplibregl.Marker({ color: "#ef4444" })
          .setLngLat([lngLat.lng, lngLat.lat])
          .addTo(mapRef.current);
      }
    },

    setCovMarker(lngLat) {
      covMarkerRef.current?.remove();
      covMarkerRef.current = null;
      if (lngLat && mapRef.current) {
        covMarkerRef.current = new maplibregl.Marker({ color: "#22c55e" })
          .setLngLat([lngLat.lng, lngLat.lat])
          .addTo(mapRef.current);
      }
    },

    resize() {
      mapRef.current?.resize();
    },
  }));

  useEffect(() => {
    if (!containerRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: {
        version: 8,
        sources: {
          hillshade: {
            type: "raster",
            tiles: [
              "https://server.arcgisonline.com/ArcGIS/rest/services/Elevation/World_Hillshade/MapServer/tile/{z}/{y}/{x}",
            ],
            tileSize: 256,
            attribution: "© Esri World Hillshade",
          },
          osm: {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "© OpenStreetMap contributors",
          },
        },
        layers: [
          { id: "hillshade", type: "raster", source: "hillshade" },
          { id: "osm", type: "raster", source: "osm", paint: { "raster-opacity": 0.55 } },
        ],
      },
      center: [121.0, 12.0],
      zoom: 6,
    });

    map.on("load", () => {
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
    });

    map.on("click", (e) => {
      const { lng, lat } = e.lngLat;
      onMapClickRef.current({ lng, lat });
    });

    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  return <div ref={containerRef} className="w-full h-full min-h-[400px]" />;
});

export default MapView;
