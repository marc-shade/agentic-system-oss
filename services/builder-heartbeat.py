#!/usr/bin/env python3
"""
Builder Node Heartbeat Service
Sends periodic status updates to orchestrator for health monitoring
"""

import json
import time
import subprocess
import requests
from datetime import datetime
from pathlib import Path
import socket

# Configuration
NODE_ID = "macpro51"
NODE_TYPE = "builder"
ORCHESTRATOR_HOST = "192.168.1.16"
ORCHESTRATOR_PORT = 9000
HEARTBEAT_INTERVAL = 30  # seconds
HEARTBEAT_ENDPOINT = f"http://{ORCHESTRATOR_HOST}:{ORCHESTRATOR_PORT}/api/v1/heartbeat"


def get_builder_status():
    """Get current Builder node status"""
    status = {
        "node_id": NODE_ID,
        "node_type": NODE_TYPE,
        "timestamp": datetime.now().isoformat(),
        "hostname": socket.gethostname(),
    }

    # Get services status
    try:
        status["services"] = {
            "builder_api": check_service_port(9000),
            "redis": check_docker_container("redis"),
            "qdrant": check_docker_container("qdrant"),
        }
    except Exception as e:
        status["services_error"] = str(e)

    # Get system resources
    try:
        with open("/proc/loadavg", "r") as f:
            load = f.read().split()[:3]
            status["load_average"] = load

        with open("/proc/meminfo", "r") as f:
            mem_lines = f.readlines()
            mem_total = mem_available = None
            for line in mem_lines:
                if "MemTotal" in line:
                    mem_total = line.split()[1]
                elif "MemAvailable" in line:
                    mem_available = line.split()[1]
            if mem_total and mem_available:
                mem_used_pct = (
                    1 - int(mem_available) / int(mem_total)
                ) * 100
                status["memory_used_percent"] = round(mem_used_pct, 1)
    except Exception as e:
        status["resources_error"] = str(e)

    # Check build cache status
    try:
        result = subprocess.run(
            ["sccache", "--show-stats"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and "Cache hits" in result.stdout:
            for line in result.stdout.split("\n"):
                if "Cache hits" in line and "%" in line:
                    # Extract hit rate percentage
                    parts = line.split()
                    for part in parts:
                        if "%" in part:
                            status["sccache_hit_rate"] = part.strip()
                            break
    except Exception:
        pass  # Cache status is optional

    return status


def check_service_port(port):
    """Check if a service is listening on a port"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            result = s.connect_ex(("localhost", port))
            return result == 0
    except Exception:
        return False


def check_docker_container(container_name):
    """Check if a Docker container is running"""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return "Up" in result.stdout
    except Exception:
        return False


def send_heartbeat(status):
    """Send heartbeat to orchestrator"""
    try:
        response = requests.post(
            HEARTBEAT_ENDPOINT,
            json=status,
            timeout=10,
            headers={"Content-Type": "application/json"},
        )

        if response.status_code == 200:
            print(f"[{datetime.now().isoformat()}] Heartbeat sent successfully")
            return True
        else:
            print(
                f"[{datetime.now().isoformat()}] Heartbeat failed: "
                f"HTTP {response.status_code} - {response.text}"
            )
            return False

    except requests.exceptions.ConnectionError:
        print(
            f"[{datetime.now().isoformat()}] Connection error: "
            f"Cannot reach orchestrator at {HEARTBEAT_ENDPOINT}"
        )
        return False
    except requests.exceptions.Timeout:
        print(f"[{datetime.now().isoformat()}] Timeout sending heartbeat")
        return False
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] Error sending heartbeat: {e}")
        return False


def main():
    """Main heartbeat loop"""
    print(f"Builder Heartbeat Service starting...")
    print(f"Node ID: {NODE_ID}")
    print(f"Orchestrator: {ORCHESTRATOR_HOST}:{ORCHESTRATOR_PORT}")
    print(f"Interval: {HEARTBEAT_INTERVAL}s")
    print(f"Endpoint: {HEARTBEAT_ENDPOINT}")
    print()

    consecutive_failures = 0
    max_failures = 10

    while True:
        try:
            # Get current status
            status = get_builder_status()

            # Send heartbeat
            success = send_heartbeat(status)

            if success:
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    print(
                        f"WARNING: {consecutive_failures} consecutive failures. "
                        f"Check orchestrator connectivity."
                    )

            # Wait for next interval
            time.sleep(HEARTBEAT_INTERVAL)

        except KeyboardInterrupt:
            print("\nShutting down heartbeat service...")
            break
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] Unexpected error: {e}")
            time.sleep(HEARTBEAT_INTERVAL)


if __name__ == "__main__":
    main()
