"""
Universal storage path detection utility for agentic system.
Works across macOS and Linux platforms.
"""

import os
import platform
from pathlib import Path


def get_storage_base() -> Path:
    """
    Auto-detect storage base path for this node.

    Priority:
    1. STORAGE_BASE environment variable
    2. Platform-specific detection (filesystem-based)
    3. Home directory fallback

    Returns:
        Path: Base path to agentic-system directory
    """
    # Check environment variable first
    if 'STORAGE_BASE' in os.environ:
        return Path(os.environ['STORAGE_BASE'])

    # Platform-specific defaults
    if platform.system() == 'Darwin':  # macOS
        # Try SSDRAID0 first (mac-studio/macbook-air)
        if Path('/Volumes/SSDRAID0/agentic-system').exists():
            return Path('/Volumes/SSDRAID0/agentic-system')
        # Try FILES drive (macbook-air backup)
        if Path('/Volumes/FILES/agentic-system').exists():
            return Path('/Volumes/FILES/agentic-system')
        # Fallback to home directory
        return Path.home() / 'agentic-system'
    else:  # Linux
        # Try /mnt first (macpro51 RAID)
        if Path('/mnt/agentic-system').exists():
            return Path('/mnt/agentic-system')
        # Try home directory in mounted storage
        if Path('/home/marc/agentic-system').exists():
            return Path('/home/marc/agentic-system')
        # Fallback to home directory
        return Path.home() / 'agentic-system'


def get_database_path(db_name: str) -> Path:
    """
    Get path to a database file.

    Args:
        db_name: Name of the database file (e.g., 'meta_learning.db')

    Returns:
        Path: Full path to database file
    """
    return get_storage_base() / 'databases' / db_name


def get_logs_path(log_name: str) -> Path:
    """
    Get path to a log file.

    Args:
        log_name: Name of the log file (e.g., 'agent_selector.log')

    Returns:
        Path: Full path to log file
    """
    return get_storage_base() / 'logs' / log_name


# Pre-computed paths for convenience
STORAGE_BASE = get_storage_base()
DATABASES_DIR = STORAGE_BASE / 'databases'
LOGS_DIR = STORAGE_BASE / 'logs'


# Ensure directories exist
DATABASES_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
