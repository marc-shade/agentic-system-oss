#!/usr/bin/env python3
"""
Debug Claude Desktop integration by monitoring server behavior during tool calls
"""
import subprocess
import json
import time
import sys
import threading
import queue
import signal
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

def monitor_server_during_claude_call():
    """Monitor enhanced memory server during Claude Desktop tool call"""
    print("🔍 Starting server monitoring for Claude Desktop integration...")
    print("📋 This will start the server and show its logs.")
    print("📋 After the server starts, try using the MCP tool in Claude Desktop.")
    print("📋 Press Ctrl+C to stop monitoring when done.\n")
    
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
    
    # Create queues for stdout and stderr
    stdout_queue = queue.Queue()
    stderr_queue = queue.Queue()
    
    def read_stdout():
        while True:
            line = proc.stdout.readline()
            if line:
                stdout_queue.put(("STDOUT", line.strip()))
            else:
                break
    
    def read_stderr():
        while True:
            line = proc.stderr.readline()
            if line:
                stderr_queue.put(("STDERR", line.strip()))
            else:
                break
    
    # Start reader threads
    stdout_thread = threading.Thread(target=read_stdout, daemon=True)
    stderr_thread = threading.Thread(target=read_stderr, daemon=True)
    stdout_thread.start()
    stderr_thread.start()
    
    def signal_handler(sig, frame):
        print("\n🛑 Stopping server monitoring...")
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except:
            proc.kill()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    print("🚀 Server starting... (waiting for initialization)")
    time.sleep(3)
    
    startup_msg_count = 0
    try:
        # Show startup messages
        while True:
            try:
                msg_type, msg = stderr_queue.get_nowait()
                print(f"[{msg_type}] {msg}")
                startup_msg_count += 1
                if startup_msg_count > 10:  # Limit startup messages
                    break
            except queue.Empty:
                break
        
        print("\n✅ Server appears to be running. Now try using the MCP tool in Claude Desktop.")
        print("📋 I'll show all server activity below:\n")
        
        # Monitor continuously
        while True:
            activity_found = False
            
            # Check stdout
            try:
                while True:
                    msg_type, msg = stdout_queue.get_nowait()
                    print(f"[{msg_type}] {msg}")
                    activity_found = True
            except queue.Empty:
                pass
            
            # Check stderr
            try:
                while True:
                    msg_type, msg = stderr_queue.get_nowait()
                    print(f"[{msg_type}] {msg}")
                    activity_found = True
            except queue.Empty:
                pass
            
            if not activity_found:
                time.sleep(0.1)  # Short sleep to avoid busy waiting
        
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped by user")
    except Exception as e:
        print(f"❌ Error during monitoring: {e}")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except:
            proc.kill()

if __name__ == "__main__":
    monitor_server_during_claude_call()