"use client";

import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { postCoverage, postCoverageRadius } from "@/lib/api";
import type { CoverageResponse } from "@/lib/types";
import FormField from "./FormField";
import CoverageResults from "./CoverageResults";
import { DEFAULTS, FIELDS, buildRequest, type CoverageFormState } from "./coverageForm";

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
      setComputedRadius(data.avg_radius_km);
      setRadiusInfo(`Avg: ${data.avg_radius_km} km | Min: ${data.min_radius_km} km | Max: ${data.max_radius_km} km`);
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
        {FIELDS.map(({ key, label }) => (
          <FormField key={key} label={label} value={form[key]} onChange={(v) => setField(key, v)} />
        ))}
      </div>

      <div>
        <Label className="text-xs">Antenna pattern</Label>
        <Select value={form.antPattern} onValueChange={(v) => setField("antPattern", v as "omni" | "dir")}>
          <SelectTrigger className="h-7 text-xs"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="omni">Omnidirectional</SelectItem>
            <SelectItem value="dir">Directional</SelectItem>
          </SelectContent>
        </Select>
      </div>

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

      <Button onClick={handleGenerate} disabled={loading || computedRadius === null} size="sm" className="w-full">
        {genButtonText}
      </Button>

      {result && (
        <CoverageResults result={result} opacity={opacity} onOpacityChange={handleOpacityChange} />
      )}
    </div>
  );
}