export interface LatLng {
  lat: number;
  lng: number;
}

// POST /api/p2p
export interface P2PRequest {
  tx: { lat: number; lon: number; h_m: number };
  rx: { lat: number; lon: number; h_m: number };
  freq_mhz: number;
  polarization: number;
  climate: number;
  time_pct: number;
  location_pct: number;
  situation_pct: number;
  k_factor: number;
  tx_power_dbm: number;
  tx_gain_dbi: number;
  rx_gain_dbi: number;
  cable_loss_db: number;
  rx_sensitivity_dbm: number;
}

export interface ProfilePoint {
  d: number;
  terrain: number;
  terrain_bulge: number;
  los: number;
  fresnel_upper: number;
  fresnel_lower: number;
  fresnel_60: number;
  blocked: boolean;
  violates_f1: boolean;
  violates_f60: boolean;
}

export interface Horizon {
  d_m: number;
  role: "tx_horizon" | "rx_horizon";
}

export interface LinkBudget {
  eirp_dbm: number;
  fspl_db: number;
  excess_loss_db: number;
  prx_dbm: number;
  margin_db: number;
  rx_sensitivity_dbm: number;
}

export interface P2PFlags {
  los_blocked: boolean;
  fresnel_60_violated: boolean;
  fresnel_f1_violated: boolean;
}

export interface P2PResponse {
  distance_m: number;
  loss_db: number;
  mode: number;
  profile: ProfilePoint[];
  horizons: Horizon[];
  flags: P2PFlags;
  link_budget: LinkBudget;
  error?: string;
}

// POST /api/coverage and /api/coverage-radius
export interface CoverageRequest {
  tx: { lat: number; lon: number; h_m: number };
  rx_h_m: number;
  freq_mhz: number;
  radius_km: number | null;
  grid_size: number;
  profile_step_m?: number;
  terrain_spacing_m: number;
  polarization: number;
  climate: number;
  time_pct: number;
  location_pct: number;
  situation_pct: number;
  tx_power_dbm: number;
  tx_gain_dbi: number;
  rx_gain_dbi: number;
  cable_loss_db: number;
  rx_sensitivity_dbm: number;
  antenna_az_deg: number | null;
  antenna_beamwidth_deg: number;
}

export interface LegendEntry {
  threshold_dbm: number;
  label: string;
  rgba: [number, number, number, number];
}

export interface CoverageStats {
  prx_min_dbm: number;
  prx_max_dbm: number;
  loss_min_db: number;
  loss_max_db: number;
  pct_above_sensitivity: number;
  terrain_grid_n: number;
  terrain_spacing_m: number;
  terrain_elev_min_m: number;
  terrain_elev_max_m: number;
  terrain_elev_std_m: number;
  pixels_total: number;
  pixels_valid: number;
}

export interface CoverageResponse {
  png_base64: string;
  bounds: [[number, number], [number, number]];
  legend: LegendEntry[];
  stats: CoverageStats;
  rx_sensitivity_dbm: number;
  eirp_dbm: number;
  from_cache: boolean;
}

export interface CoverageRadiusResponse {
  avg_radius_km: number;
  min_radius_km: number;
  max_radius_km: number;
}
