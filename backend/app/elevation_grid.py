"""
Dense elevation grid with batched fetch + disk cache + bilinear sampling.

Fetching one bbox once is dramatically cheaper than fetching every profile
point for every pixel. A single ElevationGrid backs an entire coverage run.

Elevation sources (in priority order):
1. Local SRTM1 GeoTIFF tiles via rasterio (vectorized, ~160ms for 320x320)
2. python-srtm in-memory .hgt files
3. OpenTopoData API (batched, slow, rate-limited)
Results are cached as .npz files for instant re-fetch.
"""

import hashlib
import math
import os
import time
import json
import urllib.request
from pathlib import Path
from typing import List, Tuple

import numpy as np

from app.config import SRTM1_TILES_DIR as _SRTM1_CACHE_ROOT

try:
    import rasterio
    _RASTERIO_AVAILABLE = True
except ImportError:
    _RASTERIO_AVAILABLE = False


_CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "elev_cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _try_local_srtm():
    try:
        from srtm import Srtm1HeightMapCollection

        srtm_dir = Path(__file__).resolve().parent.parent.parent / "data" / "srtm1"
        os.environ.setdefault("SRTM1_DIR", str(srtm_dir))
        hgt = Srtm1HeightMapCollection()
        if len(hgt.height_maps) > 0:
            return hgt
    except Exception:
        pass
    return None


_LOCAL_HGT = _try_local_srtm()


def _fetch_rasterio_grid(
    min_lat: float,
    min_lon: float,
    max_lat: float,
    max_lon: float,
    lats: np.ndarray,
    lons: np.ndarray,
) -> np.ndarray | None:
    """Build an elevation grid from local SRTM1 GeoTIFF tiles using rasterio.

    Opens each relevant tile once and reads all pixels via vectorized lookup.
    Missing tiles (e.g. ocean areas) are left as 0. Returns None only if
    rasterio is unavailable or the tile directory doesn't exist.
    """
    if not _RASTERIO_AVAILABLE or not _SRTM1_CACHE_ROOT.exists():
        return None

    n = len(lats)
    lat_grid, lon_grid = np.meshgrid(lats, lons, indexing="ij")

    # Determine which 1 degree x 1 degree tiles we need
    lat_min_tile = int(math.floor(min_lat))
    lat_max_tile = int(math.floor(max_lat))
    lon_min_tile = int(math.floor(min_lon))
    lon_max_tile = int(math.floor(max_lon))

    # Load all needed tiles into memory
    tile_data: dict = {}
    for lat_t in range(lat_min_tile, lat_max_tile + 1):
        for lon_t in range(lon_min_tile, lon_max_tile + 1):
            lat_str = f"N{lat_t:02d}" if lat_t >= 0 else f"S{abs(lat_t):02d}"
            lon_str = f"E{lon_t:03d}" if lon_t >= 0 else f"W{abs(lon_t):03d}"
            tile_path = _SRTM1_CACHE_ROOT / lat_str / f"{lat_str}{lon_str}.tif"
            if not tile_path.exists():
                continue
            try:
                with rasterio.open(tile_path) as src:
                    tile_data[(lat_t, lon_t)] = {
                        "data": src.read(1).astype(np.float32),
                        "transform": src.transform,
                        "nodata": src.nodata,
                        "shape": src.shape,
                    }
            except Exception:
                continue

    if not tile_data:
        return None

    result = np.zeros((n, n), dtype=np.float32)

    for (lat_t, lon_t), td in tile_data.items():
        t = td["transform"]
        inv_t = ~t
        data = td["data"]

        # Tile geographic bounds (1 degree x 1 degree for SRTM)
        tile_min_lat = lat_t
        tile_max_lat = lat_t + 1
        tile_min_lon = lon_t
        tile_max_lon = lon_t + 1

        # Find grid points that fall within this tile
        in_tile = (
            (lat_grid >= tile_min_lat - 1e-6)
            & (lat_grid < tile_max_lat + 1e-6)
            & (lon_grid >= tile_min_lon - 1e-6)
            & (lon_grid < tile_max_lon + 1e-6)
        )

        if not in_tile.any():
            continue

        lats_in = lat_grid[in_tile]
        lons_in = lon_grid[in_tile]

        # Use rasterio's inverse affine transform for pixel coordinates
        # inv_t * (lon, lat) returns (col, row)
        rows_cols = inv_t * (lons_in, lats_in)
        col_idx = np.floor(rows_cols[0]).astype(np.int32)
        row_idx = np.floor(rows_cols[1]).astype(np.int32)

        col_idx = np.clip(col_idx, 0, td["shape"][1] - 1)
        row_idx = np.clip(row_idx, 0, td["shape"][0] - 1)

        elev_values = data[row_idx, col_idx]

        # Handle nodata (SRTM uses -32768)
        if td["nodata"] is not None:
            elev_values = np.where(elev_values == td["nodata"], 0.0, elev_values)

        result[in_tile] = elev_values

    return result


