"use client";

import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { postCoverage, postCoverageRadius } from "@/lib/api";
import type { CoverageResponse } from "@/lib/types";
import FormField from "./FormField";
import SelectField from "./SelectField";
import CoverageResults from "./CoverageResults";
import { DEFAULTS, CLIMATE_OPTIONS, buildRequest, type CoverageFormState } from "./coverageForm";

const GRID_SIZE_OPTIONS = [
  { label: "64 (Fast)", value: "64" },
  { label: "128 (Balanced)", value: "128" },
  { label: "192 (Quality)", value: "192" },
  { label: "256 (High)", value: "256" },
  { label: "384 (Fine)", value: "384" },
  { label: "512 (Max)", value: "512" },
];

const TERRAIN_SPACING_OPTIONS = [
  { label: "100 m (Fine)", value: "100" },
  { label: "200 m (Balanced)", value: "200" },
  { label: "300 m (Standard)", value: "300" },
  { label: "400 m (Coarse)", value: "400" },
  { label: "500 m (Sparse)", value: "500" },
];

const POLARIZATION_OPTIONS = [
  { label: "Vertical", value: "0" },
  { label: "Horizontal", value: "1" },
];

const ELEV_SOURCE_OPTIONS = [
  { label: "GLO30 (Copernicus)", value: "glo30" },
  { label: "SRTM1", value: "srtm1" },
];

interface Props {
  txCoords: { lat: number; lon: number } | null;
  onResult: (result: CoverageResponse) => void;
  onOverlayOpacity: (opacity: number) => void;
}

