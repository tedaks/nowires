# Numba JIT Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Accelerate nowires coverage computation by (a) JIT-compiling numeric loops with Numba and (b) replacing `ThreadPoolExecutor` with `ProcessPoolExecutor` to bypass the GIL on pure-Python ITM calls.

**Architecture:** New `math_kernels.py` provides two `@numba.jit` functions consumed by `p2p.py` and `coverage.py`. Coverage grid computation switches to a persistent `ProcessPoolExecutor` (created at FastAPI startup) that receives pre-extracted PFL arrays from the main process. Coverage radius uses a per-request `ProcessPoolExecutor` with a pool initializer to share the elevation grid array once rather than pickling it per task.

**Tech Stack:** Python 3.10+, FastAPI, NumPy, Numba, pure-Python ITM (`itm` package), ProcessPoolExecutor (stdlib)

---

## File Map

| File | Change |
|------|--------|
| `backend/requirements.txt` | Add `numba>=0.57.0` |
| `backend/app/math_kernels.py` | **CREATE** — two JIT functions |
| `backend/app/p2p.py` | **MODIFY** — use `fresnel_profile_analysis` |
| `backend/app/coverage.py` | **MODIFY** — ProcessPoolExecutor + `apply_coverage_colors` |
| `backend/app/main.py` | **MODIFY** — lifespan pool |
| `backend/tests/__init__.py` | **CREATE** — empty |
| `backend/tests/conftest.py` | **CREATE** — sys.path setup |
| `backend/tests/test_math_kernels.py` | **CREATE** — unit tests |
| `backend/tests/test_coverage_workers.py` | **CREATE** — worker unit tests |

---

### Task 1: Add Numba dependency

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add numba to requirements.txt**

Replace the file contents with:
```
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
python-srtm>=0.6.0
numpy>=1.24.0
pillow>=10.0.0
pydantic>=2.0.0
numba>=0.57.0
itm
```

- [ ] **Step 2: Install numba**

Run: `pip install numba>=0.57.0`

Expected: numba installs successfully (it pulls in llvmlite automatically).

- [ ] **Step 3: Verify numba is importable**

Run: `python3 -c "import numba; print(numba.__version__)"`

Expected: version string printed, no errors.

- [ ] **Step 4: Create test scaffolding**

Create `backend/tests/__init__.py` (empty):
```python
```

Create `backend/tests/conftest.py`:
```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```

- [ ] **Step 5: Commit**

```bash
cd /home/bortre/03-final/nowires
git add backend/requirements.txt backend/tests/__init__.py backend/tests/conftest.py
git commit -m "feat: add numba dependency and test scaffolding"
```

---

### Task 2: Create `math_kernels.py` — `fresnel_profile_analysis`

**Files:**
- Create: `backend/app/math_kernels.py`
- Create: `backend/tests/test_math_kernels.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_math_kernels.py`:
```python
import math
import numpy as np
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

C = 299792458.0


def test_fresnel_arrays_have_correct_shape():
    from app.math_kernels import fresnel_profile_analysis

    n = 50
    distances = np.linspace(0, 5000.0, n)
    elevations = np.zeros(n, dtype=np.float64)
    tb, los, fr, obs, vf1, vf60 = fresnel_profile_analysis(
        distances, elevations, 30.0, 10.0, 5000.0, C / 300e6, 4.0 / 3.0
    )
    for arr in (tb, los, fr, obs, vf1, vf60):
        assert len(arr) == n


def test_fresnel_flat_terrain_no_blockage():
    from app.math_kernels import fresnel_profile_analysis

    n = 21
    dist_m = 2000.0
    distances = np.linspace(0, dist_m, n)
    elevations = np.zeros(n, dtype=np.float64)
    # Antennas well above ground → no blockage
    tb, los, fr, obs, vf1, vf60 = fresnel_profile_analysis(
        distances, elevations, 50.0, 50.0, dist_m, C / 300e6, 4.0 / 3.0
    )
    assert not obs.any(), "Flat terrain with high antennas must not block LOS"
    assert not vf60.any(), "Flat terrain with high antennas must not violate 60% Fresnel"


def test_fresnel_matches_scalar_functions():
    """fresnel_profile_analysis must reproduce the scalar loop in p2p.py exactly."""
    from app.math_kernels import fresnel_profile_analysis
    from app.p2p import fresnel_radius, earth_bulge

    n = 20
    dist_m = 3000.0
    f_mhz = 450.0
    k_factor = 4.0 / 3.0
    distances = np.linspace(0, dist_m, n)
    elevations = np.array(
        [10.0 * math.sin(i / n * math.pi) for i in range(n)], dtype=np.float64
    )
    tx_antenna_h = float(elevations[0]) + 20.0
    rx_antenna_h = float(elevations[-1]) + 5.0
    wavelength_m = C / (f_mhz * 1e6)

    tb, los, fr, obs, vf1, vf60 = fresnel_profile_analysis(
        distances, elevations, tx_antenna_h, rx_antenna_h, dist_m, wavelength_m, k_factor
    )

    for i in range(n):
        d = float(distances[i])
        t = d / dist_m
        exp_bulge = earth_bulge(d, dist_m, k_factor)
        exp_tb = float(elevations[i]) + exp_bulge
        exp_los = tx_antenna_h + t * (rx_antenna_h - tx_antenna_h)
        exp_fr = fresnel_radius(d, dist_m - d, f_mhz)

        assert abs(float(tb[i]) - exp_tb) < 1e-6, f"terrain_bulge mismatch at i={i}"
        assert abs(float(los[i]) - exp_los) < 1e-6, f"los_h mismatch at i={i}"
        assert abs(float(fr[i]) - exp_fr) < 1e-6, f"fresnel_r mismatch at i={i}"
        assert bool(obs[i]) == (exp_tb > exp_los), f"obstructs_los mismatch at i={i}"
        assert bool(vf1[i]) == (exp_tb > (exp_los - exp_fr)), f"violates_f1 mismatch at i={i}"
        assert bool(vf60[i]) == (exp_tb > (exp_los - 0.6 * exp_fr)), f"violates_f60 at i={i}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/bortre/03-final/nowires/backend && python3 -m pytest tests/test_math_kernels.py -v`

Expected: `ImportError` or `ModuleNotFoundError` — `math_kernels` does not exist yet.

- [ ] **Step 3: Create `math_kernels.py` with `fresnel_profile_analysis`**

