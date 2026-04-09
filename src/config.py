import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

DEFAULTS = {
    "stale_days": 30,
    "top_n": 10,
}


def _load_config():
    """Load configuration from config.json, creating it with defaults if missing."""
    if not os.path.exists(CONFIG_FILE):
        _save_config(DEFAULTS)
        return dict(DEFAULTS)
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def _save_config(data):
    """Save configuration to config.json."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_config(key):
    """Get a single configuration value by key."""
    config = _load_config()
    if key not in config:
        raise KeyError(f"Unknown config key: {key}")
    return config[key]


def set_config(key, value):
    """Set a single configuration value and persist it."""
    config = _load_config()
    if key not in DEFAULTS:
        raise KeyError(f"Unknown config key: {key}")
    # Convert to int if the default is int
    if isinstance(DEFAULTS[key], int):
        value = int(value)
    config[key] = value
    _save_config(config)
    return value


def list_config():
    """Return all configuration key-value pairs."""
    return _load_config()


def get_all_config():
    """Return a Config-like dict with all values, using defaults for missing keys."""
    config = _load_config()
    result = dict(DEFAULTS)
    result.update(config)
    return result