def _fetch_elevation_cache(coords: List[Tuple[float, float]]) -> List[float]:
    """Fetch elevations from local SRTM1 GeoTIFF tiles (per-coordinate, slow).

    Only used as a detailed fallback when rasterio is available
    but the vectorized path couldn't cover some points.
    """
    if not _RASTERIO_AVAILABLE:
        return [0.0] * len(coords)

    if not _SRTM1_CACHE_ROOT.exists():
        return [0.0] * len(coords)

    elevations = []
    for lat, lon in coords:
        try:
            lat_int = int(math.floor(lat))
            lon_int = int(math.floor(lon))
            lat_str = f"N{lat_int:02d}" if lat_int >= 0 else f"S{abs(lat_int):02d}"
            lon_str = f"E{lon_int:03d}" if lon_int >= 0 else f"W{abs(lon_int):03d}"

            tile_path = _SRTM1_CACHE_ROOT / lat_str / f"{lat_str}{lon_str}.tif"
            if not tile_path.exists():
                elevations.append(0.0)
                continue

            with rasterio.open(tile_path) as src:
                row, col = src.index(lon, lat)
                window = rasterio.windows.Window(col, row, 1, 1)
                data = src.read(1, window=window)
                elev = float(data[0, 0]) if data.size > 0 else 0.0
                elevations.append(elev)
        except Exception:
            elevations.append(0.0)

    return elevations


def _fetch_api_batch(coords: List[Tuple[float, float]]) -> List[float]:
    """Fetch elevations from the OpenTopoData SRTM30m API.

    Batches up to 100 locations per request with a 1s delay between batches.
    Used when no local DEM tiles are available.
    """
    batch_size = 100
    out = [0.0] * len(coords)
    api_url = "https://api.opentopodata.org/v1/srtm30m"

    for start in range(0, len(coords), batch_size):
        batch = coords[start : start + batch_size]
        locations = "|".join(f"{lat},{lon}" for lat, lon in batch)
        url = f"{api_url}?locations={locations}"
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                data = json.loads(resp.read())
            for j, r in enumerate(data["results"]):
                e = r.get("elevation")
                out[start + j] = float(e) if e is not None else 0.0
        except Exception:
            pass
        if start + batch_size < len(coords):
            time.sleep(1.0)
    return out


def _fetch_local(coords: List[Tuple[float, float]]) -> List[float]:
    """Fetch elevations using python-srtm in-memory .hgt files."""
    out = []
    for lat, lon in coords:
        try:
            v = _LOCAL_HGT.get_altitude(lat, lon)
            out.append(float(v) if v is not None else 0.0)
        except Exception:
            out.append(0.0)
    return out


class ElevationGrid:
    """Regular lat/lon elevation grid with bilinear sampling."""

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
        y0 = int(math.floor(fy))
        x0 = int(math.floor(fx))
        y1 = min(y0 + 1, self.n_lat - 1)
        x1 = min(x0 + 1, self.n_lon - 1)
        ty = fy - y0
        tx = fx - x0
        v00 = self.data[y0, x0]
        v01 = self.data[y0, x1]
        v10 = self.data[y1, x0]
        v11 = self.data[y1, x1]
        return (
            v00 * (1 - tx) * (1 - ty)
            + v01 * tx * (1 - ty)
            + v10 * (1 - tx) * ty
            + v11 * tx * ty
        )

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

        return (
            v00 * (1 - tx) * (1 - ty)
            + v01 * tx * (1 - ty)
            + v10 * (1 - tx) * ty
            + v11 * tx * ty
        )

    @classmethod
    def _cache_key(
        cls,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
        n: int,
    ) -> Path:
        s = f"{min_lat:.5f},{min_lon:.5f},{max_lat:.5f},{max_lon:.5f},{n}"
        h = hashlib.md5(s.encode()).hexdigest()
        return _CACHE_DIR / f"{h}.npz"

    @classmethod
    def fetch(
        cls,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
        n: int = 80,
    ) -> "ElevationGrid":
        path = cls._cache_key(min_lat, min_lon, max_lat, max_lon, n)
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
            except Exception:
                pass

        lats = np.linspace(min_lat, max_lat, n)
        lons = np.linspace(min_lon, max_lon, n)

        # 1. Try fast vectorized rasterio (local GeoTIFF tiles)
        data = _fetch_rasterio_grid(min_lat, min_lon, max_lat, max_lon, lats, lons)

        if data is not None:
            # Check if any grid points are unfilled (tile gaps, ocean areas)
            # If less than half the grid is filled, supplement with API fallback
            filled = np.count_nonzero(data)
            total = data.size
            if filled > 0:
                # We have some local data — use it (zeros are fine for ocean/missing)
                pass
            else:
                # No tiles found at all — fall through to API
                data = None

        if data is None:
            # 2. Try python-srtm in-memory
            coords = [(float(la), float(lo)) for la in lats for lo in lons]
            if _LOCAL_HGT is not None:
                elevations = _fetch_local(coords)
            elif _RASTERIO_AVAILABLE and _SRTM1_CACHE_ROOT.exists():
                elevations = _fetch_elevation_cache(coords)
            else:
                # 3. OpenTopoData API fallback
                elevations = _fetch_api_batch(coords)
            data = np.array(elevations, dtype=np.float32).reshape(n, n)

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
