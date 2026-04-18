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


def _warmup_numba():
    """Pre-compile Numba JIT functions to avoid first-request latency."""
    try:
        import numpy as np
        from app.math_kernels import fresnel_profile_analysis, apply_coverage_colors

        distances = np.zeros(3, dtype=np.float64)
        elevations = np.zeros(3, dtype=np.float64)
        fresnel_profile_analysis(distances, elevations, 10.0, 10.0, 1000.0, 1.0, 4.0 / 3.0)

        prx_grid = np.zeros((2, 2), dtype=np.float32)
        thresholds = np.array([-60.0], dtype=np.float64)
        colors = np.array([[0, 110, 40, 210]], dtype=np.uint8)
        rgba_out = np.zeros((2, 2, 4), dtype=np.uint8)
        apply_coverage_colors(prx_grid, thresholds, colors, rgba_out)
    except Exception:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    _warmup_numba()
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
    grid_size: int = 192
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
