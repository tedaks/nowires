# NoWires

A radio propagation analysis system for the Philippines, powered by NTIA's Irregular Terrain Model (ITM).

NoWires computes point-to-point path loss, terrain profiles with Fresnel zone analysis, and area coverage predictions. It combines a FastAPI backend with Numba-accelerated computation and an interactive MapLibre frontend.

## Features

- **Point-to-Point Analysis**: Click two points on the map for TX and RX. The app plots a terrain profile with line-of-sight, 1st Fresnel zone, and 60% Fresnel zone, and reports ITM basic transmission loss with link budget.
- **Area Coverage**: Place a transmitter and generate a color-coded coverage overlay showing signal strength over the area, with adjustable grid resolution up to 384×384.
- **Coverage Radius**: Per-bearing radius estimation showing maximum, minimum, and average coverage distance.
- **Multi-Site Comparison**: Save coverage results as named sites and overlay multiple transmitters with adjustable opacity.
- **Directional Antennas**: Support for omnidirectional and directional antenna patterns with configurable azimuth and beamwidth.

## Setup

### Prerequisites

- Python 3.12+
- Node.js 20+
- npm

### 1. Install Dependencies

```bash
pip install -r apps/api/requirements.txt
npm install
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure:

```env
# Elevation data directories (optional — will use API fallback if not set)
SRTM1_TILES_DIR=/path/to/srtm1/tiles
GLO30_TILES_DIR=/path/to/glo30/tiles

# Optional land cover data for additional analysis
LANDCOVER_DIR=/path/to/landcover/tiles
```

For frontend development, create `apps/web/.env.local`:

```env
BACKEND_URL=http://127.0.0.1:8000
DEV_ORIGINS=http://192.168.1.100:3000
```

### 3. Run the Backend

```bash
cd apps/api
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 4. Run the Frontend

```bash
npm run dev:web
```

Open http://localhost:3000 in your browser.

## Elevation Data

NoWires fetches terrain elevation from multiple sources in priority order:

1. **GLO30** (Copernicus 30m DEM) — highest priority
2. **SRTM1** (1-arcsecond / 30m) — GeoTIFF tiles
3. **python-srtm** — local `.hgt` files
4. **OpenTopography API** — fallback (rate-limited)

For best performance, download and configure local GLO30 or SRTM1 tiles. Tiles must be organized in the standard directory structure (e.g., `N14/E120.tif` for GLO30).

## Architecture

```
nowires/
├── apps/
│   ├── api/                     # FastAPI backend
│   │   └── app/
│   │       ├── main.py          # Server, CORS, rate limiting
│   │       ├── p2p.py           # Point-to-point analysis
│   │       ├── coverage.py      # Coverage grid computation
│   │       ├── coverage_radius.py  # Coverage radius estimation
│   │       ├── coverage_workers.py # Parallel ITM workers
│   │       ├── coverage_render.py  # PNG rendering
│   │       ├── itm_bridge.py   # ITM wrapper
│   │       ├── math_kernels.py # Numba JIT Fresnel kernels
│   │       ├── elevation_grid.py   # Elevation caching
│   │       ├── elevation_fetch.py  # GLO30/SRTM1/rasterio
│   │       ├── signal_levels.py # Signal-to-color mapping
│   │       ├── terrain.py       # Haversine, profile generation
│   │       └── antenna.py      # Antenna gain patterns
│   └── web/                     # Next.js 16 frontend
│       └── src/
│           ├── app/             # Routes and error boundary
│           ├── components/      # Map, P2P, Coverage panels
│           └── lib/             # API client, types, utils
├── data/                        # Runtime cache (gitignored)
├── .github/workflows/ci.yml     # CI pipeline
└── LICENSE.md
```

## Testing

```bash
# Frontend unit tests
npm --workspace apps/web run test

# Backend tests
cd apps/api && pytest -v tests/

# Full lint + typecheck + tests
npm run lint && npm --workspace apps/web run typecheck && cd apps/api && ruff check . && ruff format --check . && pytest -v tests/
```

## Performance

| Grid Size | Cold Start | Cached  |
|-----------|-----------|---------|
| 192×192   | ~2.3s     | <10ms   |
| 384×384   | ~8s       | <10ms   |

Key optimizations:
- Vectorized rasterio elevation reading (~160ms vs ~88s API fallback)
- Numba JIT for Fresnel analysis and color mapping
- ProcessPoolExecutor with shared elevation grid for ITM parallelism
- Capped profile lengths for distant pixels (max 75 points)
- LRU cache for rendered coverage PNGs

## Credits

NoWires uses the [pyitm](https://github.com/tedaks/pyitm) library for NTIA Irregular Terrain Model calculations.
