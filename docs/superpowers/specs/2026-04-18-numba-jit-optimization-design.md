# nowires Numba JIT Optimization Design

**Date:** 2026-04-18
**Scope:** `/home/bortre/03-final/nowires` only — the `itm` package is not modified.

---

## Goal

Reduce latency on coverage grid and coverage radius requests by (a) eliminating GIL contention in the coverage computation via `ProcessPoolExecutor`, and (b) JIT-compiling the numeric profile-analysis and color-mapping loops with Numba.

Expected gains:
- Coverage grid: ~40–70% wall-time reduction (multiprocessing bypasses GIL on pure-Python ITM calls)
- Coverage radius: similar, turning 7200 sequential ITM calls into 360 parallel tasks
- P2P and color mapping: ~5–15% from Numba (secondary)

**Constraint:** The ITM prediction kernel (`itm.predict_p2p`) is pure Python and cannot be Numba JIT-compiled from the application layer. The ceiling on Numba gains within nowires is modest; ProcessPoolExecutor is the primary win.

---

## Architecture

Three targeted changes inside `backend/app/`, plus one dependency addition. No other files are modified.

```
backend/app/
├── math_kernels.py        # NEW — Numba JIT functions
├── p2p.py                 # MODIFIED — call fresnel_profile_analysis()
├── coverage.py            # MODIFIED — ProcessPoolExecutor + apply_coverage_colors()
└── main.py                # MODIFIED — lifespan: create/destroy persistent pool
backend/requirements.txt   # MODIFIED — add numba
```

`itm_bridge.py`, `elevation_grid.py`, `terrain.py`, `config.py`, `frontend/` are unchanged.

---

## Component 1: `math_kernels.py` (Numba JIT)

New file. Two JIT-compiled functions operating on plain NumPy arrays.

### `fresnel_profile_analysis`

```python
@numba.jit(nopython=True, cache=True)
def fresnel_profile_analysis(
    prof_dists,      # float64[N] — distance from TX to each profile point (m)
    elevations,      # float64[N] — terrain elevation at each point (m)
    tx_elev,         # float64 — terrain elevation at TX (m)
    rx_elev,         # float64 — terrain elevation at RX (m)
    tx_height_m,     # float64 — antenna height above ground at TX (m)
    rx_height_m,     # float64 — antenna height above ground at RX (m)
    total_dist_m,    # float64 — total path distance (m)
    wavelength_m,    # float64 — signal wavelength (m)
    k_factor,        # float64 — effective Earth radius factor (typically 4/3)
) -> tuple:
    # Returns: (fresnel_radii, earth_bulge, los_height, fresnel_blocked, fresnel60_blocked)
    # All arrays shape [N], dtype float64 or bool
```

Replaces the `for i, (dist_m, elev) in enumerate(...)` loop in `p2p.py` (~lines 89–130). The caller unpacks the returned tuple and uses it directly for chart data and flag computation.

### `apply_coverage_colors`

```python
@numba.jit(nopython=True, parallel=True, cache=True)
def apply_coverage_colors(
    prx_flat,        # float32[M] — received power per valid pixel (dBm)
    thresholds,      # float64[K] — sorted thresholds (dBm), descending
    rgba_out,        # uint8[M, 4] — pre-allocated output
    colors,          # uint8[K+1, 4] — RGBA color per threshold bucket
) -> None:
    # Fills rgba_out in-place using numba.prange for parallel pixel assignment
```

Replaces the per-pixel color loop in `coverage.py`. `parallel=True` enables `prange` across the pixel dimension.

---

## Component 2: Persistent Process Pool (`main.py`)

A `ProcessPoolExecutor` is created once at app startup and destroyed at shutdown using FastAPI's lifespan context manager. Pool size defaults to `os.cpu_count()`.

```python
from contextlib import asynccontextmanager
from concurrent.futures import ProcessPoolExecutor
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = ProcessPoolExecutor(max_workers=os.cpu_count())
    yield
    app.state.pool.shutdown(wait=True)

app = FastAPI(lifespan=lifespan)
```

The pool is passed to `compute_coverage()` as a parameter. This avoids re-spawning processes per coverage grid request (which would negate the gain).

`compute_coverage_radius()` uses a **separate, per-request pool** with an initializer (see Component 4). It does not use the persistent pool.

---

## Component 3: ProcessPoolExecutor — Coverage Grid (`coverage.py`)

### Worker function

