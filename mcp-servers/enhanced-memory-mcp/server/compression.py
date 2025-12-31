"""
Compression and data utilities for Enhanced Memory MCP Server.

Extracted from server.py for better organization.

NOTE: This module uses pickle for serialization intentionally.
The memory system stores arbitrary Python objects (dicts, lists, custom types)
that cannot be fully represented in JSON. All data comes from trusted internal
sources (the memory system itself), not external/untrusted input.
"""

import hashlib
import pickle  # Required for arbitrary Python object serialization
import zlib
from typing import Any, Tuple


def compress_data(data: Any) -> Tuple[bytes, int, int, float]:
    """
    Compress data using zlib with maximum compression.

    Uses pickle for serialization to support arbitrary Python objects.
    This is safe as all data originates from the internal memory system.

    Args:
        data: Any pickleable Python object

    Returns:
        Tuple of (compressed_bytes, original_size, compressed_size, compression_ratio)
    """
    serialized = pickle.dumps(data)
    original_size = len(serialized)
    compressed = zlib.compress(serialized, level=9)
    compressed_size = len(compressed)
    compression_ratio = compressed_size / original_size if original_size > 0 else 1.0
    return compressed, original_size, compressed_size, compression_ratio


def decompress_data(compressed: bytes) -> Any:
    """
    Decompress and deserialize data.

    Uses pickle for deserialization. Data is trusted as it originates
    from the internal memory system's compress_data function.

    Args:
        compressed: zlib-compressed bytes from compress_data

    Returns:
        Original Python object
    """
    decompressed = zlib.decompress(compressed)
    return pickle.loads(decompressed)


def calculate_checksum(data: bytes) -> str:
    """
    Calculate SHA256 checksum for data integrity.

    Args:
        data: Bytes to checksum

    Returns:
        Hex-encoded SHA256 hash
    """
    return hashlib.sha256(data).hexdigest()


def classify_tier(entity_type: str, name: str) -> str:
    """
    Classify entity into memory tier based on type and name.

    Tiers:
    - core: System roles, orchestrator-related
    - working: Projects, sessions, current items
    - archive: Historical, archived items
    - reference: Default for everything else

    Args:
        entity_type: Type of entity
        name: Name of entity

    Returns:
        Tier classification string
    """
    if entity_type in ["system_role", "core_system"] or "orchestrator" in name.lower():
        return "core"
    elif entity_type in ["project", "session"] or "current" in name.lower():
        return "working"
    elif "archive" in name.lower() or "historical" in entity_type.lower():
        return "archive"
    else:
        return "reference"
