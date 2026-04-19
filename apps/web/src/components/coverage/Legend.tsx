"use client";

import type { LegendEntry } from "@/lib/types";

interface Props {
  legend: LegendEntry[];
  rxSensitivity?: number;
}

export default function Legend({ legend, rxSensitivity }: Props) {
  const sorted = [...legend].sort((a, b) => b.threshold_dbm - a.threshold_dbm);

  return (
    <div className="space-y-1 text-xs">
      {sorted.map((entry, i) => {
        const [r, g, b, a] = entry.rgba;
        return (
          <div key={i} className="flex items-center gap-2">
            <span
              className="inline-block w-4 h-4 rounded-sm flex-shrink-0"
              style={{ background: `rgba(${r},${g},${b},${a / 255})` }}
            />
            <span className="text-gray-300">≥ {entry.threshold_dbm} dBm</span>
            <span className="text-gray-500 ml-auto">{entry.label}</span>
          </div>
        );
      })}
      {rxSensitivity !== undefined && (
        <div className="text-gray-500 pt-1 border-t border-white/10">
          RX sensitivity: {rxSensitivity} dBm
        </div>
      )}
    </div>
  );
}
