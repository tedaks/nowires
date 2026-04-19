import maplibregl from "maplibre-gl";
import type { LatLng, CoverageResponse, Horizon } from "@/lib/types";
import type { CoverageSite } from "@/lib/site";

export function drawPath(map: maplibregl.Map | null, tx: LatLng, rx: LatLng) {
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
}

export function drawHorizons(
  map: maplibregl.Map | null,
  horizons: Horizon[],
  tx: LatLng,
  rx: LatLng,
  totalDistM: number
) {
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
}

export function addCoverageOverlay(map: maplibregl.Map | null, result: CoverageResponse) {
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
}

export function removeCoverageOverlay(map: maplibregl.Map | null) {
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
}

export function setOverlayOpacity(map: maplibregl.Map | null, opacity: number) {
  if (!map) return;
  if (map.getLayer("coverage-overlay-layer")) {
    map.setPaintProperty("coverage-overlay-layer", "raster-opacity", opacity);
  }
}

export function addSiteLayer(map: maplibregl.Map | null, site: CoverageSite) {
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
}

export function removeSiteLayer(map: maplibregl.Map | null, siteId: string) {
  if (!map) return;
  const layerId = `site-coverage-${siteId}`;
  const sourceId = `site-source-${siteId}`;
  if (map.getLayer(layerId)) map.removeLayer(layerId);
  if (map.getSource(sourceId)) map.removeSource(sourceId);
}

export function setSiteVisibility(map: maplibregl.Map | null, siteId: string, visible: boolean) {
  if (!map) return;
  const layerId = `site-coverage-${siteId}`;
  if (map.getLayer(layerId))
    map.setLayoutProperty(layerId, "visibility", visible ? "visible" : "none");
}

export function setSiteOpacity(map: maplibregl.Map | null, siteId: string, opacity: number) {
  if (!map) return;
  const layerId = `site-coverage-${siteId}`;
  if (map.getLayer(layerId))
    map.setPaintProperty(layerId, "raster-opacity", opacity);
}