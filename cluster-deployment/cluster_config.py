#!/usr/bin/env python3
"""
Cluster Configuration Loader

Reads cluster node configuration from cluster-nodes.toon and provides
helper functions for node discovery and management.
"""

import socket
from pathlib import Path
from typing import Dict, List, Optional
from toon_config import load_config, save_config

def get_cluster_config(config_path: Optional[str] = None) -> Dict:
    """Load cluster node configuration"""
    if config_path is None:
        # Try multiple possible locations (SSDRAID0 first - see FILE_LOCATION_POLICY.md)
        possible_paths = [
            Path("/Volumes/SSDRAID0/agentic-system/cluster-deployment/cluster-nodes.toon"),
            Path("/mnt/agentic-system/cluster-deployment/cluster-nodes.toon"),
            Path.home() / "agentic-system" / "cluster-deployment" / "cluster-nodes.toon"
        ]

        for path in possible_paths:
            if path.exists():
                config_path = str(path)
                break

    if config_path is None:
        raise FileNotFoundError("Could not find cluster-nodes.toon configuration")

    return load_config(config_path)

def get_local_node_id() -> str:
    """Detect which cluster node we're running on"""
    hostname = socket.gethostname().lower()

    # Match hostname to node ID
    if "macpro" in hostname or "mac-pro" in hostname:
        return "macpro51"
    elif "mac-studio" in hostname or "macstudio" in hostname:
        return "mac-studio"
    elif "macbook-air" in hostname or "macbook" in hostname:
        return "macbook-air-m3"
    else:
        # Fallback to IP detection
        import subprocess
        try:
            result = subprocess.run(['hostname', '-I'], capture_output=True, text=True, timeout=2)
            ip = result.stdout.strip().split()[0]

            if ip.startswith("192.168.1.183"):
                return "macpro51"
            elif ip.startswith("192.168.1.16"):
                return "mac-studio"
            elif ip.startswith("192.168.1.76"):
                return "macbook-air-m3"
        except:
            pass

    raise RuntimeError(f"Could not determine node ID from hostname: {hostname}")

def get_other_nodes(config: Optional[Dict] = None) -> Dict[str, Dict]:
    """Get all cluster nodes except the local node"""
    if config is None:
        config = get_cluster_config()

    local_node_id = get_local_node_id()
    nodes = config.get('nodes', {})

    # Return all nodes except local
    return {
        node_id: node_config
        for node_id, node_config in nodes.items()
        if node_id != local_node_id
    }

def get_node_config(node_id: str, config: Optional[Dict] = None) -> Dict:
    """Get configuration for a specific node"""
    if config is None:
        config = get_cluster_config()

    nodes = config.get('nodes', {})
    if node_id not in nodes:
        raise KeyError(f"Node {node_id} not found in cluster configuration")

    return nodes[node_id]

def get_all_nodes(config: Optional[Dict] = None) -> Dict[str, Dict]:
    """Get all cluster nodes"""
    if config is None:
        config = get_cluster_config()

    return config.get('nodes', {})

def get_discovery_config(config: Optional[Dict] = None) -> Dict:
    """Get discovery configuration (SSH settings, etc.)"""
    if config is None:
        config = get_cluster_config()

    return config.get('discovery', {})

# Example usage
if __name__ == "__main__":
    print("Cluster Configuration Test")
    print("=" * 50)

    try:
        # Load configuration
        config = get_cluster_config()
        print(f"✓ Loaded cluster configuration")

        # Detect local node
        local_node = get_local_node_id()
        print(f"✓ Local node: {local_node}")

        # Get local node config
        local_config = get_node_config(local_node)
        print(f"✓ Local node config: {local_config['hostname']}, {local_config['role']}")

        # Get other nodes
        other_nodes = get_other_nodes()
        print(f"✓ Other nodes in cluster: {list(other_nodes.keys())}")

        # Show all nodes
        print("\nAll Cluster Nodes:")
        for node_id, node_config in get_all_nodes().items():
            marker = " (LOCAL)" if node_id == local_node else ""
            print(f"  {node_id}{marker}:")
            print(f"    IP: {node_config['ip']}")
            print(f"    Role: {node_config['role']}")
            print(f"    Storage: {node_config['storage_base']}")

    except Exception as e:
        print(f"✗ Error: {e}")
