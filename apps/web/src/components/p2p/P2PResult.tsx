"use client";

import type { P2PResponse } from "@/lib/types";
import { MODE_LABELS } from "@/lib/radio";

interface Props {
  result: P2PResponse;
}

export default function P2PResult({ result }: Props) {
  const lb = result.link_budget || {};
  const modeName = MODE_LABELS[result.mode] ?? "Unknown";
  const margin = lb.margin_db;
  const prxClass =
    margin >= 10 ? "text-green-400" : margin >= 0 ? "text-yellow-400" : "text-red-400";

  return (
    <div className="space-y-2 text-sm">
      <div className="grid grid-cols-2 gap-2">
        <div>
          <div className="text-xs text-gray-400">Distance</div>
          <div className="font-mono">{(result.distance_m / 1000).toFixed(2)} km</div>
        </div>
        <div>
          <div className="text-xs text-gray-400">ITM Loss</div>
          <div className="font-mono text-red-300">{result.loss_db} dB</div>
        </div>
        <div>
          <div className="text-xs text-gray-400">Prx</div>
          <div className={`font-mono ${prxClass}`}>{lb.prx_dbm} dBm</div>
        </div>
        <div>
          <div className="text-xs text-gray-400">Margin</div>
          <div className={`font-mono ${prxClass}`}>{margin} dB</div>
        </div>
      </div>
      <div>
        <div className="text-xs text-gray-400">Mode</div>
        <div className="font-mono text-cyan-300">{modeName}</div>
      </div>
      <div className="border-t border-white/10 pt-2 space-y-1 text-xs">
        <div className="flex justify-between">
          <span className="text-gray-400">EIRP</span>
          <span>{lb.eirp_dbm} dBm</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">FSPL</span>
          <span>{lb.fspl_db} dB</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">Excess loss</span>
          <span>{lb.excess_loss_db} dB</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">RX sensitivity</span>
          <span>{lb.rx_sensitivity_dbm} dBm</span>
        </div>
      </div>
    </div>
  );
}
