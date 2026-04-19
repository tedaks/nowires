"use client";

import { useState, useCallback } from "react";
import type { MapViewHandle } from "@/components/map/MapView";
import type { CoverageSite } from "@/lib/site";
import { createSite } from "@/lib/site";
import type { CoverageResponse } from "@/lib/types";

interface UseSitesOptions {
  mapRef: React.RefObject<MapViewHandle | null>;
  onShowSites: () => void;
}

export function useSites({ mapRef, onShowSites }: UseSitesOptions) {
  const [sites, setSites] = useState<CoverageSite[]>([]);

  const addSite = useCallback(
    (name: string, txCoords: { lat: number; lon: number }, coverageResult: CoverageResponse) => {
      const site = createSite(name, txCoords, coverageResult, sites.length);
      mapRef.current?.addSiteLayer(site);
      setSites((prev) => [...prev, site]);
      onShowSites();
      return site;
    },
    [mapRef, onShowSites, sites.length]
  );

  const toggleSite = useCallback((id: number, visible: boolean) => {
    mapRef.current?.setSiteVisibility(id, visible);
    setSites((prev) => prev.map((s) => (s.id === id ? { ...s, visible } : s)));
  }, [mapRef]);

  const setSiteOpacity = useCallback((id: number, opacity: number) => {
    mapRef.current?.setSiteOpacity(id, opacity);
    setSites((prev) => prev.map((s) => (s.id === id ? { ...s, opacity } : s)));
  }, [mapRef]);

  const removeSite = useCallback((id: number) => {
    mapRef.current?.removeSiteLayer(id);
    setSites((prev) => prev.filter((s) => s.id !== id));
  }, [mapRef]);

  const clearAllSites = useCallback(() => {
    sites.forEach((s) => mapRef.current?.removeSiteLayer(s.id));
    setSites([]);
  }, [mapRef, sites]);

  return { sites, addSite, toggleSite, setSiteOpacity, removeSite, clearAllSites };
}