# pyitm Migration: Replace C++ ITM with Pure-Python ITM Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create an exact copy of `/home/bortre/03-final/itm` at `/home/bortre/03-final/pyitm`, replacing the vendored C++ ITM library (`vendor/itm/` + `backend/app/lib/libitm.so` + ctypes bridge) with the pure-Python `itm` package from `/home/bortre/02-lab/sources/pyitm/itm/`.

**Architecture:** The existing `itm` project uses a C++ shared library (`libitm.so`) called via a ctypes bridge (`itm_bridge.py`). The pyitm project will replace this with the pure-Python `itm` package, which provides the same propagation prediction via `predict_p2p()`. The key adaptation is in `itm_bridge.py`: instead of calling `_lib.ITM_P2P_TLS_Ex` via ctypes, it will call `itm.predict_p2p()` directly. The rest of the project (FastAPI backend, frontend, terrain, coverage, elevation_grid, scripts) is copied as-is.

**Tech Stack:** Python 3.10+, FastAPI, NumPy, pure-Python ITM (`itm` package), SRTM elevation data

---

## Key Differences Between C++ ITM and pyitm

### API Mapping

| C++ `ITM_P2P_TLS_Ex` (ctypes) | Python `itm.predict_p2p()` |
|---|---|
| `h_tx__meter` (float) | `h_tx__meter` (float) |
| `h_rx__meter` (float) | `h_rx__meter` (float) |
| `profile` (c_double array: `[np, step_m, elev0, elev1, ...]`) | `terrain` (TerrainProfile: `TerrainProfile.from_pfl(pfl)`) |
| `climate` (int, 0-indexed: 0=Equatorial) | `climate` (Climate enum, 1-indexed: 1=EQUATORIAL) |
| `N0` (float) | `N_0` (float) |
| `f__mhz` (float) | `f__mhz` (float) |
| `polarization` (int, 0=V, 1=H) | `pol` (Polarization enum, 0=HORIZONTAL, 1=VERTICAL) |
| `epsilon` (float) | `epsilon` (float) |
| `sigma` (float) | `sigma` (float) |
| `mdvar` (int) | `mdvar` (int) |
| `time_pct` (float, 0–100) | `time` (float, 0–100) |
| `location_pct` (float, 0–100) | `location` (float, 0–100) |
| `situation_pct` (float, 0–100) | `situation` (float, 0–100) |
| Returns: `(loss_db, warnings, IntermediateValues)` | Returns: `PropagationResult(A__db, warnings, intermediate)` |

### Critical Mapping Details

1. **Climate offset:** The C++ ITM uses 0-indexed climate codes (0=Equatorial, 1=Continental Subtropical, ..., 6=Maritime Temperate sea). The pyitm `Climate` enum uses 1-indexed (1=EQUATORIAL, 2=CONTINENTAL_SUBTROPICAL, ..., 7=MARITIME_TEMPERATE_SEA). So `climate_pyitm = climate_cpp + 1`.

2. **Polarization swap:** The C++ ITM uses 0=Vertical, 1=Horizontal. The pyitm `Polarization` enum uses 0=HORIZONTAL, 1=VERTICAL. So `pol_pyitm = 1 - polarization_cpp` (i.e., invert the value).

3. **Result field mapping:**
   - C++ `loss_db` → pyitm `PropagationResult.A__db`
   - C++ `inter.mode` → pyitm `PropagationResult.intermediate.mode` (BUT: pyitm PropMode has 3 values: LINE_OF_SIGHT=1, DIFFRACTION=2, TROPOSCATTER=3; C++ ITM returns 0=LOS, 1=Single Horizon, 2=Double Horizon, 3=Troposcatter, 4=Diffraction LOS Backward, 5=Mixed Path. These are NOT directly mappable — the `PROP_MODE_NAMES` dict in the original ITM bridge will need adjusted mode mapping)

4. **Intermediate values:** The pyitm IntermediateValues dataclass mirrors the C++ struct but as Python tuples instead of C arrays.

