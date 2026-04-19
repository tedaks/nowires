"use client";

import { Slider } from "@/components/ui/slider";
import type { CoverageResponse } from "@/lib/types";
import Legend from "./Legend";

interface Props {
  result: CoverageResponse;
  opacity: number;
  onOpacityChange: (val: number | readonly number[]) => void;
}

export default function CoverageResults({ result, opacity, onOpacityChange }: Props) {
  return (
    <div className="space-y-2">
      <div className="border-t border-white/10 pt-2">
        <div className="text-xs font-medium mb-1">Coverage opacity</div>
        <Slider
          min={0}
          max={1}
          step={0.05}
          value={[opacity]}
          onValueChange={onOpacityChange}
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
  );
}