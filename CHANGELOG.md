# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
- Point-to-point radio link analysis with ITM path loss calculation
- Terrain profile generation with Fresnel zone analysis (1st and 60% zones)
- Area coverage map computation with color-coded signal strength
- Coverage radius estimation per bearing
- Multi-site coverage comparison with overlay support
- Directional antenna pattern support (azimuth, beamwidth, front-back ratio)
- Multiple elevation source support: GLO30, SRTM1, HGT files, OpenTopography API
- NaN-aware elevation handling with linear interpolation
- LRU cache for rendered coverage PNGs
- Rate limiting middleware (30 requests/minute)
- vitest unit tests for frontend utilities
- Playwright E2E test infrastructure
- Full CI pipeline (ESLint, TypeScript, vitest, Next.js build, ruff, pytest, Playwright)

### Changed
- Frontend charting library changed from Plotly to Recharts
- Elevation data now uses NaN instead of 0.0 to represent missing values
- Frontend environment variables moved to `apps/web/.env.local`

### Fixed
- Corrected ITM time/location/situation parameter scaling
- Fixed elevation source priority chain (GLO30 → SRTM1 → HGT → API)
- Fixed climate enum indexing (API uses 0-indexed, ITM uses 1-indexed)