5. **Warnings:** Both use bitmask integers but pyitm uses `Warnings` IntFlag. The numeric values should be compatible.

6. **No `mdvar` parameter in current usage:** The original `itm_bridge.py` doesn't pass `mdvar` to the C++ function (it's not in the argtype list). The pyitm API requires `mdvar`, defaulting to 0 (SINGLE_MESSAGE) is the safe choice matching the original behavior.

7. **Terrain profile format:** Both use the same PFL format `[np, step_m, elev0, elev1, ...]`. The pyitm `TerrainProfile.from_pfl()` handles parsing this.

---

## File Structure

Files to create in `/home/bortre/03-final/pyitm/`:

```
pyitm/
├── .gitignore                       # Copy from itm, add itm.egg-info
├── README.md                        # Copy + update (remove C++ build steps)
├── backend/
│   ├── __init__.py                   # Copy (empty)
│   ├── requirements.txt             # Copy + add `itm` package dep
│   ├── app/
│   │   ├── __init__.py               # Copy (empty)
│   │   ├── main.py                   # Copy as-is
│   │   ├── itm_bridge.py             # REWRITE: call pyitm instead of ctypes
│   │   ├── terrain.py                # Copy as-is
│   │   ├── p2p.py                    # Copy as-is
│   │   ├── coverage.py               # Copy as-is
│   │   ├── elevation_grid.py         # Copy as-is
│   │   └── config.py                 # Copy as-is (remove LIB_DIR)
│   └── (no build_itm.sh)            # REMOVED: no C++ build needed
│   └── (no app/lib/ directory)      # REMOVED: no .so file needed
├── frontend/
│   ├── index.html                    # Copy as-is
│   ├── app.js                        # Copy as-is
│   └── styles.css                    # Copy as-is
├── data/
│   ├── elev_cache/                   # Create empty directory (gitignored)
│   └── srtm1/                        # Create empty directory (gitignored)
├── scripts/
│   └── fetch_srtm.py                 # Copy as-is
├── vendor/                           # REMOVED entirely (no C++ ITM source)
└── (no server.log)                   # Don't copy log files
```

Files NOT copied from original:
- `backend/build_itm.sh` — C++ build script, no longer needed
- `backend/app/lib/libitm.so` — compiled C++ library, replaced by Python
- `vendor/itm/` — entire C++ source tree, replaced by pyitm package
- `server.log` — runtime artifact
- `.venv/` — virtual environment

Files MODIFIED from original:
- `backend/app/itm_bridge.py` — Complete rewrite to call pyitm
- `backend/app/config.py` — Remove `LIB_DIR` reference
- `backend/requirements.txt` — Remove no-longer-needed deps, add `itm`
- `README.md` — Update to remove C++ build instructions, update architecture diagram
- `.gitignore` — Add `*.egg-info/`

---

### Task 1: Create project skeleton (directories + static copies)