export default function CoveragePanel({ txCoords, onResult, onOverlayOpacity }: Props) {
  const [loading, setLoading] = useState(false);
  const [loadingRadius, setLoadingRadius] = useState(false);
  const [result, setResult] = useState<CoverageResponse | null>(null);
  const [computedRadius, setComputedRadius] = useState<number | null>(null);
  const [radiusInfo, setRadiusInfo] = useState<string | null>(null);
  const [opacity, setOpacity] = useState(0.75);
  const [genButtonText, setGenButtonText] = useState("Generate Coverage");
  const [error, setError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const loadingDotsRef = useRef(0);

  const [form, setForm] = useState<CoverageFormState>(DEFAULTS);
  const setField = (key: keyof CoverageFormState, val: string) =>
    setForm((prev) => ({ ...prev, [key]: val }));

  useEffect(() => {
    if (!loading) return;
    const id = setInterval(() => {
      loadingDotsRef.current = (loadingDotsRef.current + 1) % 4;
      setGenButtonText("Generating" + ".".repeat(loadingDotsRef.current));
    }, 500);
    return () => { clearInterval(id); setGenButtonText("Generate Coverage"); };
  }, [loading]);

  useEffect(() => {
    if (!error) return;
    const t = setTimeout(() => setError(null), 5000);
    return () => clearTimeout(t);
  }, [error]);

  const formRequest = () => buildRequest(form, txCoords!, computedRadius);

  async function handleComputeRadius() {
    if (!txCoords) { setError("Select TX location first"); return; }
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setLoadingRadius(true);
    try {
      const data = await postCoverageRadius({ ...formRequest(), profile_step_m: 250 }, ctrl.signal);
      if (!data.max_radius_km || data.max_radius_km <= 0) {
        setComputedRadius(null);
        setRadiusInfo(null);
        setError("No reachable range at current parameters — TX is fully shadowed or below sensitivity in all directions.");
        return;
      }
      setComputedRadius(data.max_radius_km);
      setRadiusInfo(`Max: ${data.max_radius_km} km | Avg: ${data.avg_radius_km} km | Min: ${data.min_radius_km} km`);
    } catch (e: unknown) {
      if (e instanceof DOMException && e.name === "AbortError") return;
      setError("Error computing radius: " + (e instanceof Error ? e.message : String(e)));
    } finally {
      setLoadingRadius(false);
    }
  }

  async function handleGenerate() {
    if (!txCoords) { setError("Please select a TX location on the map."); return; }
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setLoading(true);
    try {
      const res = await postCoverage(formRequest(), ctrl.signal);
      if (!res.png_base64) { setError("No coverage data returned."); return; }
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
    const o = Array.isArray(val) ? val[0] : val;
    setOpacity(o);
    onOverlayOpacity(o);
  }

  return (
    <div className="space-y-3">
      {error && (
        <div className="text-xs text-red-400 bg-red-400/10 rounded px-2 py-1">{error}</div>
      )}
      <p className="text-xs text-gray-400">Click on the map to place TX (green).</p>

      <div>
        <Label className="text-xs text-gray-400">TX Location</Label>
        <div className="text-xs font-mono">
          {txCoords ? `${txCoords.lat.toFixed(5)}, ${txCoords.lon.toFixed(5)}` : "Not selected"}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <FormField label="TX height (m)" value={form.txH} onChange={(v) => setField("txH", v)} />
        <FormField label="RX height (m)" value={form.rxH} onChange={(v) => setField("rxH", v)} />
      </div>

      <div className="grid grid-cols-2 gap-2">
        <FormField label="Freq (MHz)" value={form.freq} onChange={(v) => setField("freq", v)} />
        <FormField label="TX Power (dBm)" value={form.txPower} onChange={(v) => setField("txPower", v)} />
      </div>

      <div className="grid grid-cols-2 gap-2">
        <FormField label="TX Gain (dBi)" value={form.txGain} onChange={(v) => setField("txGain", v)} />
        <FormField label="RX Gain (dBi)" value={form.rxGain} onChange={(v) => setField("rxGain", v)} />
      </div>

      <FormField label="RX Sensitivity (dBm)" value={form.rxSens} onChange={(v) => setField("rxSens", v)} />

      <SelectField
        label="Antenna pattern"
        value={form.antPattern}
        onChange={(v) => setField("antPattern", v as "omni" | "dir")}
        options={[
          { label: "Omnidirectional", value: "omni" },
          { label: "Directional", value: "dir" },
        ]}
      />

      {form.antPattern === "dir" && (
        <div className="grid grid-cols-2 gap-2">
          <FormField label="Azimuth (°)" value={form.antAz} onChange={(v) => setField("antAz", v)} />
          <FormField label="Beamwidth (°)" value={form.antBw} onChange={(v) => setField("antBw", v)} />
        </div>
      )}

      <Button onClick={handleComputeRadius} disabled={loadingRadius} variant="outline" size="sm" className="w-full">
        {loadingRadius ? "Computing (1–2 min)..." : "Compute Radius"}
      </Button>

      {radiusInfo && (
        <div className="text-xs text-cyan-300 bg-cyan-400/10 rounded px-2 py-1">{radiusInfo}</div>
      )}
      {computedRadius !== null && (
        <div className="text-xs text-gray-300">
          Computed radius: <span className="font-mono text-cyan-300">{computedRadius} km</span>
        </div>
      )}

      <div className="grid grid-cols-2 gap-2">
        <SelectField
          label="Grid size"
          value={form.gridSize}
          onChange={(v) => setField("gridSize", v)}
          options={GRID_SIZE_OPTIONS}
        />
        <SelectField
          label="Terrain spacing"
          value={form.terrainSpacing}
          onChange={(v) => setField("terrainSpacing", v)}
          options={TERRAIN_SPACING_OPTIONS}
        />
      </div>

      <SelectField
        label="Polarization"
        value={form.polarization}
        onChange={(v) => setField("polarization", v)}
        options={POLARIZATION_OPTIONS}
      />

      <SelectField
        label="Climate"
        value={form.climate}
        onChange={(v) => setField("climate", v)}
        options={CLIMATE_OPTIONS}
      />

      <button
        type="button"
        onClick={() => setShowAdvanced(!showAdvanced)}
        className="text-xs text-gray-400 hover:text-gray-300 underline"
      >
        {showAdvanced ? "Hide" : "Show"} advanced options
      </button>

      {showAdvanced && (
        <div className="space-y-2 pl-2 border-l border-gray-700">
          <FormField label="Cable loss (dB)" value={form.cableLoss} onChange={(v) => setField("cableLoss", v)} />
          <div className="grid grid-cols-3 gap-2">
            <FormField label="Time %" value={form.timePct} onChange={(v) => setField("timePct", v)} />
            <FormField label="Location %" value={form.locPct} onChange={(v) => setField("locPct", v)} />
            <FormField label="Situation %" value={form.sitPct} onChange={(v) => setField("sitPct", v)} />
          </div>
          <div className="grid grid-cols-3 gap-2">
            <FormField label="N₀ (N-units)" value={form.n0} onChange={(v) => setField("n0", v)} />
            <FormField label="εᵣ (ground)" value={form.epsilon} onChange={(v) => setField("epsilon", v)} />
            <FormField label="σ (S/m)" value={form.sigma} onChange={(v) => setField("sigma", v)} />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <FormField label="Profile step (m)" value={form.profileStep} onChange={(v) => setField("profileStep", v)} />
            <SelectField
              label="Elevation source"
              value={form.elevSource}
              onChange={(v) => setField("elevSource", v)}
              options={ELEV_SOURCE_OPTIONS}
            />
          </div>
        </div>
      )}

      <Button onClick={handleGenerate} disabled={loading || computedRadius === null} size="sm" className="w-full">
        {genButtonText}
      </Button>

      {result && (
        <CoverageResults result={result} opacity={opacity} onOpacityChange={handleOpacityChange} />
      )}
    </div>
  );
}