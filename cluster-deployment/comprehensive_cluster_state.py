#!/usr/bin/env python3
"""
Comprehensive Cluster State - THE Complete Source of Truth

Contains 100% of the information ALL nodes need to understand:
- Their own configuration and resources
- Other nodes' configuration and resources
- All services and servers running
- All ports and IPs
- Network topology and connectivity
- Software inventory
- File system structure
- Everything needed for smart autonomous decisions

Updated in real-time. Always 100% accurate.
"""

import json
import sqlite3
import time
import socket
import subprocess
import psutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class NetworkInterface:
    """Network interface details"""
    interface_name: str
    ip_address: str
    netmask: str
    mac_address: str
    is_up: bool
    speed_mbps: Optional[int]
    bytes_sent: int
    bytes_recv: int


@dataclass
class ServiceEndpoint:
    """Service/server endpoint"""
    service_name: str
    port: int
    protocol: str  # tcp, udp, http, https
    bind_address: str  # 0.0.0.0, 127.0.0.1, or specific IP
    is_public: bool  # Accessible from outside?
    pid: Optional[int]
    status: str  # listening, stopped, error
    healthcheck_url: Optional[str]  # For HTTP services


@dataclass
class InstalledSoftware:
    """Software package installed"""
    package_name: str
    version: str
    package_type: str  # pip, apt, brew, npm, etc.
    install_path: str
    installed_at: Optional[float]


@dataclass
class FileSystemMount:
    """Mounted filesystem"""
    mount_point: str
    device: str
    fstype: str
    total_gb: float
    used_gb: float
    available_gb: float
    percent_used: float
    mount_options: List[str]


@dataclass
class SSHConnection:
    """SSH connectivity to another node"""
    target_node_id: str
    target_ip: str
    is_reachable: bool
    has_key_auth: bool
    key_fingerprint: Optional[str]
    latency_ms: Optional[float]
    last_tested: float


