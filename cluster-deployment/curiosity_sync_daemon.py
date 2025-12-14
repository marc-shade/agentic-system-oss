#!/usr/bin/env python3
"""
Curiosity Sync Daemon - Autonomous Feature Propagation
=======================================================

This daemon orchestrates the complete curiosity-driven feature propagation
cycle across all cluster nodes.

The cycle:
1. Generate/update node identity (self-awareness)
2. Scan peer identities (peer discovery)
3. Generate desires for missing features (curiosity)
4. Export local features for peers (sharing)
5. Process fulfillment queue (integration)
6. Report status to cluster memory

Run this daemon on each node to enable autonomous feature sharing.
Each node will:
- Share what it has with others
- Discover what others have
- Desire what it's missing
- Adapt and integrate new features

Usage:
    python3 curiosity_sync_daemon.py           # Run once
    python3 curiosity_sync_daemon.py --daemon  # Run as daemon with interval
    python3 curiosity_sync_daemon.py --interval 300  # Custom interval (seconds)
"""

import argparse
import json
import sqlite3
import time
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import logging

# Import component modules
from node_identity_service import NodeIdentityService, _get_storage_base
from curiosity_engine import CuriosityEngine
from integration_agent import IntegrationAgent

STORAGE_BASE = _get_storage_base()
DB_PATH = Path(STORAGE_BASE) / "databases" / "cluster" / "node_registry.db"
LOG_DIR = Path(STORAGE_BASE) / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(str(LOG_DIR / 'curiosity-sync.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("curiosity-sync")


class CuriositySyncDaemon:
    """
    Orchestrates the complete curiosity-driven sync cycle.

    Components:
    - NodeIdentityService: Self-awareness
    - CuriosityEngine: Peer comparison and desire generation
    - IntegrationAgent: Feature adaptation and installation
    """

    def __init__(self):
        self.identity_service = NodeIdentityService()
        self.curiosity_engine = CuriosityEngine()
        self.integration_agent = IntegrationAgent()

        self.node_id = self.identity_service.node_id
        self.running = True

        # Statistics
        self.cycles_completed = 0
        self.total_desires_generated = 0
        self.total_features_integrated = 0

        logger.info(f"Curiosity Sync Daemon initialized for {self.node_id}")

    def run_cycle(self) -> Dict[str, Any]:
        """
        Run a complete sync cycle.

        Steps:
        1. Update identity (self-awareness)
        2. Scan peers (discovery)
        3. Generate desires (curiosity)
        4. Export features (sharing)
        5. Process fulfillment (integration)
        """
        cycle_start = datetime.now()
        cycle_result = {
            "node_id": self.node_id,
            "started_at": cycle_start.isoformat(),
            "steps": {}
        }

        logger.info(f"Starting sync cycle for {self.node_id}")

        # Step 1: Update identity
        try:
            logger.info("Step 1: Updating node identity...")
            identity = self.identity_service.generate_identity()
            self.identity_service.save_identity()
            cycle_result["steps"]["identity"] = {
                "success": True,
                "identity_hash": identity.get("identity_hash"),
                "capabilities": len(identity.get("capabilities", {}).get("detected_capabilities", []))
            }
        except Exception as e:
            logger.error(f"Identity update failed: {e}")
            cycle_result["steps"]["identity"] = {"success": False, "error": str(e)}

        # Step 2: Scan peers
        try:
            logger.info("Step 2: Scanning peer nodes...")
            scan_result = self.curiosity_engine.scan_peers()
            cycle_result["steps"]["peer_scan"] = {
                "success": True,
                "peers_found": scan_result.get("peers_found", 0),
                "total_gaps": scan_result.get("total_gaps", 0),
                "new_desires": scan_result.get("new_desires", 0)
            }
            self.total_desires_generated += scan_result.get("new_desires", 0)
        except Exception as e:
            logger.error(f"Peer scan failed: {e}")
            cycle_result["steps"]["peer_scan"] = {"success": False, "error": str(e)}

        # Step 3: Export local features
        try:
            logger.info("Step 3: Exporting local features...")
            exported = self.integration_agent.export_local_features()
            total_exported = (
                len(exported.get("features", {}).get("skills", [])) +
                len(exported.get("features", {}).get("agents", [])) +
                len(exported.get("features", {}).get("commands", [])) +
                len(exported.get("features", {}).get("hook_helpers", []))
            )
            cycle_result["steps"]["export"] = {
                "success": True,
                "total_exported": total_exported,
                "features": exported.get("features", {})
            }
        except Exception as e:
            logger.error(f"Feature export failed: {e}")
            cycle_result["steps"]["export"] = {"success": False, "error": str(e)}

        # Step 4: Process fulfillment queue
        try:
            logger.info("Step 4: Processing fulfillment queue...")
            fulfillment = self.integration_agent.process_fulfillment_queue()
            cycle_result["steps"]["fulfillment"] = {
                "success": True,
                "queue_size": fulfillment.get("total_in_queue", 0),
                "attempted": fulfillment.get("attempted", 0),
                "successful": fulfillment.get("successful", 0),
                "failed": fulfillment.get("failed", 0)
            }
            self.total_features_integrated += fulfillment.get("successful", 0)
        except Exception as e:
            logger.error(f"Fulfillment processing failed: {e}")
            cycle_result["steps"]["fulfillment"] = {"success": False, "error": str(e)}

        # Step 5: Report status
        try:
            logger.info("Step 5: Reporting cycle status...")
            self._save_cycle_result(cycle_result)
        except Exception as e:
            logger.error(f"Status reporting failed: {e}")

        # Complete
        cycle_end = datetime.now()
        cycle_result["completed_at"] = cycle_end.isoformat()
        cycle_result["duration_seconds"] = (cycle_end - cycle_start).total_seconds()

        self.cycles_completed += 1

        logger.info(f"Sync cycle completed in {cycle_result['duration_seconds']:.2f}s")
        return cycle_result

    def _save_cycle_result(self, result: Dict):
        """Save cycle result to cluster database"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_cycles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                duration_seconds REAL,
                peers_found INTEGER,
                gaps_identified INTEGER,
                desires_generated INTEGER,
                features_exported INTEGER,
                features_integrated INTEGER,
                full_result_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        steps = result.get("steps", {})
        cursor.execute("""
            INSERT INTO sync_cycles
            (node_id, started_at, completed_at, duration_seconds,
             peers_found, gaps_identified, desires_generated,
             features_exported, features_integrated, full_result_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result["node_id"],
            result["started_at"],
            result.get("completed_at"),
            result.get("duration_seconds"),
            steps.get("peer_scan", {}).get("peers_found", 0),
            steps.get("peer_scan", {}).get("total_gaps", 0),
            steps.get("peer_scan", {}).get("new_desires", 0),
            steps.get("export", {}).get("total_exported", 0),
            steps.get("fulfillment", {}).get("successful", 0),
            json.dumps(result)
        ))

        conn.commit()
        conn.close()

    def run_daemon(self, interval: int = 300):
        """
        Run as daemon with periodic sync cycles.

        Args:
            interval: Seconds between cycles (default 5 minutes)
        """
        logger.info(f"Starting daemon mode with {interval}s interval")

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        while self.running:
            try:
                result = self.run_cycle()
                self._print_cycle_summary(result)

                if self.running:
                    logger.info(f"Sleeping for {interval}s until next cycle...")
                    time.sleep(interval)

            except Exception as e:
                logger.error(f"Error in daemon cycle: {e}")
                if self.running:
                    time.sleep(60)  # Wait 1 min on error

        logger.info("Daemon stopped")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

    def _print_cycle_summary(self, result: Dict):
        """Print summary of cycle results"""
        steps = result.get("steps", {})

        print("\n" + "-"*60)
        print(f"SYNC CYCLE SUMMARY - {result['node_id']}")
        print("-"*60)
        print(f"Duration: {result.get('duration_seconds', 0):.2f}s")
        print()

        if "identity" in steps:
            s = steps["identity"]
            status = "OK" if s.get("success") else "FAILED"
            print(f"[{status}] Identity: hash={s.get('identity_hash', 'N/A')}")

        if "peer_scan" in steps:
            s = steps["peer_scan"]
            status = "OK" if s.get("success") else "FAILED"
            print(f"[{status}] Peer Scan: {s.get('peers_found', 0)} peers, "
                  f"{s.get('total_gaps', 0)} gaps, {s.get('new_desires', 0)} new desires")

        if "export" in steps:
            s = steps["export"]
            status = "OK" if s.get("success") else "FAILED"
            print(f"[{status}] Export: {s.get('total_exported', 0)} features shared")

        if "fulfillment" in steps:
            s = steps["fulfillment"]
            status = "OK" if s.get("success") else "FAILED"
            print(f"[{status}] Fulfillment: {s.get('successful', 0)}/{s.get('attempted', 0)} "
                  f"integrated ({s.get('queue_size', 0)} in queue)")

        print("-"*60)
        print(f"Total cycles: {self.cycles_completed} | "
              f"Total desires: {self.total_desires_generated} | "
              f"Total integrated: {self.total_features_integrated}")
        print()

    def get_cluster_status(self) -> Dict[str, Any]:
        """Get current cluster-wide sync status"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        status = {
            "checked_at": datetime.now().isoformat(),
            "nodes": [],
            "recent_cycles": []
        }

        # Get all node identities
        cursor.execute("""
            SELECT node_id, identity_hash, updated_at
            FROM node_identities
            ORDER BY updated_at DESC
        """)
        for row in cursor.fetchall():
            status["nodes"].append({
                "node_id": row[0],
                "identity_hash": row[1],
                "last_updated": row[2]
            })

        # Get recent sync cycles across all nodes
        cursor.execute("""
            SELECT node_id, started_at, duration_seconds, peers_found,
                   desires_generated, features_integrated
            FROM sync_cycles
            ORDER BY started_at DESC
            LIMIT 20
        """)
        for row in cursor.fetchall():
            status["recent_cycles"].append({
                "node_id": row[0],
                "started_at": row[1],
                "duration": row[2],
                "peers": row[3],
                "desires": row[4],
                "integrated": row[5]
            })

        conn.close()
        return status


def main():
    parser = argparse.ArgumentParser(description="Curiosity Sync Daemon")
    parser.add_argument("--daemon", action="store_true",
                       help="Run as daemon with periodic cycles")
    parser.add_argument("--interval", type=int, default=300,
                       help="Interval between cycles in seconds (default: 300)")
    parser.add_argument("--status", action="store_true",
                       help="Show cluster sync status and exit")

    args = parser.parse_args()

    daemon = CuriositySyncDaemon()

    if args.status:
        # Show status and exit
        status = daemon.get_cluster_status()
        print("\n" + "="*70)
        print("CLUSTER SYNC STATUS")
        print("="*70)
        print(f"Nodes in cluster: {len(status['nodes'])}")
        for node in status['nodes']:
            print(f"  - {node['node_id']} (hash: {node['identity_hash'][:8]}...) "
                  f"updated: {node['last_updated']}")
        print()
        print(f"Recent cycles: {len(status['recent_cycles'])}")
        for cycle in status['recent_cycles'][:5]:
            print(f"  - {cycle['node_id']} at {cycle['started_at']}: "
                  f"{cycle['desires']} desires, {cycle['integrated']} integrated")
        print("="*70)
        return

    print("\n" + "="*70)
    print(f"CURIOSITY SYNC DAEMON - {daemon.node_id}")
    print("="*70)
    print()
    print("This daemon enables autonomous feature propagation across cluster nodes.")
    print()
    print("Each cycle will:")
    print("  1. Update node identity (self-awareness)")
    print("  2. Scan peer nodes (discovery)")
    print("  3. Generate desires for missing features (curiosity)")
    print("  4. Export local features for peers (sharing)")
    print("  5. Process fulfillment queue (integration)")
    print()

    if args.daemon:
        print(f"Running as daemon with {args.interval}s interval...")
        print("Press Ctrl+C to stop")
        print()
        daemon.run_daemon(interval=args.interval)
    else:
        print("Running single cycle...")
        result = daemon.run_cycle()
        daemon._print_cycle_summary(result)


if __name__ == "__main__":
    main()
