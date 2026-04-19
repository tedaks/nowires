import { describe, expect, test } from "vitest";
import { SITE_COLORS, createSite } from "../site";
import type { CoverageResponse } from "../types";

const mockCoverage: CoverageResponse = {
  png_base64: "test",
  bounds: [[14.0, 121.0], [15.0, 122.0]],
  legend: [],
  stats: {
    prx_min_dbm: -120,
    prx_max_dbm: -40,
    loss_min_db: 80,
    loss_max_db: 150,
    pct_above_sensitivity: 75.0,
    terrain_grid_n: 192,
    terrain_spacing_m: 300,
    terrain_elev_min_m: 0,
    terrain_elev_max_m: 500,
    terrain_elev_std_m: 50,
    pixels_total: 36864,
    pixels_valid: 30000,
    pixels_attempted: 30000,
    pixels_failed: 0,
  },
  rx_sensitivity_dbm: -100,
  eirp_dbm: 49,
  from_cache: false,
};

describe("SITE_COLORS", () => {
  test("has at least 3 colors", () => {
    expect(SITE_COLORS.length).toBeGreaterThanOrEqual(3);
  });

  test("colors are hex strings", () => {
    for (const c of SITE_COLORS) {
      expect(c).toMatch(/^#[0-9a-f]{6}$/i);
    }
  });
});

describe("createSite", () => {
  test("creates site with correct properties", () => {
    const site = createSite("Test Site", { lat: 14.5, lon: 121.0 }, mockCoverage, 0);
    expect(site.name).toBe("Test Site");
    expect(site.tx.lat).toBe(14.5);
    expect(site.tx.lon).toBe(121.0);
    expect(site.coverage_data).toBe(mockCoverage);
    expect(site.visible).toBe(true);
    expect(site.opacity).toBe(0.6);
  });

  test("assigns colors cyclically", () => {
    const site0 = createSite("A", { lat: 0, lon: 0 }, mockCoverage, 0);
    const site1 = createSite("B", { lat: 0, lon: 0 }, mockCoverage, 1);
    const siteN = createSite("N", { lat: 0, lon: 0 }, mockCoverage, SITE_COLORS.length);
    expect(site0.color).toBe(SITE_COLORS[0]);
    expect(site1.color).toBe(SITE_COLORS[1]);
    expect(siteN.color).toBe(SITE_COLORS[0]);
  });

  test("generates unique IDs", () => {
    const site1 = createSite("A", { lat: 0, lon: 0 }, mockCoverage, 0);
    const site2 = createSite("B", { lat: 0, lon: 0 }, mockCoverage, 0);
    expect(site1.id).not.toBe(site2.id);
  });
});