"""Configuration management for ACD."""

import os
from pathlib import Path
from typing import Any, Optional

import yaml


_config: Optional[dict] = None


def load_config(config_path: Optional[str] = None) -> dict:
    """Load configuration from YAML file.

    Args:
        config_path: Path to config file. If None, uses default location.

    Returns:
        Configuration dictionary.
    """
    global _config

    if _config is not None and config_path is None:
        return _config

    if config_path is None:
        # Default config locations
        candidates = [
            Path(__file__).parent.parent.parent.parent / "config" / "daemon.yaml",
            Path("/mnt/agentic-system/autonomous-cognitive-daemon/config/daemon.yaml"),
            Path(os.environ.get("ACD_CONFIG", "")),
        ]
        for candidate in candidates:
            if candidate.exists():
                config_path = str(candidate)
                break

    if config_path is None or not Path(config_path).exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r") as f:
        _config = yaml.safe_load(f)

    return _config


def get_path(path_key: str, config: Optional[dict] = None) -> Path:
    """Get a path from config, expanding ~ and env vars.

    Args:
        path_key: Key in config.paths section
        config: Config dict (loads default if None)

    Returns:
        Expanded Path object
    """
    if config is None:
        config = load_config()

    path_str = config.get("paths", {}).get(path_key, "")
    if not path_str:
        raise KeyError(f"Path not found in config: {path_key}")

    # Expand ~ and environment variables
    expanded = os.path.expanduser(os.path.expandvars(path_str))
    return Path(expanded)


def get_config_value(key_path: str, default: Any = None, config: Optional[dict] = None) -> Any:
    """Get a nested config value using dot notation.

    Args:
        key_path: Dot-separated path (e.g., "scheduling.main_cycle_hours")
        default: Default value if not found
        config: Config dict (loads default if None)

    Returns:
        Config value or default
    """
    if config is None:
        config = load_config()

    keys = key_path.split(".")
    value = config

    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default

    return value
