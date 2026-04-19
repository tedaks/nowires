import type { CoverageResponse } from "./types";

export const SITE_COLORS = [
  "#ff4444",
  "#44ff44",
  "#4444ff",
  "#ffff44",
  "#ff44ff",
  "#44ffff",
];

export interface TxCoords {
  lat: number;
  lon: number;
}

export interface CoverageSite {
  id: string;
  name: string;
  tx: TxCoords;
  coverage_data: CoverageResponse;
  color: string;
  visible: boolean;
  opacity: number;
}

export function createSite(
  name: string,
  tx: TxCoords,
  coverage_data: CoverageResponse,
  index: number
): CoverageSite {
  return {
    id: crypto.randomUUID(),
    name,
    tx,
    coverage_data,
    color: SITE_COLORS[index % SITE_COLORS.length],
    visible: true,
    opacity: 0.6,
  };
}
