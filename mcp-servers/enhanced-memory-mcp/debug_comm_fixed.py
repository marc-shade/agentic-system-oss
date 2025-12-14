#!/usr/bin/env python3
"""
Fixed communication test for MCP debug server
"""
import subprocess
import json
import time
import sys
import threading
import queue
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

def test_debug_server_fixed():
    """Test debug server with proper response handling"""
    print("🔧 Starting fixed debug server test...")

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
    
    # Create queues for stdout and stderr
    stdout_queue = queue.Queue()
    stderr_queue = queue.Queue()
    
    def read_stdout():
        while True:
            line = proc.stdout.readline()
            if line:
                stdout_queue.put(line.strip())
            else:
                break
    
    def read_stderr():
        while True:
            line = proc.stderr.readline()
            if line:
                stderr_queue.put(line.strip())
            else:
                break
    
    # Start reader threads
    stdout_thread = threading.Thread(target=read_stdout, daemon=True)
    stderr_thread = threading.Thread(target=read_stderr, daemon=True)
    stdout_thread.start()
    stderr_thread.start()
    
    # Give server time to start
    time.sleep(1)
    
    try:
        # Check for startup messages
        startup_msgs = []
        try:
            while True:
                msg = stderr_queue.get_nowait()
                startup_msgs.append(msg)
        except queue.Empty:
            pass
        
        print("📋 Startup messages:")
        for msg in startup_msgs:
            print(f"  {msg}")
        
        # Send initialize message
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
        
        print(f"📤 Sending: {json.dumps(init_msg)}")
        
        # Send message
        proc.stdin.write(json.dumps(init_msg) + "\n")
        proc.stdin.flush()
        print("✅ Message sent and flushed")
        
        # Wait for response
        response_received = False
        for attempt in range(10):  # Wait up to 10 seconds
            try:
                # Check for stderr messages
                while True:
                    try:
                        stderr_msg = stderr_queue.get_nowait()
                        print(f"📋 Server: {stderr_msg}")
                    except queue.Empty:
                        break
                
                # Check for stdout response
                try:
                    response = stdout_queue.get_nowait()
                    print(f"📥 Response: {response}")
                    response_received = True
                    break
                except queue.Empty:
                    pass
                
                time.sleep(1)
                
            except Exception as e:
                print(f"❌ Error in attempt {attempt}: {e}")
        
        if not response_received:
            print("❌ No response received after 10 seconds")
        
        return response_received
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except:
            proc.kill()

if __name__ == "__main__":
    success = test_debug_server_fixed()
    print(f"\n🎯 Result: {'SUCCESS' if success else 'FAILED'}")