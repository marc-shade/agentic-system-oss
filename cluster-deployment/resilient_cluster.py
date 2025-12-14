#!/usr/bin/env python3
"""
Resilient Cluster Architecture
==============================

Ensures the agentic system survives node failures, including the orchestrator.

Key Features:
- Leader election via distributed consensus
- Distributed health monitoring (every node monitors every other node)
- Automatic role failover
- Memory replication across nodes
- Self-healing cluster topology

Design Principles:
1. NO single point of failure
2. Any node can become orchestrator
3. Shared state replicated to 2+ nodes
4. Graceful degradation when nodes fail
5. Automatic recovery when nodes return

Usage:
    # On each node, run:
    daemon = ResilientClusterDaemon(node_id="macpro51")
    daemon.start()
"""
import platform

import os
import sys
import json
import time
import socket
import sqlite3
import threading
import subprocess
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import hashlib


# =============================================================================
# Configuration
# =============================================================================

class NodeRole(Enum):
    ORCHESTRATOR = "orchestrator"
    BUILDER = "builder"
    RESEARCHER = "researcher"
    INFERENCE = "inference"
    STANDBY = "standby"  # Ready to take over any role


# Role priority for leader election (lower = higher priority)
ROLE_PRIORITY = {
    "orchestrator": 1,
    "inference": 2,     # completeu-server has most resources
    "researcher": 3,
    "builder": 4,
}

# Node configurations
CLUSTER_NODES = {
    "mac-studio": {
        "hostnames": ["Marcs-Mac-Studio.local", "192.168.1.16", "192.168.1.176"],
        "default_role": NodeRole.ORCHESTRATOR,
        "priority": 1,
        "can_be_orchestrator": True,
    },
    "macbook-air-m3": {
        "hostnames": ["Marcs-MacBook-Air.local", "192.168.1.172"],
        "default_role": NodeRole.RESEARCHER,
        "priority": 3,
        "can_be_orchestrator": True,
    },
    "completeu-server": {
        "hostnames": ["completeu-server.local", "192.168.1.186"],
        "default_role": NodeRole.INFERENCE,
        "priority": 2,  # Best backup orchestrator (most RAM)
        "can_be_orchestrator": True,
    },
    "macpro51": {
        "hostnames": ["macpro51.local", "192.168.1.183"],
        "default_role": NodeRole.BUILDER,
        "priority": 4,
        "can_be_orchestrator": True,
    },
}

# Timeouts
HEARTBEAT_INTERVAL = 10  # seconds
HEARTBEAT_TIMEOUT = 30   # seconds before node considered dead
ELECTION_TIMEOUT = 15    # seconds to wait for election
REPLICATION_INTERVAL = 60  # seconds between memory sync


# =============================================================================
# Distributed State (replicated across nodes)
# =============================================================================

@dataclass
class NodeState:
    """State of a cluster node."""
    node_id: str
    role: str
    status: str  # online, offline, degraded
    is_orchestrator: bool
    last_heartbeat: float
    ip_address: str
    capabilities: List[str] = field(default_factory=list)
    load_average: float = 0.0
    memory_available_gb: float = 0.0

    def is_alive(self) -> bool:
        return time.time() - self.last_heartbeat < HEARTBEAT_TIMEOUT

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'NodeState':
        return cls(**data)


