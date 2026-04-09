import pytest
import json
import os
import tempfile
from unittest.mock import patch
from src.config import (
    get_config, set_config, list_config, get_all_config,
    _load_config, _save_config, DEFAULTS,
)


@pytest.fixture
def temp_config(tmp_path):
    """Use a temporary config file for tests."""
    config_file = str(tmp_path / "config.json")
    with patch("src.config.CONFIG_FILE", config_file):
        yield config_file


class TestDefaults:
    def test_default_top_n(self):
        assert DEFAULTS["top_n"] == 10


class TestLoadConfig:
    def test_creates_config_if_missing(self, temp_config):
        with patch("src.config.CONFIG_FILE", temp_config):
            config = _load_config()
            assert config["top_n"] == 10
            assert os.path.exists(temp_config)

    def test_loads_existing_config(self, temp_config):
        with open(temp_config, "w") as f:
            json.dump({"top_n": 5}, f)
        with patch("src.config.CONFIG_FILE", temp_config):
            config = _load_config()
            assert config["top_n"] == 5


class TestSetConfig:
    def test_sets_value(self, temp_config):
        with patch("src.config.CONFIG_FILE", temp_config):
            result = set_config("top_n", "20")
            assert result == 20
            assert get_config("top_n") == 20

    def test_converts_to_int(self, temp_config):
        with patch("src.config.CONFIG_FILE", temp_config):
            result = set_config("top_n", "20")
            assert result == 20
            assert isinstance(result, int)

    def test_persists_value(self, temp_config):
        with patch("src.config.CONFIG_FILE", temp_config):
            set_config("top_n", "7")
            # Read directly from file to confirm persistence
            with open(temp_config) as f:
                data = json.load(f)
            assert data["top_n"] == 7

    def test_rejects_unknown_key(self, temp_config):
        with patch("src.config.CONFIG_FILE", temp_config):
            with pytest.raises(KeyError):
                set_config("unknown_key", "value")


class TestGetConfig:
    def test_gets_value(self, temp_config):
        with patch("src.config.CONFIG_FILE", temp_config):
            value = get_config("top_n")
            assert value == 10

    def test_raises_on_unknown_key(self, temp_config):
        with patch("src.config.CONFIG_FILE", temp_config):
            with pytest.raises(KeyError):
                get_config("nonexistent")


class TestListConfig:
    def test_lists_all_values(self, temp_config):
        with patch("src.config.CONFIG_FILE", temp_config):
            config = list_config()
            assert "top_n" in config


class TestGetAllConfig:
    def test_returns_all_with_defaults(self, temp_config):
        with patch("src.config.CONFIG_FILE", temp_config):
            config = get_all_config()
            assert config["top_n"] == 10

    def test_overrides_with_saved_values(self, temp_config):
        with open(temp_config, "w") as f:
            json.dump({"top_n": 7}, f)
        with patch("src.config.CONFIG_FILE", temp_config):
            config = get_all_config()
            assert config["top_n"] == 7
