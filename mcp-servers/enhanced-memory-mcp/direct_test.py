#!/usr/bin/env python3
"""
Direct test of minimal server communication
"""
import subprocess
import json
import time
import threading
import sys

def test_direct_communication():
    """Test server with direct stdin/stdout communication"""
    print("🧪 Testing direct communication with minimal server...")
    
    # Start server
    proc = subprocess.Popen(
        ["/Volumes/FILES/agentic-system/mcp/.unified_environments/base_mcp/venv/bin/python", "minimal_test_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd="/Volumes/FILES/agentic-system/mcp/enhanced-memory-mcp",
        bufsize=0  # Unbuffered
    )
    
    print("✅ Server process started")
    
    # Give it a moment to initialize
    time.sleep(0.5)
    
    # Prepare initialize request
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"}
        }
    }
    
    request_str = json.dumps(request) + '\n'
    print(f"📤 Sending: {request_str.strip()}")
    
    try:
        # Send request
        proc.stdin.write(request_str)
        proc.stdin.flush()
        print("✅ Request sent successfully")
        
        # Try to read response with timeout
        def read_output():
            try:
                line = proc.stdout.readline()
                if line:
                    print(f"📥 Received: {line.strip()}")
                    return line.strip()
                else:
                    print("❌ No output received")
                    return None
            except Exception as e:
                print(f"❌ Error reading output: {e}")
                return None
        
        # Use threading to implement timeout
        result = [None]
        def reader():
            result[0] = read_output()
        
        reader_thread = threading.Thread(target=reader)
        reader_thread.daemon = True
        reader_thread.start()
        reader_thread.join(timeout=3)
        
        if reader_thread.is_alive():
            print("⏰ Timeout waiting for response")
            success = False
        elif result[0]:
            print("🎉 Communication successful!")
            success = True
        else:
            print("❌ No valid response received")
            success = False
            
    except Exception as e:
        print(f"❌ Communication error: {e}")
        success = False
    
    finally:
        # Check stderr for logs
        try:
            stderr_data = proc.stderr.read()
            if stderr_data:
                print(f"📋 Server logs:\n{stderr_data}")
        except:
            pass
            
        # Clean shutdown
        proc.terminate()
        proc.wait(timeout=2)
        
    return success

if __name__ == "__main__":
    success = test_direct_communication()
    if success:
        print("\n🎯 RESULT: Minimal server communication works!")
    else:
        print("\n⚠️ RESULT: Communication issue identified")