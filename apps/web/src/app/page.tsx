"use client";

import { useRef, useState, useCallback, useEffect, memo } from "react";
import dynamic from "next/dynamic";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import P2PPanel from "@/components/p2p/P2PPanel";
import CoveragePanel from "@/components/coverage/CoveragePanel";
import SitesPanel from "@/components/coverage/SitesPanel";
import ProfileChart from "@/components/p2p/ProfileChart";
import { SiteNameDialog, ClearConfirmDialog } from "@/components/Dialogs";
import type { MapViewHandle } from "@/components/map/MapView";
import type { LatLng, P2PResponse, CoverageResponse } from "@/lib/types";
import type { CoverageSite } from "@/lib/site";
import { createSite } from "@/lib/site";

const MapView = dynamic(() => import("@/components/map/MapView"), { ssr: false });

type TabId = "p2p" | "coverage";

export default function Home() {
  const mapRef = useRef<MapViewHandle>(null);
  const [activeTab, setActiveTab] = useState<TabId>("p2p");

  const [txCoords, setTxCoords] = useState<LatLng | null>(null);
  const [rxCoords, setRxCoords] = useState<LatLng | null>(null);
  const txRef = useRef<LatLng | null>(null);
  const rxRef = useRef<LatLng | null>(null);

  const [covTxCoords, setCovTxCoords] = useState<{ lat: number; lon: number } | null>(null);
  const [currentCoverageResult, setCurrentCoverageResult] = useState<CoverageResponse | null>(null);
  const [sites, setSites] = useState<CoverageSite[]>([]);
  const [showSites, setShowSites] = useState(false);

  const [p2pResult, setP2pResult] = useState<P2PResponse | null>(null);
  const [showChart, setShowChart] = useState(false);

  const [siteNameDialogOpen, setSiteNameDialogOpen] = useState(false);
  const [clearConfirmDialogOpen, setClearConfirmDialogOpen] = useState(false);
  const [siteNameInput, setSiteNameInput] = useState("");
  const [pageError, setPageError] = useState<string | null>(null);

  useEffect(() => {
    if (!pageError) return;
    const t = setTimeout(() => setPageError(null), 5000);
    return () => clearTimeout(t);
  }, [pageError]);

  const activeTabRef = useRef<TabId>("p2p");
  useEffect(() => { activeTabRef.current = activeTab; }, [activeTab]);

  const handleMapClick = useCallback((lngLat: LatLng) => {
    const { lat, lng } = lngLat;
    if (activeTabRef.current === "p2p") {
      if (!txRef.current) {
        txRef.current = lngLat; setTxCoords(lngLat); mapRef.current?.setTxMarker(lngLat);
      } else if (!rxRef.current) {
        rxRef.current = lngLat; setRxCoords(lngLat); mapRef.current?.setRxMarker(lngLat);
      } else {
        txRef.current = lngLat; rxRef.current = null;
        setTxCoords(lngLat); setRxCoords(null);
        mapRef.current?.setTxMarker(lngLat); mapRef.current?.setRxMarker(null);
      }
    } else if (activeTabRef.current === "coverage") {
      setCovTxCoords({ lat, lon: lng }); mapRef.current?.setCovMarker(lngLat);
    }
  }, []);

  function handleTabChange(tab: string) {
    const t = tab as TabId;
    setActiveTab(t);
    if (t === "p2p") {
      mapRef.current?.removeCoverageOverlay(); mapRef.current?.setCovMarker(null);
      setCovTxCoords(null); setCurrentCoverageResult(null); setShowChart(false);
    } else {
      mapRef.current?.setTxMarker(null); mapRef.current?.setRxMarker(null);
      txRef.current = null; rxRef.current = null;
      setTxCoords(null); setRxCoords(null); setP2pResult(null); setShowChart(false);
    }
  }

  function handleP2PResult(result: P2PResponse) {
    const tx = txRef.current, rx = rxRef.current;
    if (!tx || !rx) return;
    setP2pResult(result);
    mapRef.current?.drawPath(tx, rx);
    mapRef.current?.drawHorizons(result.horizons || [], tx, rx, result.distance_m);
    setShowChart(true);
  }

  function handleCoverageResult(result: CoverageResponse) {
    mapRef.current?.addCoverageOverlay(result);
    setCurrentCoverageResult(result);
  }

  function handleOverlayOpacity(opacity: number) { mapRef.current?.setOverlayOpacity(opacity); }

  function handleSaveSite() {
    if (!covTxCoords || !currentCoverageResult) { setPageError("Generate coverage first"); return; }
    setSiteNameInput(`Site ${sites.length + 1}`); setSiteNameDialogOpen(true);
  }

  function confirmSaveSite() {
    if (!siteNameInput.trim() || !covTxCoords || !currentCoverageResult) return;
    const site = createSite(siteNameInput.trim(), covTxCoords, currentCoverageResult, sites.length);
    mapRef.current?.addSiteLayer(site);
    setSites((prev) => [...prev, site]); setShowSites(true); setSiteNameDialogOpen(false);
  }

  function handleSiteToggle(id: string, visible: boolean) {
    mapRef.current?.setSiteVisibility(id, visible);
    setSites((prev) => prev.map((s) => (s.id === id ? { ...s, visible } : s)));
  }

  function handleSiteOpacity(id: string, opacity: number) {
    mapRef.current?.setSiteOpacity(id, opacity);
    setSites((prev) => prev.map((s) => (s.id === id ? { ...s, opacity } : s)));
  }

  function handleSiteDelete(id: string) {
    mapRef.current?.removeSiteLayer(id);
    setSites((prev) => { const n = prev.filter((s) => s.id !== id); if (n.length === 0) setShowSites(false); return n; });
  }

  function confirmClearAll() {
    sites.forEach((s) => mapRef.current?.removeSiteLayer(s.id));
    setSites([]); setShowSites(false); setClearConfirmDialogOpen(false);
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background text-white">
      {pageError && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 text-xs text-red-400 bg-red-400/10 border border-red-400/20 rounded px-3 py-2">{pageError}</div>
      )}

      <Sidebar
        activeTab={activeTab}
        onTabChange={handleTabChange}
        txCoords={txCoords}
        rxCoords={rxCoords}
        onP2PResult={handleP2PResult}
        covTxCoords={covTxCoords}
        onCoverageResult={handleCoverageResult}
        onOverlayOpacity={handleOverlayOpacity}
        onSaveSite={handleSaveSite}
        currentCoverageResult={currentCoverageResult}
      />

      <div className="flex-1 relative min-h-0">
        <div className="absolute inset-0">
          <MapView ref={mapRef} onMapClick={handleMapClick} />
        </div>
        {showChart && p2pResult && (
          <div className="absolute bottom-4 left-4 right-4 z-10 bg-black/80 backdrop-blur-sm rounded-lg border border-white/10 p-3 max-h-[45vh]">
            <div className="flex justify-between items-center mb-1">
              <span className="text-xs font-medium">Profile</span>
               <Button variant="ghost" size="icon-xs" onClick={() => setShowChart(false)} aria-label="Close">✕</Button>
            </div>
            <ProfileChart result={p2pResult} />
          </div>
        )}
      </div>

      {showSites && sites.length > 0 && (
        <SitesPanel sites={sites} onToggle={handleSiteToggle} onOpacity={handleSiteOpacity} onDelete={handleSiteDelete} onClearAll={() => setClearConfirmDialogOpen(true)} onClose={() => setShowSites(false)} />
      )}

      <SiteNameDialog
        open={siteNameDialogOpen}
        onOpenChange={setSiteNameDialogOpen}
        siteNameInput={siteNameInput}
        onSiteNameInputChange={setSiteNameInput}
        onConfirm={confirmSaveSite}
      />

      <ClearConfirmDialog open={clearConfirmDialogOpen} onOpenChange={setClearConfirmDialogOpen} onConfirm={confirmClearAll} />
    </div>
  );
}

