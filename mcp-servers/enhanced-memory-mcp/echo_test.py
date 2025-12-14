#!/usr/bin/env python3
"""
Simple echo communication test
"""
import subprocess
import json
import threading
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

def test_communication():
    """Test basic communication with echo-style approach"""
    print("🧪 Testing basic communication...")
    
    # Start minimal server
    python_path = _STORAGE_BASE / "mcp" / ".unified_environments" / "base_mcp" / "venv" / "bin" / "python"
    server_cwd = _STORAGE_BASE / "mcp-servers" / "enhanced-memory-mcp"
    proc = subprocess.Popen(
        [str(python_path), "minimal_test_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(server_cwd)
    )
    
    def read_stderr():
        """Read stderr in background"""
        for line in iter(proc.stderr.readline, ''):
            print(f"[STDERR] {line.strip()}")
    
    stderr_thread = threading.Thread(target=read_stderr, daemon=True)
    stderr_thread.start()
    
    # Give server time to start
    time.sleep(0.5)
    
    # Simple test message
    test_msg = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    
    try:
        print("📤 Sending test message...")
        proc.stdin.write(json.dumps(test_msg) + "\n")
        proc.stdin.flush()
        
        # Set a short timeout for reading
        proc.stdout.settimeout(2)
        
        print("📥 Waiting for response...")
        response = proc.stdout.readline()
        
        if response:
            print(f"✅ Got response: {response.strip()}")
            return True
        else:
            print("❌ No response")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    success = test_communication()
    print(f"Result: {'SUCCESS' if success else 'FAILED'}")