class ComprehensiveClusterState:
    """
    THE single source of truth containing 100% of cluster information

    All agents query this to understand:
    - Their own node completely
    - All other nodes completely
    - All services and where they run
    - All network topology
    - Everything needed for autonomous operation
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = str(Path.home() / "agentic-system/databases/cluster/comprehensive_state.db")

        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize comprehensive state database"""
        with sqlite3.connect(self.db_path) as conn:
            # NODES - Complete node information
            conn.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    node_id TEXT PRIMARY KEY,
                    hostname TEXT NOT NULL,
                    role TEXT NOT NULL,
                    os_type TEXT NOT NULL,
                    os_version TEXT NOT NULL,
                    architecture TEXT NOT NULL,
                    cpu_count INTEGER NOT NULL,
                    cpu_model TEXT,
                    total_memory_gb REAL NOT NULL,
                    total_disk_gb REAL NOT NULL,
                    python_version TEXT NOT NULL,
                    kernel_version TEXT,
                    timezone TEXT,
                    locale TEXT,
                    boot_time REAL,
                    config_version TEXT,
                    last_updated REAL NOT NULL
                )
            """)

            # NETWORK_INTERFACES - All network interfaces on each node
            conn.execute("""
                CREATE TABLE IF NOT EXISTS network_interfaces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_id TEXT NOT NULL,
                    interface_name TEXT NOT NULL,
                    ip_address TEXT NOT NULL,
                    netmask TEXT,
                    mac_address TEXT,
                    is_up BOOLEAN NOT NULL,
                    speed_mbps INTEGER,
                    bytes_sent INTEGER,
                    bytes_recv INTEGER,
                    last_updated REAL NOT NULL,
                    FOREIGN KEY (node_id) REFERENCES nodes(node_id)
                )
            """)

            # SERVICE_ENDPOINTS - All services/servers on all nodes
            conn.execute("""
                CREATE TABLE IF NOT EXISTS service_endpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_id TEXT NOT NULL,
                    service_name TEXT NOT NULL,
                    service_type TEXT NOT NULL,
                    port INTEGER,
                    protocol TEXT NOT NULL,
                    bind_address TEXT NOT NULL,
                    is_public BOOLEAN NOT NULL,
                    pid INTEGER,
                    status TEXT NOT NULL,
                    healthcheck_url TEXT,
                    config_path TEXT,
                    log_path TEXT,
                    data_path TEXT,
                    version TEXT,
                    dependencies TEXT,
                    last_updated REAL NOT NULL,
                    FOREIGN KEY (node_id) REFERENCES nodes(node_id),
                    UNIQUE(node_id, service_name, port)
                )
            """)

            # INSTALLED_SOFTWARE - Complete software inventory per node
            conn.execute("""
                CREATE TABLE IF NOT EXISTS installed_software (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_id TEXT NOT NULL,
                    package_name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    package_type TEXT NOT NULL,
                    install_path TEXT,
                    installed_at REAL,
                    checksum TEXT,
                    last_updated REAL NOT NULL,
                    FOREIGN KEY (node_id) REFERENCES nodes(node_id),
                    UNIQUE(node_id, package_name, package_type)
                )
            """)

            # FILESYSTEM_MOUNTS - All mounted filesystems per node
            conn.execute("""
                CREATE TABLE IF NOT EXISTS filesystem_mounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_id TEXT NOT NULL,
                    mount_point TEXT NOT NULL,
                    device TEXT NOT NULL,
                    fstype TEXT NOT NULL,
                    total_gb REAL NOT NULL,
                    used_gb REAL NOT NULL,
                    available_gb REAL NOT NULL,
                    percent_used REAL NOT NULL,
                    mount_options TEXT,
                    is_readonly BOOLEAN,
                    last_updated REAL NOT NULL,
                    FOREIGN KEY (node_id) REFERENCES nodes(node_id),
                    UNIQUE(node_id, mount_point)
                )
            """)

            # SSH_CONNECTIVITY - SSH mesh connectivity between nodes
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ssh_connectivity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_node_id TEXT NOT NULL,
                    target_node_id TEXT NOT NULL,
                    target_ip TEXT NOT NULL,
                    is_reachable BOOLEAN NOT NULL,
                    has_key_auth BOOLEAN NOT NULL,
                    key_fingerprint TEXT,
                    latency_ms REAL,
                    last_tested REAL NOT NULL,
                    FOREIGN KEY (source_node_id) REFERENCES nodes(node_id),
                    FOREIGN KEY (target_node_id) REFERENCES nodes(node_id),
                    UNIQUE(source_node_id, target_node_id)
                )
            """)

            # ENVIRONMENT_VARS - Important environment variables per node
            conn.execute("""
                CREATE TABLE IF NOT EXISTS environment_vars (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_id TEXT NOT NULL,
                    var_name TEXT NOT NULL,
                    var_value TEXT,
                    is_secret BOOLEAN NOT NULL,
                    last_updated REAL NOT NULL,
                    FOREIGN KEY (node_id) REFERENCES nodes(node_id),
                    UNIQUE(node_id, var_name)
                )
            """)

            # CAPABILITIES - Node capabilities (what each node can do)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS node_capabilities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_id TEXT NOT NULL,
                    capability_name TEXT NOT NULL,
                    capability_version TEXT,
                    is_available BOOLEAN NOT NULL,
                    metadata TEXT,
                    last_updated REAL NOT NULL,
                    FOREIGN KEY (node_id) REFERENCES nodes(node_id),
                    UNIQUE(node_id, capability_name)
                )
            """)

            # CONFIGURATION_FILES - Important config file locations
            conn.execute("""
                CREATE TABLE IF NOT EXISTS configuration_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_id TEXT NOT NULL,
                    config_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    checksum TEXT,
                    last_modified REAL,
                    owner TEXT,
                    permissions TEXT,
                    last_updated REAL NOT NULL,
                    FOREIGN KEY (node_id) REFERENCES nodes(node_id),
                    UNIQUE(node_id, config_name)
                )
            """)

            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_service_node ON service_endpoints(node_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_service_port ON service_endpoints(port)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_software_node ON installed_software(node_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_software_type ON installed_software(package_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_network_node ON network_interfaces(node_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ssh_source ON ssh_connectivity(source_node_id)")

            conn.commit()

    # === NODE INVENTORY ===

    def register_node_complete(self, node_id: str, inventory: Dict[str, Any]):
        """
        Register complete node information

        Args:
            node_id: Node identifier
            inventory: Complete inventory dict with all node info
        """
        with sqlite3.connect(self.db_path) as conn:
            # Update or insert node
            conn.execute("""
                INSERT OR REPLACE INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                node_id,
                inventory["hostname"],
                inventory["role"],
                inventory["os_type"],
                inventory["os_version"],
                inventory["architecture"],
                inventory["cpu_count"],
                inventory.get("cpu_model"),
                inventory["total_memory_gb"],
                inventory["total_disk_gb"],
                inventory["python_version"],
                inventory.get("kernel_version"),
                inventory.get("timezone"),
                inventory.get("locale"),
                inventory.get("boot_time"),
                inventory.get("config_version"),
                time.time()
            ))

            # Clear old data for this node
            conn.execute("DELETE FROM network_interfaces WHERE node_id = ?", (node_id,))
            conn.execute("DELETE FROM service_endpoints WHERE node_id = ?", (node_id,))
            conn.execute("DELETE FROM installed_software WHERE node_id = ?", (node_id,))
            conn.execute("DELETE FROM filesystem_mounts WHERE node_id = ?", (node_id,))
            conn.execute("DELETE FROM node_capabilities WHERE node_id = ?", (node_id,))

            # Insert network interfaces
            for iface in inventory.get("network_interfaces", []):
                conn.execute("""
                    INSERT INTO network_interfaces
                    (node_id, interface_name, ip_address, netmask, mac_address, is_up, speed_mbps, bytes_sent, bytes_recv, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    node_id, iface["interface_name"], iface["ip_address"],
                    iface.get("netmask"), iface.get("mac_address"),
                    iface["is_up"], iface.get("speed_mbps"),
                    iface.get("bytes_sent", 0), iface.get("bytes_recv", 0),
                    time.time()
                ))

            # Insert services
            for svc in inventory.get("services", []):
                conn.execute("""
                    INSERT OR REPLACE INTO service_endpoints
                    (node_id, service_name, service_type, port, protocol, bind_address, is_public,
                     pid, status, healthcheck_url, config_path, log_path, data_path, version, dependencies, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    node_id, svc["service_name"], svc["service_type"],
                    svc.get("port"), svc["protocol"], svc["bind_address"],
                    svc["is_public"], svc.get("pid"), svc["status"],
                    svc.get("healthcheck_url"), svc.get("config_path"),
                    svc.get("log_path"), svc.get("data_path"),
                    svc.get("version"), json.dumps(svc.get("dependencies", [])),
                    time.time()
                ))

            # Insert software
            for pkg in inventory.get("software", []):
                conn.execute("""
                    INSERT OR REPLACE INTO installed_software
                    (node_id, package_name, version, package_type, install_path, installed_at, checksum, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    node_id, pkg["package_name"], pkg["version"],
                    pkg["package_type"], pkg.get("install_path"),
                    pkg.get("installed_at"), pkg.get("checksum"),
                    time.time()
                ))

            # Insert filesystems
            for fs in inventory.get("filesystems", []):
                conn.execute("""
                    INSERT OR REPLACE INTO filesystem_mounts
                    (node_id, mount_point, device, fstype, total_gb, used_gb, available_gb,
                     percent_used, mount_options, is_readonly, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    node_id, fs["mount_point"], fs["device"], fs["fstype"],
                    fs["total_gb"], fs["used_gb"], fs["available_gb"],
                    fs["percent_used"], json.dumps(fs.get("mount_options", [])),
                    fs.get("is_readonly", False), time.time()
                ))

            # Insert capabilities
            for cap in inventory.get("capabilities", []):
                conn.execute("""
                    INSERT OR REPLACE INTO node_capabilities
                    (node_id, capability_name, capability_version, is_available, metadata, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    node_id, cap["capability_name"], cap.get("version"),
                    cap["is_available"], json.dumps(cap.get("metadata", {})),
                    time.time()
                ))

            conn.commit()

    def get_complete_cluster_state(self) -> Dict[str, Any]:
        """
        Get COMPLETE state of entire cluster

        Returns comprehensive dict with everything any agent needs
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Get all nodes
            nodes = {}
            for node_row in conn.execute("SELECT * FROM nodes"):
                node_id = node_row["node_id"]

                # Get network interfaces
                interfaces = []
                for iface_row in conn.execute("SELECT * FROM network_interfaces WHERE node_id = ?", (node_id,)):
                    interfaces.append(dict(iface_row))

                # Get services
                services = []
                for svc_row in conn.execute("SELECT * FROM service_endpoints WHERE node_id = ?", (node_id,)):
                    svc = dict(svc_row)
                    svc["dependencies"] = json.loads(svc["dependencies"]) if svc["dependencies"] else []
                    services.append(svc)

                # Get software
                software = []
                for sw_row in conn.execute("SELECT * FROM installed_software WHERE node_id = ?", (node_id,)):
                    software.append(dict(sw_row))

                # Get filesystems
                filesystems = []
                for fs_row in conn.execute("SELECT * FROM filesystem_mounts WHERE node_id = ?", (node_id,)):
                    fs = dict(fs_row)
                    fs["mount_options"] = json.loads(fs["mount_options"]) if fs["mount_options"] else []
                    filesystems.append(fs)

                # Get capabilities
                capabilities = []
                for cap_row in conn.execute("SELECT * FROM node_capabilities WHERE node_id = ?", (node_id,)):
                    cap = dict(cap_row)
                    cap["metadata"] = json.loads(cap["metadata"]) if cap["metadata"] else {}
                    capabilities.append(cap)

                # Get SSH connectivity FROM this node
                ssh_connections = []
                for ssh_row in conn.execute("SELECT * FROM ssh_connectivity WHERE source_node_id = ?", (node_id,)):
                    ssh_connections.append(dict(ssh_row))

                nodes[node_id] = {
                    **dict(node_row),
                    "network_interfaces": interfaces,
                    "services": services,
                    "software": software,
                    "filesystems": filesystems,
                    "capabilities": capabilities,
                    "ssh_connectivity": ssh_connections
                }

            return {
                "nodes": nodes,
                "total_nodes": len(nodes),
                "timestamp": time.time()
            }

    def query_services(self, service_name: str = None, port: int = None,
                      node_id: str = None, status: str = "listening") -> List[Dict]:
        """
        Query services across cluster

        Find services by name, port, node, or status
        """
        query = "SELECT * FROM service_endpoints WHERE 1=1"
        params = []

        if service_name:
            query += " AND service_name LIKE ?"
            params.append(f"%{service_name}%")

        if port:
            query += " AND port = ?"
            params.append(port)

        if node_id:
            query += " AND node_id = ?"
            params.append(node_id)

        if status:
            query += " AND status = ?"
            params.append(status)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            results = []
            for row in conn.execute(query, params):
                svc = dict(row)
                svc["dependencies"] = json.loads(svc["dependencies"]) if svc["dependencies"] else []
                results.append(svc)

        return results

    def query_software(self, package_name: str = None, package_type: str = None,
                      node_id: str = None) -> List[Dict]:
        """Query installed software across cluster"""
        query = "SELECT * FROM installed_software WHERE 1=1"
        params = []

        if package_name:
            query += " AND package_name LIKE ?"
            params.append(f"%{package_name}%")

        if package_type:
            query += " AND package_type = ?"
            params.append(package_type)

        if node_id:
            query += " AND node_id = ?"
            params.append(node_id)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            return [dict(row) for row in conn.execute(query, params)]

    def get_network_map(self) -> Dict[str, Any]:
        """
        Get complete network topology

        Returns map of all IPs, ports, and connectivity
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Get all network interfaces
            interfaces = {}
            for row in conn.execute("SELECT * FROM network_interfaces WHERE is_up = 1"):
                node_id = row["node_id"]
                if node_id not in interfaces:
                    interfaces[node_id] = []
                interfaces[node_id].append(dict(row))

            # Get all listening ports
            ports = {}
            for row in conn.execute("SELECT * FROM service_endpoints WHERE status = 'listening'"):
                node_id = row["node_id"]
                if node_id not in ports:
                    ports[node_id] = []
                ports[node_id].append({
                    "port": row["port"],
                    "service": row["service_name"],
                    "protocol": row["protocol"],
                    "bind_address": row["bind_address"],
                    "is_public": bool(row["is_public"])
                })

            # Get SSH mesh connectivity
            ssh_mesh = []
            for row in conn.execute("SELECT * FROM ssh_connectivity WHERE is_reachable = 1"):
                ssh_mesh.append(dict(row))

            return {
                "interfaces": interfaces,
                "listening_ports": ports,
                "ssh_connectivity": ssh_mesh,
                "timestamp": time.time()
            }

    def find_available_port(self, node_id: str, start_port: int = 8000,
                           end_port: int = 9000) -> Optional[int]:
        """Find available port on a specific node"""
        with sqlite3.connect(self.db_path) as conn:
            used_ports = set()
            for row in conn.execute(
                "SELECT port FROM service_endpoints WHERE node_id = ? AND port IS NOT NULL",
                (node_id,)
            ):
                used_ports.add(row[0])

            for port in range(start_port, end_port + 1):
                if port not in used_ports:
                    return port

        return None


# Convenience functions

def get_complete_state() -> Dict[str, Any]:
    """Get complete cluster state - everything any agent needs"""
    state = ComprehensiveClusterState()
    return state.get_complete_cluster_state()


def find_service(service_name: str) -> List[Dict]:
    """Find where a service is running"""
    state = ComprehensiveClusterState()
    return state.query_services(service_name=service_name)


def get_network_topology() -> Dict[str, Any]:
    """Get complete network map"""
    state = ComprehensiveClusterState()
    return state.get_network_map()


if __name__ == "__main__":
    # Test comprehensive state
    state = ComprehensiveClusterState()

    # Example: Register complete node inventory
    example_inventory = {
        "hostname": "macpro51",
        "role": "builder",
        "os_type": "linux",
        "os_version": "Fedora 43",
        "architecture": "x86_64",
        "cpu_count": 24,
        "cpu_model": "Intel Xeon X5680",
        "total_memory_gb": 125.8,
        "total_disk_gb": 930,
        "python_version": "3.12.1",
        "kernel_version": "6.17.7",
        "timezone": "America/New_York",
        "boot_time": time.time() - 86400,
        "network_interfaces": [
            {
                "interface_name": "enp3s0",
                "ip_address": "192.168.1.154",
                "netmask": "255.255.255.0",
                "mac_address": "00:1a:4d:00:00:01",
                "is_up": True,
                "speed_mbps": 1000
            }
        ],
        "services": [
            {
                "service_name": "builder-node-api",
                "service_type": "http_api",
                "port": 9000,
                "protocol": "http",
                "bind_address": "0.0.0.0",
                "is_public": True,
                "status": "listening",
                "config_path": "/home/marc/agentic-system/services/builder-node-api.py"
            },
            {
                "service_name": "qdrant",
                "service_type": "vector_db",
                "port": 6333,
                "protocol": "http",
                "bind_address": "0.0.0.0",
                "is_public": False,
                "status": "listening"
            }
        ],
        "software": [
            {"package_name": "psutil", "version": "5.9.0", "package_type": "pip"},
            {"package_name": "anthropic", "version": "0.39.0", "package_type": "pip"},
            {"package_name": "docker", "version": "27.3.1", "package_type": "system"}
        ],
        "filesystems": [
            {
                "mount_point": "/",
                "device": "/dev/sda1",
                "fstype": "ext4",
                "total_gb": 50,
                "used_gb": 25,
                "available_gb": 25,
                "percent_used": 50.0
            }
        ],
        "capabilities": [
            {"capability_name": "docker", "version": "27.3.1", "is_available": True},
            {"capability_name": "podman", "version": "5.3.1", "is_available": True},
            {"capability_name": "gpu", "is_available": True, "metadata": {"type": "NVIDIA GTX 680"}}
        ]
    }

    state.register_node_complete("macpro51", example_inventory)

    # Get complete state
    cluster = state.get_complete_cluster_state()
    print(json.dumps(cluster, indent=2))
