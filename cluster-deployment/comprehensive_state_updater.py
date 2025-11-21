#!/usr/bin/env python3
"""
Comprehensive State Updater - Keeps Cluster State 100% Accurate

Runs continuously in the background to:
- Update node inventory every 5 minutes
- Monitor for service changes (new/stopped services)
- Track software installations/removals
- Update network interface status
- Test SSH connectivity
- Keep comprehensive state always current

Ensures the single source of truth is ALWAYS accurate.
"""

import time
import signal
import sys
import logging
from pathlib import Path
from collect_node_inventory import NodeInventoryCollector
from comprehensive_cluster_state import ComprehensiveClusterState
import socket


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path.home() / "agentic-system/logs/comprehensive_state_updater.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("comprehensive-state-updater")


class ComprehensiveStateUpdater:
    """Daemon that keeps comprehensive cluster state up-to-date"""

    def __init__(self, node_id: str, role: str, update_interval: int = 300):
        """
        Args:
            node_id: This node's identifier
            role: This node's role in cluster
            update_interval: Seconds between full inventory updates (default: 300 = 5 minutes)
        """
        self.node_id = node_id
        self.role = role
        self.update_interval = update_interval
        self.running = False
        self.collector = NodeInventoryCollector(node_id, role)
        self.state = ComprehensiveClusterState()

        # Known nodes (will be updated from state)
        self.known_nodes = {
            "mac-studio": "192.168.1.157",
            "macbook-air": "192.168.1.76",
            "macpro51": "192.168.1.154",
            "completeu-server": "192.168.1.186",
        }

    def start(self):
        """Start the updater daemon"""
        self.running = True
        logger.info(f"🚀 Starting comprehensive state updater for {self.node_id}")
        logger.info(f"   Update interval: {self.update_interval} seconds")

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        # Initial inventory collection
        self._update_inventory()

        # Main update loop
        while self.running:
            try:
                time.sleep(self.update_interval)

                if self.running:
                    self._update_inventory()

            except Exception as e:
                logger.error(f"❌ Error in update loop: {e}", exc_info=True)
                time.sleep(60)  # Wait a minute before retrying

    def _update_inventory(self):
        """Collect and update complete node inventory"""
        try:
            logger.info("🔄 Updating node inventory...")

            # Collect complete inventory
            inventory = self.collector.collect_complete_inventory()

            # Update known nodes from state
            self._refresh_known_nodes()

            # Test SSH connectivity
            logger.info("🔌 Testing SSH connectivity...")
            ssh_connectivity = self.collector.test_ssh_connectivity(self.known_nodes)
            inventory["ssh_connectivity"] = ssh_connectivity

            # Register in comprehensive state
            logger.info("💾 Updating comprehensive cluster state...")
            self.state.register_node_complete(self.node_id, inventory)

            logger.info(f"✅ Inventory updated successfully")
            logger.info(f"   Services: {len(inventory['services'])}")
            logger.info(f"   Software: {len(inventory['software'])}")
            logger.info(f"   SSH connectivity: {sum(1 for s in ssh_connectivity if s['has_key_auth'])} reachable")

        except Exception as e:
            logger.error(f"❌ Failed to update inventory: {e}", exc_info=True)

    def _refresh_known_nodes(self):
        """Refresh known nodes list from comprehensive state"""
        try:
            cluster_state = self.state.get_complete_cluster_state()

            for node_id, node_info in cluster_state.get("nodes", {}).items():
                # Get primary IP from network interfaces
                interfaces = node_info.get("network_interfaces", [])
                for iface in interfaces:
                    ip = iface.get("ip_address")
                    # Skip loopback
                    if ip and not ip.startswith("127."):
                        self.known_nodes[node_id] = ip
                        break

        except Exception as e:
            logger.warning(f"⚠️ Could not refresh known nodes: {e}")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"🛑 Received signal {signum}, shutting down...")
        self.running = False
        sys.exit(0)


def main():
    """Main entry point"""
    # Detect node identity
    hostname = socket.gethostname()

    # Map hostname to node_id and role
    node_map = {
        "macpro51": ("macpro51", "builder"),
        "Mac-Studio": ("mac-studio", "orchestrator"),
        "MacBook-Air": ("macbook-air", "researcher"),
        "Mac.fios-router.home": ("macbook-air", "researcher"),  # MacBook Air alternate hostname
        "completeu-server": ("completeu-server", "ai-inference"),
        "completeu-server.local": ("completeu-server", "ai-inference"),
    }

    node_id, role = node_map.get(hostname, (hostname, "worker"))

    # Create and start updater
    updater = ComprehensiveStateUpdater(node_id, role, update_interval=300)
    updater.start()


if __name__ == "__main__":
    main()
