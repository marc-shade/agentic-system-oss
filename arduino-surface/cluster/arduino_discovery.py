#!/usr/bin/env python3
"""
Arduino Cluster Discovery
Finds which node has the Arduino connected and enables cluster-wide access
"""

import json
import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import glob


@dataclass
class ArduinoLocation:
    """Arduino device location"""
    node_id: str  # mac-studio, macbook-air, macbook-pro
    serial_port: str  # /dev/tty.usbmodem*
    host: str  # hostname or IP
    relay_port: int = 8200  # HTTP relay port


class ArduinoClusterDiscovery:
    """Discover Arduino across cluster nodes"""

    # Cluster node definitions
    CLUSTER_NODES = {
        "mac-studio": {"hostname": "mac-studio.local", "priority": 1},
        "macbook-air": {"hostname": "macbook-air.local", "priority": 2},
        "macbook-pro": {"hostname": "macbook-pro.local", "priority": 3}
    }

    def __init__(self):
        self.current_node = self._detect_current_node()

    def _detect_current_node(self) -> str:
        """Detect which cluster node we're running on"""
        hostname = socket.gethostname().lower()

        for node_id, node_info in self.CLUSTER_NODES.items():
            if node_id in hostname or node_info["hostname"].split('.')[0] in hostname:
                return node_id

        # Default to hostname-based guess
        return hostname.split('.')[0]

    def _find_local_arduino(self) -> Optional[str]:
        """Find Arduino on local machine"""
        # macOS
        ports = glob.glob("/dev/tty.usbmodem*")
        if ports:
            return ports[0]

        # Linux
        ports = glob.glob("/dev/ttyACM*")
        if ports:
            return ports[0]

        return None

    def _check_remote_arduino(self, node_id: str, node_info: dict) -> Optional[str]:
        """Check if remote node has Arduino via relay service"""
        try:
            # Try to connect to relay service
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((node_info["hostname"], 8200))
            sock.close()

            if result == 0:
                # Relay is running, Arduino should be there
                return f"relay://{node_info['hostname']}:8200"

        except Exception:
            pass

        return None

    def discover(self) -> Optional[ArduinoLocation]:
        """
        Discover Arduino location across cluster

        Returns:
            ArduinoLocation if found, None otherwise
        """
        # 1. Check local machine first
        local_port = self._find_local_arduino()
        if local_port:
            return ArduinoLocation(
                node_id=self.current_node,
                serial_port=local_port,
                host="localhost",
                relay_port=8200
            )

        # 2. Check other cluster nodes (in priority order)
        nodes_by_priority = sorted(
            self.CLUSTER_NODES.items(),
            key=lambda x: x[1]["priority"]
        )

        for node_id, node_info in nodes_by_priority:
            if node_id == self.current_node:
                continue  # Already checked

            remote_port = self._check_remote_arduino(node_id, node_info)
            if remote_port:
                return ArduinoLocation(
                    node_id=node_id,
                    serial_port=remote_port,
                    host=node_info["hostname"],
                    relay_port=8200
                )

        # Arduino not found on any node
        return None


if __name__ == "__main__":
    discovery = ArduinoClusterDiscovery()
    location = discovery.discover()

    if location:
        print(f"✓ Arduino found on {location.node_id}")
        print(f"  Port: {location.serial_port}")
        print(f"  Host: {location.host}")
    else:
        print("✗ Arduino not found on any cluster node")