```python
def _itm_worker(args):
    # Top-level function (required for pickling)
    # args: (i, j, pfl, itm_params_dict)
    # Returns: (i, j, loss_db, mode, warnings)
```

Must be defined at module top level (not nested) so Python's pickle can find it by name.

### New dispatch flow

```
Main process:
  1. Build ElevationGrid (unchanged)
  2. Compute distance/bearing masks (unchanged, NumPy)
  3. For each valid (i, j): call grid.sample_line() → build PFL list
     (NumPy, stays in main process — no ElevationGrid pickling)
  4. Submit (i, j, pfl, itm_params) to pool via executor.map()
  5. Collect (i, j, loss_db, ...) results
  6. Build Prx grid array
  7. Call apply_coverage_colors() → RGBA PNG

Workers (each in own process):
  - Receive plain data: pfl list + itm_params dict
  - Call itm_p2p_loss() → return scalar results
  - No imports of ElevationGrid or FastAPI state
```

Each worker imports `itm_bridge` on first use (module-level import in worker process). Pool processes are reused across requests — import cost is paid once per worker process lifetime.

---

## Component 4: ProcessPoolExecutor — Coverage Radius (`coverage.py`)

### Worker function

```python
def _radius_worker(args):
    # args: (bearing, tx_lat, tx_lon, tx_h_m,
    #        grid_data,    # raw float32 numpy array
    #        grid_meta,    # dict: min_lat, max_lat, min_lon, max_lon, shape
    #        itm_params, link_params, sensitivity_dbm)
    # Reconstructs a thin sampler from grid_data + grid_meta
    # Runs 20-iteration binary search for this bearing
    # Returns: (bearing, radius_m)
```

The elevation grid is shared with workers via a pool initializer — the raw `grid.data` NumPy array is sent once to each worker process at pool creation time (stored as a module-level global), not re-pickled per task. Each `_radius_worker` task then receives only scalars (bearing, tx coords, itm_params dict). This avoids the 400KB × 360 = 144MB IPC overhead that would occur if the array were passed per-task.

The pool initializer signature: `_init_radius_pool(grid_data, grid_meta)` — sets module-level globals `_GRID_DATA` and `_GRID_META` in each worker process. The pool is created with `initializer=_init_radius_pool, initargs=(grid.data, grid_meta)` at the start of each `compute_coverage_radius()` call (a short-lived pool, not the shared persistent pool, since initargs vary per request).

### New dispatch flow

```
Main process:
  1. Build ElevationGrid (unchanged)
  2. Extract grid_data = grid.data (numpy array)
  3. Build grid_meta dict (scalars only)
  4. Submit 360 _radius_worker tasks to pool
  5. Collect (bearing, radius_m) results
  6. Assemble radii array + compute statistics
```

360 tasks × 20 ITM calls each = 7200 ITM calls, now fully parallel across `cpu_count` processes.

---

## Data Flow Summary

```
Request → main.py (pool from app.state)
         ↓
    coverage.py
         ↓ pre-extract PFLs (main process, NumPy)
         ↓ submit to ProcessPoolExecutor
         ↓
    _itm_worker × N (worker processes)
         ↓ itm_p2p_loss() per pixel
         ↓ return (i, j, loss_db)
         ↓
    coverage.py (main process)
         ↓ build Prx grid
         ↓ apply_coverage_colors() [Numba, parallel]
         ↓ encode PNG
         ↓
    Response
```

---

## Error Handling

- Worker exceptions propagate via `Future.exception()` — `executor.map()` re-raises them in the main process. No silent failure.
- If a single pixel's ITM call raises, the exception surfaces on the next `results` iteration; the request returns HTTP 500 with the traceback (existing FastAPI behavior).
- Pool shutdown is always called in the lifespan `finally` path — no leaked processes on app crash.

---

## Testing

No existing test suite. Verification approach:

1. **Numerical correctness** — run a fixed P2P request and coverage request before and after, assert `loss_db` values match to within 0.01 dB (ProcessPoolExecutor and Numba must not change results).
2. **Numba compilation check** — import `math_kernels` and call each function with small test arrays; assert no `numba.core.errors.TypingError`.
3. **Pool lifecycle check** — start the FastAPI app, make one coverage request, assert response is 200 and pool is still alive.

---

## Out of Scope

- Modifying the `itm` package source
- Numba JIT on `elevation_grid.sample_line()` (already NumPy-vectorized, not a bottleneck)
- LRU caching on ITM calls (Approach C — deferred)
- Any frontend changes
