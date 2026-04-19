import asyncio
import logging
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

_backend_dir = str(Path(__file__).resolve().parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from app.coverage import compute_coverage  # noqa: E402
from app.coverage_radius import compute_coverage_radius  # noqa: E402
from app.p2p import analyze_p2p  # noqa: E402

COVERAGE_TIMEOUT_S = 120


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 30, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._timestamps: dict[str, list[float]] = {}
        self._last_cleanup = time.time()
        self._cleanup_interval = 300

    async def dispatch(self, request: Request, call_next):
        client = request.client.host if request.client else "unknown"

        now = time.time()
        if now - self._last_cleanup > self._cleanup_interval:
            self._timestamps = {
                c: ts
                for c, ts in self._timestamps.items()
                if any(now - t < self.window_seconds for t in ts)
            }
            self._last_cleanup = now

        if client not in self._timestamps:
            self._timestamps[client] = []
        self._timestamps[client] = [
            t for t in self._timestamps[client] if now - t < self.window_seconds
        ]
        if len(self._timestamps[client]) >= self.max_requests:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
            )
        self._timestamps[client].append(now)
        return await call_next(request)


def _warmup_numba():
    """Pre-compile Numba JIT functions to avoid first-request latency."""
    try:
        import numpy as np

        from app.math_kernels import apply_coverage_colors, fresnel_profile_analysis

        distances = np.zeros(3, dtype=np.float64)
        elevations = np.zeros(3, dtype=np.float64)
        fresnel_profile_analysis(distances, elevations, 10.0, 10.0, 1000.0, 1.0, 4.0 / 3.0)

        prx_grid = np.zeros((2, 2), dtype=np.float32)
        thresholds = np.array([-60.0], dtype=np.float64)
        colors = np.array([[0, 110, 40, 210]], dtype=np.uint8)
        rgba_out = np.zeros((2, 2, 4), dtype=np.uint8)
        apply_coverage_colors(prx_grid, thresholds, colors, rgba_out)
    except Exception as e:
        logger.warning("Numba warmup failed: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.config import _ensure_dirs

    _ensure_dirs()
    _warmup_numba()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware, max_requests=30, window_seconds=60)


class Coordinates(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    h_m: float = Field(default=30.0, gt=0)


class P2PRequest(BaseModel):
    tx: Coordinates
    rx: Coordinates
    freq_mhz: float = Field(default=300.0, gt=0, le=40000)
    polarization: int = Field(default=0, ge=0, le=1)
    climate: int = Field(default=1, ge=0, le=7)
    N0: float = Field(default=301.0, gt=0)
    epsilon: float = Field(default=15.0, gt=0)
    sigma: float = Field(default=0.005, gt=0)
    time_pct: float = Field(default=50.0, gt=0, le=100)
    location_pct: float = Field(default=50.0, gt=0, le=100)
    situation_pct: float = Field(default=50.0, gt=0, le=100)
    k_factor: float = Field(default=4.0 / 3.0, gt=0)
    tx_power_dbm: float = Field(default=43.0)
    tx_gain_dbi: float = Field(default=8.0)
    rx_gain_dbi: float = Field(default=2.0)
    cable_loss_db: float = Field(default=2.0, ge=0)
    rx_sensitivity_dbm: float = Field(default=-100.0)


class CoverageRequest(BaseModel):
    tx: Coordinates
    rx_h_m: float = Field(default=10.0, gt=0)
    freq_mhz: float = Field(default=300.0, gt=0, le=40000)
    radius_km: float = Field(default=50.0, gt=0, le=500)
    grid_size: int = Field(default=192, ge=16, le=512)
    profile_step_m: float = Field(default=250.0, gt=0)
    terrain_spacing_m: float = Field(default=300.0, gt=0)
    elev_grid_n: Optional[int] = None
    elevation_source: str = Field(default="glo30")
    polarization: int = Field(default=0, ge=0, le=1)
    climate: int = Field(default=1, ge=0, le=7)
    N0: float = Field(default=301.0, gt=0)
    epsilon: float = Field(default=15.0, gt=0)
    sigma: float = Field(default=0.005, gt=0)
    time_pct: float = Field(default=50.0, gt=0, le=100)
    location_pct: float = Field(default=50.0, gt=0, le=100)
    situation_pct: float = Field(default=50.0, gt=0, le=100)
    tx_power_dbm: float = Field(default=43.0)
    tx_gain_dbi: float = Field(default=8.0)
    rx_gain_dbi: float = Field(default=2.0)
    cable_loss_db: float = Field(default=2.0, ge=0)
    rx_sensitivity_dbm: float = Field(default=-100.0)
    antenna_az_deg: Optional[float] = None
    antenna_beamwidth_deg: float = Field(default=360.0, gt=0, le=360)


@app.post("/api/p2p")
async def p2p_endpoint(req: P2PRequest):
    return analyze_p2p(
        tx_lat=req.tx.lat,
        tx_lon=req.tx.lon,
        tx_h_m=req.tx.h_m,
        rx_lat=req.rx.lat,
        rx_lon=req.rx.lon,
        rx_h_m=req.rx.h_m,
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
async def coverage_endpoint(req: CoverageRequest):
    try:
        result = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None,
                lambda: compute_coverage(
                    tx_lat=req.tx.lat,
                    tx_lon=req.tx.lon,
                    tx_h_m=req.tx.h_m,
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
                    terrain_spacing_m=req.terrain_spacing_m,
                    elev_grid_n=req.elev_grid_n,
                    elevation_source=req.elevation_source,
                ),
            ),
            timeout=COVERAGE_TIMEOUT_S,
        )
        return result
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Coverage computation timed out")
    except Exception as e:
        logger.exception("Coverage computation failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/coverage-radius")
async def coverage_radius_endpoint(req: CoverageRequest):
    try:
        result = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None,
                lambda: compute_coverage_radius(
                    tx_lat=req.tx.lat,
                    tx_lon=req.tx.lon,
                    tx_h_m=req.tx.h_m,
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
                    terrain_spacing_m=req.terrain_spacing_m,
                    elev_grid_n=req.elev_grid_n,
                    elevation_source=req.elevation_source,
                ),
            ),
            timeout=COVERAGE_TIMEOUT_S,
        )
        return result
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Coverage radius computation timed out")
    except Exception as e:
        logger.exception("Coverage radius computation failed")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
