#!/usr/bin/env python3
"""
Simplified communication test with proper timeout handling
"""
import subprocess
import json
import threading
import time
import select
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

def test_simple_communication():
    """Test basic stdin/stdout communication"""
    print("🧪 Testing simplified communication...")
    
    # Start minimal server
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
    time.sleep(0.5)
    
    try:
        # Send a simple initialize message
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
        
        print("📤 Sending initialize message...")
        proc.stdin.write(json.dumps(init_msg) + "\n")
        proc.stdin.flush()
        
        # Use select with timeout (Unix-only)
        if sys.platform != 'win32':
            ready, _, _ = select.select([proc.stdout], [], [], 3.0)
            if ready:
                response = proc.stdout.readline()
                if response.strip():
                    print(f"✅ Response: {response.strip()}")
                    return True
                else:
                    print("❌ Empty response")
                    return False
            else:
                print("❌ Timeout waiting for response")
                return False
        else:
            # Windows fallback
            print("Windows platform detected - using thread-based timeout")
            response = [None]
            
            def reader():
                response[0] = proc.stdout.readline()
            
            t = threading.Thread(target=reader)
            t.daemon = True
            t.start()
            t.join(timeout=3)
            
            if t.is_alive():
                print("❌ Timeout")
                return False
            elif response[0] and response[0].strip():
                print(f"✅ Response: {response[0].strip()}")
                return True
            else:
                print("❌ No response")
                return False
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        # Get any stderr output
        try:
            stderr_data = proc.stderr.read()
            if stderr_data:
                print(f"📋 Server output: {stderr_data}")
        except:
            pass
        
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except:
            proc.kill()

if __name__ == "__main__":
    success = test_simple_communication()
    print(f"\n🎯 Result: {'SUCCESS' if success else 'FAILED'}")