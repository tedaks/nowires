from pathlib import Path
from dotenv import load_dotenv
import os

# Load .env from project root
_project_root = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(_project_root / ".env")

BASE_DIR = _project_root
DATA_DIR = BASE_DIR / "data"

SRTM1_DIR = DATA_DIR / "srtm1"
SRTM1_DIR.mkdir(parents=True, exist_ok=True)

# Custom GeoTIFF tile directory for elevation data.
# Set SRTM1_TILES_DIR in .env to override the default path.
# Default: ~/.cache/elevation/SRTM1/cache
_SRTM1_TILES_DIR_ENV = os.environ.get("SRTM1_TILES_DIR", "").strip()
SRTM1_TILES_DIR = Path(_SRTM1_TILES_DIR_ENV) if _SRTM1_TILES_DIR_ENV else Path.home() / ".cache" / "elevation" / "SRTM1" / "cache"

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
