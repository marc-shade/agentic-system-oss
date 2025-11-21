#!/usr/bin/env python3
"""
TOON Configuration Loader

Utility for loading TOON format configuration files across the agentic system.
Provides backward compatibility with JSON files during migration.
"""

import json
from pathlib import Path
from typing import Any, Dict
from toon_py import encode

def load_config(config_path: Path | str) -> Dict[str, Any]:
    """
    Load configuration from TOON or JSON file.

    Tries to load .toon file first, falls back to .json for backward compatibility.

    Args:
        config_path: Path to config file (with or without extension)

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If neither .toon nor .json file exists
    """
    config_path = Path(config_path)

    # Remove extension if provided to handle both .json and .toon
    if config_path.suffix in ['.json', '.toon']:
        base_path = config_path.with_suffix('')
    else:
        base_path = config_path

    toon_path = base_path.with_suffix('.toon')
    json_path = base_path.with_suffix('.json')

    # Try TOON first (new format)
    if toon_path.exists():
        with open(toon_path, 'r') as f:
            toon_content = f.read()
        # TOON-PY doesn't have decode yet, so we need to use a workaround
        # For now, we'll parse it manually or use JSON as fallback
        # TODO: Implement TOON decoder when available
        if json_path.exists():
            with open(json_path, 'r') as f:
                return json.load(f)
        else:
            raise NotImplementedError(
                f"TOON file exists at {toon_path} but decoder not yet implemented. "
                f"Keep JSON file at {json_path} for now."
            )

    # Fall back to JSON (legacy format)
    elif json_path.exists():
        with open(json_path, 'r') as f:
            return json.load(f)

    else:
        raise FileNotFoundError(
            f"Configuration file not found: {base_path}.toon or {base_path}.json"
        )


def save_config(data: Dict[str, Any], config_path: Path | str,
                format: str = 'both') -> None:
    """
    Save configuration to TOON and/or JSON format.

    Args:
        data: Configuration dictionary
        config_path: Path to config file (without extension)
        format: 'toon', 'json', or 'both' (default: 'both' for migration)
    """
    config_path = Path(config_path)

    # Remove extension if provided
    if config_path.suffix in ['.json', '.toon']:
        base_path = config_path.with_suffix('')
    else:
        base_path = config_path

    if format in ['toon', 'both']:
        toon_path = base_path.with_suffix('.toon')
        toon_content = encode(data)
        with open(toon_path, 'w') as f:
            f.write(toon_content)

    if format in ['json', 'both']:
        json_path = base_path.with_suffix('.json')
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)


def load_node_config() -> Dict[str, Any]:
    """
    Load node configuration from standard location.

    Returns:
        Node configuration dictionary
    """
    return load_config(Path.home() / '.claude' / 'node-config')


# Example usage
if __name__ == '__main__':
    # Test loading node config
    try:
        config = load_node_config()
        print("✓ Successfully loaded node config:")
        print(f"  Node ID: {config.get('node_id')}")
        print(f"  Node Type: {config.get('node_type')}")
        print(f"  Capabilities: {', '.join(config.get('capabilities', []))}")
    except Exception as e:
        print(f"✗ Error loading config: {e}")
