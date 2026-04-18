# ITM Philippines Demo (pyitm)

Radio propagation analysis using NTIA's Irregular Terrain Model (ITM) for the Philippines, powered by the pure-Python `itm` package.

## Setup

### 1. Install Python Dependencies

```bash
pip install -e /home/bortre/02-lab/sources/pyitm/
pip install -r backend/requirements.txt
```

The `itm` package is a pure-Python port of the NTIA ITM — no C++ compilation required.

### 2. Fetch SRTM Terrain Data (optional, for real terrain)

```bash
python scripts/fetch_srtm.py
```

Downloads SRTM1 tiles covering the Philippines (lat 4-21°N, lon 116-127°E) to `data/srtm1/`.

### 3. Run the Server

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000 in your browser.

## Features

- **Point-to-Point Analysis**: Click two points on the map for TX and RX. The app plots a terrain profile with line-of-sight and 1st Fresnel zone, and reports ITM basic transmission loss.
- **Area Coverage**: Place a transmitter and generate a color-coded coverage overlay showing signal attenuation over the area.

## Architecture

```
pyitm/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI server
│   │   ├── itm_bridge.py        # Python wrapper for itm package
│   │   ├── terrain.py           # SRTM elevation helpers
│   │   ├── p2p.py               # P2P analysis endpoint
│   │   ├── coverage.py          # Coverage grid computation
│   │   ├── elevation_grid.py    # Dense elevation grid with caching
│   │   └── config.py            # Paths and defaults
│   └── requirements.txt
├── frontend/
│   ├── index.html               # Single-page app
│   ├── app.js                  # MapLibre + Plotly logic
│   └── styles.css
└── data/srtm1/                  # SRTM1 tiles (gitignored)
```

## Differences from the C++ version

This project uses the pure-Python `itm` package instead of the vendored C++ NTIA ITM source. Key differences:

- **No C++ compilation step** — no `build_itm.sh`, no `libitm.so`, no `vendor/` directory
- **Climate codes** — the `itm` package uses 1-indexed climate enums (1–7) vs. the C++ 0-indexed (0–6). The bridge handles the mapping.
- **Propagation modes** — the `itm` package reports 3 modes (LOS, Diffraction, Troposcatter) vs. the C++ 6 modes. The bridge maps them to the closest equivalent.