Create `backend/app/math_kernels.py`:
```python
import math
import numpy as np
import numba
from numba import prange


@numba.jit(nopython=True, cache=True)
def fresnel_profile_analysis(
    distances: np.ndarray,
    elevations: np.ndarray,
    tx_antenna_h: float,
    rx_antenna_h: float,
    dist_m: float,
    wavelength_m: float,
    k_factor: float,
):
    """Vectorised Fresnel/earth-bulge/LOS analysis over a terrain profile.

    Returns six arrays of length N:
        terrain_bulge  — terrain elevation + earth bulge (m)
        los_h          — LOS height at each point (m)
        fresnel_r      — 1st Fresnel zone radius (m)
        obstructs_los  — True where terrain_bulge > los_h
        violates_f1    — True where terrain_bulge > los_h - fresnel_r
        violates_f60   — True where terrain_bulge > los_h - 0.6*fresnel_r
    """
    n = len(distances)
    terrain_bulge = np.empty(n, dtype=np.float64)
    los_h = np.empty(n, dtype=np.float64)
    fresnel_r = np.empty(n, dtype=np.float64)
    obstructs_los = np.empty(n, dtype=np.bool_)
    violates_f1 = np.empty(n, dtype=np.bool_)
    violates_f60 = np.empty(n, dtype=np.bool_)

    a_eff = k_factor * 6371000.0

    for i in range(n):
        d = distances[i]
        t = d / dist_m if dist_m > 0.0 else 0.0
        bulge = (d * (dist_m - d)) / (2.0 * a_eff)
        tb = elevations[i] + bulge
        los = tx_antenna_h + t * (rx_antenna_h - tx_antenna_h)
        d2 = dist_m - d
        fr = math.sqrt(wavelength_m * d * d2 / (d + d2)) if d > 0.0 and d2 > 0.0 else 0.0

        terrain_bulge[i] = tb
        los_h[i] = los
        fresnel_r[i] = fr
        obstructs_los[i] = tb > los
        violates_f1[i] = tb > (los - fr)
        violates_f60[i] = tb > (los - 0.6 * fr)

    return terrain_bulge, los_h, fresnel_r, obstructs_los, violates_f1, violates_f60
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/bortre/03-final/nowires/backend && python3 -m pytest tests/test_math_kernels.py::test_fresnel_arrays_have_correct_shape tests/test_math_kernels.py::test_fresnel_flat_terrain_no_blockage tests/test_math_kernels.py::test_fresnel_matches_scalar_functions -v`

Expected: 3 passed. (First run may be slow due to Numba JIT compilation; subsequent runs use cache.)

- [ ] **Step 5: Commit**

```bash
cd /home/bortre/03-final/nowires
git add backend/app/math_kernels.py backend/tests/test_math_kernels.py
git commit -m "feat: add fresnel_profile_analysis JIT kernel"
```

---

### Task 3: Add `apply_coverage_colors` to `math_kernels.py`

**Files:**
- Modify: `backend/app/math_kernels.py`
- Modify: `backend/tests/test_math_kernels.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_math_kernels.py`:
```python
def test_apply_coverage_colors_excellent_signal():
    """Signal above highest threshold (-60 dBm) maps to Excellent color (0,110,40,210)."""
    from app.math_kernels import apply_coverage_colors
    from app.coverage import SIGNAL_LEVELS

    thresholds = np.array([t for t, _, _ in SIGNAL_LEVELS], dtype=np.float64)
    colors = np.array(
        [list(c) for _, c, _ in SIGNAL_LEVELS] + [[90, 20, 20, 170]], dtype=np.uint8
    )
    prx_grid = np.full((4, 4), -50.0, dtype=np.float32)
    rgba_out = np.zeros((4, 4, 4), dtype=np.uint8)

    apply_coverage_colors(prx_grid, thresholds, colors, rgba_out)

    np.testing.assert_array_equal(rgba_out[0, 0], [0, 110, 40, 210])


def test_apply_coverage_colors_below_all_thresholds():
    """Signal below all thresholds gets the fallback color (90,20,20,170)."""
    from app.math_kernels import apply_coverage_colors
    from app.coverage import SIGNAL_LEVELS

    thresholds = np.array([t for t, _, _ in SIGNAL_LEVELS], dtype=np.float64)
    colors = np.array(
        [list(c) for _, c, _ in SIGNAL_LEVELS] + [[90, 20, 20, 170]], dtype=np.uint8
    )
    prx_grid = np.full((2, 2), -130.0, dtype=np.float32)
    rgba_out = np.zeros((2, 2, 4), dtype=np.uint8)

    apply_coverage_colors(prx_grid, thresholds, colors, rgba_out)

    np.testing.assert_array_equal(rgba_out[0, 0], [90, 20, 20, 170])


def test_apply_coverage_colors_nan_is_transparent():
    """NaN pixels must produce alpha=0."""
    from app.math_kernels import apply_coverage_colors
    from app.coverage import SIGNAL_LEVELS

    thresholds = np.array([t for t, _, _ in SIGNAL_LEVELS], dtype=np.float64)
    colors = np.array(
        [list(c) for _, c, _ in SIGNAL_LEVELS] + [[90, 20, 20, 170]], dtype=np.uint8
    )
    prx_grid = np.full((3, 3), np.nan, dtype=np.float32)
    rgba_out = np.ones((3, 3, 4), dtype=np.uint8) * 255

    apply_coverage_colors(prx_grid, thresholds, colors, rgba_out)

    assert rgba_out[:, :, 3].max() == 0, "All NaN pixels must have alpha=0"


def test_apply_coverage_colors_y_flip():
    """prx_grid row 0 maps to rgba_out last row (image y-axis is flipped)."""
    from app.math_kernels import apply_coverage_colors
    from app.coverage import SIGNAL_LEVELS

    thresholds = np.array([t for t, _, _ in SIGNAL_LEVELS], dtype=np.float64)
    colors = np.array(
        [list(c) for _, c, _ in SIGNAL_LEVELS] + [[90, 20, 20, 170]], dtype=np.uint8
    )
    rows = 6
    prx_grid = np.full((rows, 4), np.nan, dtype=np.float32)
    prx_grid[0, :] = -50.0  # only row 0 has signal
    rgba_out = np.zeros((rows, 4, 4), dtype=np.uint8)

    apply_coverage_colors(prx_grid, thresholds, colors, rgba_out)

    assert rgba_out[rows - 1, 0, 3] > 0, "prx row 0 → image last row must be filled"
    assert rgba_out[0, 0, 3] == 0, "prx row 0 → image row 0 must be empty"


def test_apply_coverage_colors_matches_prx_to_color():
    """apply_coverage_colors must produce the same RGBA as the original _prx_to_color."""
    from app.math_kernels import apply_coverage_colors
    from app.coverage import SIGNAL_LEVELS, _prx_to_color

    thresholds = np.array([t for t, _, _ in SIGNAL_LEVELS], dtype=np.float64)
    colors = np.array(
        [list(c) for _, c, _ in SIGNAL_LEVELS] + [[90, 20, 20, 170]], dtype=np.uint8
    )
    test_values = [-50.0, -70.0, -80.0, -90.0, -100.0, -110.0, -130.0]
    rows = len(test_values)
    prx_grid = np.zeros((rows, 1), dtype=np.float32)
    for i, v in enumerate(test_values):
        prx_grid[i, 0] = v
    rgba_out = np.zeros((rows, 1, 4), dtype=np.uint8)

    apply_coverage_colors(prx_grid, thresholds, colors, rgba_out)

    for i, v in enumerate(test_values):
        # Image row for prx row i is (rows-1-i)
        img_row = rows - 1 - i
        expected = list(_prx_to_color(v))
        actual = list(rgba_out[img_row, 0])
        assert actual == expected, f"Mismatch at prx={v}: got {actual}, want {expected}"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/bortre/03-final/nowires/backend && python3 -m pytest tests/test_math_kernels.py::test_apply_coverage_colors_excellent_signal -v`

Expected: `ImportError` — `apply_coverage_colors` not defined yet.

- [ ] **Step 3: Add `apply_coverage_colors` to `math_kernels.py`**

