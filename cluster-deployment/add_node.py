#!/usr/bin/env python3
"""
Add Node to GitMQ Cluster
=========================

Easy tool for registering new nodes to the cluster and testing connectivity.

Usage:
    # Add a new node
    python3 add_node.py --node-id macbook-pro --ip 192.168.1.100 --role developer

    # Discover nodes on network
    python3 add_node.py --discover

    # Test connectivity to all nodes
    python3 add_node.py --test-all
"""

import argparse
import json
import socket
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Node registry database
CLUSTER_DB = Path("/mnt/agentic-system/databases/cluster/node_registry.db")
NODE_CONFIG = Path.home() / ".claude/node-config.json"


def discover_nodes() -> List[Dict[str, str]]:
    """Discover agentic nodes on local network via Avahi."""
    print("🔍 Discovering nodes on local network...")

    try:
        result = subprocess.run(
            ["avahi-browse", "-t", "-p", "_agentic-builder._tcp"],
            capture_output=True,
            text=True,
            timeout=5
        )

        nodes = []
        for line in result.stdout.split('\n'):
            if line.startswith('='):
                parts = line.split(';')
                if len(parts) >= 9:
                    nodes.append({
                        "name": parts[3],
                        "ip": parts[7],
                        "port": parts[8],
                        "type": "builder"
                    })

        return nodes
    except Exception as e:
        print(f"⚠️  Discovery failed: {e}")
        return []


def test_node_connectivity(node_id: str, ip: str, port: int = 9000) -> bool:
    """Test if node is reachable."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def register_node(node_id: str, ip: str, port: int, role: str):
    """Register a new node in the cluster."""
    import sqlite3

    # Ensure database directory exists
    CLUSTER_DB.parent.mkdir(parents=True, exist_ok=True)

    # Initialize database if needed (use existing schema)
    with sqlite3.connect(CLUSTER_DB) as conn:
        # Add port column if it doesn't exist
        try:
            conn.execute("ALTER TABLE nodes ADD COLUMN port INTEGER DEFAULT 9000")
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Insert or update node
        conn.execute("""
            INSERT INTO nodes (node_id, hostname, ip_address, persona_name, persona_id, specialty, port)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(node_id) DO UPDATE SET
                ip_address = excluded.ip_address,
                port = excluded.port,
                specialty = excluded.specialty,
                last_heartbeat = CURRENT_TIMESTAMP
        """, (node_id, node_id, ip, role.title(), node_id, role, port))

        conn.commit()

    print(f"✅ Registered node: {node_id} ({role}) at {ip}:{port}")


def get_all_nodes() -> List[Dict]:
    """Get all registered nodes."""
    import sqlite3

    if not CLUSTER_DB.exists():
        return []

    with sqlite3.connect(CLUSTER_DB) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM nodes ORDER BY node_id")
        return [dict(row) for row in cursor]


def test_all_nodes():
    """Test connectivity to all registered nodes."""
    nodes = get_all_nodes()

    if not nodes:
        print("⚠️  No nodes registered yet")
        return

    print(f"\n🔗 Testing {len(nodes)} registered nodes...\n")

    for node in nodes:
        node_id = node['node_id']
        ip = node['ip_address']
        port = node['port']
        role = node['role']

        print(f"Testing {node_id} ({role})...", end=" ")

        if test_node_connectivity(node_id, ip, port):
            print("✅ Online")
        else:
            print("❌ Offline")


def show_cluster_status():
    """Show current cluster status."""
    nodes = get_all_nodes()

    if not nodes:
        print("⚠️  No nodes registered")
        return

    print("\n📊 Cluster Status\n")
    print(f"{'Node ID':<20} {'Role':<15} {'Address':<25} {'Status':<10}")
    print("=" * 70)

    for node in nodes:
        role = node.get('specialty') or node.get('role', 'unknown')
        port = node.get('port', 9000)
        status = "✅ Online" if test_node_connectivity(
            node['node_id'],
            node['ip_address'],
            port
        ) else "❌ Offline"

        print(f"{node['node_id']:<20} {role:<15} "
              f"{node['ip_address']}:{port:<20} {status:<10}")


def get_local_ip() -> str:
    """Get local IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip


def init_current_node():
    """Initialize current node and register it."""
    # Get node config
    if NODE_CONFIG.exists():
        with open(NODE_CONFIG) as f:
            config = json.load(f)
            node_id = config.get('node_id', socket.gethostname())
            role = config.get('role', 'worker')
    else:
        node_id = socket.gethostname()
        role = 'worker'

    ip = get_local_ip()
    port = 9000  # Default builder API port

    print(f"🚀 Initializing node: {node_id}")
    print(f"   Role: {role}")
    print(f"   IP: {ip}:{port}")

    register_node(node_id, ip, port, role)

    print(f"\n✅ Node {node_id} registered successfully!")
    print(f"   Other nodes can connect at: http://{ip}:{port}")


def main():
    parser = argparse.ArgumentParser(
        description="Add and manage nodes in GitMQ cluster"
    )

    parser.add_argument("--node-id", help="Node identifier")
    parser.add_argument("--ip", help="Node IP address")
    parser.add_argument("--port", type=int, default=9000, help="Node port (default: 9000)")
    parser.add_argument("--role", choices=["orchestrator", "worker", "builder", "researcher"],
                       help="Node role")

    parser.add_argument("--discover", action="store_true",
                       help="Discover nodes via Avahi")
    parser.add_argument("--test-all", action="store_true",
                       help="Test connectivity to all nodes")
    parser.add_argument("--status", action="store_true",
                       help="Show cluster status")
    parser.add_argument("--init", action="store_true",
                       help="Initialize current node")

    args = parser.parse_args()

    # Handle commands
    if args.init:
        init_current_node()

    elif args.discover:
        nodes = discover_nodes()
        print(f"\n✅ Found {len(nodes)} nodes:\n")
        for node in nodes:
            print(f"  - {node['name']} at {node['ip']}:{node['port']}")

    elif args.test_all:
        test_all_nodes()

    elif args.status:
        show_cluster_status()

    elif args.node_id and args.ip and args.role:
        register_node(args.node_id, args.ip, args.port, args.role)

    else:
        parser.print_help()
        print("\n💡 Quick start:")
        print("   1. Initialize current node:  python3 add_node.py --init")
        print("   2. Show cluster status:      python3 add_node.py --status")
        print("   3. Test all nodes:           python3 add_node.py --test-all")


if __name__ == "__main__":
    main()
