#!/usr/bin/env python3
"""
Detailed communication debugging for MCP server
"""
import subprocess
import json
import time
import sys
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

def test_debug_server_detailed():
    """Test debug server with detailed logging"""
    print("🔍 Starting detailed debug server test...")

    python_path = _STORAGE_BASE / "mcp" / ".unified_environments" / "base_mcp" / "venv" / "bin" / "python"
    server_cwd = _STORAGE_BASE / "mcp-servers" / "enhanced-memory-mcp"
    proc = subprocess.Popen(
        [str(python_path), "debug_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(server_cwd)
    )
    
    # Give server time to start
    time.sleep(1)
    
    try:
        # Test 1: Send initialize message
        init_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"}
            }
        }
        
        print("📤 Sending:", json.dumps(init_msg))
        
        # Send message
        proc.stdin.write(json.dumps(init_msg) + "\n")
        proc.stdin.flush()
        print("✅ Message sent and flushed")
        
        # Wait and check if anything happened
        time.sleep(2)
        
        # Check if process is still running
        if proc.poll() is not None:
            print(f"❌ Process terminated with return code: {proc.poll()}")
            return False
        
        print("✅ Process still running")
        
        # Try to read stderr to see server messages
        proc.stdin.close()  # Signal EOF to break the input loop
        
        # Wait for process to finish
        stdout_data, stderr_data = proc.communicate(timeout=5)
        
        print(f"📤 Stdout: {stdout_data}")
        print(f"📋 Stderr: {stderr_data}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except:
                proc.kill()

if __name__ == "__main__":
    success = test_debug_server_detailed()
    print(f"\n🎯 Result: {'SUCCESS' if success else 'FAILED'}")