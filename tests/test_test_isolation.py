"""Tests must never read or write the developer's real cache (#46).

Before this, tests wrote .cache/analysis_cache.json in the repo. Later runs
then found cached entries and took different code paths, so local coverage
was lower than CI's and results depended on leftover files.
"""

from pathlib import Path

from src import cache

REPO_CACHE_DIR = Path(__file__).resolve().parents[1] / ".cache"


def test_cache_points_at_a_temporary_directory():
    assert REPO_CACHE_DIR not in Path(cache.CACHE_FILE).parents
    assert Path(cache.CACHE_DIR) != REPO_CACHE_DIR


def test_each_test_starts_with_an_empty_cache():
    assert not Path(cache.CACHE_FILE).exists()
    cache.save_cache({"leftover": {"x": 1}})


def test_and_the_next_one_does_too():
    assert not Path(cache.CACHE_FILE).exists()
