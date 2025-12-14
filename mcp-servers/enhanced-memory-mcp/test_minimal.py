#!/usr/bin/env python3
"""
Test script specifically for the minimal MCP server
"""
import sys
import json
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

def test_minimal_server():
    """Test the minimal server with MCP protocol messages"""

    # Start the minimal server
    print("Starting minimal server...")
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
    
    # Wait a moment for startup
    time.sleep(1)
    
    # Check stderr for any startup messages
    print("Checking for startup messages...")
    
    # Send initialize request
    initialize_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"}
        }
    }
    
    print("Sending initialize request...")
    try:
        proc.stdin.write(json.dumps(initialize_request) + "\n")
        proc.stdin.flush()
        
        # Wait for response with timeout
        import select
        ready, _, _ = select.select([proc.stdout], [], [], 3)  # 3 second timeout
        
        if ready:
            response_line = proc.stdout.readline()
            if response_line:
                print(f"✅ Response received: {response_line.strip()}")
                
                # Send tools/list request to test further
                tools_request = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list"
                }
                print("Sending tools/list request...")
                proc.stdin.write(json.dumps(tools_request) + "\n")
                proc.stdin.flush()
                
                # Wait for tools response
                ready2, _, _ = select.select([proc.stdout], [], [], 3)
                if ready2:
                    tools_response = proc.stdout.readline()
                    print(f"✅ Tools response: {tools_response.strip()}")
                    print("🎉 Minimal server working correctly!")
                    success = True
                else:
                    print("❌ No tools response received")
                    success = False
            else:
                print("❌ Empty response received")
                success = False
        else:
            print("❌ No response received (timeout)")
            success = False
            
        # Check if process is still alive
        if proc.poll() is None:
            print("✅ Server is still running")
        else:
            print(f"❌ Server exited with code: {proc.returncode}")
            success = False
            
        # Get any stderr output
        stderr_output = proc.stderr.read()
        if stderr_output:
            print(f"Server logs: {stderr_output}")
            
    except Exception as e:
        print(f"Error: {e}")
        success = False
    finally:
        proc.terminate()
        proc.wait()
        
    return success

if __name__ == "__main__":
    success = test_minimal_server()
    if success:
        print("\n🎯 CONCLUSION: Minimal server works - issue is in main server initialization")
    else:
        print("\n⚠️ CONCLUSION: Issue is in core MCP communication setup")