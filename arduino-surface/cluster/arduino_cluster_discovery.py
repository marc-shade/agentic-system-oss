#!/usr/bin/env python3
"""
Arduino Cluster Discovery Service
==================================

Discovers and tracks Arduino device location across the cluster.
When Arduino is not connected locally, finds it on remote nodes
and enables transparent remote access.

Features:
- Scans all cluster nodes for Arduino serial ports via SSH
- Registers Arduino location in cluster state database
- Provides remote command proxy for cross-node access
- Auto-updates when Arduino is moved between nodes
- Graceful handling when Arduino is disconnected

Cluster Nodes:
- mac-studio (192.168.1.16): Orchestrator, macOS
- macpro51 (192.168.1.27): Builder, Linux
- macbook-air (192.168.1.55): Researcher, macOS
- macmini (192.168.1.36): Inference, macOS
"""

import asyncio
import json
import logging
import os
import socket
import sqlite3
import subprocess
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import threading

# Dynamic path detection
STORAGE_BASE = os.environ.get('STORAGE_BASE', '/Volumes/SSDRAID0/agentic-system' if os.path.exists('/Volumes/SSDRAID0') else '/home/marc/agentic-system')
LOG_DIR = os.path.join(STORAGE_BASE, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'arduino_cluster.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('arduino-cluster')


class NodePlatform(Enum):
    """Node platform types"""
    MACOS = "macos"
    LINUX = "linux"


@dataclass
class ClusterNode:
    """Cluster node information"""
    node_id: str
    hostname: str
    ip: str
    platform: NodePlatform
    ssh_user: str = "marc"
    ssh_port: int = 22

    @property
    def arduino_patterns(self) -> List[str]:
        """Serial port patterns to search for Arduino"""
        if self.platform == NodePlatform.MACOS:
            return ["/dev/tty.usbmodem*", "/dev/cu.usbmodem*"]
        else:  # Linux
            return ["/dev/ttyACM*", "/dev/ttyUSB*"]


@dataclass
class ArduinoLocation:
    """Arduino device location in cluster"""
    node_id: str
    port: str
    discovered_at: datetime
    last_verified: datetime
    is_local: bool
    broker_running: bool = False
    broker_port: int = 8200  # HTTP proxy port


# Cluster node definitions
CLUSTER_NODES = {
    "mac-studio": ClusterNode(
        node_id="mac-studio",
        hostname="MarcsMacStudio.fios-router.home",
        ip="192.168.1.16",
        platform=NodePlatform.MACOS
    ),
    "macpro51": ClusterNode(
        node_id="macpro51",
        hostname="macpro51.fios-router.home",
        ip="192.168.1.27",
        platform=NodePlatform.LINUX
    ),
    "macbook-air": ClusterNode(
        node_id="macbook-air",
        hostname="Mac.fios-router.home",
        ip="192.168.1.55",
        platform=NodePlatform.MACOS
    ),
    "macmini": ClusterNode(
        node_id="macmini",
        hostname="macmini.fios-router.home",
        ip="192.168.1.36",
        platform=NodePlatform.MACOS
    )
}


class ArduinoClusterDiscovery:
    """
    Discovers and manages Arduino location across the cluster.
    Enables transparent remote access to Arduino on any node.
    """

    def __init__(self, db_path: Optional[str] = None):
        """Initialize Arduino cluster discovery service"""
        self.db_path = db_path or os.path.join(STORAGE_BASE, 'databases', 'arduino_cluster.db')
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self.local_node_id = self._detect_local_node()
        self.current_location: Optional[ArduinoLocation] = None
        self.discovery_lock = threading.Lock()

        self._init_database()
        logger.info(f"Arduino Cluster Discovery initialized on {self.local_node_id}")

    def _detect_local_node(self) -> str:
        """Detect which cluster node we're running on"""
        hostname = socket.gethostname().lower()

        # Map hostnames to node IDs
        hostname_map = {
            "marcsmacstudio": "mac-studio",
            "macpro51": "macpro51",
            "mac": "macbook-air",
            "macmini": "macmini"
        }

        for key, node_id in hostname_map.items():
            if key in hostname:
                return node_id

        # Fallback: Check IP addresses
        try:
            local_ip = socket.gethostbyname(socket.gethostname())
            for node_id, node in CLUSTER_NODES.items():
                if node.ip == local_ip:
                    return node_id
        except:
            pass

        return "unknown"

    def _init_database(self):
        """Initialize SQLite database for Arduino state"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS arduino_location (
                id INTEGER PRIMARY KEY,
                node_id TEXT NOT NULL,
                port TEXT NOT NULL,
                discovered_at TEXT NOT NULL,
                last_verified TEXT NOT NULL,
                is_local INTEGER NOT NULL,
                broker_running INTEGER DEFAULT 0,
                broker_port INTEGER DEFAULT 8200
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS discovery_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                node_id TEXT NOT NULL,
                port TEXT,
                action TEXT NOT NULL,
                details TEXT
            )
        ''')

        conn.commit()
        conn.close()

    def _log_discovery_event(self, node_id: str, port: Optional[str], action: str, details: str = ""):
        """Log discovery events to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO discovery_history (timestamp, node_id, port, action, details)
            VALUES (?, ?, ?, ?, ?)
        ''', (datetime.now().isoformat(), node_id, port, action, details))

        conn.commit()
        conn.close()

    def scan_local_arduino(self) -> Optional[Tuple[str, str]]:
        """Scan for Arduino on the local node"""
        node = CLUSTER_NODES.get(self.local_node_id)
        if not node:
            return None

        for pattern in node.arduino_patterns:
            try:
                import glob
                ports = glob.glob(pattern)
                if ports:
                    # Return the first found port
                    port = ports[0]
                    logger.info(f"Found local Arduino at {port}")
                    return (self.local_node_id, port)
            except Exception as e:
                logger.debug(f"Error scanning pattern {pattern}: {e}")

        return None

    def scan_remote_arduino(self, node: ClusterNode, timeout: int = 5) -> Optional[str]:
        """Scan for Arduino on a remote node via SSH"""
        try:
            # Build find command for Arduino ports
            find_commands = [f"ls {pattern} 2>/dev/null" for pattern in node.arduino_patterns]
            ssh_command = " || ".join(find_commands)

            result = subprocess.run(
                [
                    "ssh", "-o", "ConnectTimeout=3",
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "BatchMode=yes",
                    f"{node.ssh_user}@{node.ip}",
                    ssh_command
                ],
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode == 0 and result.stdout.strip():
                ports = result.stdout.strip().split('\n')
                port = ports[0].strip()
                if port:
                    logger.info(f"Found Arduino on {node.node_id} at {port}")
                    return port

            return None

        except subprocess.TimeoutExpired:
            logger.debug(f"SSH timeout scanning {node.node_id}")
            return None
        except Exception as e:
            logger.debug(f"Error scanning {node.node_id}: {e}")
            return None

    def discover_arduino(self, force_scan: bool = False) -> Optional[ArduinoLocation]:
        """
        Discover Arduino location across the cluster.

        Returns the ArduinoLocation if found, None if not connected anywhere.
        """
        with self.discovery_lock:
            # First, check local node
            local_result = self.scan_local_arduino()
            if local_result:
                node_id, port = local_result
                location = ArduinoLocation(
                    node_id=node_id,
                    port=port,
                    discovered_at=datetime.now(),
                    last_verified=datetime.now(),
                    is_local=True
                )
                self._save_location(location)
                self._log_discovery_event(node_id, port, "discovered", "Found locally")
                self.current_location = location
                return location

            # Not local - scan remote nodes
            logger.info("Arduino not found locally, scanning remote nodes...")

            for node_id, node in CLUSTER_NODES.items():
                if node_id == self.local_node_id:
                    continue  # Skip local node, already checked

                port = self.scan_remote_arduino(node)
                if port:
                    location = ArduinoLocation(
                        node_id=node_id,
                        port=port,
                        discovered_at=datetime.now(),
                        last_verified=datetime.now(),
                        is_local=False
                    )
                    self._save_location(location)
                    self._log_discovery_event(node_id, port, "discovered", f"Found on remote node {node_id}")
                    self.current_location = location
                    return location

            # Not found anywhere
            logger.warning("Arduino not found on any cluster node")
            self._log_discovery_event("none", None, "not_found", "Arduino not connected to any node")
            self.current_location = None
            return None

    def _save_location(self, location: ArduinoLocation):
        """Save Arduino location to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Clear existing and insert new
        cursor.execute('DELETE FROM arduino_location')
        cursor.execute('''
            INSERT INTO arduino_location
            (node_id, port, discovered_at, last_verified, is_local, broker_running, broker_port)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            location.node_id,
            location.port,
            location.discovered_at.isoformat(),
            location.last_verified.isoformat(),
            1 if location.is_local else 0,
            1 if location.broker_running else 0,
            location.broker_port
        ))

        conn.commit()
        conn.close()

    def get_cached_location(self) -> Optional[ArduinoLocation]:
        """Get cached Arduino location from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM arduino_location LIMIT 1')
        row = cursor.fetchone()
        conn.close()

        if row:
            return ArduinoLocation(
                node_id=row[1],
                port=row[2],
                discovered_at=datetime.fromisoformat(row[3]),
                last_verified=datetime.fromisoformat(row[4]),
                is_local=bool(row[5]),
                broker_running=bool(row[6]),
                broker_port=row[7]
            )

        return None

    def verify_arduino_connection(self, location: ArduinoLocation) -> bool:
        """Verify Arduino is still connected at the cached location"""
        if location.is_local:
            # Check local port exists
            return os.path.exists(location.port)
        else:
            # Check remote port via SSH
            node = CLUSTER_NODES.get(location.node_id)
            if not node:
                return False

            try:
                result = subprocess.run(
                    [
                        "ssh", "-o", "ConnectTimeout=3",
                        "-o", "StrictHostKeyChecking=no",
                        "-o", "BatchMode=yes",
                        f"{node.ssh_user}@{node.ip}",
                        f"test -e {location.port} && echo yes"
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return result.returncode == 0 and "yes" in result.stdout
            except:
                return False

    def get_arduino_location(self, use_cache: bool = True, max_cache_age_seconds: int = 60) -> Optional[ArduinoLocation]:
        """
        Get Arduino location, using cache if valid.

        Args:
            use_cache: Whether to use cached location
            max_cache_age_seconds: Maximum age of cache before re-discovering

        Returns:
            ArduinoLocation if found, None otherwise
        """
        if use_cache:
            cached = self.get_cached_location()
            if cached:
                # Check cache age
                age = (datetime.now() - cached.last_verified).total_seconds()
                if age < max_cache_age_seconds:
                    # Verify connection still valid
                    if self.verify_arduino_connection(cached):
                        return cached
                    else:
                        logger.info("Cached location no longer valid, re-discovering...")

        return self.discover_arduino()

    def get_discovery_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent discovery history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT timestamp, node_id, port, action, details
            FROM discovery_history
            ORDER BY id DESC LIMIT ?
        ''', (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "timestamp": row[0],
                "node_id": row[1],
                "port": row[2],
                "action": row[3],
                "details": row[4]
            }
            for row in rows
        ]

    def start_remote_broker(self, location: ArduinoLocation) -> bool:
        """
        Start the Arduino broker on a remote node.

        This enables remote access to the Arduino via HTTP proxy.
        """
        if location.is_local:
            logger.info("Arduino is local, use local broker instead")
            return False

        node = CLUSTER_NODES.get(location.node_id)
        if not node:
            return False

        try:
            # Start the HTTP Arduino proxy on the remote node
            # This runs the broker with an HTTP wrapper for network access
            start_cmd = f"""
                cd {STORAGE_BASE}/arduino-surface &&
                nohup python3 cluster/arduino_http_proxy.py --port {location.broker_port} --serial-port {location.port} > /tmp/arduino_http_proxy.log 2>&1 &
            """

            result = subprocess.run(
                [
                    "ssh", "-o", "ConnectTimeout=5",
                    "-o", "StrictHostKeyChecking=no",
                    f"{node.ssh_user}@{node.ip}",
                    start_cmd
                ],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                location.broker_running = True
                self._save_location(location)
                logger.info(f"Started Arduino HTTP proxy on {node.node_id}:{location.broker_port}")
                return True
            else:
                logger.error(f"Failed to start remote broker: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error starting remote broker: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get complete Arduino cluster status"""
        location = self.get_arduino_location(use_cache=True)

        return {
            "local_node": self.local_node_id,
            "arduino_connected": location is not None,
            "location": asdict(location) if location else None,
            "cluster_nodes": list(CLUSTER_NODES.keys()),
            "discovery_history": self.get_discovery_history(limit=5)
        }


