#!/usr/bin/env python3
"""
Cluster Sentinel Service
Always-on monitoring and coordination for agentic cluster

Responsibilities:
- Health check all cluster nodes
- Service discovery maintenance
- Wake-on-LAN coordination
- Performance pattern learning
- Alert on node failures
"""

import sys
import time
import socket
import subprocess
import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests

# Add cluster deployment to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'cluster-deployment'))
from toon_config import load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/var/log/cluster-sentinel.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ClusterSentinel:
    """Always-on cluster monitoring and coordination"""

    def __init__(self, config_path: str = None):
        """Initialize sentinel with configuration"""
        config_path = config_path or str(Path.home() / '.claude' / 'node-config')
        self.config = load_config(config_path)

        self.node_id = self.config.get('node_id', 'bpi-sentinel')
        self.check_interval = self.config.get('services', {}).get('cluster_sentinel', {}).get('check_interval_seconds', 30)
        self.alert_threshold = self.config.get('services', {}).get('cluster_sentinel', {}).get('alert_threshold_failures', 3)

        # Get cluster database paths
        agentic_root = Path.home() / 'agentic-system'
        self.node_registry_db = agentic_root / 'databases' / 'cluster' / 'node_registry.db'
        self.shared_memory_db = agentic_root / 'databases' / 'cluster' / 'shared_memories.db'

        # Track node failures
        self.failure_counts: Dict[str, int] = {}
        self.last_seen: Dict[str, datetime] = {}
        self.performance_log: List[Dict] = []

        logger.info(f"Cluster Sentinel initialized: {self.node_id}")

    def get_peer_nodes(self) -> List[Dict]:
        """Get list of peer nodes from configuration"""
        peers = self.config.get('cluster', {}).get('peer_nodes', [])
        return [
            {
                'node_id': p.split(',')[0].split(':')[1].strip(),
                'ip': p.split(',')[1].split(':')[1].strip(),
                'role': p.split(',')[2].split(':')[1].strip(),
                'arch': p.split(',')[3].split(':')[1].strip()
            }
            for p in peers
        ]

    def ping_node(self, ip: str, timeout: int = 2) -> bool:
        """Ping a node to check if it's alive"""
        try:
            result = subprocess.run(
                ['ping', '-c', '1', '-W', str(timeout), ip],
                capture_output=True,
                timeout=timeout + 1
            )
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"Ping failed for {ip}: {e}")
            return False

    def check_ssh(self, ip: str, timeout: int = 5) -> bool:
        """Check if SSH is accessible"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, 22))
            sock.close()
            return result == 0
        except Exception as e:
            logger.warning(f"SSH check failed for {ip}: {e}")
            return False

    def check_node_api(self, node: Dict) -> Optional[Dict]:
        """Check node API endpoint if available"""
        # Builder nodes have API on port 9000
        if node['role'] == 'builder':
            try:
                response = requests.get(
                    f"http://{node['ip']}:9000/api/v1/status",
                    timeout=3
                )
                if response.status_code == 200:
                    return response.json()
            except Exception as e:
                logger.debug(f"API check failed for {node['node_id']}: {e}")
        return None

    def check_node_health(self, node: Dict) -> Dict:
        """Comprehensive health check for a node"""
        node_id = node['node_id']
        ip = node['ip']

        health = {
            'node_id': node_id,
            'timestamp': datetime.now().isoformat(),
            'ping': False,
            'ssh': False,
            'api': None,
            'status': 'down',
            'response_time_ms': None
        }

        # Ping test
        start = time.time()
        health['ping'] = self.ping_node(ip)

        if health['ping']:
            health['response_time_ms'] = int((time.time() - start) * 1000)

            # SSH test
            health['ssh'] = self.check_ssh(ip)

            # API test
            health['api'] = self.check_node_api(node)

            # Overall status
            if health['ssh']:
                health['status'] = 'online'
            else:
                health['status'] = 'degraded'
        else:
            health['status'] = 'down'

        return health

    def update_node_registry(self, health_results: List[Dict]):
        """Update node registry with health check results"""
        try:
            conn = sqlite3.connect(str(self.node_registry_db))
            cursor = conn.cursor()

            for health in health_results:
                cursor.execute("""
                    UPDATE nodes
                    SET status = ?,
                        last_seen = ?,
                        metadata = json_set(
                            COALESCE(metadata, '{}'),
                            '$.last_health_check',
                            ?
                        )
                    WHERE node_id = ?
                """, (
                    health['status'],
                    health['timestamp'],
                    json.dumps(health),
                    health['node_id']
                ))

            conn.commit()
            conn.close()
            logger.debug(f"Updated node registry with {len(health_results)} health checks")
        except Exception as e:
            logger.error(f"Failed to update node registry: {e}")

    def log_performance_pattern(self, node_id: str, response_time_ms: int):
        """Log node performance for pattern learning"""
        self.performance_log.append({
            'node_id': node_id,
            'timestamp': datetime.now().isoformat(),
            'response_time_ms': response_time_ms,
            'hour_of_day': datetime.now().hour,
            'day_of_week': datetime.now().weekday()
        })

        # Keep only last 24 hours
        cutoff = datetime.now() - timedelta(hours=24)
        self.performance_log = [
            p for p in self.performance_log
            if datetime.fromisoformat(p['timestamp']) > cutoff
        ]

    def detect_failure(self, node_id: str, health: Dict):
        """Detect and handle node failures"""
        if health['status'] == 'down':
            self.failure_counts[node_id] = self.failure_counts.get(node_id, 0) + 1

            if self.failure_counts[node_id] >= self.alert_threshold:
                self.alert_node_failure(node_id, health)
        else:
            # Node recovered
            if self.failure_counts.get(node_id, 0) > 0:
                logger.info(f"✓ Node {node_id} recovered after {self.failure_counts[node_id]} failures")
                self.alert_node_recovery(node_id, health)
            self.failure_counts[node_id] = 0
            self.last_seen[node_id] = datetime.now()

    def alert_node_failure(self, node_id: str, health: Dict):
        """Alert on node failure by storing in cluster memory"""
        try:
            conn = sqlite3.connect(str(self.shared_memory_db))
            cursor = conn.cursor()

            alert = {
                'type': 'node_failure',
                'severity': 'critical',
                'node_id': node_id,
                'failure_count': self.failure_counts[node_id],
                'last_seen': self.last_seen.get(node_id, datetime.now()).isoformat(),
                'health_check': health
            }

            cursor.execute("""
                INSERT INTO entities (name, entity_type, observations, node_id, created_at, updated_at)
                VALUES (?, 'alert', ?, ?, datetime('now'), datetime('now'))
            """, (
                f"node_failure_{node_id}_{int(time.time())}",
                json.dumps([json.dumps(alert)]),
                self.node_id
            ))

            conn.commit()
            conn.close()

            logger.error(f"⚠️  ALERT: Node {node_id} DOWN (failures: {self.failure_counts[node_id]})")
        except Exception as e:
            logger.error(f"Failed to store alert: {e}")

    def alert_node_recovery(self, node_id: str, health: Dict):
        """Alert on node recovery"""
        try:
            conn = sqlite3.connect(str(self.shared_memory_db))
            cursor = conn.cursor()

            alert = {
                'type': 'node_recovery',
                'severity': 'info',
                'node_id': node_id,
                'recovered_at': datetime.now().isoformat(),
                'health_check': health
            }

            cursor.execute("""
                INSERT INTO entities (name, entity_type, observations, node_id, created_at, updated_at)
                VALUES (?, 'alert', ?, ?, datetime('now'), datetime('now'))
            """, (
                f"node_recovery_{node_id}_{int(time.time())}",
                json.dumps([json.dumps(alert)]),
                self.node_id
            ))

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to store recovery alert: {e}")

    def run_health_check_cycle(self):
        """Run one complete health check cycle"""
        logger.info("Starting health check cycle...")

        peers = self.get_peer_nodes()
        health_results = []

        for node in peers:
            logger.debug(f"Checking {node['node_id']} ({node['ip']})...")
            health = self.check_node_health(node)
            health_results.append(health)

            # Log performance
            if health['response_time_ms']:
                self.log_performance_pattern(node['node_id'], health['response_time_ms'])

            # Detect failures
            self.detect_failure(node['node_id'], health)

            # Log status
            status_icon = "✓" if health['status'] == 'online' else "⚠️" if health['status'] == 'degraded' else "✗"
            logger.info(f"{status_icon} {node['node_id']}: {health['status']} ({health['response_time_ms']}ms)")

        # Update registry
        self.update_node_registry(health_results)

        logger.info(f"Health check cycle complete. {len([h for h in health_results if h['status'] == 'online'])}/{len(peers)} nodes online")

    def run(self):
        """Main sentinel loop"""
        logger.info(f"🛡️  Cluster Sentinel starting (check interval: {self.check_interval}s)")

        try:
            while True:
                try:
                    self.run_health_check_cycle()
                except Exception as e:
                    logger.error(f"Error in health check cycle: {e}", exc_info=True)

                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            logger.info("Sentinel shutting down gracefully...")
        except Exception as e:
            logger.error(f"Fatal error in sentinel: {e}", exc_info=True)
            raise


def main():
    """Entry point"""
    sentinel = ClusterSentinel()
    sentinel.run()


if __name__ == '__main__':
    main()
