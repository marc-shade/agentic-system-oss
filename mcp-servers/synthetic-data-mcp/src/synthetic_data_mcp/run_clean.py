#!/usr/bin/env python3
"""Ultra-clean MCP server runner that suppresses ALL output except JSON"""

# CRITICAL: Suppress warnings BEFORE any imports
import warnings
warnings.filterwarnings("ignore")
warnings.simplefilter("ignore")

import sys
import os
import io

# Suppress ALL Python warnings
os.environ['PYTHONWARNINGS'] = 'ignore'
sys.warnoptions = []

# Create a null stream for stderr
class NullWriter:
    def write(self, msg):
        pass
    def flush(self):
        pass

# Redirect stderr to null during imports to suppress ALL warnings
original_stderr = sys.stderr
sys.stderr = NullWriter()

# Set all necessary environment variables
os.environ.update({
    'PYTHONWARNINGS': 'ignore',
    'LOGURU_LEVEL': 'CRITICAL',
    'SYNTHETIC_DATA_AUDIT_DIR': os.path.expanduser("~/.synthetic-data-mcp/audit"),
    'SYNTHETIC_DATA_LOGS_DIR': os.path.expanduser("~/.synthetic-data-mcp/logs"),
    'FASTMCP_DISABLE_BANNER': '1',
    'NO_COLOR': '1',
    'TERM': 'dumb'
})

# Completely disable loguru before importing anything that uses it
import logging
logging.disable(logging.CRITICAL)

# Monkey patch loguru to be completely silent
try:
    from loguru import logger
    logger.remove()  # Remove all handlers
    logger.disable("synthetic_data_mcp")  # Disable for our package
    logger.disable("fastmcp")  # Disable for FastMCP

    # Monkey patch logger.add to prevent file creation
    original_add = logger.add
    def safe_add(sink, *args, **kwargs):
        # Only allow stdout/stderr sinks, not file paths
        if isinstance(sink, str) and (sink.startswith("/") or sink.startswith("logs/")):
            # Redirect to user directory
            if sink.startswith("logs/"):
                sink = os.path.expanduser(f"~/.synthetic-data-mcp/{sink}")
            elif sink.startswith("/logs/"):
                sink = os.path.expanduser(f"~/.synthetic-data-mcp/logs/{sink[6:]}")
            # Create parent directory if needed
            parent = os.path.dirname(sink)
            if parent:
                os.makedirs(parent, exist_ok=True)
        return original_add(sink, *args, **kwargs)
    logger.add = safe_add
except:
    pass

# Create necessary directories
for dir_path in [
    os.path.expanduser("~/.synthetic-data-mcp/audit"),
    os.path.expanduser("~/.synthetic-data-mcp/migrations"),
    os.path.expanduser("~/.synthetic-data-mcp/data"),
    os.path.expanduser("~/.synthetic-data-mcp/logs")
]:
    os.makedirs(dir_path, exist_ok=True)

# Monkey patch os.makedirs to prevent creating /logs
original_makedirs = os.makedirs
def safe_makedirs(path, *args, **kwargs):
    # Convert any absolute /logs path to user directory
    if path == "logs" or path == "/logs":
        path = os.path.expanduser("~/.synthetic-data-mcp/logs")
    elif path.startswith("/logs/"):
        path = os.path.expanduser("~/.synthetic-data-mcp") + path
    return original_makedirs(path, *args, **kwargs)
os.makedirs = safe_makedirs

# Monkey patch open() to redirect /logs file operations
import builtins
original_open = builtins.open
def safe_open(file, *args, **kwargs):
    # Convert any /logs file path to user directory
    if isinstance(file, str):
        if file.startswith("/logs/"):
            file = os.path.expanduser("~/.synthetic-data-mcp/logs/") + file[6:]
        elif file == "/logs":
            file = os.path.expanduser("~/.synthetic-data-mcp/logs")
    return original_open(file, *args, **kwargs)
builtins.open = safe_open

# Monkey patch print to prevent ANY print statements during import
original_print = builtins.print
def safe_print(*args, **kwargs):
    # Completely suppress all print statements
    pass
builtins.print = safe_print

# Now import the server (with stderr still suppressed)
try:
    from synthetic_data_mcp.server import app
    # Restore stderr and print after imports
    sys.stderr = original_stderr
    builtins.print = original_print
except Exception as e:
    # Restore stderr and print to report critical errors
    sys.stderr = original_stderr
    builtins.print = original_print
    sys.stderr.write(f"Critical error: {e}\n")
    sys.exit(1)

if __name__ == "__main__":
    # Run with banner disabled and stdio transport
    app.run(transport="stdio", show_banner=False)