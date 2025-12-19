#!/usr/bin/env python3
"""
System Health Monitor - Ensures all services are always running
Monitors and auto-restarts: AutoKitteh, Temporal, n8n, KutiraAI services, Qdrant, Dashboard
Uses centralized logging with rotation to prevent unbounded log growth.
"""

import subprocess
import time
import json
from pathlib import Path
from datetime import datetime
import signal
import sys

# Add logging utilities
sys.path.insert(0, str(Path.home() / ".claude" / "utils"))
from setup_logging import setup_logger

# Service definitions
SERVICES = {
    "dashboard": {
        "name": "KutiraAI Dashboard",
        "check_cmd": ["curl", "-sf", "http://localhost:3101"],
        "start_cmd": ["nohup", "python3", "/tmp/simple-dashboard-3101.py"],
        "log_file": "/tmp/dashboard-3101.log",
        "critical": True
    },
    "n8n": {
        "name": "n8n Workflow Automation",
        "check_cmd": ["curl", "-sf", "http://localhost:5678"],
        "start_cmd": ["nohup", "n8n"],
        "log_file": "/tmp/n8n.log",
        "critical": True
    },
    "autokitteh": {
        "name": "AutoKitteh",
        "check_cmd": ["curl", "-sf", "http://localhost:9980/healthz"],
        "start_cmd": None,  # Already managed
        "log_file": "/tmp/autokitteh.log",
        "critical": True
    },
    "temporal": {
        "name": "Temporal",
        "check_cmd": ["pgrep", "-f", "temporal"],
        "start_cmd": None,  # Already managed
        "log_file": None,
        "critical": True
    }
}

STATE_FILE = Path.home() / ".claude" / "logs" / "service-state.json"
PREV_STATE_FILE = Path.home() / ".claude" / "logs" / "service-prev-state.json"

# Set up logger with rotation (1MB max, 3 backups)
logger = setup_logger("system-health-monitor", level="WARNING", max_mb=1, backup_count=3)

def log_state_change(message, level="info"):
    """Log only when state changes to reduce log spam"""
    if level == "error":
        logger.error(message)
    elif level == "warning":
        logger.warning(message)
    else:
        logger.info(message)

def check_service(service_id, config):
    """Check if a service is running"""
    try:
        result = subprocess.run(
            config['check_cmd'],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        # Only log errors, not routine checks
        return False

def start_service(service_id, config):
    """Start a service"""
    if config['start_cmd'] is None:
        log_state_change(f"{config['name']} managed externally, not restarting", "warning")
        return False

    try:
        log_state_change(f"Starting {config['name']}...", "warning")

        cmd = config['start_cmd'][:]
        if config['log_file']:
            cmd.extend([">", config['log_file'], "2>&1", "&"])
            # Use shell for redirection
            cmd_str = ' '.join(cmd)
            subprocess.Popen(cmd_str, shell=True)
        else:
            subprocess.Popen(cmd)

        time.sleep(3)

        if check_service(service_id, config):
            log_state_change(f"{config['name']} started successfully", "info")
            return True
        else:
            log_state_change(f"{config['name']} failed to start", "error")
            return False
    except Exception as e:
        log_state_change(f"Error starting {config['name']}: {e}", "error")
        return False

def load_prev_state():
    """Load previous state for comparison"""
    if PREV_STATE_FILE.exists():
        with open(PREV_STATE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_state(state):
    """Save service state to file"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

    # Save for next cycle comparison
    with open(PREV_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def monitor_loop():
    """Main monitoring loop - only logs state changes"""
    logger.info("System Health Monitor started")

    cycle = 0
    prev_state = load_prev_state()

    while True:
        cycle += 1
        state = {
            "timestamp": datetime.now().isoformat(),
            "cycle": cycle,
            "services": {}
        }

        for service_id, config in SERVICES.items():
            is_running = check_service(service_id, config)
            state["services"][service_id] = {
                "name": config["name"],
                "running": is_running,
                "critical": config.get("critical", False)
            }

            # Only log when state changes from previous cycle
            prev_running = prev_state.get("services", {}).get(service_id, {}).get("running")

            if is_running != prev_running:
                if is_running:
                    logger.info(f"{config['name']} is now UP")
                else:
                    logger.warning(f"{config['name']} is now DOWN")

            # Only attempt restart if down and was previously up (avoid spam)
            if not is_running and config.get("critical") and config['start_cmd']:
                if prev_running is not False:  # First detection or was running
                    start_service(service_id, config)

        save_state(state)
        prev_state = state
        time.sleep(60)  # Check every 60 seconds (reduced from 30)

def signal_handler(sig, frame):
    """Handle shutdown gracefully"""
    logger.info("System Health Monitor shutting down")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        monitor_loop()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
