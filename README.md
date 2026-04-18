# NoWires

A radio propagation analysis system for the Philippines, powered by NTIA's Irregular Terrain Model (ITM).

NoWires computes point-to-point path loss, terrain profiles with Fresnel zone analysis, and area coverage predictions using real SRTM1 elevation data. It combines a FastAPI backend with Numba-accelerated computation and an interactive MapLibre/Plotly frontend.

## Features

- **Point-to-Point Analysis**: Click two points on the map for TX and RX. The app plots a terrain profile with line-of-sight, 1st Fresnel zone, and 60% Fresnel zone, and reports ITM basic transmission loss with link budget.
- **Area Coverage**: Place a transmitter and generate a color-coded coverage overlay showing signal attenuation over the area, with adjustable grid resolution up to 384×384.
- **Coverage Radius**: Binary-search per-bearing radius estimation showing maximum, minimum, and average coverage distance.
- **Multi-Site Comparison**: Save coverage results as named sites and overlay multiple transmitters with adjustable opacity.
- **Directional Antennas**: Support for omnidirectional and directional antenna patterns with configurable azimuth and beamwidth.

## Setup

### 1. Install Python Dependencies

```bash
pip install -r backend/requirements.txt
```

### 2. Configure Elevation Data

NoWires uses SRTM1 GeoTIFF tiles for terrain data. Set `SRTM1_TILES_DIR` in `.env` to point to your tile cache:

```env
# SRTM1_TILES_DIR=/path/to/tiles   # or leave empty for ~/.cache/elevation/SRTM1/cache
```

Tiles must be organized as `N##/N##E###.tif` (the standard elevation download format).

### 3. Run the Server

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000 in your browser.

## Architecture

```
nowires/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI server with Numba warmup
│   │   ├── p2p.py               # Point-to-point analysis
│   │   ├── coverage.py          # Coverage grid + radius computation
│   │   ├── itm_bridge.py        # Python wrapper for itm package
│   │   ├── elevation_grid.py    # Vectorized SRTM1 GeoTIFF reader + bilinear sampling
│   │   ├── math_kernels.py      # Numba JIT kernels (Fresnel, color mapping)
│   │   ├── config.py            # Paths, defaults, .env loader
│   │   └── terrain.py           # Elevation profile extraction
│   └── requirements.txt
├── frontend/
│   ├── index.html               # Single-page app
│   ├── app.js                   # MapLibre + Plotly logic
│   └── styles.css
├── data/                        # Runtime cache (gitignored)
└── docs/
    └── superpowers/             # Design specs and implementation plans
```

## Performance

| Grid Size | Cold Start | Cached |
|-----------|-----------|--------|
| 192×192   | ~2.3s    | <10ms |
| 384×384   | ~8s      | <10ms |

Key optimizations:
- Vectorized rasterio elevation reading (~160ms vs ~88s API fallback)
- Numba JIT for Fresnel analysis and color mapping
- ProcessPoolExecutor with shared elevation grid for ITM parallelism
- Capped profile lengths for distant pixels (max 75 points)