Append to `backend/app/math_kernels.py` (after the `fresnel_profile_analysis` function):
```python

@numba.jit(nopython=True, parallel=True, cache=True)
def apply_coverage_colors(
    prx_grid: np.ndarray,
    thresholds: np.ndarray,
    colors: np.ndarray,
    rgba_out: np.ndarray,
) -> None:
    """Map a float32 prx grid to RGBA pixels in-place with a y-axis flip.

    prx_grid  — float32 (rows, cols), NaN = no data
    thresholds — float64 (K,) descending threshold values
    colors    — uint8 (K+1, 4) RGBA per bucket; last row is the below-all-thresholds color
    rgba_out  — uint8 (rows, cols, 4) output, written in place
    """
    rows, cols = prx_grid.shape
    n_thresh = len(thresholds)
    for i in prange(rows):
        out_row = rows - 1 - i
        for j in range(cols):
            v = prx_grid[i, j]
            if np.isnan(v):
                rgba_out[out_row, j, 0] = 0
                rgba_out[out_row, j, 1] = 0
                rgba_out[out_row, j, 2] = 0
                rgba_out[out_row, j, 3] = 0
                continue
            k = n_thresh  # default: below all thresholds
            for t_idx in range(n_thresh):
                if v >= thresholds[t_idx]:
                    k = t_idx
                    break
            rgba_out[out_row, j, 0] = colors[k, 0]
            rgba_out[out_row, j, 1] = colors[k, 1]
            rgba_out[out_row, j, 2] = colors[k, 2]
            rgba_out[out_row, j, 3] = colors[k, 3]
```

- [ ] **Step 4: Run all math_kernels tests**

Run: `cd /home/bortre/03-final/nowires/backend && python3 -m pytest tests/test_math_kernels.py -v`

Expected: all 8 tests pass.

- [ ] **Step 5: Commit**

```bash
cd /home/bortre/03-final/nowires
git add backend/app/math_kernels.py backend/tests/test_math_kernels.py
git commit -m "feat: add apply_coverage_colors JIT kernel"
```

---

### Task 4: Update `p2p.py` to use `fresnel_profile_analysis`

**Files:**
- Modify: `backend/app/p2p.py`

- [ ] **Step 1: Replace the profile loop in `p2p.py`**

In `backend/app/p2p.py`, replace the entire file with:
```python
import math
import numpy as np
from typing import List, Dict, Any

from .terrain import profile as get_profile, haversine_m
from .itm_bridge import itm_p2p_loss, PROP_MODE_NAMES
from .math_kernels import fresnel_profile_analysis


C = 299792458.0
EARTH_RADIUS_M = 6371000.0


def fresnel_radius(d1_m: float, d2_m: float, f_mhz: float) -> float:
    if d1_m <= 0 or d2_m <= 0:
        return 0.0
    lambda_m = C / (f_mhz * 1e6)
    return math.sqrt(lambda_m * d1_m * d2_m / (d1_m + d2_m))


def earth_bulge(d_m: float, total_dist_m: float, k_factor: float) -> float:
    a_eff = k_factor * EARTH_RADIUS_M
    return (d_m * (total_dist_m - d_m)) / (2.0 * a_eff)


def build_pfl(elevations: List[float], step_m: float) -> List[float]:
    n = len(elevations) - 1
    return [float(n), step_m] + elevations


def analyze_p2p(
    tx_lat: float,
    tx_lon: float,
    tx_h_m: float,
    rx_lat: float,
    rx_lon: float,
    rx_h_m: float,
    f_mhz: float = 300.0,
    polarization: int = 0,
    climate: int = 1,
    N0: float = 301.0,
    epsilon: float = 15.0,
    sigma: float = 0.005,
    time_pct: float = 50.0,
    location_pct: float = 50.0,
    situation_pct: float = 50.0,
    k_factor: float = 4.0 / 3.0,
    tx_power_dbm: float = 43.0,
    tx_gain_dbi: float = 8.0,
    rx_gain_dbi: float = 2.0,
    cable_loss_db: float = 2.0,
    rx_sensitivity_dbm: float = -100.0,
) -> Dict[str, Any]:
    dist_m = haversine_m(tx_lat, tx_lon, rx_lat, rx_lon)
    points = get_profile(tx_lat, tx_lon, rx_lat, rx_lon, step_m=30.0)

    if len(points) < 2:
        return {"error": "Profile too short"}

    distances = [p[0] for p in points]
    elevations = [p[1] for p in points]
    step_m = distances[1] - distances[0] if len(distances) > 1 else 30.0

    pfl = build_pfl(elevations, step_m)

    result = itm_p2p_loss(
        h_tx__meter=tx_h_m,
        h_rx__meter=rx_h_m,
        profile=pfl,
        climate=climate,
        N0=N0,
        f__mhz=f_mhz,
        polarization=polarization,
        epsilon=epsilon,
        sigma=sigma,
        time_pct=time_pct,
        location_pct=location_pct,
        situation_pct=situation_pct,
    )

    tx_elev = elevations[0]
    rx_elev = elevations[-1]
    tx_antenna_h = tx_elev + tx_h_m
    rx_antenna_h = rx_elev + rx_h_m

    dist_arr = np.asarray(distances, dtype=np.float64)
    elev_arr = np.asarray(elevations, dtype=np.float64)
    wavelength_m = C / (f_mhz * 1e6)

    terrain_bulge, los_h_arr, fresnel_r_arr, obstructs_arr, vf1_arr, vf60_arr = \
        fresnel_profile_analysis(
            dist_arr, elev_arr, tx_antenna_h, rx_antenna_h,
            dist_m, wavelength_m, k_factor,
        )

    any_blockage = bool(obstructs_arr.any())
    any_fresnel_violation = bool(vf1_arr.any())
    any_fresnel60_violation = bool(vf60_arr.any())

    profile_data = []
    for i in range(len(distances)):
        d = distances[i]
        terrain = elevations[i]
        tb = float(terrain_bulge[i])
        los = float(los_h_arr[i])
        fr = float(fresnel_r_arr[i])
        profile_data.append(
            {
                "d": round(d, 1),
                "terrain": round(terrain, 1),
                "terrain_bulge": round(tb, 2),
                "los": round(los, 2),
                "fresnel_upper": round(los + fr, 2),
                "fresnel_lower": round(los - fr, 2),
                "fresnel_60": round(los - 0.6 * fr, 2),
                "blocked": bool(obstructs_arr[i]),
                "violates_f1": bool(vf1_arr[i]),
                "violates_f60": bool(vf60_arr[i]),
            }
        )

    # Downsample profile for chart if necessary
    max_chart_points = 400
    if len(profile_data) > max_chart_points:
        step = len(profile_data) / max_chart_points
        downsampled = [profile_data[int(i * step)] for i in range(max_chart_points)]
        downsampled.append(profile_data[-1])
        profile_data = downsampled

    # Link budget
    eirp_dbm = tx_power_dbm + tx_gain_dbi - cable_loss_db
    prx_dbm = eirp_dbm + rx_gain_dbi - result.loss_db
    margin_db = prx_dbm - rx_sensitivity_dbm
    fspl_db = (
        20.0 * math.log10(dist_m / 1000.0)
        + 20.0 * math.log10(f_mhz)
        + 32.44
        if dist_m > 0 and f_mhz > 0
        else 0.0
    )

    link_budget = {
        "tx_power_dbm": round(tx_power_dbm, 2),
        "tx_gain_dbi": round(tx_gain_dbi, 2),
        "rx_gain_dbi": round(rx_gain_dbi, 2),
        "cable_loss_db": round(cable_loss_db, 2),
        "eirp_dbm": round(eirp_dbm, 2),
        "fspl_db": round(fspl_db, 2),
        "itm_loss_db": round(result.loss_db, 2),
        "excess_loss_db": round(result.loss_db - fspl_db, 2),
        "prx_dbm": round(prx_dbm, 2),
        "rx_sensitivity_dbm": round(rx_sensitivity_dbm, 2),
        "margin_db": round(margin_db, 2),
    }

    horizons = []
    if 0 < result.d_hzn_tx_m < dist_m:
        horizons.append({"role": "tx_horizon", "d_m": round(result.d_hzn_tx_m, 1)})
    if 0 < result.d_hzn_rx_m < dist_m:
        horizons.append(
            {"role": "rx_horizon", "d_m": round(dist_m - result.d_hzn_rx_m, 1)}
        )

    return {
        "distance_m": round(dist_m, 1),
        "profile": profile_data,
        "loss_db": round(result.loss_db, 2),
        "mode": result.mode,
        "mode_name": PROP_MODE_NAMES.get(result.mode, "Unknown"),
        "warnings": result.warnings,
        "link_budget": link_budget,
        "horizons": horizons,
        "flags": {
            "los_blocked": any_blockage,
            "fresnel_f1_violated": any_fresnel_violation,
            "fresnel_60_violated": any_fresnel60_violation,
        },
        "k_factor": round(k_factor, 3),
        "intermediates": {
            "d_hzn_tx_m": round(result.d_hzn_tx_m, 1),
            "d_hzn_rx_m": round(result.d_hzn_rx_m, 1),
            "h_e_tx_m": round(result.h_e_tx_m, 2),
            "h_e_rx_m": round(result.h_e_rx_m, 2),
            "delta_h_m": round(result.delta_h_m, 2),
            "A_ref_db": round(result.A_ref_db, 2),
        },
    }
```

