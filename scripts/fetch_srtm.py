#!/usr/bin/env python3
"""
SRTM tile fetcher for the Philippines.

NOTE: The USGS SRTM1 download requires a free NASA Earthdata account.
Register at https://urs.earthdata.nasa.gov/users/new then set credentials:
    export EARTHDATA_USER=your_username
    export EARTHDATA_PASS=your_password
before running this script.

If no credentials are set, the app falls back to the OpenTopoData SRTM 30m API
(https://api.opentopodata.org/v1/srtm30m) which requires no authentication
and covers the full Philippines. The API approach is used by default.
"""

import os
import math
import zipfile
import urllib.request
import urllib.parse
import netrc
from pathlib import Path

SRTM1_DIR = Path(__file__).parent.parent / "data" / "srtm1"
SRTM1_DIR.mkdir(parents=True, exist_ok=True)

MIN_LAT, MAX_LAT = 4.0, 21.0
MIN_LON, MAX_LON = 116.0, 127.0

BASE_URL = "https://e4ftl01.cr.usgs.gov/MEASURES/SRTMGL1.003/2000.02.11"


def tile_name(lat: float, lon: float) -> str:
    ns = "N" if lat >= 0 else "S"
    ew = "E" if lon >= 0 else "W"
    return f"{ns}{abs(int(lat)):02d}{ew}{abs(int(lon)):03d}"


def get_credentials():
    user = os.environ.get("EARTHDATA_USER")
    password = os.environ.get("EARTHDATA_PASS")
    if user and password:
        return user, password
    try:
        n = netrc.netrc()
        info = n.authenticators("urs.earthdata.nasa.gov")
        if info:
            return info[0], info[2]
    except (FileNotFoundError, netrc.NetrcParseError):
        pass
    return None, None


def _safe_extract(zf, dest):
    dest = dest.resolve()
    for member in zf.infolist():
        member_path = (dest / member.filename).resolve()
        if not str(member_path).startswith(str(dest)):
            raise ValueError(f"Path traversal in zip: {member.filename}")
    zf.extractall(dest)


def download_tile(tile: str) -> bool:
    hgt_path = SRTM1_DIR / f"{tile}.hgt"
    if hgt_path.exists():
        print(f"  {tile}: already exists, skipping")
        return True

    user, password = get_credentials()
    if not user:
        print(f"  {tile}: SKIPPED (no Earthdata credentials set)")
        return False

    zip_path = SRTM1_DIR / f"{tile}.hgt.zip"
    url = f"{BASE_URL}/{tile}.SRTMGL1.hgt.zip"

    try:
        print(f"  {tile}: downloading from {url}")
        password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(None, "urs.earthdata.nasa.gov", user, password)
        password_mgr.add_password(None, "e4ftl01.cr.usgs.gov", user, password)
        handler = urllib.request.HTTPBasicAuthHandler(password_mgr)
        opener = urllib.request.build_opener(handler)

        with opener.open(url) as resp:
            with open(zip_path, "wb") as f:
                f.write(resp.read())

        with zipfile.ZipFile(zip_path, "r") as zf:
            _safe_extract(zf, SRTM1_DIR)
        zip_path.unlink()
        print(f"  {tile}: downloaded and extracted")
        return True
    except Exception as e:
        print(f"  {tile}: FAILED - {e}")
        if zip_path.exists():
            zip_path.unlink()
        return False


if __name__ == "__main__":
    tiles = []
    for lat in range(int(MIN_LAT), int(MAX_LAT) + 1):
        for lon in range(int(MIN_LON), int(MAX_LON) + 1):
            tiles.append(tile_name(lat, lon))

    unique_tiles = sorted(set(tiles))

    print(f"Philippines SRTM1 tiles ({len(unique_tiles)} tiles):")
    user, _ = get_credentials()
    if not user:
        print("WARNING: No Earthdata credentials found.")
        print(
            "The app uses the OpenTopoData API by default, which works without local tiles."
        )
        print(
            "To download tiles, set EARTHDATA_USER and EARTHDATA_PASS environment variables"
        )
        print(
            "with your NASA Earthdata account (register at https://urs.earthdata.nasa.gov)"
        )
        print()

    downloaded = 0
    for t in unique_tiles:
        if download_tile(t):
            downloaded += 1

    print(f"\nDone. {downloaded}/{len(unique_tiles)} tiles downloaded to {SRTM1_DIR}")
    if downloaded == 0:
        print(
            "No tiles downloaded. The app will use the OpenTopoData SRTM 30m API instead."
        )