**Files:**
- Create: `pyitm/` directory structure
- Copy: all files that don't need modification

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p /home/bortre/03-final/pyitm/backend/app
mkdir -p /home/bortre/03-final/pyitm/frontend
mkdir -p /home/bortre/03-final/pyitm/data/elev_cache
mkdir -p /home/bortre/03-final/pyitm/data/srtm1
mkdir -p /home/bortre/03-final/pyitm/scripts
```

- [ ] **Step 2: Copy static files (frontend, scripts, empty inits)**

```bash
cp /home/bortre/03-final/itm/frontend/index.html /home/bortre/03-final/pyitm/frontend/index.html
cp /home/bortre/03-final/itm/frontend/app.js /home/bortre/03-final/pyitm/frontend/app.js
cp /home/bortre/03-final/itm/frontend/styles.css /home/bortre/03-final/pyitm/frontend/styles.css
cp /home/bortre/03-final/itm/scripts/fetch_srtm.py /home/bortre/03-final/pyitm/scripts/fetch_srtm.py
cp /home/bortre/03-final/itm/backend/__init__.py /home/bortre/03-final/pyitm/backend/__init__.py
cp /home/bortre/03-final/itm/backend/app/__init__.py /home/bortre/03-final/pyitm/backend/app/__init__.py
```

- [ ] **Step 3: Copy backend files that need no changes**

```bash
cp /home/bortre/03-final/itm/backend/app/main.py /home/bortre/03-final/pyitm/backend/app/main.py
cp /home/bortre/03-final/itm/backend/app/terrain.py /home/bortre/03-final/pyitm/backend/app/terrain.py
cp /home/bortre/03-final/itm/backend/app/p2p.py /home/bortre/03-final/pyitm/backend/app/p2p.py
cp /home/bortre/03-final/itm/backend/app/coverage.py /home/bortre/03-final/pyitm/backend/app/coverage.py
cp /home/bortre/03-final/itm/backend/app/elevation_grid.py /home/bortre/03-final/pyitm/backend/app/elevation_grid.py
```

- [ ] **Step 4: Commit**

```bash
cd /home/bortre/03-final/pyitm
git add -A
git commit -m "feat: scaffold pyitm project with static file copies from itm"
```

---

### Task 2: Rewrite `itm_bridge.py` to call pyitm instead of ctypes

**Files:**
- Create: `pyitm/backend/app/itm_bridge.py`

This is the core adaptation. The new `itm_bridge.py` must:
1. Import `itm.predict_p2p`, `itm.models.*`
2. Expose the same `itm_p2p_loss()` function signature that `p2p.py` and `coverage.py` call
3. Map climate codes (0-indexed → 1-indexed `Climate` enum)
4. Map polarization (0=V→1=VERTICAL, 1=H→0=HORIZONTAL)
5. Convert the PFL list to `TerrainProfile.from_pfl()`
6. Return an `ITMResult` dataclass with the same fields the callers expect
7. Map `PropagationResult.intermediate.mode` (PropMode enum: 1=LOS, 2=DIFFRACTION, 3=TROPOSCATTER) back to the integer mode codes expected by `PROP_MODE_NAMES` in the original bridge (0=LOS, 1=Single Horizon Diffraction, 2=Double Horizon Diffraction, 3=Troposcatter, 4=Diffraction LOS Backward, 5=Mixed Path)

**Mode mapping analysis:** The pyitm `PropMode` has 3 values (LINE_OF_SIGHT=1, DIFFRACTION=2, TROPOSCATTER=3). The original C++ ITM bridge defined `PROP_MODE_NAMES` with 6 entries (0–5). The pyitm modes don't have the sub-categories. The mapping should be:
- pyitm `LINE_OF_SIGHT` (1) → mode 0 ("Line-of-Sight")
- pyitm `DIFFRACTION` (2) → mode 2 ("Double Horizon Diffraction") — most common diffraction
- pyitm `TROPOSCATTER` (3) → mode 3 ("Troposcatter")

This is a lossy mapping but covers the three main propagation modes and provides correct mode names for the frontend.

- [ ] **Step 1: Write the new `itm_bridge.py`**

```python
import math
from dataclasses import dataclass
from itm import predict_p2p, Climate, Polarization, TerrainProfile

PROP_MODE_NAMES = {
    0: "Line-of-Sight",
    1: "Single Horizon Diffraction",
    2: "Double Horizon Diffraction",
    3: "Troposcatter",
    4: "Diffraction LOS Backward",
    5: "Mixed Path",
}

_PYMODE_TO_CPPMODE = {
    1: 0,
    2: 2,
    3: 3,
}


@dataclass
class ITMResult:
    loss_db: float
    mode: int
    warnings: int
    d_hzn_tx_m: float = 0.0
    d_hzn_rx_m: float = 0.0
    theta_hzn_tx: float = 0.0
    theta_hzn_rx: float = 0.0
    h_e_tx_m: float = 0.0
    h_e_rx_m: float = 0.0
    N_s: float = 0.0
    delta_h_m: float = 0.0
    A_ref_db: float = 0.0
    A_fs_db: float = 0.0
    d_km: float = 0.0


