#!/usr/bin/env python3
"""
Simple startup test for enhanced memory MCP server
"""
import subprocess
import time
import os

def test_startup():
    """Test if server starts without hanging"""
    print("Testing server startup...")
    
    # Start the server
    proc = subprocess.Popen(
        ["/Volumes/FILES/agentic-system/mcp/.unified_environments/base_mcp/venv/bin/python", "server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd="/Volumes/FILES/agentic-system/mcp/enhanced-memory-mcp"
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