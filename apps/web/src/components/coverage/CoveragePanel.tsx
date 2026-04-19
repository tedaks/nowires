"use client";

import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { postCoverage, postCoverageRadius } from "@/lib/api";
import { fnum, fint } from "@/lib/radio";
import type { CoverageResponse } from "@/lib/types";
import Legend from "./Legend";

interface Props {
  txCoords: { lat: number; lon: number } | null;
  onResult: (result: CoverageResponse) => void;
  onOverlayOpacity: (opacity: number) => void;
}

export default function CoveragePanel({
  txCoords,
  onResult,
  onOverlayOpacity,
}: Props) {
  const [loading, setLoading] = useState(false);
  const [loadingRadius, setLoadingRadius] = useState(false);
  const [result, setResult] = useState<CoverageResponse | null>(null);
  const [computedRadius, setComputedRadius] = useState<number | null>(null);
  const [opacity, setOpacity] = useState(0.75);
  const [genButtonText, setGenButtonText] = useState("Generate Coverage");
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!loading) return;
    let dots = 0;
    const interval = setInterval(() => {
      dots = (dots + 1) % 4;
      setGenButtonText("Generating" + ".".repeat(dots));
    }, 500);
    return () => {
      clearInterval(interval);
      setGenButtonText("Generate Coverage");
    };
  }, [loading]);

  useEffect(() => {
    if (error) {
      const t = setTimeout(() => setError(null), 5000);
      return () => clearTimeout(t);
    }
  }, [error]);

  // Form state
  const [txH, setTxH] = useState("30");
  const [rxH, setRxH] = useState("10");
  const [freq, setFreq] = useState("450");
  const [gridSize, setGridSize] = useState("192");
  const [terrainSpacing, setTerrainSpacing] = useState("300");
  const [polarization, setPolarization] = useState("0");
  const [climate, setClimate] = useState("1");
  const [timePct, setTimePct] = useState("50");
  const [locPct, setLocPct] = useState("50");
  const [sitPct, setSitPct] = useState("50");
  const [txPower, setTxPower] = useState("43");
  const [txGain, setTxGain] = useState("8");
  const [rxGain, setRxGain] = useState("2");
  const [cableLoss, setCableLoss] = useState("2");
  const [rxSens, setRxSens] = useState("-100");
  const [antPattern, setAntPattern] = useState<"omni" | "dir">("omni");
  const [antAz, setAntAz] = useState("0");
  const [antBw, setAntBw] = useState("90");

  function buildRequest(radius: number | null) {
    return {
      tx: {
        lat: txCoords!.lat,
        lon: txCoords!.lon,
        h_m: fnum(txH, 30),
      },
      rx_h_m: fnum(rxH, 10),
      freq_mhz: fnum(freq, 450),
      radius_km: radius,
      grid_size: fint(gridSize, 192),
      terrain_spacing_m: fnum(terrainSpacing, 300),
      polarization: fint(polarization, 0),
      climate: fint(climate, 1),
      time_pct: fnum(timePct, 50),
      location_pct: fnum(locPct, 50),
      situation_pct: fnum(sitPct, 50),
      tx_power_dbm: fnum(txPower, 43),
      tx_gain_dbi: fnum(txGain, 8),
      rx_gain_dbi: fnum(rxGain, 2),
      cable_loss_db: fnum(cableLoss, 2),
      rx_sensitivity_dbm: fnum(rxSens, -100),
      antenna_az_deg: antPattern === "dir" ? fnum(antAz, 0) : null,
      antenna_beamwidth_deg: antPattern === "dir" ? fnum(antBw, 90) : 360,
    };
  }

  async function handleComputeRadius() {
    if (!txCoords) {
      setError("Select TX location first");
      return;
    }
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoadingRadius(true);
    try {
      const data = await postCoverageRadius({
        ...buildRequest(100),
        profile_step_m: 250,
      }, controller.signal);
      setComputedRadius(data.avg_radius_km);
      setError(`Avg: ${data.avg_radius_km} km | Min: ${data.min_radius_km} km | Max: ${data.max_radius_km} km`);
    } catch (e: unknown) {
      if (e instanceof DOMException && e.name === "AbortError") return;
      setError("Error computing radius: " + (e instanceof Error ? e.message : String(e)));
    } finally {
      setLoadingRadius(false);
    }
  }

  async function handleGenerate() {
    if (!txCoords) {
      setError("Please select a TX location on the map.");
      return;
    }
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    try {
      const res = await postCoverage(buildRequest(computedRadius), controller.signal);
      if (!res.png_base64) {
        setError("No coverage data returned.");
        return;
      }
      setResult(res);
      onResult(res);
    } catch (e: unknown) {
      if (e instanceof DOMException && e.name === "AbortError") return;
      setError("Coverage generation failed: " + (e instanceof Error ? e.message : String(e)));
    } finally {
      setLoading(false);
    }
  }

  function handleOpacityChange(val: number | readonly number[]) {
    const o = Array.isArray(val) ? (val as number[])[0] : (val as number);
    setOpacity(o);
    onOverlayOpacity(o);
  }

  return (
    <div className="space-y-3">
      {error && (
        <div className="text-xs text-red-400 bg-red-400/10 rounded px-2 py-1">{error}</div>
      )}
      <p className="text-xs text-gray-400">
        Click on the map to place TX (green).
      </p>

      <div>
        <Label className="text-xs text-gray-400">TX Location</Label>
        <div className="text-xs font-mono">
          {txCoords
            ? `${txCoords.lat.toFixed(5)}, ${txCoords.lon.toFixed(5)}`
            : "Not selected"}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div>
          <Label className="text-xs">TX height (m)</Label>
          <Input value={txH} onChange={(e) => setTxH(e.target.value)} className="h-7 text-xs" />
        </div>
        <div>
          <Label className="text-xs">RX height (m)</Label>
          <Input value={rxH} onChange={(e) => setRxH(e.target.value)} className="h-7 text-xs" />
        </div>
        <div>
          <Label className="text-xs">Freq (MHz)</Label>
          <Input value={freq} onChange={(e) => setFreq(e.target.value)} className="h-7 text-xs" />
        </div>
        <div>
          <Label className="text-xs">Grid size</Label>
          <Input value={gridSize} onChange={(e) => setGridSize(e.target.value)} className="h-7 text-xs" />
        </div>
        <div>
          <Label className="text-xs">Terrain spacing (m)</Label>
          <Input value={terrainSpacing} onChange={(e) => setTerrainSpacing(e.target.value)} className="h-7 text-xs" />
        </div>
        <div>
          <Label className="text-xs">Polarization</Label>
          <Input value={polarization} onChange={(e) => setPolarization(e.target.value)} className="h-7 text-xs" />
        </div>
        <div>
          <Label className="text-xs">Climate</Label>
          <Input value={climate} onChange={(e) => setClimate(e.target.value)} className="h-7 text-xs" />
        </div>
        <div>
          <Label className="text-xs">Time %</Label>
          <Input value={timePct} onChange={(e) => setTimePct(e.target.value)} className="h-7 text-xs" />
        </div>
        <div>
          <Label className="text-xs">Location %</Label>
          <Input value={locPct} onChange={(e) => setLocPct(e.target.value)} className="h-7 text-xs" />
        </div>
        <div>
          <Label className="text-xs">Situation %</Label>
          <Input value={sitPct} onChange={(e) => setSitPct(e.target.value)} className="h-7 text-xs" />
        </div>
        <div>
          <Label className="text-xs">TX Power (dBm)</Label>
          <Input value={txPower} onChange={(e) => setTxPower(e.target.value)} className="h-7 text-xs" />
        </div>
        <div>
          <Label className="text-xs">TX Gain (dBi)</Label>
          <Input value={txGain} onChange={(e) => setTxGain(e.target.value)} className="h-7 text-xs" />
        </div>
        <div>
          <Label className="text-xs">RX Gain (dBi)</Label>
          <Input value={rxGain} onChange={(e) => setRxGain(e.target.value)} className="h-7 text-xs" />
        </div>
        <div>
          <Label className="text-xs">Cable loss (dB)</Label>
          <Input value={cableLoss} onChange={(e) => setCableLoss(e.target.value)} className="h-7 text-xs" />
        </div>
        <div>
          <Label className="text-xs">RX sensitivity (dBm)</Label>
          <Input value={rxSens} onChange={(e) => setRxSens(e.target.value)} className="h-7 text-xs" />
        </div>
      </div>

      <div>
        <Label className="text-xs">Antenna pattern</Label>
        <Select value={antPattern} onValueChange={(v) => setAntPattern(v as "omni" | "dir")}>
          <SelectTrigger className="h-7 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="omni">Omnidirectional</SelectItem>
            <SelectItem value="dir">Directional</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {antPattern === "dir" && (
        <div className="grid grid-cols-2 gap-2">
          <div>
            <Label className="text-xs">Azimuth (°)</Label>
            <Input value={antAz} onChange={(e) => setAntAz(e.target.value)} className="h-7 text-xs" />
          </div>
          <div>
            <Label className="text-xs">Beamwidth (°)</Label>
            <Input value={antBw} onChange={(e) => setAntBw(e.target.value)} className="h-7 text-xs" />
          </div>
        </div>
      )}

      <Button
        onClick={handleComputeRadius}
        disabled={loadingRadius}
        variant="outline"
        size="sm"
        className="w-full"
      >
        {loadingRadius ? "Computing (1–2 min)..." : "Compute Radius"}
      </Button>

      {computedRadius !== null && (
        <div className="text-xs text-gray-300">
          Computed radius: <span className="font-mono text-cyan-300">{computedRadius} km</span>
        </div>
      )}

      <Button
        onClick={handleGenerate}
        disabled={loading || computedRadius === null}
        size="sm"
        className="w-full"
      >
        {genButtonText}
      </Button>

      {result && (
        <div className="space-y-2">
          <div className="border-t border-white/10 pt-2">
            <div className="text-xs font-medium mb-1">Coverage opacity</div>
            <Slider
              min={0}
              max={1}
              step={0.05}
              value={[opacity]}
              onValueChange={handleOpacityChange}
            />
          </div>

          <div className="text-xs space-y-1">
            <div className="flex justify-between">
              <span className="text-gray-400">EIRP</span>
              <span>{result.eirp_dbm} dBm</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Prx range</span>
              <span>
                {result.stats?.prx_min_dbm?.toFixed(1)} to{" "}
                {result.stats?.prx_max_dbm?.toFixed(1)} dBm
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">ITM loss</span>
              <span>
                {result.stats?.loss_min_db?.toFixed(1)} to{" "}
                {result.stats?.loss_max_db?.toFixed(1)} dB
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Served area</span>
              <span>{result.stats?.pct_above_sensitivity?.toFixed(1)}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Terrain grid</span>
              <span>
                {result.stats?.terrain_grid_n}² @ {result.stats?.terrain_spacing_m} m
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Terrain relief</span>
              <span>
                {result.stats?.terrain_elev_min_m?.toFixed(0)} to{" "}
                {result.stats?.terrain_elev_max_m?.toFixed(0)} m (σ{" "}
                {result.stats?.terrain_elev_std_m} m)
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Cache</span>
              <span>{result.from_cache ? "hit" : "miss"}</span>
            </div>
          </div>

          <Legend legend={result.legend} rxSensitivity={result.rx_sensitivity_dbm} />
        </div>
      )}
    </div>
  );
}