def itm_p2p_loss(
    h_tx__meter: float,
    h_rx__meter: float,
    profile: list,
    climate: int = 1,
    N0: float = 301.0,
    f__mhz: float = 300.0,
    polarization: int = 0,
    epsilon: float = 15.0,
    sigma: float = 0.005,
    mdvar: int = 0,
    time_pct: float = 50.0,
    location_pct: float = 50.0,
    situation_pct: float = 50.0,
) -> ITMResult:
    terrain = TerrainProfile.from_pfl(profile)

    climate_enum = Climate(int(climate) + 1)

    pol_enum = Polarization(1 - int(polarization))

    result = predict_p2p(
        h_tx__meter=h_tx__meter,
        h_rx__meter=h_rx__meter,
        terrain=terrain,
        climate=climate_enum,
        N_0=N0,
        f__mhz=f__mhz,
        pol=pol_enum,
        epsilon=epsilon,
        sigma=sigma,
        mdvar=int(mdvar),
        time=time_pct,
        location=location_pct,
        situation=situation_pct,
        return_intermediate=True,
    )

    inter = result.intermediate

    mode = _PYMODE_TO_CPPMODE.get(int(inter.mode), int(inter.mode)) if inter else 0

    warnings_val = int(result.warnings)

    if inter is not None:
        return ITMResult(
            loss_db=result.A__db,
            mode=mode,
            warnings=warnings_val,
            d_hzn_tx_m=inter.d_hzn__meter[0],
            d_hzn_rx_m=inter.d_hzn__meter[1],
            theta_hzn_tx=inter.theta_hzn[0],
            theta_hzn_rx=inter.theta_hzn[1],
            h_e_tx_m=inter.h_e__meter[0],
            h_e_rx_m=inter.h_e__meter[1],
            N_s=inter.N_s,
            delta_h_m=inter.delta_h__meter,
            A_ref_db=inter.A_ref__db,
            A_fs_db=inter.A_fs__db,
            d_km=inter.d__km,
        )

    return ITMResult(
        loss_db=result.A__db,
        mode=mode,
        warnings=warnings_val,
    )
```

- [ ] **Step 2: Verify the file was written correctly**

Run: `python3 -c "import ast; ast.parse(open('/home/bortre/03-final/pyitm/backend/app/itm_bridge.py').read()); print('Syntax OK')"`

- [ ] **Step 3: Commit**

```bash
cd /home/bortre/03-final/pyitm
git add backend/app/itm_bridge.py
git commit -m "feat: rewrite itm_bridge.py to call pure-python itm package"
```

---

### Task 3: Update `config.py` (remove LIB_DIR)

**Files:**
- Modify: `pyitm/backend/app/config.py`

The original `config.py` has `LIB_DIR = BASE_DIR / "backend" / "app" / "lib"` which pointed to the directory containing `libitm.so`. This is no longer needed.

- [ ] **Step 1: Remove the `LIB_DIR` line from config.py**

In `pyitm/backend/app/config.py`, remove line 4:
```python
LIB_DIR = BASE_DIR / "backend" / "app" / "lib"
```

The file should become:

```python
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"

SRTM1_DIR = DATA_DIR / "srtm1"
SRTM1_DIR.mkdir(parents=True, exist_ok=True)

PH_BBOX = {
    "min_lat": 4.0,
    "max_lat": 21.0,
    "min_lon": 116.0,
    "max_lon": 127.0,
}

DEFAULT_PARAMS = {
    "polarization": 0,
    "climate": 1,
    "N0": 301.0,
    "epsilon": 15.0,
    "sigma": 0.005,
    "mdvar": 0,
    "time": 0.5,
    "location": 0.5,
    "situation": 0.5,
}

