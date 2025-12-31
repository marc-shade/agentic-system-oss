#!/usr/bin/env python3
"""
Node Metrics - Real-time load monitoring for cluster nodes

Collects and shares:
- CPU usage
- Memory usage
- Load average
- Active task count
- Inference latency (for LLM nodes)

Usage:
    # Get local metrics
    metrics = NodeMetrics()
    local = metrics.get_local_metrics()

    # Get cluster-wide metrics
    cluster = metrics.get_cluster_metrics()

    # Check if node is healthy for task assignment
    if metrics.is_healthy("macpro51"):
        router.assign_task(task, "macpro51")
"""

import json
import os
import socket
import subprocess
import time
import sqlite3
import psutil
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, Optional, List
from datetime import datetime, timezone
import threading


@dataclass
class NodeMetric:
    """Real-time metrics for a cluster node"""
    node_id: str
    timestamp: float
    cpu_percent: float
    memory_percent: float
    load_avg_1m: float
    load_avg_5m: float
    load_avg_15m: float
    active_tasks: int
    queue_depth: int
    disk_percent: float
    inference_latency_ms: Optional[float] = None  # For LLM-capable nodes
    is_healthy: bool = True
    health_reason: str = "ok"

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'NodeMetric':
        return cls(**data)


class NodeMetrics:
    """Collect and share node metrics across cluster"""

    # Thresholds for health determination
    CPU_THRESHOLD = 90.0      # Unhealthy if CPU > 90%
    MEMORY_THRESHOLD = 90.0   # Unhealthy if memory > 90%
    LOAD_THRESHOLD = 8.0      # Unhealthy if 1m load avg > 8
    STALE_THRESHOLD = 60      # Metrics older than 60s are stale
    PING_TIMEOUT = 2.0        # Timeout for ping fallback

    # Node hostname mappings for ping fallback
    NODE_HOSTNAMES = {
        "macpro51": ["macpro51.local", "macpro51"],
        "mac-studio": ["mac-studio.local", "Mac-Studio.local", "mac-studio"],
        "macbook-air": ["macbook-air.local", "MacBook-Air.local", "macbook-air"],
        "completeu-server": ["completeu-server.local", "completeu-server"],
    }

    def __init__(self):
        self.local_node_id = self._detect_local_node()
        self.db_path = self._get_db_path()
        self._init_database()
        self._background_collector: Optional[threading.Thread] = None
        self._stop_collector = threading.Event()

    def _detect_local_node(self) -> str:
        """Detect which node we're running on"""
        hostname = socket.gethostname().lower()

        if "macpro51" in hostname:
            return "macpro51"
        elif "macbook" in hostname or "air" in hostname:
            return "macbook-air"
        elif "studio" in hostname:
            return "mac-studio"
        else:
            # Check OS for fallback
            if os.path.exists("/home/marc"):
                return "macpro51"
            return "mac-studio"

    def _get_db_path(self) -> Path:
        """Get path to metrics database"""
        if self.local_node_id == "macpro51":
            base = Path("/home/marc/agentic-system")
        else:
            base = Path.home() / "agentic-system"

        db_dir = base / "databases" / "cluster"
        db_dir.mkdir(parents=True, exist_ok=True)
        return db_dir / "node_metrics.db"

    def _init_database(self):
        """Initialize metrics database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS node_metrics (
                node_id TEXT PRIMARY KEY,
                timestamp REAL,
                cpu_percent REAL,
                memory_percent REAL,
                load_avg_1m REAL,
                load_avg_5m REAL,
                load_avg_15m REAL,
                active_tasks INTEGER,
                queue_depth INTEGER,
                disk_percent REAL,
                inference_latency_ms REAL,
                is_healthy INTEGER,
                health_reason TEXT
            )
        """)

        # History table for trending
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT,
                timestamp REAL,
                cpu_percent REAL,
                memory_percent REAL,
                load_avg_1m REAL,
                active_tasks INTEGER
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_metrics_history_node
            ON metrics_history(node_id, timestamp)
        """)

        conn.commit()
        conn.close()

    def get_local_metrics(self) -> NodeMetric:
        """Collect current metrics from local system"""
        try:
            cpu = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent

            # Load average (Linux/macOS)
            load_avg = os.getloadavg()

            # Get active task count from task_queue.db
            active_tasks = self._get_active_task_count()
            queue_depth = self._get_queue_depth()

            # Determine health
            is_healthy, health_reason = self._check_health(
                cpu, memory, load_avg[0]
            )

            metric = NodeMetric(
                node_id=self.local_node_id,
                timestamp=time.time(),
                cpu_percent=cpu,
                memory_percent=memory,
                load_avg_1m=load_avg[0],
                load_avg_5m=load_avg[1],
                load_avg_15m=load_avg[2],
                active_tasks=active_tasks,
                queue_depth=queue_depth,
                disk_percent=disk,
                inference_latency_ms=None,  # TODO: Measure if LLM available
                is_healthy=is_healthy,
                health_reason=health_reason
            )

            # Store locally
            self._store_metric(metric)

            return metric

        except Exception as e:
            return NodeMetric(
                node_id=self.local_node_id,
                timestamp=time.time(),
                cpu_percent=0,
                memory_percent=0,
                load_avg_1m=0,
                load_avg_5m=0,
                load_avg_15m=0,
                active_tasks=0,
                queue_depth=0,
                disk_percent=0,
                is_healthy=False,
                health_reason=f"Error collecting metrics: {e}"
            )

    def _get_active_task_count(self) -> int:
        """Get count of currently executing tasks"""
        try:
            task_db = self.db_path.parent / "task_queue.db"
            if not task_db.exists():
                return 0

            conn = sqlite3.connect(task_db)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM task_queue
                WHERE assigned_to = ? AND status IN ('assigned', 'running')
            """, (self.local_node_id,))
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except:
            return 0

    def _get_queue_depth(self) -> int:
        """Get depth of pending task queue"""
        try:
            task_db = self.db_path.parent / "task_queue.db"
            if not task_db.exists():
                return 0

            conn = sqlite3.connect(task_db)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM task_queue
                WHERE status = 'pending'
            """)
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except:
            return 0

    def _check_health(self, cpu: float, memory: float, load: float) -> tuple:
        """Determine if node is healthy based on metrics"""
        reasons = []

        if cpu > self.CPU_THRESHOLD:
            reasons.append(f"CPU high ({cpu:.1f}%)")
        if memory > self.MEMORY_THRESHOLD:
            reasons.append(f"Memory high ({memory:.1f}%)")
        if load > self.LOAD_THRESHOLD:
            reasons.append(f"Load high ({load:.1f})")

        if reasons:
            return False, "; ".join(reasons)
        return True, "ok"

    def _ping_node(self, node_id: str) -> bool:
        """
        Ping fallback for health check when metrics are stale/missing.

        Tries multiple hostnames for the node until one responds.
        Returns True if node is reachable, False otherwise.
        """
        hostnames = self.NODE_HOSTNAMES.get(node_id, [])
        if not hostnames:
            return False

        for hostname in hostnames:
            try:
                # Use ping with short timeout
                # -c 1 = single ping, -W = timeout in seconds (Linux), -t = timeout (macOS)
                import platform
                if platform.system() == "Darwin":
                    cmd = ["ping", "-c", "1", "-t", str(int(self.PING_TIMEOUT)), hostname]
                else:
                    cmd = ["ping", "-c", "1", "-W", str(int(self.PING_TIMEOUT)), hostname]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=self.PING_TIMEOUT + 1
                )

                if result.returncode == 0:
                    return True

            except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
                continue

        return False

    def _store_metric(self, metric: NodeMetric):
        """Store metric in local database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Upsert current metrics
        cursor.execute("""
            INSERT OR REPLACE INTO node_metrics
            (node_id, timestamp, cpu_percent, memory_percent,
             load_avg_1m, load_avg_5m, load_avg_15m,
             active_tasks, queue_depth, disk_percent,
             inference_latency_ms, is_healthy, health_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metric.node_id, metric.timestamp, metric.cpu_percent,
            metric.memory_percent, metric.load_avg_1m, metric.load_avg_5m,
            metric.load_avg_15m, metric.active_tasks, metric.queue_depth,
            metric.disk_percent, metric.inference_latency_ms,
            1 if metric.is_healthy else 0, metric.health_reason
        ))

        # Append to history (keep last 24 hours)
        cursor.execute("""
            INSERT INTO metrics_history
            (node_id, timestamp, cpu_percent, memory_percent, load_avg_1m, active_tasks)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            metric.node_id, metric.timestamp, metric.cpu_percent,
            metric.memory_percent, metric.load_avg_1m, metric.active_tasks
        ))

        # Cleanup old history (keep 24 hours)
        cutoff = time.time() - 86400
        cursor.execute("DELETE FROM metrics_history WHERE timestamp < ?", (cutoff,))

        conn.commit()
        conn.close()

    def get_node_metrics(self, node_id: str) -> Optional[NodeMetric]:
        """Get metrics for a specific node"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT node_id, timestamp, cpu_percent, memory_percent,
                   load_avg_1m, load_avg_5m, load_avg_15m,
                   active_tasks, queue_depth, disk_percent,
                   inference_latency_ms, is_healthy, health_reason
            FROM node_metrics WHERE node_id = ?
        """, (node_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return NodeMetric(
            node_id=row[0],
            timestamp=row[1],
            cpu_percent=row[2],
            memory_percent=row[3],
            load_avg_1m=row[4],
            load_avg_5m=row[5],
            load_avg_15m=row[6],
            active_tasks=row[7],
            queue_depth=row[8],
            disk_percent=row[9],
            inference_latency_ms=row[10],
            is_healthy=bool(row[11]),
            health_reason=row[12]
        )

    def get_cluster_metrics(self) -> Dict[str, NodeMetric]:
        """Get metrics for all cluster nodes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT node_id, timestamp, cpu_percent, memory_percent,
                   load_avg_1m, load_avg_5m, load_avg_15m,
                   active_tasks, queue_depth, disk_percent,
                   inference_latency_ms, is_healthy, health_reason
            FROM node_metrics
        """)

        results = {}
        for row in cursor.fetchall():
            metric = NodeMetric(
                node_id=row[0],
                timestamp=row[1],
                cpu_percent=row[2],
                memory_percent=row[3],
                load_avg_1m=row[4],
                load_avg_5m=row[5],
                load_avg_15m=row[6],
                active_tasks=row[7],
                queue_depth=row[8],
                disk_percent=row[9],
                inference_latency_ms=row[10],
                is_healthy=bool(row[11]),
                health_reason=row[12]
            )

            # Mark stale metrics as unhealthy
            if time.time() - metric.timestamp > self.STALE_THRESHOLD:
                metric.is_healthy = False
                metric.health_reason = "stale metrics"

            results[row[0]] = metric

        conn.close()
        return results

    def is_healthy(self, node_id: str, use_ping_fallback: bool = True) -> bool:
        """
        Check if a node is currently healthy using multi-method detection.

        Priority order:
        1. Fresh metrics (< STALE_THRESHOLD old) - use metric health status
        2. Ping fallback - if metrics stale/missing, try ICMP ping
        3. Return False if all methods fail

        Args:
            node_id: Node identifier to check
            use_ping_fallback: Whether to try ping if metrics are stale (default: True)

        Returns:
            True if node is healthy and reachable, False otherwise
        """
        metric = self.get_node_metrics(node_id)

        # Method 1: Check fresh metrics
        if metric:
            metrics_age = time.time() - metric.timestamp
            if metrics_age <= self.STALE_THRESHOLD:
                # Metrics are fresh, trust them
                return metric.is_healthy

        # Method 2: Ping fallback for stale/missing metrics
        if use_ping_fallback:
            if self._ping_node(node_id):
                # Node is reachable via ping - consider it healthy
                # (we just can't see detailed metrics)
                return True

        # All methods failed
        return False

    def get_load_score(self, node_id: str) -> float:
        """
        Get a normalized load score for routing decisions.

        Returns 0.0 (idle) to 1.0 (overloaded).
        Uses ping fallback when metrics are stale/unavailable.
        """
        metric = self.get_node_metrics(node_id)

        # No metrics available
        if not metric:
            # Try ping fallback - if reachable, assume moderate load
            if self._ping_node(node_id):
                return 0.5  # Reachable but no metrics = assume moderate load
            return 1.0  # Unreachable = avoid

        # Check for stale metrics
        if time.time() - metric.timestamp > self.STALE_THRESHOLD:
            # Stale metrics - use ping fallback
            if self._ping_node(node_id):
                return 0.5  # Reachable but stale = assume moderate load
            return 1.0  # Unreachable = avoid

        if not metric.is_healthy:
            return 1.0  # Unhealthy = avoid

        # Weighted combination of factors
        cpu_score = metric.cpu_percent / 100.0
        mem_score = metric.memory_percent / 100.0
        load_score = min(metric.load_avg_1m / 8.0, 1.0)
        task_score = min(metric.active_tasks / 5.0, 1.0)

        # Weighted average (CPU and load matter most)
        combined = (
            cpu_score * 0.35 +
            load_score * 0.35 +
            mem_score * 0.15 +
            task_score * 0.15
        )

        return min(combined, 1.0)

    def start_background_collection(self, interval: float = 10.0):
        """Start background metric collection"""
        if self._background_collector and self._background_collector.is_alive():
            return

        self._stop_collector.clear()

        def collector():
            while not self._stop_collector.is_set():
                self.get_local_metrics()
                self._stop_collector.wait(interval)

        self._background_collector = threading.Thread(
            target=collector, daemon=True
        )
        self._background_collector.start()

    def stop_background_collection(self):
        """Stop background metric collection"""
        self._stop_collector.set()
        if self._background_collector:
            self._background_collector.join(timeout=5.0)

    def broadcast_metrics(self, nodes: List[str] = None):
        """Broadcast local metrics to other cluster nodes (future: implement gossip)"""
        # For now, we rely on shared database via rsync
        # Future: implement gossip protocol for real-time sync
        pass


