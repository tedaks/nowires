"""
Dense elevation grid with batched fetch + disk cache + bilinear sampling.

Fetching one bbox once is dramatically cheaper than fetching every profile
point for every pixel. A single ElevationGrid backs an entire coverage run.

Elevation sources (in priority order):
1. GLO30 via rasterio (vectorized, ~160ms for 320x320)
2. SRTM1 via rasterio
3. python-srtm in-memory .hgt files
4. OpenTopoData API (batched, slow, rate-limited)
Results are cached as .npz files for instant re-fetch.
"""

import hashlib
import logging
from pathlib import Path

import numpy as np

from app.elevation_fetch import (
    fetch_api_batch,
    fetch_glo30_grid,
    fetch_local_hgt,
    fetch_srtm1_grid,
)

logger = logging.getLogger(__name__)

_CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "elev_cache"


def _ensure_cache_dir():
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)


class ElevationGrid:
    def __init__(
        self,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
        data: np.ndarray,
    ):
        self.min_lat = min_lat
        self.min_lon = min_lon
        self.max_lat = max_lat
        self.max_lon = max_lon
        self.data = data
        self.n_lat, self.n_lon = data.shape
        self.d_lat = (max_lat - min_lat) / (self.n_lat - 1)
        self.d_lon = (max_lon - min_lon) / (self.n_lon - 1)

    def sample(self, lat: float, lon: float) -> float:
        fy = (lat - self.min_lat) / self.d_lat
        fx = (lon - self.min_lon) / self.d_lon
        if fy < 0 or fx < 0 or fy > self.n_lat - 1 or fx > self.n_lon - 1:
            return 0.0
        y0 = int(lat // self.d_lat)
        x0 = int(lon // self.d_lon)
        y1 = min(y0 + 1, self.n_lat - 1)
        x1 = min(x0 + 1, self.n_lon - 1)
        ty = fy - y0
        tx = fx - x0
        v00 = self.data[y0, x0]
        v01 = self.data[y0, x1]
        v10 = self.data[y1, x0]
        v11 = self.data[y1, x1]
        return v00 * (1 - tx) * (1 - ty) + v01 * tx * (1 - ty) + v10 * (1 - tx) * ty + v11 * tx * ty

    def sample_line(
        self, lat1: float, lon1: float, lat2: float, lon2: float, n_points: int
    ) -> np.ndarray:
        ts = np.linspace(0.0, 1.0, n_points)
        lats = lat1 + ts * (lat2 - lat1)
        lons = lon1 + ts * (lon2 - lon1)
        fy = (lats - self.min_lat) / self.d_lat
        fx = (lons - self.min_lon) / self.d_lon
        fy = np.clip(fy, 0, self.n_lat - 1 - 1e-9)
        fx = np.clip(fx, 0, self.n_lon - 1 - 1e-9)
        y0 = np.floor(fy).astype(np.int32)
        x0 = np.floor(fx).astype(np.int32)
        y1 = np.clip(y0 + 1, 0, self.n_lat - 1)
        x1 = np.clip(x0 + 1, 0, self.n_lon - 1)
        ty = (fy - y0).astype(np.float32)
        tx = (fx - x0).astype(np.float32)
        v00 = self.data[y0, x0]
        v01 = self.data[y0, x1]
        v10 = self.data[y1, x0]
        v11 = self.data[y1, x1]
        return v00 * (1 - tx) * (1 - ty) + v01 * tx * (1 - ty) + v10 * (1 - tx) * ty + v11 * tx * ty

    @classmethod
    def _cache_key(
        cls,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
        n: int,
        source: str,
    ) -> Path:
        s = f"{source},{min_lat:.5f},{min_lon:.5f},{max_lat:.5f},{max_lon:.5f},{n}"
        h = hashlib.sha256(s.encode()).hexdigest()
        return _CACHE_DIR / f"{h}.npz"

    @classmethod
    def fetch(
        cls,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
        n: int = 80,
        source: str = "glo30",
    ) -> "ElevationGrid":
        _ensure_cache_dir()
        path = cls._cache_key(min_lat, min_lon, max_lat, max_lon, n, source)
        if path.exists():
            try:
                z = np.load(path)
                return cls(
                    min_lat=float(z["min_lat"]),
                    min_lon=float(z["min_lon"]),
                    max_lat=float(z["max_lat"]),
                    max_lon=float(z["max_lon"]),
                    data=z["data"].astype(np.float32),
                )
            except Exception as e:
                logger.debug("Failed to load cache %s: %s", path, e)

        lats = np.linspace(min_lat, max_lat, n)
        lons = np.linspace(min_lon, max_lon, n)

        data = _fetch_grid(min_lat, min_lon, max_lat, max_lon, lats, lons, source)

        try:
            np.savez_compressed(
                path,
                min_lat=min_lat,
                min_lon=min_lon,
                max_lat=max_lat,
                max_lon=max_lon,
                data=data,
            )
        except Exception:
            pass

        return cls(min_lat, min_lon, max_lat, max_lon, data)


def _fetch_grid(
    min_lat: float,
    min_lon: float,
    max_lat: float,
    max_lon: float,
    lats: np.ndarray,
    lons: np.ndarray,
    source: str,
) -> np.ndarray:
    coords = [(float(la), float(lo)) for la in lats for lo in lons]

    if source == "glo30":
        data = fetch_glo30_grid(min_lat, min_lon, max_lat, max_lon, lats, lons)
        if data is not None and np.count_nonzero(data) > 0:
            return data
        data = fetch_srtm1_grid(min_lat, min_lon, max_lat, max_lon, lats, lons)
        if data is not None and np.count_nonzero(data) > 0:
            return data
        elevations = fetch_local_hgt(coords)
        if any(e != 0.0 for e in elevations):
            return np.array(elevations, dtype=np.float32).reshape(len(lats), len(lons))
        return np.array(fetch_api_batch(coords), dtype=np.float32).reshape(len(lats), len(lons))

    elif source == "srtm1":
        data = fetch_srtm1_grid(min_lat, min_lon, max_lat, max_lon, lats, lons)
        if data is not None and np.count_nonzero(data) > 0:
            return data
        elevations = fetch_local_hgt(coords)
        if any(e != 0.0 for e in elevations):
            return np.array(elevations, dtype=np.float32).reshape(len(lats), len(lons))
        return np.array(fetch_api_batch(coords), dtype=np.float32).reshape(len(lats), len(lons))

    else:
        return np.array(fetch_api_batch(coords), dtype=np.float32).reshape(len(lats), len(lons))
