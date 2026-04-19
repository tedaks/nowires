"use client";

import { Slider } from "@/components/ui/slider";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import type { CoverageSite } from "@/lib/site";

interface Props {
  sites: CoverageSite[];
  onToggle: (id: number, visible: boolean) => void;
  onOpacity: (id: number, opacity: number) => void;
  onDelete: (id: number) => void;
  onClearAll: () => void;
  onClose: () => void;
}

export default function SitesPanel({
  sites,
  onToggle,
  onOpacity,
  onDelete,
  onClearAll,
  onClose,
}: Props) {
  const visibleSites = sites.filter((s) => s.visible);
  const avgCoverage =
    visibleSites.length > 0
      ? (
          visibleSites.reduce(
            (acc, s) => acc + (s.coverage_data.stats?.pct_above_sensitivity ?? 0),
            0
          ) / visibleSites.length
        ).toFixed(1)
      : "0";

  return (
    <div className="fixed bottom-4 right-4 w-64 bg-[#1a1a1a] border border-white/10 rounded-lg p-3 shadow-xl z-10 text-sm">
      <div className="flex justify-between items-center mb-2">
        <span className="font-medium">Multi-Site Coverage</span>
        <Button variant="ghost" size="sm" onClick={onClose} className="h-5 w-5 p-0 text-gray-400 hover:text-white">
          ✕
        </Button>
      </div>

      <div className="space-y-2 max-h-48 overflow-y-auto">
        {sites.map((site) => (
          <div
            key={site.id}
            className="flex items-center gap-2 p-2 bg-white/5 rounded"
          >
            <Checkbox
              checked={site.visible}
              onCheckedChange={(checked) =>
                onToggle(site.id, checked === true)
              }
            />
            <div className="flex-1 min-w-0">
              <div
                className="text-xs font-bold truncate"
                style={{ color: site.color }}
              >
                {site.name}
              </div>
              <div className="text-[10px] text-gray-500">
                {site.tx.lat.toFixed(3)}°, {site.tx.lon.toFixed(3)}°
              </div>
            </div>
            <div className="flex flex-col gap-1 items-end">
              <Slider
                min={0}
                max={1}
                step={0.1}
                value={[site.opacity]}
                onValueChange={(val) => {
                  const o = Array.isArray(val) ? (val as number[])[0] : (val as number);
                  onOpacity(site.id, o);
                }}
                className="w-14"
              />
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onDelete(site.id)}
                className="h-4 w-4 p-0 text-[10px] text-gray-400 hover:text-red-400"
              >
                ✕
              </Button>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-2 pt-2 border-t border-white/10 text-xs text-gray-400 space-y-1">
        <div>
          <strong className="text-white">Active Sites:</strong> {visibleSites.length}
        </div>
        <div>
          <strong className="text-white">Avg Coverage:</strong> {avgCoverage}%
        </div>
        <div className="text-[10px] text-gray-500">Blended view shows all sites</div>
      </div>

      <Button
        onClick={onClearAll}
        variant="outline"
        size="sm"
        className="w-full mt-2 text-xs"
      >
        Clear All Sites
      </Button>
    </div>
  );
}
