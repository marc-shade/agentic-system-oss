"""
Configuration and constants for the Enhanced Memory MCP Server.

Extracted from server.py for better organization.
"""

import logging
import platform
import sys
from pathlib import Path
from typing import Callable, Optional

# Configuration
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"

# Create directories
MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    system = platform.system()
    if system == "Darwin":  # macOS
        if Path("/Volumes/SSDRAID0/agentic-system").exists():
            return Path("/Volumes/SSDRAID0/agentic-system")
        elif Path("/Volumes/FILES/agentic-system").exists():
            return Path("/Volumes/FILES/agentic-system")
    elif system == "Linux":
        if Path("/home/marc/agentic-system").exists():
            return Path("/home/marc/agentic-system")
        elif Path("/mnt/agentic-system").exists():
            return Path("/mnt/agentic-system")
    # Fallback to script location
    return Path(__file__).parent.parent.parent


STORAGE_BASE = get_storage_base()
HOOKS_PATH = STORAGE_BASE / "scripts" / "hooks"

# Add hooks to path for TPU and entropy scoring
if str(HOOKS_PATH) not in sys.path:
    sys.path.insert(0, str(HOOKS_PATH))


# Logging configuration
# MCP servers MUST NOT output to stderr - Claude Code interprets it as errors
# Force-redirect ALL logging to file
_log_file = Path(__file__).parent.parent / "server.log"
_file_handler = logging.FileHandler(str(_log_file), mode='a')
_file_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
)

# Remove ALL existing handlers from root logger and add file handler only
logging.root.handlers.clear()
logging.root.addHandler(_file_handler)
logging.root.setLevel(logging.INFO)

logger = logging.getLogger("enhanced-memory-git")


# Tool usage callback for eval infrastructure
_tool_usage_callback: Optional[Callable] = None


def set_tool_usage_callback(callback: Callable) -> None:
    """Set the tool usage callback. Called from main block."""
    global _tool_usage_callback
    _tool_usage_callback = callback


def log_tool_usage(
    tool_name: str,
    module: str = "core",
    success: bool = True,
    duration_ms: float = 0
) -> None:
    """Log tool usage if logging is enabled. Safe to call before logger is initialized."""
    if _tool_usage_callback:
        try:
            _tool_usage_callback(tool_name, module, success, duration_ms)
        except Exception:
            pass  # Never fail on logging