- [ ] **Step 2: Verify the module parses correctly**

Run: `python3 -c "import ast; ast.parse(open('/home/bortre/03-final/nowires/backend/app/p2p.py').read()); print('Syntax OK')"`

Expected: `Syntax OK`

- [ ] **Step 3: Run math_kernels tests to confirm nothing regressed**

Run: `cd /home/bortre/03-final/nowires/backend && python3 -m pytest tests/test_math_kernels.py -v`

Expected: all 8 pass.

- [ ] **Step 4: Commit**

```bash
cd /home/bortre/03-final/nowires
git add backend/app/p2p.py
git commit -m "perf: use fresnel_profile_analysis JIT kernel in p2p.py"
```

---

### Task 5: Refactor `coverage.py` — coverage grid with ProcessPoolExecutor

**Files:**
- Modify: `backend/app/coverage.py`
- Create: `backend/tests/test_coverage_workers.py`

- [ ] **Step 1: Write the failing worker tests**

Create `backend/tests/test_coverage_workers.py`:
```python
import math
import numpy as np
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _make_mock_itm_result(loss_db: float):
    r = MagicMock()
    r.loss_db = loss_db
    return r


def test_itm_worker_returns_tuple_on_success():
    import app.coverage as cov

    pfl = [2.0, 100.0, 0.0, 50.0, 0.0]
    # args: i, j, pfl, tx_h_m, rx_h_m, climate, N0, f_mhz,
    #       polarization, epsilon, sigma, time_pct, loc_pct, sit_pct,
    #       eirp_dbm, ant_gain_adj, rx_gain_dbi
    args = (3, 7, pfl, 30.0, 10.0, 1, 301.0, 300.0,
            0, 15.0, 0.005, 50.0, 50.0, 50.0,
            49.0, 0.0, 2.0)

    with patch.object(cov, "itm_p2p_loss", return_value=_make_mock_itm_result(100.0)):
        result = cov._itm_worker(args)

    assert result is not None
    i, j, loss_db, prx = result
    assert i == 3
    assert j == 7
    assert loss_db == 100.0
    assert abs(prx - (49.0 + 0.0 + 2.0 - 100.0)) < 1e-9


def test_itm_worker_returns_none_on_exception():
    import app.coverage as cov

    pfl = [2.0, 100.0, 0.0, 50.0, 0.0]
    args = (0, 0, pfl, 30.0, 10.0, 1, 301.0, 300.0,
            0, 15.0, 0.005, 50.0, 50.0, 50.0,
            49.0, 0.0, 2.0)

    with patch.object(cov, "itm_p2p_loss", side_effect=RuntimeError("ITM exploded")):
        result = cov._itm_worker(args)

    assert result is None


def test_itm_worker_returns_none_on_infinite_loss():
    import app.coverage as cov

    pfl = [2.0, 100.0, 0.0, 50.0, 0.0]
    args = (0, 0, pfl, 30.0, 10.0, 1, 301.0, 300.0,
            0, 15.0, 0.005, 50.0, 50.0, 50.0,
            49.0, 0.0, 2.0)

    with patch.object(cov, "itm_p2p_loss", return_value=_make_mock_itm_result(float("inf"))):
        result = cov._itm_worker(args)

    assert result is None


def test_itm_worker_applies_antenna_gain_adjustment():
    import app.coverage as cov

    pfl = [2.0, 100.0, 0.0, 50.0, 0.0]
    # ant_gain_adj = -5.0 dB (off-boresight)
    args = (1, 2, pfl, 30.0, 10.0, 1, 301.0, 300.0,
            0, 15.0, 0.005, 50.0, 50.0, 50.0,
            49.0, -5.0, 2.0)

    with patch.object(cov, "itm_p2p_loss", return_value=_make_mock_itm_result(80.0)):
        result = cov._itm_worker(args)

    assert result is not None
    _, _, loss_db, prx = result
    assert abs(prx - (49.0 + (-5.0) + 2.0 - 80.0)) < 1e-9
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `cd /home/bortre/03-final/nowires/backend && python3 -m pytest tests/test_coverage_workers.py -v`

Expected: `AttributeError` — `_itm_worker` not found in `coverage` module.

- [ ] **Step 3: Rewrite `coverage.py`**

Replace `backend/app/coverage.py` entirely with:
```python
"""
Per-pixel ITM coverage with link-budget (dBm) output.

For each output pixel we extract a real terrain profile from TX to that pixel
(bilinear-sampled from a pre-fetched elevation grid) and call ITM. Path loss
is combined with TX power, antenna gains, cable loss, and optional antenna
pattern to produce received power in dBm, which is then colored by signal
level the way commercial radio planning tools do.
"""

import math
import os
import io
import base64
import hashlib
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, Any, List, Tuple, Optional

import numpy as np
from PIL import Image

from .elevation_grid import ElevationGrid
from .itm_bridge import itm_p2p_loss
from .math_kernels import apply_coverage_colors


_png_cache: Dict[str, Dict[str, Any]] = {}

# Module-level globals written by _init_radius_pool in each worker process.
_radius_grid_data: Optional[np.ndarray] = None
_radius_grid_meta: dict = {}


SIGNAL_LEVELS = [
    (-60.0, (0, 110, 40, 210), "Excellent"),
    (-75.0, (0, 180, 80, 200), "Good"),
    (-85.0, (180, 220, 40, 195), "Fair"),
    (-95.0, (240, 180, 40, 190), "Marginal"),
    (-105.0, (230, 110, 40, 185), "Weak"),
    (-120.0, (200, 40, 40, 180), "No service"),
]

# Pre-built threshold and color arrays for apply_coverage_colors (built once).
_THRESHOLDS = np.array([t for t, _, _ in SIGNAL_LEVELS], dtype=np.float64)
_COLORS = np.array(
    [list(c) for _, c, _ in SIGNAL_LEVELS] + [[90, 20, 20, 170]], dtype=np.uint8
)


def _prx_to_color(prx_dbm: float) -> Tuple[int, int, int, int]:
    if not math.isfinite(prx_dbm):
        return (0, 0, 0, 0)
    for thresh, rgba, _ in SIGNAL_LEVELS:
        if prx_dbm >= thresh:
            return rgba
    return (90, 20, 20, 170)


def _build_pfl(elevations: np.ndarray, step_m: float) -> List[float]:
    n = len(elevations) - 1
    return [float(n), float(step_m)] + [float(x) for x in elevations]


