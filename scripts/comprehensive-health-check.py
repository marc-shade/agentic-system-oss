#!/usr/bin/env python3
"""
Comprehensive Health Check - Writes to health_history.json
Monitors all critical services: Temporal, Qdrant, PM2, AutoKitteh, MCP Servers, Task Queue, System Resources
"""

import os
import platform
import subprocess
import json
from datetime import datetime
from pathlib import Path
import sys


def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path("/Volumes/SSDRAID0/agentic-system").exists():
            return Path("/Volumes/SSDRAID0/agentic-system")
        elif Path("/Volumes/FILES/agentic-system").exists():
            return Path("/Volumes/FILES/agentic-system")
    elif system == "Linux":
        if Path("/home/marc/agentic-system").exists():
            return Path("/home/marc/agentic-system")
        elif Path("/mnt/agentic-system").exists():
            return Path("/mnt/agentic-system")
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()
HEALTH_HISTORY = _STORAGE_BASE / "logs" / "health_history.json"
MAX_HISTORY = 1000  # Keep last 1000 entries

def check_temporal():
    """Check if Temporal is running"""
    try:
        result = subprocess.run(['pgrep', '-f', 'temporal'], capture_output=True, timeout=2)
        running = bool(result.stdout.strip())
        return {
            "check": "Temporal",
            "timestamp": datetime.now().isoformat(),
            "status": "healthy" if running else "unhealthy",
            "message": "Temporal server responding" if running else "Temporal not running",
            "consecutive_failures": 0 if running else 1
        }
    except Exception as e:
        return {
            "check": "Temporal",
            "timestamp": datetime.now().isoformat(),
            "status": "unhealthy",
            "message": f"Check failed: {e}",
            "consecutive_failures": 1
        }

def check_autokitteh():
    """Check if AutoKitteh is running"""
    try:
        # Check for 'ak up' process
        result = subprocess.run(['pgrep', '-f', 'ak up'], capture_output=True, timeout=2)
        running = bool(result.stdout.strip())

        # Also check port 9980
        port_check = subprocess.run(['lsof', '-Pi', ':9980', '-sTCP:LISTEN'],
                                   capture_output=True, timeout=2)
        port_open = bool(port_check.stdout.strip())

        healthy = running or port_open
        return {
            "check": "AutoKitteh",
            "timestamp": datetime.now().isoformat(),
            "status": "healthy" if healthy else "unhealthy",
            "message": "AutoKitteh responding on port 9980" if healthy else "AutoKitteh not running",
            "consecutive_failures": 0 if healthy else 1
        }
    except Exception as e:
        return {
            "check": "AutoKitteh",
            "timestamp": datetime.now().isoformat(),
            "status": "unhealthy",
            "message": f"Check failed: {e}",
            "consecutive_failures": 1
        }

def check_qdrant():
    """Check if Qdrant is running"""
    try:
        result = subprocess.run(['curl', '-sf', 'http://localhost:6333/healthz'],
                              capture_output=True, timeout=2)
        healthy = result.returncode == 0
        return {
            "check": "Qdrant",
            "timestamp": datetime.now().isoformat(),
            "status": "healthy" if healthy else "unhealthy",
            "message": "Qdrant responding" if healthy else "Qdrant not responding",
            "consecutive_failures": 0 if healthy else 1
        }
    except Exception as e:
        return {
            "check": "Qdrant",
            "timestamp": datetime.now().isoformat(),
            "status": "unhealthy",
            "message": f"Check failed: {e}",
            "consecutive_failures": 1
        }

def check_pm2():
    """Check if PM2 is running"""
    try:
        result = subprocess.run(['pm2', 'list'], capture_output=True, timeout=2)
        healthy = result.returncode == 0
        return {
            "check": "PM2",
            "timestamp": datetime.now().isoformat(),
            "status": "healthy" if healthy else "unhealthy",
            "message": "PM2 responding" if healthy else "PM2 not responding",
            "consecutive_failures": 0 if healthy else 1
        }
    except Exception as e:
        return {
            "check": "PM2",
            "timestamp": datetime.now().isoformat(),
            "status": "unhealthy",
            "message": f"Check failed: {e}",
            "consecutive_failures": 1
        }