def print_cluster_status():
    """CLI utility to print cluster metrics"""
    metrics = NodeMetrics()

    # Collect fresh local metrics
    local = metrics.get_local_metrics()
    print(f"\nLocal Node: {local.node_id}")
    print(f"  CPU: {local.cpu_percent:.1f}%")
    print(f"  Memory: {local.memory_percent:.1f}%")
    print(f"  Load (1m/5m/15m): {local.load_avg_1m:.2f}/{local.load_avg_5m:.2f}/{local.load_avg_15m:.2f}")
    print(f"  Active Tasks: {local.active_tasks}")
    print(f"  Health: {'OK' if local.is_healthy else local.health_reason}")

    print("\nCluster Status:")
    cluster = metrics.get_cluster_metrics()
    for node_id, metric in sorted(cluster.items()):
        age = time.time() - metric.timestamp
        status = "OK" if metric.is_healthy else metric.health_reason
        stale = " (stale)" if age > metrics.STALE_THRESHOLD else ""
        print(f"  {node_id}: CPU={metric.cpu_percent:.0f}% Load={metric.load_avg_1m:.1f} Tasks={metric.active_tasks} [{status}]{stale}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "daemon":
        # Run as background daemon
        print("Starting metrics collection daemon...")
        metrics = NodeMetrics()
        metrics.start_background_collection(interval=10.0)

        try:
            while True:
                time.sleep(60)
                local = metrics.get_local_metrics()
                print(f"[{datetime.now(timezone.utc).isoformat()}] CPU={local.cpu_percent:.0f}% Mem={local.memory_percent:.0f}% Load={local.load_avg_1m:.1f}")
        except KeyboardInterrupt:
            metrics.stop_background_collection()
            print("\nStopped.")
    else:
        print_cluster_status()