def _bearing_destination(
    lat: float, lon: float, bearing_deg: float, dist_m: float
) -> Tuple[float, float]:
    R = 6371000.0
    brng = math.radians(bearing_deg)
    lat_r = math.radians(lat)
    lon_r = math.radians(lon)
    d_r = dist_m / R
    lat2 = math.asin(
        math.sin(lat_r) * math.cos(d_r)
        + math.cos(lat_r) * math.sin(d_r) * math.cos(brng)
    )
    lon2 = lon_r + math.atan2(
        math.sin(brng) * math.sin(d_r) * math.cos(lat_r),
        math.cos(d_r) - math.sin(lat_r) * math.sin(lat2),
    )
    return math.degrees(lat2), math.degrees(lon2)


def _antenna_gain_factor(
    bearing_from_tx_deg: float,
    az_deg: float | None,
    beamwidth_deg: float,
    front_back_db: float = 25.0,
) -> float:
    """Cosine-squared pattern within beamwidth, F/B attenuation outside."""
    if az_deg is None:
        return 0.0
    diff = (bearing_from_tx_deg - az_deg + 540.0) % 360.0 - 180.0
    if abs(diff) <= beamwidth_deg / 2.0:
        x = diff / (beamwidth_deg / 2.0)
        attn = 3.0 * x * x
        return -attn
    return -front_back_db


# ---------------------------------------------------------------------------
# Coverage grid worker (top-level so ProcessPoolExecutor can pickle it)
# ---------------------------------------------------------------------------

def _itm_worker(args):
    """Compute ITM loss + received power for one grid pixel.

    args: (i, j, pfl, tx_h_m, rx_h_m, climate, N0, f_mhz,
           polarization, epsilon, sigma, time_pct, location_pct, situation_pct,
           eirp_dbm, ant_gain_adj, rx_gain_dbi)

    Returns (i, j, loss_db, prx_dbm) or None on failure.
    """
    (i, j, pfl, tx_h_m, rx_h_m, climate, N0, f_mhz,
     polarization, epsilon, sigma, time_pct, location_pct, situation_pct,
     eirp_dbm, ant_gain_adj, rx_gain_dbi) = args
    try:
        res = itm_p2p_loss(
            h_tx__meter=tx_h_m,
            h_rx__meter=rx_h_m,
            profile=pfl,
            climate=climate,
            N0=N0,
            f__mhz=f_mhz,
            polarization=polarization,
            epsilon=epsilon,
            sigma=sigma,
            time_pct=time_pct,
            location_pct=location_pct,
            situation_pct=situation_pct,
        )
    except Exception:
        return None
    if not math.isfinite(res.loss_db) or res.loss_db > 400.0:
        return None
    prx = eirp_dbm + ant_gain_adj + rx_gain_dbi - res.loss_db
    return (i, j, res.loss_db, prx)


# ---------------------------------------------------------------------------
# Coverage radius worker + pool initializer
# ---------------------------------------------------------------------------

def _init_radius_pool(grid_data: np.ndarray, grid_meta: dict) -> None:
    """Pool initializer: store the elevation grid in each worker process once."""
    global _radius_grid_data, _radius_grid_meta
    _radius_grid_data = grid_data
    _radius_grid_meta = grid_meta


def _radius_worker(args):
    """Binary-search the coverage radius for one bearing.

    Uses the elevation grid stored by _init_radius_pool.

    args: (bearing_deg, tx_lat, tx_lon, tx_h_m, rx_h_m, f_mhz,
           polarization, climate, N0, epsilon, sigma,
           time_pct, location_pct, situation_pct,
           eirp_dbm, rx_gain_dbi, rx_sensitivity_dbm,
           antenna_az_deg, antenna_beamwidth_deg)

    Returns (bearing_deg, radius_m).
    """
    (bearing_deg, tx_lat, tx_lon, tx_h_m, rx_h_m, f_mhz,
     polarization, climate, N0, epsilon, sigma,
     time_pct, location_pct, situation_pct,
     eirp_dbm, rx_gain_dbi, rx_sensitivity_dbm,
     antenna_az_deg, antenna_beamwidth_deg) = args

    gd = _radius_grid_data
    gm = _radius_grid_meta
    min_lat = gm["min_lat"]
    max_lat = gm["max_lat"]
    min_lon = gm["min_lon"]
    max_lon = gm["max_lon"]
    n_lat = gm["n_lat"]
    n_lon = gm["n_lon"]
    d_lat = (max_lat - min_lat) / (n_lat - 1)
    d_lon = (max_lon - min_lon) / (n_lon - 1)

    def _sample_line(lat1, lon1, lat2, lon2, n_pts):
        ts = np.linspace(0.0, 1.0, n_pts)
        lats = lat1 + ts * (lat2 - lat1)
        lons = lon1 + ts * (lon2 - lon1)
        fy = np.clip((lats - min_lat) / d_lat, 0, n_lat - 1 - 1e-9)
        fx = np.clip((lons - min_lon) / d_lon, 0, n_lon - 1 - 1e-9)
        y0 = np.floor(fy).astype(np.int32)
        x0 = np.floor(fx).astype(np.int32)
        y1 = np.clip(y0 + 1, 0, n_lat - 1)
        x1 = np.clip(x0 + 1, 0, n_lon - 1)
        ty = (fy - y0).astype(np.float32)
        tx_ = (fx - x0).astype(np.float32)
        return (
            gd[y0, x0] * (1 - tx_) * (1 - ty)
            + gd[y0, x1] * tx_ * (1 - ty)
            + gd[y1, x0] * (1 - tx_) * ty
            + gd[y1, x1] * tx_ * ty
        )

    d_min, d_max = 100.0, 100_000.0
    for _ in range(20):
        d_mid = (d_min + d_max) / 2.0
        lat_end, lon_end = _bearing_destination(tx_lat, tx_lon, bearing_deg, d_mid)
        n_pts = max(3, int(round(d_mid / 250.0)) + 1)
        elevs = _sample_line(tx_lat, tx_lon, lat_end, lon_end, n_pts)
        step_m = d_mid / (n_pts - 1)
        pfl = _build_pfl(elevs, step_m)
        try:
            res = itm_p2p_loss(
                h_tx__meter=tx_h_m,
                h_rx__meter=rx_h_m,
                profile=pfl,
                climate=climate,
                N0=N0,
                f__mhz=f_mhz,
                polarization=polarization,
                epsilon=epsilon,
                sigma=sigma,
                time_pct=time_pct,
                location_pct=location_pct,
                situation_pct=situation_pct,
            )
        except Exception:
            d_min = d_mid
            continue
        if not math.isfinite(res.loss_db):
            d_min = d_mid
            continue
        ant_gain_adj = _antenna_gain_factor(
            bearing_deg, antenna_az_deg, antenna_beamwidth_deg
        )
        prx = eirp_dbm + ant_gain_adj + rx_gain_dbi - res.loss_db
        if prx >= rx_sensitivity_dbm:
            d_min = d_mid
        else:
            d_max = d_mid

    return (bearing_deg, (d_min + d_max) / 2.0)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_coverage_radius(
    tx_lat: float,
    tx_lon: float,
    tx_h_m: float,
    rx_h_m: float,
    f_mhz: float,
    tx_power_dbm: float = 43.0,
    tx_gain_dbi: float = 8.0,
    rx_gain_dbi: float = 2.0,
    cable_loss_db: float = 2.0,
    rx_sensitivity_dbm: float = -100.0,
    antenna_az_deg: float | None = None,
    antenna_beamwidth_deg: float = 360.0,
    polarization: int = 0,
    climate: int = 1,
    N0: float = 301.0,
    epsilon: float = 15.0,
    sigma: float = 0.005,
    time_pct: float = 50.0,
    location_pct: float = 50.0,
    situation_pct: float = 50.0,
    terrain_spacing_m: float = 300.0,
    elev_grid_n: int | None = None,
) -> Dict[str, Any]:
    """Compute coverage radius per bearing via link-budget threshold crossing."""
    deg_per_m = 1.0 / 111320.0
    pad_deg = 2.0 * terrain_spacing_m * deg_per_m
    padded_bbox_m = 2.0 * 100.0 * 1000.0 + 4.0 * terrain_spacing_m
    if elev_grid_n is None:
        elev_grid_n = max(64, min(320, int(padded_bbox_m / terrain_spacing_m) + 1))

    lat_per_m = 1.0 / 111320.0
    lon_per_m = 1.0 / (111320.0 * max(math.cos(math.radians(tx_lat)), 0.01))
    half_lat = 100.0 * 1000.0 * lat_per_m
    half_lon = 100.0 * 1000.0 * lon_per_m

    elev = ElevationGrid.fetch(
        min_lat=tx_lat - half_lat - pad_deg,
        min_lon=tx_lon - half_lon - pad_deg,
        max_lat=tx_lat + half_lat + pad_deg,
        max_lon=tx_lon + half_lon + pad_deg,
        n=elev_grid_n,
    )

    eirp_dbm = tx_power_dbm + tx_gain_dbi - cable_loss_db

    grid_meta = {
        "min_lat": elev.min_lat, "max_lat": elev.max_lat,
        "min_lon": elev.min_lon, "max_lon": elev.max_lon,
        "n_lat": elev.n_lat, "n_lon": elev.n_lon,
    }

    worker_args = [
        (float(b), tx_lat, tx_lon, tx_h_m, rx_h_m, f_mhz,
         polarization, climate, N0, epsilon, sigma,
         time_pct, location_pct, situation_pct,
         eirp_dbm, rx_gain_dbi, rx_sensitivity_dbm,
         antenna_az_deg, antenna_beamwidth_deg)
        for b in np.arange(0, 360, 1.0)
    ]

    n_workers = max(1, os.cpu_count() or 1)
    with ProcessPoolExecutor(
        max_workers=n_workers,
        initializer=_init_radius_pool,
        initargs=(elev.data, grid_meta),
    ) as radius_pool:
        radius_per_bearing = list(radius_pool.map(_radius_worker, worker_args))

    radii = [r for _, r in radius_per_bearing]
    max_radius_km = max(radii) / 1000.0 if radii else 0.0
    min_radius_km = min(radii) / 1000.0 if radii else 0.0
    avg_radius_km = float(np.mean(radii)) / 1000.0 if radii else 0.0

    return {
        "max_radius_km": round(max_radius_km, 2),
        "min_radius_km": round(min_radius_km, 2),
        "avg_radius_km": round(avg_radius_km, 2),
        "per_bearing": [(float(b), round(r / 1000.0, 2)) for b, r in radius_per_bearing],
    }


