import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_elevation_grid_sample_center():
    from app.elevation_grid import ElevationGrid

    data = np.array([[0, 50], [0, 100]], dtype=np.float32)
    grid = ElevationGrid(min_lat=0, min_lon=0, max_lat=1, max_lon=1, data=data)
    val = grid.sample(0.5, 0.5)
    assert 36 < val < 64


def test_elevation_grid_sample_corner():
    from app.elevation_grid import ElevationGrid

    data = np.array([[10, 20], [30, 40]], dtype=np.float32)
    grid = ElevationGrid(min_lat=0, min_lon=0, max_lat=1, max_lon=1, data=data)
    assert grid.sample(0.0, 0.0) == 10.0
    assert grid.sample(0.0, 1.0) == 20.0
    assert grid.sample(1.0, 0.0) == 30.0
    assert grid.sample(1.0, 1.0) == 40.0


def test_elevation_grid_sample_out_of_bounds():
    from app.elevation_grid import ElevationGrid

    data = np.array([[10, 20], [30, 40]], dtype=np.float32)
    grid = ElevationGrid(min_lat=0, min_lon=0, max_lat=1, max_lon=1, data=data)
    assert grid.sample(-1.0, 0.5) == 0.0
    assert grid.sample(0.5, -1.0) == 0.0


def test_elevation_grid_sample_line():
    from app.elevation_grid import ElevationGrid

    data = np.array([[0, 100], [0, 100]], dtype=np.float32)
    grid = ElevationGrid(min_lat=0, min_lon=0, max_lat=1, max_lon=1, data=data)
    result = grid.sample_line(0, 0, 0, 1, 3)
    assert len(result) == 3
    assert result[0] == 0.0
    assert result[2] == 100.0