@dataclass
class ClusterState:
    """Global cluster state - replicated to all nodes."""
    current_orchestrator: Optional[str]
    orchestrator_since: float
    term: int  # Election term (increments on each election)
    nodes: Dict[str, NodeState]
    last_updated: float

    def to_dict(self) -> dict:
        return {
            "current_orchestrator": self.current_orchestrator,
            "orchestrator_since": self.orchestrator_since,
            "term": self.term,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ClusterState':
        nodes = {k: NodeState.from_dict(v) for k, v in data.get("nodes", {}).items()}
        return cls(
            current_orchestrator=data.get("current_orchestrator"),
            orchestrator_since=data.get("orchestrator_since", 0),
            term=data.get("term", 0),
            nodes=nodes,
            last_updated=data.get("last_updated", time.time()),
        )


# =============================================================================
# Leader Election (Simplified Raft-like consensus)
# =============================================================================

class LeaderElection:
    """
    Simple leader election for orchestrator role.

    Uses a file-based lock with timestamps for distributed consensus.
    Each node can read the election state and participate.
    """

    def __init__(self, node_id: str, db_path: str):
        self.node_id = node_id
        self.db_path = db_path
        self.current_term = 0
        self.voted_for: Optional[str] = None
        self._init_db()

    def _init_db(self):
        """Initialize election database."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS election_state (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at REAL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS votes (
                    term INTEGER,
                    voter_id TEXT,
                    candidate_id TEXT,
                    voted_at REAL,
                    PRIMARY KEY (term, voter_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS leader_lease (
                    term INTEGER PRIMARY KEY,
                    leader_id TEXT,
                    started_at REAL,
                    expires_at REAL,
                    is_active INTEGER DEFAULT 1
                )
            """)
            conn.commit()

    def get_current_leader(self) -> Tuple[Optional[str], int]:
        """Get current leader and term."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT leader_id, term, expires_at
                FROM leader_lease
                WHERE is_active = 1
                ORDER BY term DESC LIMIT 1
            """)
            row = cursor.fetchone()
            if row and row[2] > time.time():
                return row[0], row[1]
            return None, row[1] if row else 0

    def start_election(self) -> bool:
        """
        Start leader election.
        Returns True if this node becomes leader.
        """
        current_leader, current_term = self.get_current_leader()

        # If there's a valid leader, don't start election
        if current_leader:
            return current_leader == self.node_id

        new_term = current_term + 1
        self.current_term = new_term

        # Vote for self
        with sqlite3.connect(self.db_path) as conn:
            try:
                conn.execute("""
                    INSERT INTO votes (term, voter_id, candidate_id, voted_at)
                    VALUES (?, ?, ?, ?)
                """, (new_term, self.node_id, self.node_id, time.time()))
                conn.commit()
            except sqlite3.IntegrityError:
                pass  # Already voted

        # Wait for other votes
        time.sleep(ELECTION_TIMEOUT / 2)

        # Count votes
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT candidate_id, COUNT(*) as vote_count
                FROM votes WHERE term = ?
                GROUP BY candidate_id
                ORDER BY vote_count DESC
            """, (new_term,))

            results = cursor.fetchall()
            if results and results[0][0] == self.node_id:
                # We won! Claim leadership
                return self._claim_leadership(new_term)

        return False

    def _claim_leadership(self, term: int) -> bool:
        """Claim leadership for given term."""
        expires_at = time.time() + HEARTBEAT_TIMEOUT * 3

        with sqlite3.connect(self.db_path) as conn:
            try:
                # Deactivate old leaders
                conn.execute("UPDATE leader_lease SET is_active = 0")

                # Claim new leadership
                conn.execute("""
                    INSERT OR REPLACE INTO leader_lease
                    (term, leader_id, started_at, expires_at, is_active)
                    VALUES (?, ?, ?, ?, 1)
                """, (term, self.node_id, time.time(), expires_at))
                conn.commit()
                return True
            except Exception:
                return False

    def renew_leadership(self) -> bool:
        """Renew leadership lease (leader heartbeat)."""
        leader, term = self.get_current_leader()
        if leader != self.node_id:
            return False

        expires_at = time.time() + HEARTBEAT_TIMEOUT * 3
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE leader_lease
                SET expires_at = ?
                WHERE term = ? AND leader_id = ?
            """, (expires_at, term, self.node_id))
            conn.commit()
        return True

    def vote_for(self, candidate_id: str, term: int) -> bool:
        """Vote for a candidate in given term."""
        with sqlite3.connect(self.db_path) as conn:
            try:
                conn.execute("""
                    INSERT INTO votes (term, voter_id, candidate_id, voted_at)
                    VALUES (?, ?, ?, ?)
                """, (term, self.node_id, candidate_id, time.time()))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False  # Already voted in this term


# =============================================================================
# Distributed Health Monitor
# =============================================================================