def compute_coverage(
    tx_lat: float,
    tx_lon: float,
    tx_h_m: float,
    rx_h_m: float,
    f_mhz: float,
    radius_km: float = 50.0,
    grid_size: int = 96,
    profile_step_m: float = 250.0,
    tx_power_dbm: float = 43.0,
    tx_gain_dbi: float = 8.0,
    rx_gain_dbi: float = 2.0,
    cable_loss_db: float = 2.0,
    rx_sensitivity_dbm: float = -100.0,
    antenna_az_deg: float | None = None,
    antenna_beamwidth_deg: float = 360.0,
    polarization: int = 0,
    climate: int = 1,
    N0: float = 301.0,
    epsilon: float = 15.0,
    sigma: float = 0.005,
    time_pct: float = 50.0,
    location_pct: float = 50.0,
    situation_pct: float = 50.0,
    terrain_spacing_m: float = 300.0,
    elev_grid_n: int | None = None,
    pool: ProcessPoolExecutor | None = None,
) -> Dict[str, Any]:
    deg_per_m = 1.0 / 111320.0
    pad_deg = 2.0 * terrain_spacing_m * deg_per_m
    padded_bbox_m = 2.0 * radius_km * 1000.0 + 4.0 * terrain_spacing_m
    if elev_grid_n is None:
        elev_grid_n = max(64, min(320, int(padded_bbox_m / terrain_spacing_m) + 1))

    cache_key_src = (
        f"{tx_lat:.5f},{tx_lon:.5f},{tx_h_m:.1f},{rx_h_m:.1f},{f_mhz:.1f},"
        f"{radius_km},{grid_size},{profile_step_m},{elev_grid_n},"
        f"{tx_power_dbm},{tx_gain_dbi},"
        f"{rx_gain_dbi},{cable_loss_db},{antenna_az_deg},{antenna_beamwidth_deg},"
        f"{polarization},{climate},{time_pct},{location_pct},{situation_pct}"
    )
    cache_key = hashlib.md5(cache_key_src.encode()).hexdigest()
    if cache_key in _png_cache:
        return {**_png_cache[cache_key], "from_cache": True}

    radius_m = radius_km * 1000.0
    lat_per_m = 1.0 / 111320.0
    lon_per_m = 1.0 / (111320.0 * max(math.cos(math.radians(tx_lat)), 0.01))
    half_lat = radius_m * lat_per_m
    half_lon = radius_m * lon_per_m

    min_lat = tx_lat - half_lat
    max_lat = tx_lat + half_lat
    min_lon = tx_lon - half_lon
    max_lon = tx_lon + half_lon

    elev = ElevationGrid.fetch(
        min_lat=min_lat - pad_deg,
        min_lon=min_lon - pad_deg,
        max_lat=max_lat + pad_deg,
        max_lon=max_lon + pad_deg,
        n=elev_grid_n,
    )

    eirp_dbm = tx_power_dbm + tx_gain_dbi - cable_loss_db

    lats = np.linspace(min_lat, max_lat, grid_size)
    lons = np.linspace(min_lon, max_lon, grid_size)

    prx_grid = np.full((grid_size, grid_size), np.nan, dtype=np.float32)
    loss_grid = np.full((grid_size, grid_size), np.nan, dtype=np.float32)

    lat_grid_2d = lats.reshape(-1, 1).repeat(grid_size, axis=1)
    lon_grid_2d = lons.reshape(1, -1).repeat(grid_size, axis=0)
    dlat = (lat_grid_2d - tx_lat) / lat_per_m
    dlon = (lon_grid_2d - tx_lon) / lon_per_m
    dist_grid = np.sqrt(dlat * dlat + dlon * dlon)
    bearing_grid = (np.degrees(np.arctan2(dlon, dlat)) + 360.0) % 360.0

    # Pre-extract all PFLs in the main process (ElevationGrid stays here).
    tasks = []
    for i in range(grid_size):
        for j in range(grid_size):
            d_m = float(dist_grid[i, j])
            if d_m < 50.0 or d_m > radius_m:
                continue
            bearing = float(bearing_grid[i, j])
            n_pts = max(3, int(round(d_m / profile_step_m)) + 1)
            elevs = elev.sample_line(tx_lat, tx_lon, lats[i], lons[j], n_pts)
            step_m = d_m / (n_pts - 1)
            pfl = _build_pfl(elevs, step_m)
            ant_gain_adj = _antenna_gain_factor(
                bearing, antenna_az_deg, antenna_beamwidth_deg
            )
            tasks.append(
                (i, j, pfl, tx_h_m, rx_h_m, climate, N0, f_mhz,
                 polarization, epsilon, sigma, time_pct, location_pct, situation_pct,
                 eirp_dbm, ant_gain_adj, rx_gain_dbi)
            )

    _own_pool = pool is None
    if _own_pool:
        pool = ProcessPoolExecutor(max_workers=max(1, os.cpu_count() or 1))
    try:
        for result in pool.map(_itm_worker, tasks):
            if result is not None:
                i, j, loss_db, prx = result
                loss_grid[i, j] = loss_db
                prx_grid[i, j] = prx
    finally:
        if _own_pool:
            pool.shutdown(wait=True)

    # Render to RGBA PNG using Numba JIT color mapping.
    rgba = np.zeros((grid_size, grid_size, 4), dtype=np.uint8)
    apply_coverage_colors(prx_grid, _THRESHOLDS, _COLORS, rgba)

    pil_img = Image.fromarray(rgba, mode="RGBA")
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    png_b64 = base64.b64encode(buf.getvalue()).decode()

    geo_bounds = [[min_lat, min_lon], [max_lat, max_lon]]

    valid = ~np.isnan(prx_grid)
    stats = {
        "pixels_total": int(grid_size * grid_size),
        "pixels_valid": int(valid.sum()),
        "prx_min_dbm": float(np.nanmin(prx_grid)) if valid.any() else None,
        "prx_max_dbm": float(np.nanmax(prx_grid)) if valid.any() else None,
        "pct_above_sensitivity": (
            float((prx_grid[valid] >= rx_sensitivity_dbm).sum())
            / max(valid.sum(), 1)
            * 100.0
            if valid.any()
            else 0.0
        ),
        "terrain_grid_n": int(elev_grid_n),
        "terrain_spacing_m": round(
            (elev.d_lat + elev.d_lon * math.cos(math.radians(tx_lat))) / 2.0 / deg_per_m,
            1,
        ),
        "terrain_elev_min_m": float(np.nanmin(elev.data)),
        "terrain_elev_max_m": float(np.nanmax(elev.data)),
        "terrain_elev_std_m": round(float(np.nanstd(elev.data)), 1),
        "loss_min_db": float(np.nanmin(loss_grid)) if valid.any() else None,
        "loss_max_db": float(np.nanmax(loss_grid)) if valid.any() else None,
    }

    legend = [
        {"threshold_dbm": t, "rgba": list(c), "label": lbl}
        for t, c, lbl in SIGNAL_LEVELS
    ]

    out = {
        "png_base64": png_b64,
        "bounds": geo_bounds,
        "legend": legend,
        "eirp_dbm": round(eirp_dbm, 2),
        "rx_sensitivity_dbm": rx_sensitivity_dbm,
        "stats": stats,
        "from_cache": False,
    }
    _png_cache[cache_key] = {k: v for k, v in out.items() if k != "from_cache"}
    return out
