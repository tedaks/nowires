"""
Elevation fetching from local DEM tiles, python-srtm, or OpenTopoData API.

Priority: GLO30 rasterio → SRTM1 rasterio → python-srtm → OpenTopoData API
"""

import json
import math
import os
import time
import urllib.request
from pathlib import Path
from typing import List, Tuple

import numpy as np

from app.config import GLO30_TILES_DIR as _GLO30_CACHE_ROOT
from app.config import SRTM1_TILES_DIR as _SRTM1_CACHE_ROOT

try:
    import rasterio

    _RASTERIO_AVAILABLE = True
except ImportError:
    _RASTERIO_AVAILABLE = False

import logging

logger = logging.getLogger(__name__)

_RASTERIO_SOURCES = {
    "glo30": _GLO30_CACHE_ROOT,
    "srtm1": _SRTM1_CACHE_ROOT,
}


def _srtm1_tile_path(lat: int, lon: int) -> Path:
    lat_str = f"N{lat:02d}" if lat >= 0 else f"S{abs(lat):02d}"
    lon_str = f"E{lon:03d}" if lon >= 0 else f"W{abs(lon):03d}"
    return _SRTM1_CACHE_ROOT / lat_str / f"{lat_str}{lon_str}.tif"


def _glo30_tile_path(lat: int, lon: int) -> Path:
    lat_str = f"N{lat:02d}" if lat >= 0 else f"S{abs(lat):02d}"
    lon_str = f"E{lon:03d}" if lon >= 0 else f"W{abs(lon):03d}"
    return _GLO30_CACHE_ROOT / f"Copernicus_DSM_COG_10_{lat_str}_00_{lon_str}_00_DEM.tif"


def _read_tile(path: Path) -> dict | None:
    try:
        with rasterio.open(path) as src:
            return {
                "data": src.read(1).astype(np.float32),
                "transform": src.transform,
                "nodata": src.nodata,
                "shape": src.shape,
            }
    except Exception as e:
        logger.debug("Failed to read tile %s: %s", path, e)
        return None


def _apply_tile(
    lat_grid: np.ndarray,
    lon_grid: np.ndarray,
    lat_t: int,
    lon_t: int,
    tile_data: dict,
    result: np.ndarray,
) -> None:
    tile_min_lat, tile_max_lat = lat_t, lat_t + 1
    tile_min_lon, tile_max_lon = lon_t, lon_t + 1
    in_tile = (
        (lat_grid >= tile_min_lat - 1e-6)
        & (lat_grid < tile_max_lat + 1e-6)
        & (lon_grid >= tile_min_lon - 1e-6)
        & (lon_grid < tile_max_lon + 1e-6)
    )
    if not in_tile.any():
        return
    lats_in = lat_grid[in_tile]
    lons_in = lon_grid[in_tile]
    inv_t = ~tile_data["transform"]
    rows_cols = inv_t * (lons_in, lats_in)
    col_idx = np.clip(np.floor(rows_cols[0]).astype(np.int32), 0, tile_data["shape"][1] - 1)
    row_idx = np.clip(np.floor(rows_cols[1]).astype(np.int32), 0, tile_data["shape"][0] - 1)
    elev_values = tile_data["data"][row_idx, col_idx]
    if tile_data["nodata"] is not None:
        elev_values = np.where(elev_values == tile_data["nodata"], np.nan, elev_values)
    result[in_tile] = elev_values


def _fetch_rasterio_grid(
    min_lat: float,
    min_lon: float,
    max_lat: float,
    max_lon: float,
    lats: np.ndarray,
    lons: np.ndarray,
    tile_path_fn: callable,
) -> np.ndarray | None:
    if not _RASTERIO_AVAILABLE:
        return None
    cache_root = tile_path_fn(0, 0).parent
    if not cache_root.exists():
        return None
    n = len(lats)
    lat_grid, lon_grid = np.meshgrid(lats, lons, indexing="ij")
    tile_data: dict = {}
    for lat_t in range(int(math.floor(min_lat)), int(math.floor(max_lat)) + 1):
        for lon_t in range(int(math.floor(min_lon)), int(math.floor(max_lon)) + 1):
            path = tile_path_fn(lat_t, lon_t)
            if not path.exists():
                continue
            td = _read_tile(path)
            if td:
                tile_data[(lat_t, lon_t)] = td
    if not tile_data:
        return None
    result = np.full((n, n), np.nan, dtype=np.float32)
    for (lat_t, lon_t), td in tile_data.items():
        _apply_tile(lat_grid, lon_grid, lat_t, lon_t, td, result)
    return result


def fetch_srtm1_grid(
    min_lat: float,
    min_lon: float,
    max_lat: float,
    max_lon: float,
    lats: np.ndarray,
    lons: np.ndarray,
) -> np.ndarray | None:
    return _fetch_rasterio_grid(min_lat, min_lon, max_lat, max_lon, lats, lons, _srtm1_tile_path)


def fetch_glo30_grid(
    min_lat: float,
    min_lon: float,
    max_lat: float,
    max_lon: float,
    lats: np.ndarray,
    lons: np.ndarray,
) -> np.ndarray | None:
    return _fetch_rasterio_grid(min_lat, min_lon, max_lat, max_lon, lats, lons, _glo30_tile_path)


def _try_local_srtm():
    try:
        from srtm import Srtm1HeightMapCollection

        srtm_dir = Path(__file__).resolve().parent.parent.parent / "data" / "srtm1"
        os.environ.setdefault("SRTM1_DIR", str(srtm_dir))
        hgt = Srtm1HeightMapCollection()
        if len(hgt.height_maps) > 0:
            return hgt
    except Exception as e:
        logger.debug("Failed to initialize local SRTM: %s", e)
    return None


_LOCAL_HGT = None
_local_init_done = False


def _get_local_hgt():
    global _LOCAL_HGT, _local_init_done
    if not _local_init_done:
        _local_init_done = True
        _LOCAL_HGT = _try_local_srtm()
    return _LOCAL_HGT


def fetch_rasterio_cache(coords: List[Tuple[float, float]]) -> List[float]:
    if not _RASTERIO_AVAILABLE or not _SRTM1_CACHE_ROOT.exists():
        return [float("nan")] * len(coords)
    elevations = []
    for lat, lon in coords:
        path = _srtm1_tile_path(int(math.floor(lat)), int(math.floor(lon)))
        if not path.exists():
            elevations.append(float("nan"))
            continue
        try:
            with rasterio.open(path) as src:
                row, col = src.index(lon, lat)
                window = rasterio.windows.Window(col, row, 1, 1)
                data = src.read(1, window=window)
                if data.size > 0:
                    v = float(data[0, 0])
                    if src.nodata is not None and v == src.nodata:
                        elevations.append(float("nan"))
                    else:
                        elevations.append(v)
                else:
                    elevations.append(float("nan"))
        except Exception:
            elevations.append(float("nan"))
    return elevations


def fetch_api_batch(coords: List[Tuple[float, float]]) -> List[float]:
    batch_size = 100
    out = [float("nan")] * len(coords)
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
                out[start + j] = float(e) if e is not None else float("nan")
        except Exception as e:
            logger.warning("API batch request failed for %d coords: %s", len(batch), e)
        if start + batch_size < len(coords):
            time.sleep(1.0)
    return out


def fetch_local_hgt(coords: List[Tuple[float, float]]) -> List[float]:
    local_hgt = _get_local_hgt()
    out = []
    for lat, lon in coords:
        try:
            v = local_hgt.get_altitude(lat, lon)
            out.append(float(v) if v is not None else float("nan"))
        except Exception:
            out.append(float("nan"))
    return out