const Sidebar = memo(function Sidebar({ activeTab, onTabChange, txCoords, rxCoords, onP2PResult, covTxCoords, onCoverageResult, onOverlayOpacity, onSaveSite, currentCoverageResult }: SidebarProps) {
  return (
    <div className="w-72 flex-shrink-0 flex flex-col overflow-hidden border-r border-white/10">
      <div className="p-4 border-b border-white/10">
        <h2 className="text-lg font-bold">nowires</h2>
        <p className="text-xs text-gray-400">radio planning system</p>
      </div>
      <Tabs value={activeTab} onValueChange={onTabChange} className="flex flex-col flex-1 overflow-hidden">
        <TabsList className="mx-3 mt-3 grid grid-cols-2">
          <TabsTrigger value="p2p">Point-to-Point</TabsTrigger>
          <TabsTrigger value="coverage">Coverage</TabsTrigger>
        </TabsList>
        <div className="flex-1 overflow-y-auto">
          <TabsContent value="p2p" className="p-3 mt-0">
            <h3 className="text-sm font-semibold mb-2">Link Analysis</h3>
            <P2PPanel txCoords={txCoords} rxCoords={rxCoords} onResult={onP2PResult} />
          </TabsContent>
          <TabsContent value="coverage" className="p-3 mt-0">
            <h3 className="text-sm font-semibold mb-2">Coverage</h3>
            <CoveragePanel txCoords={covTxCoords} onResult={onCoverageResult} onOverlayOpacity={onOverlayOpacity} />
            {currentCoverageResult && <Button variant="outline" size="sm" onClick={onSaveSite} className="mt-3 w-full">+ Save to comparison</Button>}
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
});

type SidebarProps = {
  activeTab: TabId;
  onTabChange: (tab: string) => void;
  txCoords: LatLng | null;
  rxCoords: LatLng | null;
  onP2PResult: (r: P2PResponse) => void;
  covTxCoords: { lat: number; lon: number } | null;
  onCoverageResult: (r: CoverageResponse) => void;
  onOverlayOpacity: (o: number) => void;
  onSaveSite: () => void;
  currentCoverageResult: CoverageResponse | null;
};