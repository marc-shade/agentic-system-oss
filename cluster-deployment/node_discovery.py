#!/usr/bin/env python3
"""
Node Discovery - Dynamic Hostname Resolution for Cluster Nodes

Instead of hardcoding IP addresses (which change via DHCP), this module
provides dynamic node discovery using multiple resolution methods:

1. Avahi/mDNS (.local hostnames)
2. DNS lookup
3. /etc/hosts entries  
4. Cached IP addresses (fallback)

No more hardcoded IPs! This is an opportunity to shine with smart discovery.
"""

import socket
import subprocess
import logging
from typing import Dict, Optional
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class NodeDiscovery:
    """
    Dynamically discover cluster nodes without hardcoded IPs

    Uses multiple resolution methods in priority order:
    1. Avahi/mDNS (.local)
    2. DNS lookup
    3. IP cache (refreshed regularly)
    """

    def __init__(self, cache_file: Optional[Path] = None):
        """
        Initialize node discovery

        Args:
            cache_file: Optional path to cache discovered IPs
        """
        self.cache_file = cache_file or Path.home() / ".agentic/node_ip_cache.json"
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.ip_cache = self._load_cache()

        # Known hostnames (NOT IPs!)
        self.known_nodes = {
            "macpro51": {
                "hostnames": ["macpro51.local", "macpro51"],
                "user": "marc",
                "role": "builder"
            },
            "mac-studio": {
                "hostnames": ["mac-studio.local", "Mac-Studio.local", "mac-studio"],
                "user": "marc",
                "role": "orchestrator"
            },
            "macbook-air": {
                "hostnames": ["macbook-air.local", "MacBook-Air.local", "Mac.fios-router.home", "macbook-air"],
                "user": "marc",
                "role": "researcher"
            },
            "completeu-server": {
                "hostnames": ["completeu-server.local", "completeu-server"],
                "user": "marc",
                "role": "ai-inference"
            }
        }

    def _load_cache(self) -> Dict[str, str]:
        """Load cached IP addresses"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file) as f:
                    cache = json.load(f)
                    logger.debug(f"Loaded IP cache with {len(cache)} entries")
                    return cache
        except Exception as e:
            logger.warning(f"Failed to load IP cache: {e}")
        return {}

    def _save_cache(self):
        """Save IP cache to disk"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.ip_cache, f, indent=2)
            logger.debug(f"Saved IP cache with {len(self.ip_cache)} entries")
        except Exception as e:
            logger.warning(f"Failed to save IP cache: {e}")

    def resolve_node_ip(self, node_id: str) -> Optional[str]:
        """
        Resolve node IP address dynamically

        Tries multiple methods in order:
        1. Avahi/mDNS (.local)
        2. Standard DNS
        3. Cached IP (if still reachable)

        Args:
            node_id: Node identifier (e.g., "macpro51")

        Returns:
            IP address if resolved, None otherwise
        """
        if node_id not in self.known_nodes:
            logger.warning(f"Unknown node: {node_id}")
            return None

        node_info = self.known_nodes[node_id]

        # Try each hostname in order
        for hostname in node_info["hostnames"]:
            # Method 1: Try DNS/mDNS resolution
            ip = self._resolve_via_dns(hostname)
            if ip:
                logger.info(f"✓ Resolved {node_id} via DNS: {hostname} -> {ip}")
                self.ip_cache[node_id] = ip
                self._save_cache()
                return ip

            # Method 2: Try Avahi service discovery
            ip = self._resolve_via_avahi(hostname)
            if ip:
                logger.info(f"✓ Resolved {node_id} via Avahi: {hostname} -> {ip}")
                self.ip_cache[node_id] = ip
                self._save_cache()
                return ip

        # Method 3: Try cached IP (if still reachable)
        if node_id in self.ip_cache:
            cached_ip = self.ip_cache[node_id]
            if self._is_reachable(cached_ip):
                logger.info(f"✓ Using cached IP for {node_id}: {cached_ip}")
                return cached_ip
            else:
                logger.warning(f"Cached IP for {node_id} no longer reachable: {cached_ip}")
                del self.ip_cache[node_id]
                self._save_cache()

        logger.error(f"✗ Failed to resolve {node_id} via any method")
        return None

    def _resolve_via_dns(self, hostname: str) -> Optional[str]:
        """Resolve hostname via DNS/mDNS"""
        try:
            ip = socket.gethostbyname(hostname)
            return ip
        except socket.gaierror:
            return None

    def _resolve_via_avahi(self, hostname: str) -> Optional[str]:
        """
        Resolve hostname via Avahi service discovery

        Uses avahi-resolve command for mDNS lookup
        """
        try:
            result = subprocess.run(
                ["avahi-resolve", "-n", hostname],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                # Output format: "hostname\tIP"
                parts = result.stdout.strip().split('\t')
                if len(parts) == 2:
                    return parts[1]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return None

    def _is_reachable(self, ip: str, timeout: float = 2.0) -> bool:
        """Check if IP is reachable via ping"""
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", str(int(timeout)), ip],
                capture_output=True,
                timeout=timeout + 1
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def get_all_nodes(self) -> Dict[str, Dict[str, str]]:
        """
        Get all known nodes with resolved IPs

        Returns:
            Dict mapping node_id to {ip, user, role, db_path}
        """
        nodes = {}

        for node_id, node_info in self.known_nodes.items():
            ip = self.resolve_node_ip(node_id)

            if ip:
                nodes[node_id] = {
                    "ip": ip,
                    "user": node_info["user"],
                    "role": node_info["role"],
                    "db_path": self._get_db_path(node_id)
                }

        logger.info(f"Discovered {len(nodes)}/{len(self.known_nodes)} nodes")
        return nodes

    def _get_db_path(self, node_id: str) -> str:
        """Get database path for node (platform-specific)"""
        if node_id == "macpro51":
            return "/mnt/agentic-system/databases/cluster/comprehensive_state.db"
        else:
            return "~/agentic-system/databases/cluster/comprehensive_state.db"

    def refresh_cache(self):
        """Force refresh of all cached IPs"""
        logger.info("Refreshing IP cache for all nodes...")
        self.ip_cache.clear()
        self.get_all_nodes()
        logger.info("IP cache refreshed")


def main():
    """Demo node discovery"""
    import logging
    logging.basicConfig(level=logging.INFO)

    print("\n" + "="*60)
    print("NODE DISCOVERY DEMONSTRATION")
    print("="*60 + "\n")

    discovery = NodeDiscovery()

    print("Discovering all cluster nodes dynamically...")
    print("(No hardcoded IPs!)\n")

    nodes = discovery.get_all_nodes()

    print(f"\nDiscovered {len(nodes)} nodes:\n")
    for node_id, info in sorted(nodes.items()):
        print(f"  • {node_id} ({info['role']})")
        print(f"    IP: {info['ip']}")
        print(f"    User: {info['user']}")
        print(f"    DB: {info['db_path']}")
        print()

    if len(nodes) < len(discovery.known_nodes):
        print(f"⚠️  {len(discovery.known_nodes) - len(nodes)} nodes could not be reached")
        unreachable = set(discovery.known_nodes.keys()) - set(nodes.keys())
        for node_id in unreachable:
            print(f"  ✗ {node_id}")

    print("\n" + "="*60)
    print(f"Cache file: {discovery.cache_file}")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
