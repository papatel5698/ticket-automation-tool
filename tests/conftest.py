import pytest

from src import cache


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    """Point the analysis cache at a fresh temp directory for every test.

    Without this, tests use the repo's real .cache/ and results depend on
    whatever earlier runs left there (#46).
    """
    cache_dir = tmp_path / ".cache"
    monkeypatch.setattr(cache, "CACHE_DIR", str(cache_dir))
    monkeypatch.setattr(cache, "CACHE_FILE", str(cache_dir / "analysis_cache.json"))
    return cache_dir
