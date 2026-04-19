import { fnum, fint } from "@/lib/radio";
import type { CoverageRequest } from "@/lib/types";

export interface CoverageFormState {
  txH: string;
  rxH: string;
  freq: string;
  gridSize: string;
  terrainSpacing: string;
  polarization: string;
  climate: string;
  timePct: string;
  locPct: string;
  sitPct: string;
  txPower: string;
  txGain: string;
  rxGain: string;
  cableLoss: string;
  rxSens: string;
  antPattern: "omni" | "dir";
  antAz: string;
  antBw: string;
  n0: string;
  epsilon: string;
  sigma: string;
  profileStep: string;
  elevSource: string;
}

export const DEFAULTS: CoverageFormState = {
  txH: "30",
  rxH: "10",
  freq: "450",
  gridSize: "192",
  terrainSpacing: "300",
  polarization: "0",
  climate: "1",
  timePct: "50",
  locPct: "50",
  sitPct: "50",
  txPower: "43",
  txGain: "8",
  rxGain: "2",
  cableLoss: "2",
  rxSens: "-100",
  antPattern: "omni",
  antAz: "0",
  antBw: "90",
  n0: "301",
  epsilon: "15",
  sigma: "0.005",
  profileStep: "250",
  elevSource: "glo30",
};

export function buildRequest(
  form: CoverageFormState,
  txCoords: { lat: number; lon: number },
  radius: number | null
): CoverageRequest {
  return {
    tx: {
      lat: txCoords.lat,
      lon: txCoords.lon,
      h_m: fnum(form.txH, 30),
    },
    rx_h_m: fnum(form.rxH, 10),
    freq_mhz: fnum(form.freq, 450),
    radius_km: radius,
    grid_size: fint(form.gridSize, 192),
    terrain_spacing_m: fnum(form.terrainSpacing, 300),
    polarization: fint(form.polarization, 0),
    climate: fint(form.climate, 1),
    time_pct: fnum(form.timePct, 50),
    location_pct: fnum(form.locPct, 50),
    situation_pct: fnum(form.sitPct, 50),
    tx_power_dbm: fnum(form.txPower, 43),
    tx_gain_dbi: fnum(form.txGain, 8),
    rx_gain_dbi: fnum(form.rxGain, 2),
    cable_loss_db: fnum(form.cableLoss, 2),
    rx_sensitivity_dbm: fnum(form.rxSens, -100),
    antenna_az_deg: form.antPattern === "dir" ? fnum(form.antAz, 0) : null,
    antenna_beamwidth_deg: form.antPattern === "dir" ? fnum(form.antBw, 90) : 360,
    N0: fnum(form.n0, 301),
    epsilon: fnum(form.epsilon, 15),
    sigma: fnum(form.sigma, 0.005),
    profile_step_m: fnum(form.profileStep, 250),
    elevation_source: form.elevSource || "glo30",
  };
}

export type StringFieldKey = Exclude<keyof CoverageFormState, "antPattern">;

export const FIELDS: { key: StringFieldKey; label: string }[] = [
  { key: "txH", label: "TX height (m)" },
  { key: "rxH", label: "RX height (m)" },
  { key: "freq", label: "Freq (MHz)" },
  { key: "polarization", label: "Polarization" },
  { key: "climate", label: "Climate" },
  { key: "timePct", label: "Time %" },
  { key: "locPct", label: "Location %" },
  { key: "sitPct", label: "Situation %" },
  { key: "txPower", label: "TX Power (dBm)" },
  { key: "txGain", label: "TX Gain (dBi)" },
  { key: "rxGain", label: "RX Gain (dBi)" },
  { key: "cableLoss", label: "Cable loss (dB)" },
  { key: "rxSens", label: "RX sensitivity (dBm)" },
];

export const CLIMATE_OPTIONS = [
  { label: "Equatorial", value: "0" },
  { label: "Continental Subtropical", value: "1" },
  { label: "Maritime Subtropical", value: "2" },
  { label: "Desert", value: "3" },
  { label: "Continental Temperate", value: "4" },
  { label: "Maritime Temperate (Land)", value: "5" },
  { label: "Maritime Temperate (Sea)", value: "6" },
];
