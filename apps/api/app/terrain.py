import logging
import os
import math
import time
import urllib.request
import json
from collections import OrderedDict
from typing import List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

_data_dir = Path(__file__).resolve().parent.parent.parent / "data" / "srtm1"


def _ensure_data_dir():
    _data_dir.mkdir(parents=True, exist_ok=True)


_hgt = None
_hgt_init_done = False


def _get_hgt():
    global _hgt, _hgt_init_done
    if not _hgt_init_done:
        _hgt_init_done = True
        _ensure_data_dir()
        try:
            os.environ["SRTM1_DIR"] = str(_data_dir)
            from srtm import Srtm1HeightMapCollection

            _hgt = Srtm1HeightMapCollection()
            if len(_hgt.height_maps) == 0:
                _hgt = None
        except Exception as e:
            logger.warning("Failed to initialize SRTM: %s", e)
            _hgt = None
    return _hgt


_API_URL = "https://api.opentopodata.org/v1/srtm30m"
_API_CACHE_MAX = 4096
_api_cache: OrderedDict = OrderedDict()
_API_BATCH = 50
_API_RETRY = 3
_API_DELAY = 0.5


def _batch_api_elevations(coords: List[Tuple[float, float]]) -> List[float]:
    all_elevations = [None] * len(coords)
    uncached = []
    uncached_idx = []

    for i, (lat, lon) in enumerate(coords):
        key = (round(lat, 5), round(lon, 5))
        if key in _api_cache:
            all_elevations[i] = _api_cache[key]
        else:
            uncached.append((lat, lon))
            uncached_idx.append(i)

    for start in range(0, len(uncached), _API_BATCH):
        batch = uncached[start : start + _API_BATCH]
        batch_idx = uncached_idx[start : start + _API_BATCH]
        locations = "|".join(f"{lat},{lon}" for lat, lon in batch)
        url = f"{_API_URL}?locations={locations}"

        for attempt in range(_API_RETRY):
            try:
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read())
                for j, r in enumerate(data["results"]):
                    e = r["elevation"]
                    val = float(e) if e is not None else 0.0
                    all_elevations[batch_idx[j]] = val
                    lat, lon = batch[j]
                    _api_cache[(round(lat, 5), round(lon, 5))] = val
                    if len(_api_cache) > _API_CACHE_MAX:
                        _api_cache.popitem(last=False)
                break
            except Exception as e:
                logger.debug("API batch request failed: %s", e)
                if attempt < _API_RETRY - 1:
                    time.sleep(_API_DELAY * (attempt + 1))
                else:
                    for j in range(len(batch)):
                        if all_elevations[batch_idx[j]] is None:
                            all_elevations[batch_idx[j]] = 0.0

        if start + _API_BATCH < len(uncached):
            time.sleep(_API_DELAY)

    filled = [e if e is not None else 0.0 for e in all_elevations]

    for i in range(len(filled)):
        if filled[i] == 0.0:
            left = right = None
            for j in range(i - 1, -1, -1):
                if filled[j] != 0.0:
                    left = filled[j]
                    break
            for j in range(i + 1, len(filled)):
                if filled[j] != 0.0:
                    right = filled[j]
                    break
            if left is not None and right is not None:
                filled[i] = (left + right) / 2.0
            elif left is not None:
                filled[i] = left
            elif right is not None:
                filled[i] = right

    return filled


def get_elevation(lat: float, lon: float) -> float:
    hgt = _get_hgt()
    if hgt is not None:
        try:
            elev = hgt.get_altitude(lat, lon)
            if elev is not None:
                return float(elev)
        except Exception as e:
            logger.debug("SRTM lookup failed for (%s, %s): %s", lat, lon, e)
    key = (round(lat, 5), round(lon, 5))
    if key in _api_cache:
        _api_cache.move_to_end(key)
        return _api_cache[key]
    result = _batch_api_elevations([(lat, lon)])
    return result[0]


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))


def profile(
    lat1: float, lon1: float, lat2: float, lon2: float, step_m: float = 1000.0
) -> List[Tuple[float, float]]:
    dist = haversine_m(lat1, lon1, lat2, lon2)
    if dist < step_m:
        step_m = dist / 3.0 if dist > 0 else 1.0

    n_steps = max(2, int(round(dist / step_m)))

    coords = []
    for i in range(n_steps + 1):
        t = i / n_steps
        lat = lat1 + t * (lat2 - lat1)
        lon = lon1 + t * (lon2 - lon1)
        coords.append((lat, lon))

    hgt = _get_hgt()
    if hgt is not None:
        elevations = []
        for lat, lon in coords:
            try:
                elev = hgt.get_altitude(lat, lon)
                elevations.append(float(elev) if elev is not None else 0.0)
            except Exception as e:
                logger.debug("SRTM elevation failed at (%s, %s): %s", lat, lon, e)
                elevations.append(0.0)
    else:
        elevations = _batch_api_elevations(coords)

    results = []
    for i in range(len(coords)):
        t = i / n_steps
        d = t * dist
        results.append((d, elevations[i]))

    return results