```

- [ ] **Step 4: Run worker tests**

Run: `cd /home/bortre/03-final/nowires/backend && python3 -m pytest tests/test_coverage_workers.py -v`

Expected: 4 tests pass.

- [ ] **Step 5: Run all tests**

Run: `cd /home/bortre/03-final/nowires/backend && python3 -m pytest tests/ -v`

Expected: all 12 tests pass (8 from math_kernels + 4 from coverage_workers).

- [ ] **Step 6: Verify syntax**

Run: `python3 -c "import ast; ast.parse(open('/home/bortre/03-final/nowires/backend/app/coverage.py').read()); print('OK')"`

Expected: `OK`

- [ ] **Step 7: Commit**

```bash
cd /home/bortre/03-final/nowires
git add backend/app/coverage.py backend/tests/test_coverage_workers.py
git commit -m "perf: ProcessPoolExecutor coverage grid + Numba color mapping"
```

---

### Task 6: Add radius worker tests

**Files:**
- Modify: `backend/tests/test_coverage_workers.py`

- [ ] **Step 1: Write the radius worker tests**

Append to `backend/tests/test_coverage_workers.py`:
```python
def test_radius_worker_returns_tuple():
    """_radius_worker should return (bearing_deg, radius_m) within search bounds."""
    import app.coverage as cov

    # Set grid globals directly (as if pool initializer ran)
    cov._radius_grid_data = np.zeros((10, 10), dtype=np.float32)
    cov._radius_grid_meta = {
        "min_lat": 14.0, "max_lat": 15.0,
        "min_lon": 121.0, "max_lon": 122.0,
        "n_lat": 10, "n_lon": 10,
    }

    # High loss → always below sensitivity → search settles at d_max
    with patch.object(cov, "itm_p2p_loss", return_value=_make_mock_itm_result(300.0)):
        bearing, radius_m = cov._radius_worker((
            45.0, 14.5, 121.5, 30.0, 10.0, 300.0,
            0, 1, 301.0, 15.0, 0.005,
            50.0, 50.0, 50.0,
            49.0, 2.0, -100.0,
            None, 360.0,
        ))

    assert bearing == 45.0
    assert 100.0 <= radius_m <= 100_000.0


def test_radius_worker_low_loss_returns_large_radius():
    """Very low path loss → signal always above sensitivity → radius near d_max."""
    import app.coverage as cov

    cov._radius_grid_data = np.zeros((10, 10), dtype=np.float32)
    cov._radius_grid_meta = {
        "min_lat": 14.0, "max_lat": 15.0,
        "min_lon": 121.0, "max_lon": 122.0,
        "n_lat": 10, "n_lon": 10,
    }

    # eirp=49, rx_gain=2, loss=10 → prx = 49+2-10 = 41 dBm >> sensitivity (-100)
    with patch.object(cov, "itm_p2p_loss", return_value=_make_mock_itm_result(10.0)):
        _, radius_m = cov._radius_worker((
            90.0, 14.5, 121.5, 30.0, 10.0, 300.0,
            0, 1, 301.0, 15.0, 0.005,
            50.0, 50.0, 50.0,
            49.0, 2.0, -100.0,
            None, 360.0,
        ))

    # 20 iterations of binary search: d_min converges toward 100 km
    assert radius_m > 90_000.0, "Low loss should yield near-maximum radius"


def test_init_radius_pool_sets_globals():
    """_init_radius_pool must write grid_data and grid_meta to module globals."""
    import app.coverage as cov

    data = np.ones((5, 5), dtype=np.float32)
    meta = {"min_lat": 1.0, "max_lat": 2.0, "min_lon": 3.0, "max_lon": 4.0,
            "n_lat": 5, "n_lon": 5}

    cov._init_radius_pool(data, meta)

    np.testing.assert_array_equal(cov._radius_grid_data, data)
    assert cov._radius_grid_meta == meta
```

- [ ] **Step 2: Run all tests**

Run: `cd /home/bortre/03-final/nowires/backend && python3 -m pytest tests/ -v`

Expected: all 15 tests pass.

- [ ] **Step 3: Commit**

```bash
cd /home/bortre/03-final/nowires
git add backend/tests/test_coverage_workers.py
git commit -m "test: add radius worker unit tests"
```

---

### Task 7: Update `main.py` — lifespan pool

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Rewrite `main.py` with lifespan and pool**

Replace `backend/app/main.py` entirely with:
```python
import os
import sys
from contextlib import asynccontextmanager
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

