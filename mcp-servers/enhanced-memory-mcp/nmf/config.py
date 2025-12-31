"""
Configuration and models for Neural Memory Fabric.

Extracted from neural_memory_fabric.py for modularity.
Contains:
- MemoryTier enum
- RetrievalMode enum
- MemoryUnit dataclass
- Configuration loading
"""

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger("neural-memory-fabric")


class MemoryTier(Enum):
    """Memory tier enumeration"""
    ULTRA_FAST = "ultra_fast"
    WORKING = "working"
    LONG_TERM = "long_term"
    ARCHIVAL = "archival"


class RetrievalMode(Enum):
    """Retrieval strategy enumeration"""
    SEMANTIC = "semantic"  # Vector search only
    GRAPH = "graph"  # Graph traversal only
    TEMPORAL = "temporal"  # Time-based
    HYBRID = "hybrid"  # All combined


@dataclass
class MemoryUnit:
    """A single memory unit with all attributes"""
    id: str
    content: str
    timestamp: str
    valid_from: str
    valid_until: Optional[str]
    keywords: List[str]
    tags: List[str]
    context_description: str
    embedding: Optional[List[float]]
    linked_memories: List[str]
    importance_score: float
    access_count: int
    last_accessed: str
    tier: str
    agent_id: str
    version: int
    checksum: str
    metadata: Dict[str, Any]


def load_config(config_path: Optional[str] = None) -> Dict:
    """
    Load configuration from YAML file.

    Args:
        config_path: Optional path to config file

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If config not found in any location
    """
    if config_path is None:
        # Try multiple locations
        possible_paths = [
            Path(__file__).parent.parent.parent.parent / "memory-fabric" / "nmf_config.yaml",
            Path("/Volumes/FILES/agentic-system/memory-fabric/nmf_config.yaml"),
            Path(__file__).parent.parent / "nmf_config.yaml"
        ]

        for path in possible_paths:
            if path.exists():
                config_path = path
                break
        else:
            raise FileNotFoundError(
                f"Config not found in any location: {[str(p) for p in possible_paths]}"
            )

    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


__all__ = [
    'MemoryTier',
    'RetrievalMode',
    'MemoryUnit',
    'load_config',
    'logger',
]
