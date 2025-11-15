#!/usr/bin/env python3
"""
Test script to diagnose enhanced memory MCP server issues
"""
import sys
import json
import subprocess
import time

def test_server():
    """Test the server with MCP protocol messages"""
    
    # Start the server
    print("Starting server...")
    proc = subprocess.Popen(
        ["/Volumes/FILES/agentic-system/mcp/.unified_environments/base_mcp/venv/bin/python", "server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd="/Volumes/FILES/agentic-system/mcp/enhanced-memory-mcp"
    )
    
    # Wait a moment for startup
    time.sleep(2)
    
    # Check stderr for any startup errors first
    print("Checking for startup errors...")
    time.sleep(1)
    stderr_output = proc.stderr.read()
    if stderr_output:
        print(f"Startup stderr: {stderr_output}")
    
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
        ready, _, _ = select.select([proc.stdout], [], [], 5)  # 5 second timeout
        
        if ready:
            response_line = proc.stdout.readline()
            if response_line:
                print(f"Response: {response_line.strip()}")
                
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
                ready2, _, _ = select.select([proc.stdout], [], [], 5)
                if ready2:
                    tools_response = proc.stdout.readline()
                    print(f"Tools response: {tools_response.strip()}")
                else:
                    print("No tools response received")
            else:
                print("Empty response received")
        else:
            print("No response received (timeout)")
            
        # Check if process is still alive
        if proc.poll() is None:
            print("Server is still running")
        else:
            print(f"Server exited with code: {proc.returncode}")
            stderr_output = proc.stderr.read()
            if stderr_output:
                print(f"Final stderr: {stderr_output}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    test_server()