_backend_dir = str(Path(__file__).resolve().parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from app.p2p import analyze_p2p
from app.coverage import compute_coverage, compute_coverage_radius


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = ProcessPoolExecutor(max_workers=os.cpu_count() or 1)
    yield
    app.state.pool.shutdown(wait=True)


app = FastAPI(lifespan=lifespan)

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = PROJECT_DIR / "frontend"


class P2PRequest(BaseModel):
    tx: dict
    rx: dict
    freq_mhz: float = 300.0
    polarization: int = 0
    climate: int = 1
    N0: float = 301.0
    epsilon: float = 15.0
    sigma: float = 0.005
    time_pct: float = 50.0
    location_pct: float = 50.0
    situation_pct: float = 50.0
    k_factor: float = 4.0 / 3.0
    tx_power_dbm: float = 43.0
    tx_gain_dbi: float = 8.0
    rx_gain_dbi: float = 2.0
    cable_loss_db: float = 2.0
    rx_sensitivity_dbm: float = -100.0


class CoverageRequest(BaseModel):
    tx: dict
    rx_h_m: float = 10.0
    freq_mhz: float = 300.0
    radius_km: float = 50.0
    grid_size: int = 96
    profile_step_m: float = 250.0
    terrain_spacing_m: float = 300.0
    elev_grid_n: Optional[int] = None
    polarization: int = 0
    climate: int = 1
    N0: float = 301.0
    epsilon: float = 15.0
    sigma: float = 0.005
    time_pct: float = 50.0
    location_pct: float = 50.0
    situation_pct: float = 50.0
    tx_power_dbm: float = 43.0
    tx_gain_dbi: float = 8.0
    rx_gain_dbi: float = 2.0
    cable_loss_db: float = 2.0
    rx_sensitivity_dbm: float = -100.0
    antenna_az_deg: Optional[float] = None
    antenna_beamwidth_deg: float = 360.0


@app.get("/")
async def root():
    with open(FRONTEND_DIR / "index.html") as f:
        return HTMLResponse(content=f.read())


@app.post("/api/p2p")
async def p2p_endpoint(req: P2PRequest):
    return analyze_p2p(
        tx_lat=req.tx["lat"],
        tx_lon=req.tx["lon"],
        tx_h_m=req.tx.get("h_m", 30.0),
        rx_lat=req.rx["lat"],
        rx_lon=req.rx["lon"],
        rx_h_m=req.rx.get("h_m", 10.0),
        f_mhz=req.freq_mhz,
        polarization=req.polarization,
        climate=req.climate,
        N0=req.N0,
        epsilon=req.epsilon,
        sigma=req.sigma,
        time_pct=req.time_pct,
        location_pct=req.location_pct,
        situation_pct=req.situation_pct,
        k_factor=req.k_factor,
        tx_power_dbm=req.tx_power_dbm,
        tx_gain_dbi=req.tx_gain_dbi,
        rx_gain_dbi=req.rx_gain_dbi,
        cable_loss_db=req.cable_loss_db,
        rx_sensitivity_dbm=req.rx_sensitivity_dbm,
    )


@app.post("/api/coverage")
async def coverage_endpoint(req: CoverageRequest, request: Request):
    return compute_coverage(
        tx_lat=req.tx["lat"],
        tx_lon=req.tx["lon"],
        tx_h_m=req.tx.get("h_m", 30.0),
        rx_h_m=req.rx_h_m,
        f_mhz=req.freq_mhz,
        radius_km=req.radius_km,
        grid_size=req.grid_size,
        profile_step_m=req.profile_step_m,
        terrain_spacing_m=req.terrain_spacing_m,
        elev_grid_n=req.elev_grid_n,
        tx_power_dbm=req.tx_power_dbm,
        tx_gain_dbi=req.tx_gain_dbi,
        rx_gain_dbi=req.rx_gain_dbi,
        cable_loss_db=req.cable_loss_db,
        rx_sensitivity_dbm=req.rx_sensitivity_dbm,
        antenna_az_deg=req.antenna_az_deg,
        antenna_beamwidth_deg=req.antenna_beamwidth_deg,
        polarization=req.polarization,
        climate=req.climate,
        N0=req.N0,
        epsilon=req.epsilon,
        sigma=req.sigma,
        time_pct=req.time_pct,
        location_pct=req.location_pct,
        situation_pct=req.situation_pct,
        pool=request.app.state.pool,
    )


@app.post("/api/coverage-radius")
async def coverage_radius_endpoint(req: CoverageRequest):
    return compute_coverage_radius(
        tx_lat=req.tx["lat"],
        tx_lon=req.tx["lon"],
        tx_h_m=req.tx.get("h_m", 30.0),
        rx_h_m=req.rx_h_m,
        f_mhz=req.freq_mhz,
        tx_power_dbm=req.tx_power_dbm,
        tx_gain_dbi=req.tx_gain_dbi,
        rx_gain_dbi=req.rx_gain_dbi,
        cable_loss_db=req.cable_loss_db,
        rx_sensitivity_dbm=req.rx_sensitivity_dbm,
        antenna_az_deg=req.antenna_az_deg,
        antenna_beamwidth_deg=req.antenna_beamwidth_deg,
        polarization=req.polarization,
        climate=req.climate,
        N0=req.N0,
        epsilon=req.epsilon,
        sigma=req.sigma,
        time_pct=req.time_pct,
        location_pct=req.location_pct,
        situation_pct=req.situation_pct,
    )


app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
```

- [ ] **Step 2: Verify syntax**

Run: `python3 -c "import ast; ast.parse(open('/home/bortre/03-final/nowires/backend/app/main.py').read()); print('OK')"`

Expected: `OK`

- [ ] **Step 3: Run all tests**

Run: `cd /home/bortre/03-final/nowires/backend && python3 -m pytest tests/ -v`

Expected: all 15 tests pass.

- [ ] **Step 4: Verify backend imports cleanly**

Run:
```bash
cd /home/bortre/03-final/nowires/backend && python3 -c "
from app.p2p import analyze_p2p
from app.coverage import compute_coverage, compute_coverage_radius, _itm_worker, _radius_worker
from app.math_kernels import fresnel_profile_analysis, apply_coverage_colors
print('All imports OK')
"
```

Expected: `All imports OK`

- [ ] **Step 5: Commit**

```bash
cd /home/bortre/03-final/nowires
git add backend/app/main.py
git commit -m "feat: lifespan ProcessPoolExecutor for coverage grid endpoint"
```

---

## Self-Review

**Spec coverage:**
- `math_kernels.py` with two JIT functions → Tasks 2, 3 ✓
- `p2p.py` calls `fresnel_profile_analysis` → Task 4 ✓
- `coverage.py` ProcessPoolExecutor for grid → Task 5 ✓
- `coverage.py` `apply_coverage_colors` → Task 5 ✓
- `coverage.py` ProcessPoolExecutor + initializer for radius → Task 5 ✓
- `main.py` lifespan pool → Task 7 ✓
- `requirements.txt` numba → Task 1 ✓

**Placeholder scan:** No TBD, no vague steps. All code is shown in full.

**Type consistency:**
- `fresnel_profile_analysis` defined in Task 2, imported in Task 4 with matching signature ✓
- `apply_coverage_colors` defined in Task 3, imported at module top in Task 5 via `_THRESHOLDS`/`_COLORS` ✓
- `_itm_worker(args)` defined and tested in Tasks 5–6; arg tuple matches construction in `compute_coverage` ✓
- `_radius_worker(args)` defined and tested in Tasks 5–6; arg tuple matches construction in `compute_coverage_radius` ✓
- `compute_coverage` gains `pool` parameter (default `None`) in Task 5; `main.py` passes `pool=request.app.state.pool` in Task 7 ✓
- `_init_radius_pool` and globals `_radius_grid_data`/`_radius_grid_meta` set up in Task 5, tested in Task 6 ✓