def check_mcp_servers():
    """Check MCP servers via Claude Code"""
    try:
        # Count running Claude Code processes as proxy for MCP health
        result = subprocess.run(['pgrep', '-f', 'claude'], capture_output=True, timeout=2, text=True)
        running = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
        healthy = running > 0
        return {
            "check": "MCP Servers",
            "timestamp": datetime.now().isoformat(),
            "status": "healthy" if healthy else "unhealthy",
            "message": f"{running} MCP processes running" if healthy else "No MCP processes",
            "consecutive_failures": 0 if healthy else 1
        }
    except Exception as e:
        return {
            "check": "MCP Servers",
            "timestamp": datetime.now().isoformat(),
            "status": "unhealthy",
            "message": f"Check failed: {e}",
            "consecutive_failures": 1
        }

def check_task_queue():
    """Check Task Queue health (from agent-runtime-mcp)"""
    try:
        # Check for agent-runtime database
        possible_paths = [
            _STORAGE_BASE / "databases" / "mcp" / "agent_runtime.db",
            Path(Path.home() / ".mcp" / "agent-runtime" / "agent_runtime.db"),
        ]

        for db_path in possible_paths:
            if db_path.exists() and db_path.stat().st_size > 0:
                return {
                    "check": "Task Queue",
                    "timestamp": datetime.now().isoformat(),
                    "status": "healthy",
                    "message": "Task queue database accessible",
                    "consecutive_failures": 0
                }

        return {
            "check": "Task Queue",
            "timestamp": datetime.now().isoformat(),
            "status": "unhealthy",
            "message": "Task queue database not found",
            "consecutive_failures": 1
        }
    except Exception as e:
        return {
            "check": "Task Queue",
            "timestamp": datetime.now().isoformat(),
            "status": "unhealthy",
            "message": f"Check failed: {e}",
            "consecutive_failures": 1
        }

def check_system_resources():
    """Check system resource usage"""
    try:
        # Get CPU usage from top
        result = subprocess.run(['top', '-l', '1', '-n', '0'],
                              capture_output=True, text=True, timeout=2)

        cpu_usage = 0.0
        for line in result.stdout.split('\n'):
            if 'CPU usage:' in line:
                # Parse "CPU usage: 12.34% user, 5.67% sys, 81.99% idle"
                parts = line.split(',')
                for part in parts:
                    if 'idle' in part:
                        idle = float(part.split('%')[0].split()[-1])
                        cpu_usage = 100.0 - idle
                        break

        return {
            "check": "System Resources",
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",
            "message": f"CPU: {cpu_usage:.1f}% used",
            "consecutive_failures": 0
        }
    except Exception as e:
        return {
            "check": "System Resources",
            "timestamp": datetime.now().isoformat(),
            "status": "unhealthy",
            "message": f"Check failed: {e}",
            "consecutive_failures": 1
        }

def load_history():
    """Load existing health history"""
    if HEALTH_HISTORY.exists():
        try:
            with open(HEALTH_HISTORY, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_history(history):
    """Save health history"""
    HEALTH_HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with open(HEALTH_HISTORY, 'w') as f:
        json.dump(history, f, indent=2)

def run_checks():
    """Run all health checks"""
    checks = [
        check_temporal(),
        check_autokitteh(),
        check_qdrant(),
        check_pm2(),
        check_mcp_servers(),
        check_task_queue(),
        check_system_resources()
    ]

    # Load existing history
    history = load_history()

    # Add new checks
    history.extend(checks)

    # Keep only last MAX_HISTORY entries
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]

    # Save updated history
    save_history(history)

    # Print summary
    print(f"Health Check Complete: {datetime.now().isoformat()}")
    for check in checks:
        status_icon = "✅" if check['status'] == 'healthy' else "❌"
        print(f"  {status_icon} {check['check']}: {check['message']}")

if __name__ == "__main__":
    try:
        run_checks()
    except Exception as e:
        print(f"Error running health checks: {e}", file=sys.stderr)
        sys.exit(1)
