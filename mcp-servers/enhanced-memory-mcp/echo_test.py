#!/usr/bin/env python3
"""
Simple echo communication test
"""
import subprocess
import json
import threading
import time

def test_communication():
    """Test basic communication with echo-style approach"""
    print("🧪 Testing basic communication...")
    
    # Start minimal server
    proc = subprocess.Popen(
        ["/Volumes/FILES/agentic-system/mcp/.unified_environments/base_mcp/venv/bin/python", "minimal_test_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd="/Volumes/FILES/agentic-system/mcp/enhanced-memory-mcp"
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