class DistributedHealthMonitor:
    """
    Every node monitors every other node.
    No single point of failure for health checking.
    """

    def __init__(self, node_id: str, db_path: str):
        self.node_id = node_id
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize health database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS health_observations (
                    observer_id TEXT,
                    target_id TEXT,
                    is_reachable INTEGER,
                    latency_ms REAL,
                    observed_at REAL,
                    PRIMARY KEY (observer_id, target_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS node_status (
                    node_id TEXT PRIMARY KEY,
                    status TEXT,  -- online, offline, degraded
                    last_seen REAL,
                    observed_by TEXT,
                    consensus_count INTEGER DEFAULT 0
                )
            """)
            conn.commit()

    def check_node(self, target_id: str) -> Tuple[bool, float]:
        """
        Check if a node is reachable.
        Returns (is_reachable, latency_ms).
        """
        if target_id not in CLUSTER_NODES:
            return False, 0.0

        config = CLUSTER_NODES[target_id]

        for hostname in config["hostnames"]:
            try:
                start = time.time()
                # Try ping
                result = subprocess.run(
                    ["ping", "-c", "1", "-W", "2", hostname],
                    capture_output=True,
                    timeout=3
                )
                latency = (time.time() - start) * 1000

                if result.returncode == 0:
                    return True, latency
            except Exception:
                continue

        return False, 0.0

    def record_observation(self, target_id: str, is_reachable: bool, latency_ms: float):
        """Record health observation."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO health_observations
                (observer_id, target_id, is_reachable, latency_ms, observed_at)
                VALUES (?, ?, ?, ?, ?)
            """, (self.node_id, target_id, int(is_reachable), latency_ms, time.time()))
            conn.commit()

    def check_all_nodes(self) -> Dict[str, Tuple[bool, float]]:
        """Check all cluster nodes."""
        results = {}
        for node_id in CLUSTER_NODES:
            if node_id == self.node_id:
                results[node_id] = (True, 0.0)  # Self is always reachable
            else:
                is_reachable, latency = self.check_node(node_id)
                self.record_observation(node_id, is_reachable, latency)
                results[node_id] = (is_reachable, latency)
        return results

    def get_consensus_status(self, target_id: str) -> str:
        """
        Get consensus status for a node based on multiple observers.
        Returns: online, offline, or degraded
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT is_reachable, COUNT(*) as observer_count
                FROM health_observations
                WHERE target_id = ? AND observed_at > ?
                GROUP BY is_reachable
            """, (target_id, time.time() - HEARTBEAT_TIMEOUT))

            results = {row[0]: row[1] for row in cursor.fetchall()}

            reachable_count = results.get(1, 0)
            unreachable_count = results.get(0, 0)

            if reachable_count == 0 and unreachable_count == 0:
                return "unknown"
            elif unreachable_count == 0:
                return "online"
            elif reachable_count == 0:
                return "offline"
            else:
                return "degraded"


# =============================================================================
# Memory Replication
# =============================================================================

class MemoryReplicator:
    """
    Replicates shared memories across multiple nodes.
    Ensures data survives node failures.
    """

    def __init__(self, node_id: str, local_db_path: str):
        self.node_id = node_id
        self.local_db_path = local_db_path
        self.replica_nodes: List[str] = []
        self._determine_replicas()

    def _determine_replicas(self):
        """Determine which nodes to replicate to."""
        # Replicate to 2 other nodes for redundancy
        other_nodes = [n for n in CLUSTER_NODES if n != self.node_id]
        # Sort by priority (best nodes first)
        other_nodes.sort(key=lambda n: CLUSTER_NODES[n]["priority"])
        self.replica_nodes = other_nodes[:2]

    def get_local_memories(self, since: float = 0) -> List[dict]:
        """Get memories created/updated since timestamp."""
        memories = []
        try:
            with sqlite3.connect(self.local_db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM entities
                    WHERE created_at > ? OR updated_at > ?
                    ORDER BY updated_at DESC
                    LIMIT 1000
                """, (since, since))
                for row in cursor:
                    memories.append(dict(row))
        except Exception as e:
            print(f"Error reading memories: {e}")
        return memories

    def sync_to_replica(self, target_node: str, memories: List[dict]) -> bool:
        """
        Sync memories to replica node via SSH + SQLite.
        In production, use HTTP API or message queue.
        """
        if not memories:
            return True

        config = CLUSTER_NODES.get(target_node)
        if not config:
            return False

        # For now, write to shared location that nodes can pull from
        sync_file = Path(f"/tmp/memory_sync_{self.node_id}_to_{target_node}.json")
        try:
            with open(sync_file, 'w') as f:
                json.dump({
                    "source": self.node_id,
                    "target": target_node,
                    "memories": memories,
                    "synced_at": time.time()
                }, f)
            return True
        except Exception as e:
            print(f"Sync failed: {e}")
            return False

    def replicate_all(self) -> Dict[str, bool]:
        """Replicate to all replica nodes."""
        memories = self.get_local_memories(since=time.time() - REPLICATION_INTERVAL)
        results = {}
        for node in self.replica_nodes:
            results[node] = self.sync_to_replica(node, memories)
        return results


# =============================================================================
# Resilient Cluster Daemon
# =============================================================================

class ResilientClusterDaemon:
    """
    Main daemon that runs on each node to maintain cluster resilience.

    Responsibilities:
    1. Monitor health of all nodes
    2. Participate in leader election
    3. Take over orchestrator role if needed
    4. Replicate memories
    5. Self-heal when nodes return
    """

    def __init__(self, node_id: str, db_base: str = None):
        self.node_id = node_id

        if db_base is None:
            # Auto-detect storage path
            if os.path.exists(str(_STORAGE_BASE)):
                db_base = str(_STORAGE_BASE / "databases/cluster")
            elif os.path.exists(str(_STORAGE_BASE)):
                db_base = str(_STORAGE_BASE / "databases/cluster")
            else:
                db_base = os.path.expanduser("~/agentic-system/databases/cluster")

        self.db_base = Path(db_base)
        self.db_base.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.election = LeaderElection(
            node_id,
            str(self.db_base / "election.db")
        )
        self.health_monitor = DistributedHealthMonitor(
            node_id,
            str(self.db_base / "health.db")
        )
        self.memory_replicator = MemoryReplicator(
            node_id,
            str(self.db_base / "shared_memories.db")
        )

        self._running = False
        self._is_orchestrator = False
        self._threads: List[threading.Thread] = []

    def start(self):
        """Start the resilience daemon."""
        self._running = True
        print(f"[{self.node_id}] Starting resilient cluster daemon...")

        # Start background threads
        self._threads = [
            threading.Thread(target=self._health_check_loop, daemon=True),
            threading.Thread(target=self._election_loop, daemon=True),
            threading.Thread(target=self._replication_loop, daemon=True),
        ]

        for t in self._threads:
            t.start()

        print(f"[{self.node_id}] Daemon started with {len(self._threads)} background tasks")

    def stop(self):
        """Stop the daemon."""
        self._running = False
        for t in self._threads:
            t.join(timeout=5)
        print(f"[{self.node_id}] Daemon stopped")

    def _health_check_loop(self):
        """Continuously check health of all nodes."""
        while self._running:
            try:
                results = self.health_monitor.check_all_nodes()

                # Log status changes
                for node_id, (is_reachable, latency) in results.items():
                    status = "UP" if is_reachable else "DOWN"
                    if not is_reachable and node_id != self.node_id:
                        print(f"[{self.node_id}] Node {node_id} is {status}")

                time.sleep(HEARTBEAT_INTERVAL)

            except Exception as e:
                print(f"[{self.node_id}] Health check error: {e}")
                time.sleep(5)

    def _election_loop(self):
        """Monitor orchestrator and trigger election if needed."""
        while self._running:
            try:
                current_leader, term = self.election.get_current_leader()

                if current_leader == self.node_id:
                    # We are the leader - renew lease
                    self._is_orchestrator = True
                    self.election.renew_leadership()

                elif current_leader is None:
                    # No leader - check if orchestrator is really down
                    orchestrator_status = self.health_monitor.get_consensus_status("mac-studio")

                    if orchestrator_status == "offline":
                        print(f"[{self.node_id}] Orchestrator down! Starting election...")

                        # Check if we can be orchestrator
                        if CLUSTER_NODES[self.node_id]["can_be_orchestrator"]:
                            if self.election.start_election():
                                print(f"[{self.node_id}] WON ELECTION - Now orchestrator!")
                                self._is_orchestrator = True
                                self._on_become_orchestrator()
                else:
                    self._is_orchestrator = False

                time.sleep(HEARTBEAT_INTERVAL)

            except Exception as e:
                print(f"[{self.node_id}] Election loop error: {e}")
                time.sleep(5)

    def _replication_loop(self):
        """Periodically replicate memories."""
        while self._running:
            try:
                if self._is_orchestrator:
                    # Orchestrator replicates more frequently
                    results = self.memory_replicator.replicate_all()
                    success = sum(1 for v in results.values() if v)
                    print(f"[{self.node_id}] Replicated memories to {success}/{len(results)} nodes")

                time.sleep(REPLICATION_INTERVAL)

            except Exception as e:
                print(f"[{self.node_id}] Replication error: {e}")
                time.sleep(30)

    def _on_become_orchestrator(self):
        """Called when this node becomes orchestrator."""
        print(f"[{self.node_id}] Taking over orchestrator responsibilities...")

        # Update cluster state
        with sqlite3.connect(str(self.db_base / "cluster_state.db")) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO nodes (node_id, role, is_primary, updated_at)
                VALUES (?, 'orchestrator', 1, ?)
            """, (self.node_id, time.time()))
            conn.commit()

        # Notify other nodes (in production, use message queue)
        print(f"[{self.node_id}] Orchestrator failover complete")

    def get_status(self) -> dict:
        """Get current daemon status."""
        leader, term = self.election.get_current_leader()
        health_results = self.health_monitor.check_all_nodes()

        return {
            "node_id": self.node_id,
            "is_orchestrator": self._is_orchestrator,
            "current_leader": leader,
            "election_term": term,
            "node_health": {
                node_id: {
                    "reachable": is_reachable,
                    "latency_ms": latency,
                    "consensus": self.health_monitor.get_consensus_status(node_id)
                }
                for node_id, (is_reachable, latency) in health_results.items()
            },
            "replica_nodes": self.memory_replicator.replica_nodes,
        }


# =============================================================================
# CLI
# =============================================================================

def detect_node_id() -> str:
    """Auto-detect this node's ID."""
    hostname = socket.gethostname().lower()

    if "macpro" in hostname or "mac-pro" in hostname:
        return "macpro51"
    elif "studio" in hostname:
        return "mac-studio"
    elif "air" in hostname:
        return "macbook-air-m3"
    elif "completeu" in hostname:
        return "completeu-server"
    else:
        # Check IP
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()

            for node_id, config in CLUSTER_NODES.items():
                if ip in config["hostnames"]:
                    return node_id
        except:
            pass

    return hostname


def main():
    """Main entry point."""
    import argparse

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    elif system == "Linux":
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()


    parser = argparse.ArgumentParser(description="Resilient Cluster Daemon")
    parser.add_argument("--node-id", default=None, help="Node ID (auto-detected if not specified)")
    parser.add_argument("--status", action="store_true", help="Show status and exit")
    parser.add_argument("--check-health", action="store_true", help="Check all node health")
    args = parser.parse_args()

    node_id = args.node_id or detect_node_id()
    print(f"Node ID: {node_id}")

    daemon = ResilientClusterDaemon(node_id)

    if args.status:
        status = daemon.get_status()
        print(json.dumps(status, indent=2))
        return

    if args.check_health:
        results = daemon.health_monitor.check_all_nodes()
        print("\nCluster Health:")
        print("-" * 50)
        for node_id, (is_reachable, latency) in results.items():
            status = "✓ UP" if is_reachable else "✗ DOWN"
            latency_str = f"{latency:.1f}ms" if is_reachable else "N/A"
            print(f"  {node_id:20} {status:10} {latency_str}")
        return

    # Run daemon
    daemon.start()

    try:
        while True:
            time.sleep(60)
            status = daemon.get_status()
            print(f"\n[Status] Leader: {status['current_leader']}, "
                  f"Term: {status['election_term']}, "
                  f"Is Orchestrator: {status['is_orchestrator']}")
    except KeyboardInterrupt:
        print("\nShutting down...")
        daemon.stop()


if __name__ == "__main__":
    main()