# Singleton instance
_discovery_instance: Optional[ArduinoClusterDiscovery] = None


def get_discovery_service() -> ArduinoClusterDiscovery:
    """Get or create the singleton discovery service"""
    global _discovery_instance
    if _discovery_instance is None:
        _discovery_instance = ArduinoClusterDiscovery()
    return _discovery_instance


def discover_arduino() -> Optional[ArduinoLocation]:
    """Convenience function to discover Arduino"""
    return get_discovery_service().get_arduino_location()


def get_status() -> Dict[str, Any]:
    """Convenience function to get status"""
    return get_discovery_service().get_status()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Arduino Cluster Discovery")
    parser.add_argument("--discover", action="store_true", help="Discover Arduino location")
    parser.add_argument("--status", action="store_true", help="Show cluster status")
    parser.add_argument("--history", action="store_true", help="Show discovery history")
    parser.add_argument("--force", action="store_true", help="Force fresh discovery (ignore cache)")

    args = parser.parse_args()

    service = get_discovery_service()

    if args.discover or (not args.status and not args.history):
        print("=" * 60)
        print("Arduino Cluster Discovery")
        print("=" * 60)

        location = service.get_arduino_location(use_cache=not args.force)

        if location:
            print(f"\n✓ Arduino found!")
            print(f"  Node: {location.node_id}")
            print(f"  Port: {location.port}")
            print(f"  Local: {location.is_local}")
            print(f"  Discovered: {location.discovered_at}")
        else:
            print("\n✗ Arduino not found on any cluster node")

    if args.status:
        status = service.get_status()
        print("\nCluster Status:")
        print(json.dumps(status, indent=2, default=str))

    if args.history:
        history = service.get_discovery_history(20)
        print("\nDiscovery History:")
        for entry in history:
            print(f"  [{entry['timestamp']}] {entry['action']}: {entry['node_id']} - {entry['details']}")
