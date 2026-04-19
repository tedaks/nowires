"use client";

import { useState, useRef, useEffect } from "react";
import dynamic from "next/dynamic";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { postP2P } from "@/lib/api";
import { fnum, fint } from "@/lib/radio";
import type { P2PResponse, LatLng } from "@/lib/types";
import P2PResult from "./P2PResult";

const ProfileChart = dynamic(() => import("./ProfileChart"), { ssr: false });

interface Props {
  txCoords: LatLng | null;
  rxCoords: LatLng | null;
  onResult: (result: P2PResponse) => void;
}

export default function P2PPanel({ txCoords, rxCoords, onResult }: Props) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<P2PResponse | null>(null);
  const [showChart, setShowChart] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

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
  const [polarization, setPolarization] = useState("0");
  const [climate, setClimate] = useState("1");
  const [timePct, setTimePct] = useState("50");
  const [locPct, setLocPct] = useState("50");
  const [sitPct, setSitPct] = useState("50");
  const [kFactor, setKFactor] = useState("1.3333");
  const [txPower, setTxPower] = useState("43");
  const [txGain, setTxGain] = useState("8");
  const [rxGain, setRxGain] = useState("2");
  const [cableLoss, setCableLoss] = useState("2");
  const [rxSens, setRxSens] = useState("-100");

  async function handleAnalyze() {
    if (!txCoords || !rxCoords) {
      setError("Please select both TX and RX locations on the map.");
      return;
    }
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    try {
      const res = await postP2P({
        tx: { lat: txCoords.lat, lon: txCoords.lng, h_m: fnum(txH, 30) },
        rx: { lat: rxCoords.lat, lon: rxCoords.lng, h_m: fnum(rxH, 10) },
        freq_mhz: fnum(freq, 450),
        polarization: fint(polarization, 0),
        climate: fint(climate, 1),
        time_pct: fnum(timePct, 50),
        location_pct: fnum(locPct, 50),
        situation_pct: fnum(sitPct, 50),
        k_factor: fnum(kFactor, 4 / 3),
        tx_power_dbm: fnum(txPower, 43),
        tx_gain_dbi: fnum(txGain, 8),
        rx_gain_dbi: fnum(rxGain, 2),
        cable_loss_db: fnum(cableLoss, 2),
        rx_sensitivity_dbm: fnum(rxSens, -100),
      }, controller.signal);
      if (res.error) {
        setError("Error: " + res.error);
        return;
      }
      setResult(res);
      setShowChart(true);
      onResult(res);
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setError("Analysis failed: " + (err instanceof Error ? err.message : String(err)));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-3">
      {error && (
        <div className="text-xs text-red-400 bg-red-400/10 rounded px-2 py-1">{error}</div>
      )}
      <p className="help-text text-xs text-gray-400">
        Click on the map to place TX (green) then RX (red).
      </p>

      <div className="coord-row">
        <Label className="text-xs text-gray-400">TX Location</Label>
        <div className="text-xs font-mono">
          {txCoords
            ? `${txCoords.lat.toFixed(5)}, ${txCoords.lng.toFixed(5)}`
            : "Not selected"}
        </div>
      </div>
      <div className="coord-row">
        <Label className="text-xs text-gray-400">RX Location</Label>
        <div className="text-xs font-mono">
          {rxCoords
            ? `${rxCoords.lat.toFixed(5)}, ${rxCoords.lng.toFixed(5)}`
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
          <Label className="text-xs">Polarization</Label>
          <Input value={polarization} onChange={(e) => setPolarization(e.target.value)} className="h-7 text-xs" />
        </div>
        <div>
          <Label className="text-xs">Climate</Label>
          <Input value={climate} onChange={(e) => setClimate(e.target.value)} className="h-7 text-xs" />
        </div>
        <div>
          <Label className="text-xs">k-factor</Label>
          <Input value={kFactor} onChange={(e) => setKFactor(e.target.value)} className="h-7 text-xs" />
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

      <Button
        onClick={handleAnalyze}
        disabled={loading}
        className="w-full"
        size="sm"
      >
        {loading ? "Analyzing..." : "Analyze Path"}
      </Button>

      {result && <P2PResult result={result} />}

      {result && showChart && (
        <div className="mt-2">
          <div className="flex justify-between items-center mb-1">
            <span className="text-xs font-medium">Profile</span>
            <button
              className="text-xs text-gray-400 hover:text-white"
              onClick={() => setShowChart(false)}
            >
              ✕
            </button>
          </div>
          <ProfileChart result={result} />
        </div>
      )}
    </div>
  );
}