ITM_DEFAULTS = {
    "h_tx__meter": 30.0,
    "h_rx__meter": 10.0,
    "frequency__mhz": 300.0,
    "radius_km": 50.0,
    "n_radials": 72,
    "n_steps": 60,
}

CLIMATE_NAMES = {
    0: "Equatorial",
    1: "Continental Subtropical",
    2: "Maritime Subtropical",
    3: "Desert",
    4: "Continental Temperate",
    5: "Maritime Temperate (land)",
    6: "Maritime Temperate (sea)",
}
```

- [ ] **Step 2: Commit**

```bash
cd /home/bortre/03-final/pyitm
git add backend/app/config.py
git commit -m "refactor: remove LIB_DIR from config.py (no C++ shared library)"
```

---

### Task 4: Update `requirements.txt`

**Files:**
- Modify: `pyitm/backend/requirements.txt`

The original requirements.txt is:
```
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
python-srtm>=0.6.0
numpy>=1.24.0
pillow>=10.0.0
pydantic>=2.0.0
```

Add the `itm` package. Since it's a local package from `/home/bortre/02-lab/sources/pyitm/`, we'll reference it as a local editable install. The `itm` package already depends on `numpy>=1.21`, but it's fine to keep numpy in requirements.txt for explicitness.

- [ ] **Step 1: Write updated `requirements.txt`**

```
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
python-srtm>=0.6.0
numpy>=1.24.0
pillow>=10.0.0
pydantic>=2.0.0
itm
```

Note: `itm` will be installed from the local source at `/home/bortre/02-lab/sources/pyitm/` via `pip install -e /home/bortre/02-lab/sources/pyitm/`.

- [ ] **Step 2: Commit**

```bash
cd /home/bortre/03-final/pyitm
git add backend/requirements.txt
git commit -m "feat: add itm package dependency to requirements.txt"
```

---

### Task 5: Update `.gitignore`

**Files:**
- Create: `pyitm/.gitignore`

- [ ] **Step 1: Write `.gitignore`**

```gitignore
__pycache__/
*.pyc
*.so
*.egg-info/
.venv/
venv/
env/
data/srtm1/*.hgt
data/srtm1/*.zip
*.png
.DS_Store
server.log
```

Changes from original: added `*.egg-info/` and `server.log` to avoid copying runtime artifacts.

- [ ] **Step 2: Commit**

```bash
cd /home/bortre/03-final/pyitm
git add .gitignore
git commit -m "chore: add .gitignore for pyitm project"
```

---

### Task 6: Write `README.md` (updated for pyitm)

**Files:**
- Create: `pyitm/README.md`

The readme should mirror the original but remove all C++ build instructions and update the architecture diagram.

- [ ] **Step 1: Write `README.md`**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
cd /home/bortre/03-final/pyitm
git add README.md
git commit -m "docs: add README.md for pyitm project"
```

---

### Task 7: Install the itm package and verify the bridge works

**Files:**
- No file changes — verification only

- [ ] **Step 1: Install itm package from local source**

```bash
pip install -e /home/bortre/02-lab/sources/pyitm/
```

- [ ] **Step 2: Run pyitm tests to ensure the package works**

```bash
cd /home/bortre/02-lab/sources/pyitm && python3 -m pytest
```

Expected: All tests pass.

- [ ] **Step 3: Verify the bridge module can be imported and the API produces reasonable output**

```bash
cd /home/bortre/03-final/pyitm/backend && python3 -c "
from app.itm_bridge import itm_p2p_loss
result = itm_p2p_loss(
    h_tx__meter=30.0,
    h_rx__meter=10.0,
    profile=[3, 100.0, 0.0, 50.0, 100.0, 50.0, 0.0],
    climate=1,
    N0=301.0,
    f__mhz=300.0,
    polarization=0,
    epsilon=15.0,
    sigma=0.005,
    mdvar=0,
    time_pct=50.0,
    location_pct=50.0,
    situation_pct=50.0,
)
print(f'loss_db={result.loss_db:.2f}, mode={result.mode}, warnings={result.warnings}')
print(f'd_km={result.d_km:.2f}, A_ref_db={result.A_ref_db:.2f}')
print('Bridge verification PASSED')
"
```

Expected: A finite loss value, mode 0 or 2, and no import errors.

- [ ] **Step 4: Install remaining backend requirements**

```bash
pip install -r /home/bortre/03-final/pyitm/backend/requirements.txt
```

- [ ] **Step 5: Verify the full backend can start (import check only)**

```bash
cd /home/bortre/03-final/pyitm/backend && python3 -c "
from app.main import app
from app.p2p import analyze_p2p
from app.coverage import compute_coverage
print('All backend imports successful')
"
```

Expected: No import errors.

---

## Self-Review

**1. Spec coverage:**
- Copy entire `itm` project structure → Task 1
- Replace C++ ITM with pyitm → Task 2 (bridge rewrite)
- Remove `vendor/itm/` → Task 1 (simply not copied)
- Remove `build_itm.sh` → Task 1 (simply not copied)
- Remove `app/lib/libitm.so` → Task 1 (simply not copied)
- Update `itm_bridge.py` → Task 2
- Update `config.py` → Task 3
- Update `requirements.txt` → Task 4
- Update `.gitignore` → Task 5
- Update `README.md` → Task 6
- Verify everything works → Task 7

**2. Placeholder scan:** No TBD, TODO, "implement later", or vague steps found. All code is shown in full.

**3. Type consistency:**
- `itm_p2p_loss()` returns `ITMResult` with fields matching what `p2p.py` and `coverage.py` expect (`loss_db`, `mode`, `warnings`, `d_hzn_tx_m`, `d_hzn_rx_m`, etc.)
- `PROP_MODE_NAMES` dict is defined in the new `itm_bridge.py` — same as original
- The `p2p.py` and `coverage.py` files call `itm_p2p_loss()` and `PROP_MODE_NAMES` from `.itm_bridge` — these imports remain unchanged since the new bridge provides the same interface
- Climate mapping: 0-indexed (C++) → 1-indexed (pyitm enum), handled by `Climate(int(climate) + 1)`
- Polarization mapping: 0=V (C++) → 1=VERTICAL (pyitm), handled by `Polarization(1 - int(polarization))`
- One potential issue: `p2p.py` and `coverage.py` pass `climate` as int (0-indexed from the C++ API). The new bridge will add 1 internally. The frontend also sends 0-indexed climate codes. This is consistent.

**Gap found:** The `p2p.py` `build_pfl()` function returns `[float(n), step_m] + elevations` — this is the same PFL format that `TerrainProfile.from_pfl()` expects. Good.

**Gap found:** The `coverage.py` `_build_pfl()` function also returns the same PFL format. Good.

**Gap found:** The original `itm_bridge.py` doesn't pass `mdvar` to the C function (it's not in `_ITM_P2P.argtypes`). The pyitm `predict_p2p` requires `mdvar`. We default to 0 (SINGLE_MESSAGE), which matches the C++ ITM default behavior for the `ITM_P2P_TLS_Ex` variant.

**Important note on climate in config.py:** The `CLIMATE_NAMES` dict in `config.py` uses 0-indexed keys (0-6). This is for display/frontend use only and doesn't affect the bridge, so it can stay as-is. The frontend sends 0-indexed climate codes to the API, which passes them to `itm_p2p_loss()`, which then adds 1 for the pyitm enum. This is correct.

**Important note on p2p.py climate parameter:** Looking at the `p2p.py` code, `climate` is passed as `climate=climate` to `itm_p2p_loss()`. The frontend sends 0-indexed integers. The new bridge adds 1. This is consistent.

**Important note on coverage.py climate parameter:** Same pattern. The frontend sends 0-indexed, bridge adds 1. Consistent.