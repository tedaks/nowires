"use client";

import { useRef, useState, useCallback, useEffect } from "react";
import dynamic from "next/dynamic";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import P2PPanel from "@/components/p2p/P2PPanel";
import CoveragePanel from "@/components/coverage/CoveragePanel";
import SitesPanel from "@/components/coverage/SitesPanel";
import type { MapViewHandle } from "@/components/map/MapView";
import type { LatLng, P2PResponse, CoverageResponse } from "@/lib/types";
import type { CoverageSite } from "@/lib/site";
import { createSite } from "@/lib/site";

const MapView = dynamic(() => import("@/components/map/MapView"), { ssr: false });

type TabId = "p2p" | "coverage";

export default function Home() {
  const mapRef = useRef<MapViewHandle>(null);
  const [activeTab, setActiveTab] = useState<TabId>("p2p");

  // P2P state — tracks click sequence (null → tx set → rx set → reset cycle)
  const [txCoords, setTxCoords] = useState<LatLng | null>(null);
  const [rxCoords, setRxCoords] = useState<LatLng | null>(null);
  // Use refs to read current values inside the callback without stale closure
  const txRef = useRef<LatLng | null>(null);
  const rxRef = useRef<LatLng | null>(null);

  // Coverage state
  const [covTxCoords, setCovTxCoords] = useState<{ lat: number; lon: number } | null>(null);
  const [currentCoverageResult, setCurrentCoverageResult] = useState<CoverageResponse | null>(null);
  const [sites, setSites] = useState<CoverageSite[]>([]);
  const [showSites, setShowSites] = useState(false);

  // Dialog state
  const [siteNameDialogOpen, setSiteNameDialogOpen] = useState(false);
  const [clearConfirmDialogOpen, setClearConfirmDialogOpen] = useState(false);
  const [siteNameInput, setSiteNameInput] = useState("");

  const activeTabRef = useRef<TabId>("p2p");
  // Keep ref in sync outside render via effect so it's safe to read in the callback
  // (eslint react-hooks/refs forbids mutating ref.current during render)
  useEffect(() => {
    activeTabRef.current = activeTab;
  }, [activeTab]);

  const handleMapClick = useCallback((lngLat: LatLng) => {
    const { lat, lng } = lngLat;

    if (activeTabRef.current === "p2p") {
      if (!txRef.current) {
        txRef.current = lngLat;
        setTxCoords(lngLat);
        mapRef.current?.setTxMarker(lngLat);
      } else if (!rxRef.current) {
        rxRef.current = lngLat;
        setRxCoords(lngLat);
        mapRef.current?.setRxMarker(lngLat);
      } else {
        // Reset: start new TX
        txRef.current = lngLat;
        rxRef.current = null;
        setTxCoords(lngLat);
        setRxCoords(null);
        mapRef.current?.setTxMarker(lngLat);
        mapRef.current?.setRxMarker(null);
      }
    } else if (activeTabRef.current === "coverage") {
      setCovTxCoords({ lat, lon: lng });
      mapRef.current?.setCovMarker(lngLat);
    }
  }, []);

  function handleTabChange(tab: string) {
    const t = tab as TabId;
    setActiveTab(t);
    if (t === "p2p") {
      mapRef.current?.removeCoverageOverlay();
      mapRef.current?.setCovMarker(null);
      setCovTxCoords(null);
      setCurrentCoverageResult(null);
    } else {
      mapRef.current?.setTxMarker(null);
      mapRef.current?.setRxMarker(null);
      txRef.current = null;
      rxRef.current = null;
      setTxCoords(null);
      setRxCoords(null);
    }
  }

  function handleP2PResult(result: P2PResponse) {
    const tx = txRef.current;
    const rx = rxRef.current;
    if (!tx || !rx) return;
    mapRef.current?.drawPath(tx, rx);
    mapRef.current?.drawHorizons(result.horizons || [], tx, rx, result.distance_m);
  }

  function handleCoverageResult(result: CoverageResponse) {
    mapRef.current?.addCoverageOverlay(result);
    setCurrentCoverageResult(result);
  }

  function handleOverlayOpacity(opacity: number) {
    mapRef.current?.setOverlayOpacity(opacity);
  }

  function handleSaveSite() {
    if (!covTxCoords || !currentCoverageResult) {
      alert("Generate coverage first");
      return;
    }
    setSiteNameInput(`Site ${sites.length + 1}`);
    setSiteNameDialogOpen(true);
  }

  function confirmSaveSite() {
    if (!siteNameInput.trim() || !covTxCoords || !currentCoverageResult) return;
    const site = createSite(siteNameInput.trim(), covTxCoords, currentCoverageResult, sites.length);
    mapRef.current?.addSiteLayer(site);
    setSites((prev) => [...prev, site]);
    setShowSites(true);
    setSiteNameDialogOpen(false);
  }

  function handleSiteToggle(id: number, visible: boolean) {
    mapRef.current?.setSiteVisibility(id, visible);
    setSites((prev) => prev.map((s) => (s.id === id ? { ...s, visible } : s)));
  }

  function handleSiteOpacity(id: number, opacity: number) {
    mapRef.current?.setSiteOpacity(id, opacity);
    setSites((prev) => prev.map((s) => (s.id === id ? { ...s, opacity } : s)));
  }

  function handleSiteDelete(id: number) {
    mapRef.current?.removeSiteLayer(id);
    setSites((prev) => {
      const next = prev.filter((s) => s.id !== id);
      if (next.length === 0) setShowSites(false);
      return next;
    });
  }

  function handleClearAll() {
    setClearConfirmDialogOpen(true);
  }

  function confirmClearAll() {
    sites.forEach((s) => mapRef.current?.removeSiteLayer(s.id));
    setSites([]);
    setShowSites(false);
    setClearConfirmDialogOpen(false);
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[#0f0f0f] text-white">
      {/* Sidebar */}
      <div className="w-72 flex-shrink-0 flex flex-col overflow-hidden border-r border-white/10">
        <div className="p-4 border-b border-white/10">
          <h2 className="text-lg font-bold">nowires</h2>
          <p className="text-xs text-gray-400">radio planning system</p>
        </div>

        <Tabs
          value={activeTab}
          onValueChange={handleTabChange}
          className="flex flex-col flex-1 overflow-hidden"
        >
          <TabsList className="mx-3 mt-3 grid grid-cols-2">
            <TabsTrigger value="p2p">Point-to-Point</TabsTrigger>
            <TabsTrigger value="coverage">Coverage</TabsTrigger>
          </TabsList>

          <div className="flex-1 overflow-y-auto">
            <TabsContent value="p2p" className="p-3 mt-0">
              <h3 className="text-sm font-semibold mb-2">Link Analysis</h3>
              <P2PPanel
                txCoords={txCoords}
                rxCoords={rxCoords}
                onResult={handleP2PResult}
              />
            </TabsContent>

            <TabsContent value="coverage" className="p-3 mt-0">
              <h3 className="text-sm font-semibold mb-2">Coverage</h3>
              <CoveragePanel
                txCoords={covTxCoords}
                onResult={handleCoverageResult}
                onOverlayOpacity={handleOverlayOpacity}
              />
              {currentCoverageResult && (
                <Button variant="outline" size="sm" onClick={handleSaveSite} className="mt-3 w-full">
                  + Save to comparison
                </Button>
              )}
            </TabsContent>
          </div>
        </Tabs>
      </div>

      {/* Map */}
      <div className="flex-1 relative min-h-0">
        <div className="absolute inset-0">
          <MapView ref={mapRef} onMapClick={handleMapClick} />
        </div>
      </div>

      {showSites && sites.length > 0 && (
        <SitesPanel
          sites={sites}
          onToggle={handleSiteToggle}
          onOpacity={handleSiteOpacity}
          onDelete={handleSiteDelete}
          onClearAll={handleClearAll}
          onClose={() => setShowSites(false)}
        />
      )}

      {/* Site name dialog */}
      <Dialog open={siteNameDialogOpen} onOpenChange={setSiteNameDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Save Site</DialogTitle>
            <DialogDescription>Enter a name for this coverage site.</DialogDescription>
          </DialogHeader>
          <Input
            value={siteNameInput}
            onChange={(e) => setSiteNameInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") confirmSaveSite();
            }}
            placeholder="Site name"
            autoFocus
          />
          <DialogFooter>
            <Button variant="ghost" onClick={() => setSiteNameDialogOpen(false)}>
              Cancel
            </Button>
            <Button variant="default" onClick={confirmSaveSite}>
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Clear confirmation dialog */}
      <Dialog open={clearConfirmDialogOpen} onOpenChange={setClearConfirmDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Clear All Sites</DialogTitle>
            <DialogDescription>This will remove all saved sites from the map.</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setClearConfirmDialogOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={confirmClearAll}>
              Clear All
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
