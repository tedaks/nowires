export const MODE_LABELS: Record<number, string> = {
  0: "Line-of-Sight",
  1: "Single Horizon Diffraction",
  2: "Double Horizon Diffraction",
  3: "Troposcatter",
  4: "Diffraction LOS Backward",
  5: "Mixed Path",
};

export function fnum(value: string, dflt: number): number {
  const v = parseFloat(value);
  return Number.isFinite(v) ? v : dflt;
}

export function fint(value: string, dflt: number): number {
  const v = parseFloat(value);
  return Number.isFinite(v) ? Math.round(v) : dflt;
}
