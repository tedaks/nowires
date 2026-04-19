import sys
from collections import OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.coverage as cov


def _reset_cache():
    cov._png_cache.clear()
    cov._png_cache = OrderedDict()


def test_cache_put_and_get():
    _reset_cache()
    cov._cache_put("key1", {"data": 1})
    result = cov._cache_get("key1")
    assert result == {"data": 1}


def test_cache_get_miss_returns_none():
    _reset_cache()
    result = cov._cache_get("nonexistent")
    assert result is None


def test_cache_evicts_lru_on_overflow():
    _reset_cache()
    for i in range(40):
        cov._cache_put(f"key_{i}", {"data": i})
    assert len(cov._png_cache) == 32
    assert cov._cache_get("key_0") is None
    assert cov._cache_get("key_39") is not None


def test_cache_move_to_end_on_hit():
    _reset_cache()
    original_max = cov._PNG_CACHE_MAX
    cov._PNG_CACHE_MAX = 3
    try:
        cov._cache_put("a", {"data": 1})
        cov._cache_put("b", {"data": 2})
        cov._cache_get("a")
        cov._cache_put("c", {"data": 3})
        cov._cache_put("d", {"data": 4})
        assert cov._cache_get("a") is not None
        assert cov._cache_get("b") is None
    finally:
        cov._PNG_CACHE_MAX = original_max
