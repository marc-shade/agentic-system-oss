#!/usr/bin/env python3
"""
Simple startup test for enhanced memory MCP server
"""
import subprocess
import time
import os
import platform
from pathlib import Path


def _get_storage_base() -> Path:
    """Get storage base path based on environment variable or platform detection."""
    if env_path := os.environ.get("AGENTIC_SYSTEM_PATH"):
        return Path(env_path)
    if platform.system() == "Darwin":
        for p in [Path("/Volumes/SSDRAID0/agentic-system"), Path("/Volumes/FILES/agentic-system")]:
            if p.exists():
                return p
    else:
        for p in [Path("/home/marc/agentic-system"), Path("/mnt/agentic-system")]:
            if p.exists():
                return p
    return Path.home() / "agentic-system"


_STORAGE_BASE = _get_storage_base()

def test_startup():
    """Test if server starts without hanging"""
    print("Testing server startup...")

    # Start the server
    python_path = _STORAGE_BASE / "mcp" / ".unified_environments" / "base_mcp" / "venv" / "bin" / "python"
    server_cwd = _STORAGE_BASE / "mcp-servers" / "enhanced-memory-mcp"
    proc = subprocess.Popen(
        [str(python_path), "server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(server_cwd)
    )
    
    # Wait 3 seconds to see if it starts
    time.sleep(3)
    
    # Check if process is still alive
    if proc.poll() is None:
        print("✅ Server started successfully and is running")
        
        # Read any stderr output
        proc.stderr.read()
        stderr_output = proc.communicate(timeout=2)[1]
        if stderr_output:
            print(f"Startup logs: {stderr_output}")
            
        # Terminate cleanly
        proc.terminate()
        proc.wait()
        return True
    else:
        print(f"❌ Server exited with code: {proc.returncode}")
        stderr_output = proc.stderr.read()
        if stderr_output:
            print(f"Error output: {stderr_output}")
        return False

if __name__ == "__main__":
    test_startup()