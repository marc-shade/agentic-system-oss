#!/usr/bin/env python3
"""
Arduino Cluster Discovery
Finds Arduino Surface across distributed cluster nodes

Features:
- Local serial port scanning
- Remote node discovery via cluster registry
- SSH-based remote Arduino detection
- Telnet command relay support
"""

import os
import platform
import sys
import json
import sqlite3
import socket
import subprocess
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass


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
    return Path(__file__).parent.parent.parent


_STORAGE_BASE = _get_storage_base()


@dataclass
class ArduinoLocation:
    """Arduino location information"""
    node_id: str
    node_ip: str
    port: str
    is_local: bool
    relay_method: str  # 'direct', 'ssh', 'telnet'


class ArduinoClusterDiscovery:
    """Discover Arduino Surface across cluster nodes"""

    def __init__(self):
        self.cluster_db = _STORAGE_BASE / "databases" / "cluster" / "node_registry.db"
        self.local_node_config = Path.home() / ".claude" / "node-config.json"

    def discover(self) -> Optional[ArduinoLocation]:
        """
        Discover Arduino location across cluster

        Returns:
            ArduinoLocation if found, None otherwise
        """
        # 1. Try local serial ports first (fastest)
        local_port = self._scan_local_serial_ports()
        if local_port:
            return ArduinoLocation(
                node_id=self._get_local_node_id(),
                node_ip="localhost",
                port=local_port,
                is_local=True,
                relay_method="direct"
            )

        # 2. Query cluster nodes
        cluster_nodes = self._get_cluster_nodes()

        for node in cluster_nodes:
            if node["node_id"] == self._get_local_node_id():
                continue  # Skip local node (already scanned)

            # Check if this node has Arduino
            arduino_port = self._check_remote_node(node)
            if arduino_port:
                # Determine relay method based on node capabilities
                relay_method = "ssh" if node.get("ssh_available") else "telnet"

                return ArduinoLocation(
                    node_id=node["node_id"],
                    node_ip=node["ip"],
                    port=arduino_port,
                    is_local=False,
                    relay_method=relay_method
                )

        return None

    def _scan_local_serial_ports(self) -> Optional[str]:
        """
        Scan local serial ports for Arduino

        Returns:
            Port path if found, None otherwise
        """
        # Common Arduino USB serial patterns
        patterns = [
            "/dev/tty.usbmodem*",
            "/dev/ttyACM*",
            "/dev/ttyUSB*",
            "/dev/cu.usbmodem*"
        ]

        from glob import glob

        for pattern in patterns:
            ports = glob(pattern)
            for port in ports:
                if self._test_arduino_connection(port):
                    return port

        return None

    def _test_arduino_connection(self, port: str) -> bool:
        """
        Test if port has Arduino Surface

        Args:
            port: Serial port path

        Returns:
            True if Arduino responds to ping
        """
        try:
            import serial
            import time

            ser = serial.Serial(port, 115200, timeout=2)
            time.sleep(3)  # Wait for Arduino reset

            # Clear buffer
            while ser.in_waiting:
                ser.readline()

            # Send PING
            ser.write(b"PING\n")
            ser.flush()

            # Wait for response
            start = time.time()
            while time.time() - start < 2:
                if ser.in_waiting:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        try:
                            response = json.loads(line)
                            if response.get("status") == "ok":
                                ser.close()
                                return True
                        except:
                            pass
                time.sleep(0.1)

            ser.close()
            return False

        except Exception as e:
            return False

    def _get_cluster_nodes(self) -> List[Dict]:
        """
        Get list of cluster nodes from registry

        Returns:
            List of node dictionaries
        """
        if not self.cluster_db.exists():
            return []

        try:
            conn = sqlite3.connect(self.cluster_db)
            cursor = conn.cursor()

            # Try to get nodes from registry
            # Note: The actual schema might differ, this is a safe attempt
            try:
                cursor.execute("SELECT * FROM nodes")
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()

                nodes = []
                for row in rows:
                    node = dict(zip(columns, row))
                    nodes.append(node)

                conn.close()
                return nodes

            except sqlite3.OperationalError:
                # Table doesn't exist yet
                conn.close()
                return self._get_nodes_from_config()

        except Exception as e:
            print(f"Error querying cluster registry: {e}", file=sys.stderr)
            return self._get_nodes_from_config()

    def _get_nodes_from_config(self) -> List[Dict]:
        """
        Fallback: Get known nodes from hardcoded config

        Returns:
            List of known cluster nodes
        """
        # Known cluster configuration
        return [
            {
                "node_id": "macpro51",
                "ip": "192.168.1.183",
                "persona": "Builder",
                "ssh_available": True
            },
            {
                "node_id": "macbook-air-m3",
                "ip": "192.168.1.76",
                "persona": "Researcher",
                "ssh_available": True
            }
        ]

    def _check_remote_node(self, node: Dict) -> Optional[str]:
        """
        Check if remote node has Arduino connected

        Args:
            node: Node dictionary with ip and node_id

        Returns:
            Arduino port path if found, None otherwise
        """
        node_ip = node.get("ip")
        if not node_ip:
            return None

        # Method 1: Try telnet command listener (port 9999)
        try:
            port = self._check_via_telnet(node_ip, node["node_id"])
            if port:
                return port
        except:
            pass

        # Method 2: Try SSH if available
        if node.get("ssh_available"):
            try:
                port = self._check_via_ssh(node_ip)
                if port:
                    return port
            except:
                pass

        return None

    def _check_via_telnet(self, node_ip: str, node_id: str) -> Optional[str]:
        """
        Check for Arduino via telnet command listener

        Args:
            node_ip: Node IP address
            node_id: Node identifier

        Returns:
            Arduino port if found
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect((node_ip, 9999))

            # Read welcome message
            sock.recv(1024)

            # Send command to check for Arduino
            command = b"exec ls /dev/tty.usbmodem* /dev/ttyACM* /dev/ttyUSB* 2>/dev/null | head -1\n"
            sock.send(command)

            # Read response
            response = sock.recv(4096).decode('utf-8')
            sock.send(b"quit\n")
            sock.close()

            # Parse response for port path
            for line in response.split('\n'):
                if '/dev/tty' in line or '/dev/cu' in line:
                    port = line.strip()
                    if port:
                        return port

            return None

        except Exception as e:
            return None

    def _check_via_ssh(self, node_ip: str) -> Optional[str]:
        """
        Check for Arduino via SSH

        Args:
            node_ip: Node IP address

        Returns:
            Arduino port if found
        """
        try:
            result = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=2", "-o", "StrictHostKeyChecking=no",
                 f"marc@{node_ip}",
                 "ls /dev/tty.usbmodem* /dev/ttyACM* /dev/ttyUSB* 2>/dev/null | head -1"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()

            return None

        except Exception as e:
            return None

    def _get_local_node_id(self) -> str:
        """Get local node ID from config"""
        try:
            with open(self.local_node_config) as f:
                config = json.load(f)
                return config.get("node_id", "mac-studio")
        except:
            return "mac-studio"


def main():
    """CLI interface for testing"""
    print("🔍 Searching for Arduino Surface across cluster...\n")

    discovery = ArduinoClusterDiscovery()
    location = discovery.discover()

    if location:
        print(f"✅ Arduino found!")
        print(f"   Node: {location.node_id}")
        print(f"   IP: {location.node_ip}")
        print(f"   Port: {location.port}")
        print(f"   Local: {location.is_local}")
        print(f"   Relay: {location.relay_method}")
    else:
        print("❌ Arduino not found on any cluster node")
        print("\nSearched:")
        print("  - Local serial ports")
        print("  - macpro51 (192.168.1.183)")
        print("  - macbook-air-m3 (192.168.1.76)")


if __name__ == "__main__":
    main()
