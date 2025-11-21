#!/usr/bin/env python3
"""
<<<<<<< HEAD
Performance Optimizer for Cluster Execution

Monitors system performance and provides optimization recommendations:
- CPU usage tracking
- Memory utilization
- Load average monitoring
- Overload detection

Now includes TOON serialization for 50% token reduction on metrics broadcasts.
=======
Performance Optimization Daemon

Continuously monitors system load and automatically offloads work
to keep the active node responsive.

Features:
- Real-time CPU and memory monitoring
- Automatic task offloading when load exceeds thresholds
- Proactive work distribution
- Integration with distributed task router

Usage:
    # Run as daemon
    python3 performance_optimizer.py --daemon

    # Run in foreground (for debugging)
    python3 performance_optimizer.py
>>>>>>> origin/main
"""

import os
import sys
<<<<<<< HEAD
import psutil
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

# Add cluster-deployment to path for TOON imports
sys.path.insert(0, str(Path(__file__).parent))
from toon_serialization import encode_metrics


@dataclass
class SystemMetrics:
    """System performance metrics"""
=======
import time
import psutil
import socket
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
import signal

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

from distributed_task_router import DistributedTaskRouter, CLUSTER_NODES


@dataclass
class NodeMetrics:
    """Real-time node performance metrics"""
>>>>>>> origin/main
    cpu_percent: float
    memory_percent: float
    load_average_1m: float
    load_average_5m: float
    load_average_15m: float
<<<<<<< HEAD
    active_tasks: int = 0


class PerformanceOptimizer:
    """Monitors and optimizes system performance"""

    def __init__(self):
        self.cpu_threshold = 70.0  # %
        self.memory_threshold = 80.0  # %
        self.load_threshold = 4.0  # For overload detection

    def get_current_metrics(self) -> SystemMetrics:
        """Get current system performance metrics"""

        # Get CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)

        # Get memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent

        # Get load average
        try:
            load_avg = os.getloadavg()
            load_1m, load_5m, load_15m = load_avg
        except (AttributeError, OSError):
            # Windows doesn't have getloadavg
            load_1m = load_5m = load_15m = 0.0

        # Estimate active tasks from process count
        active_tasks = len([p for p in psutil.process_iter() if p.status() == psutil.STATUS_RUNNING])

        return SystemMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            load_average_1m=load_1m,
            load_average_5m=load_5m,
            load_average_15m=load_15m,
            active_tasks=active_tasks
        )

    def is_overloaded(self, metrics: Optional[SystemMetrics] = None) -> bool:
        """Determine if system is currently overloaded"""

        if metrics is None:
            metrics = self.get_current_metrics()

        # Check if any metric exceeds threshold
        if metrics.cpu_percent > self.cpu_threshold:
            return True

        if metrics.memory_percent > self.memory_threshold:
            return True

        if metrics.load_average_1m > self.load_threshold:
            return True

        return False

    def should_offload(self, metrics: Optional[SystemMetrics] = None) -> bool:
        """Determine if work should be offloaded to other nodes"""

        if metrics is None:
            metrics = self.get_current_metrics()

        # Lower thresholds for offloading decision
        offload_cpu = 40.0  # %
        offload_load = 4.0

        if metrics.cpu_percent > offload_cpu:
            return True

        if metrics.load_average_1m > offload_load:
            return True

        return False

    def get_health_status(self) -> dict:
        """Get comprehensive health status"""

        metrics = self.get_current_metrics()
        overloaded = self.is_overloaded(metrics)

        return {
            "status": "overloaded" if overloaded else "healthy",
            "metrics": {
                "cpu_percent": metrics.cpu_percent,
                "memory_percent": metrics.memory_percent,
                "load_1m": metrics.load_average_1m,
                "load_5m": metrics.load_average_5m,
                "load_15m": metrics.load_average_15m,
                "active_tasks": metrics.active_tasks
            },
            "thresholds": {
                "cpu": self.cpu_threshold,
                "memory": self.memory_threshold,
                "load": self.load_threshold
            }
        }

    def get_health_status_toon(self) -> str:
        """Get comprehensive health status in TOON format (50% token reduction)"""
        health_dict = self.get_health_status()
        return encode_metrics(health_dict)
=======
    active_tasks: int
    timestamp: float


class PerformanceOptimizer:
    """
    Monitors system performance and automatically offloads work
    """

    def __init__(
        self,
        check_interval: int = 10,
        cpu_threshold: float = 70.0,
        memory_threshold: float = 80.0,
        load_threshold: float = 8.0  # For 24-thread system
    ):
        self.check_interval = check_interval
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.load_threshold = load_threshold

        self.router = DistributedTaskRouter()
        self.local_node_id = self.router.local_node_id

        self.running = False
        self.metrics_history: List[NodeMetrics] = []
        self.max_history = 100

    def get_current_metrics(self) -> NodeMetrics:
        """Collect current system metrics"""
        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory().percent

        load_avg = os.getloadavg()

        # Count active cluster tasks
        import sqlite3
        try:
            conn = sqlite3.connect(self.router.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM task_queue
                WHERE assigned_to = ? AND status IN ('pending', 'in_progress')
            """, (self.local_node_id,))
            active_tasks = cursor.fetchone()[0]
            conn.close()
        except:
            active_tasks = 0

        return NodeMetrics(
            cpu_percent=cpu,
            memory_percent=memory,
            load_average_1m=load_avg[0],
            load_average_5m=load_avg[1],
            load_average_15m=load_avg[2],
            active_tasks=active_tasks,
            timestamp=time.time()
        )

    def is_overloaded(self, metrics: NodeMetrics) -> bool:
        """Check if node is overloaded"""
        if metrics.cpu_percent > self.cpu_threshold:
            return True
        if metrics.memory_percent > self.memory_threshold:
            return True
        if metrics.load_average_1m > self.load_threshold:
            return True
        return False

    def get_best_offload_target(self) -> Optional[str]:
        """
        Find the best node to offload work to

        Queries remote nodes for their current load and selects
        the least loaded one.
        """
        candidates = []

        for node_id, node_info in CLUSTER_NODES.items():
            if node_id == self.local_node_id:
                continue  # Skip self

            try:
                # Try to get remote node metrics via SSH
                cmd = f"ssh -o ConnectTimeout=2 {node_info['ip']} 'python3 -c \"import psutil; print(psutil.cpu_percent()); print(psutil.virtual_memory().percent)\"'"
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    remote_cpu = float(lines[0])
                    remote_memory = float(lines[1])

                    # Calculate load score (lower is better)
                    load_score = (remote_cpu * 0.7) + (remote_memory * 0.3)
                    candidates.append((node_id, load_score))
            except:
                # If we can't get metrics, give it a moderate score
                candidates.append((node_id, 50.0))

        if not candidates:
            return None

        # Return node with lowest load
        candidates.sort(key=lambda x: x[1])
        return candidates[0][0]

    def identify_heavy_processes(self) -> List[Dict]:
        """
        Identify processes that could be offloaded

        Returns list of processes with high CPU/memory usage
        """
        heavy = []

        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'cmdline']):
            try:
                info = proc.info

                # Skip system processes
                if info['pid'] < 1000:
                    continue

                # Look for heavy processes
                if info['cpu_percent'] > 30 or info['memory_percent'] > 10:
                    cmdline = ' '.join(info['cmdline']) if info['cmdline'] else ''

                    # Check if it's an offloadable task
                    if any(keyword in cmdline.lower() for keyword in [
                        'python', 'make', 'cargo', 'npm', 'node', 'gcc', 'g++',
                        'docker', 'podman', 'test', 'build', 'compile'
                    ]):
                        heavy.append({
                            'pid': info['pid'],
                            'name': info['name'],
                            'cpu': info['cpu_percent'],
                            'memory': info['memory_percent'],
                            'cmdline': cmdline
                        })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return heavy

    def recommend_offloading(self, metrics: NodeMetrics):
        """
        Analyze system state and recommend offloading actions
        """
        print(f"\n{'='*60}")
        print(f"Performance Analysis - {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        print(f"Node: {self.local_node_id}")
        print(f"CPU: {metrics.cpu_percent:.1f}% (threshold: {self.cpu_threshold}%)")
        print(f"Memory: {metrics.memory_percent:.1f}% (threshold: {self.memory_threshold}%)")
        print(f"Load: {metrics.load_average_1m:.2f} (threshold: {self.load_threshold})")
        print(f"Active tasks: {metrics.active_tasks}")

        if self.is_overloaded(metrics):
            print(f"\n⚠️  OVERLOADED - Recommending offload actions:")

            # Find best offload target
            target_node = self.get_best_offload_target()
            if target_node:
                print(f"   Best offload target: {target_node}")

            # Identify heavy processes
            heavy = self.identify_heavy_processes()
            if heavy:
                print(f"\n   Heavy processes detected ({len(heavy)}):")
                for proc in heavy[:5]:  # Show top 5
                    print(f"   - {proc['name']} (PID {proc['pid']}): CPU {proc['cpu']:.1f}%, Mem {proc['memory']:.1f}%")
                    if 'python' in proc['name'].lower() and 'test' in proc['cmdline'].lower():
                        print(f"     💡 Could offload: Looks like a test suite")
                    elif 'make' in proc['cmdline'].lower() or 'cargo' in proc['cmdline'].lower():
                        print(f"     💡 Could offload: Build process → {target_node}")
        else:
            print(f"\n✅ System load is healthy")

        print(f"{'='*60}\n")

    def run_optimization_cycle(self):
        """Run one optimization cycle"""
        metrics = self.get_current_metrics()

        # Store in history
        self.metrics_history.append(metrics)
        if len(self.metrics_history) > self.max_history:
            self.metrics_history.pop(0)

        # Analyze and recommend
        self.recommend_offloading(metrics)

        # Auto-offload if severely overloaded
        if metrics.cpu_percent > 90 or metrics.load_average_1m > self.load_threshold * 1.5:
            print("🚨 CRITICAL LOAD - Auto-offloading would trigger here")
            # TODO: Implement auto-offload logic

    def run(self):
        """Main daemon loop"""
        print(f"Performance Optimizer started for {self.local_node_id}")
        print(f"Monitoring every {self.check_interval} seconds")
        print(f"Thresholds: CPU {self.cpu_threshold}%, Memory {self.memory_threshold}%, Load {self.load_threshold}")
        print(f"\nPress Ctrl+C to stop\n")

        self.running = True

        try:
            while self.running:
                self.run_optimization_cycle()
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            print("\n\nStopping performance optimizer...")
            self.running = False

    def get_stats(self) -> Dict:
        """Get statistics about optimization"""
        if not self.metrics_history:
            return {"error": "No metrics collected yet"}

        recent = self.metrics_history[-10:]

        avg_cpu = sum(m.cpu_percent for m in recent) / len(recent)
        avg_memory = sum(m.memory_percent for m in recent) / len(recent)
        avg_load = sum(m.load_average_1m for m in recent) / len(recent)

        overload_count = sum(1 for m in recent if self.is_overloaded(m))

        return {
            "node": self.local_node_id,
            "samples": len(recent),
            "avg_cpu": round(avg_cpu, 1),
            "avg_memory": round(avg_memory, 1),
            "avg_load": round(avg_load, 2),
            "overload_count": overload_count,
            "health": "healthy" if overload_count == 0 else "stressed" if overload_count < 5 else "overloaded"
        }


def main():
    """CLI interface"""
    import argparse

    parser = argparse.ArgumentParser(description="Performance Optimization Daemon")
    parser.add_argument("--daemon", action="store_true", help="Run as background daemon")
    parser.add_argument("--interval", type=int, default=10, help="Check interval in seconds")
    parser.add_argument("--cpu-threshold", type=float, default=70.0, help="CPU threshold %%")
    parser.add_argument("--memory-threshold", type=float, default=80.0, help="Memory threshold %%")
    parser.add_argument("--load-threshold", type=float, default=8.0, help="Load average threshold")
    parser.add_argument("--stats", action="store_true", help="Show current stats and exit")

    args = parser.parse_args()

    optimizer = PerformanceOptimizer(
        check_interval=args.interval,
        cpu_threshold=args.cpu_threshold,
        memory_threshold=args.memory_threshold,
        load_threshold=args.load_threshold
    )

    if args.stats:
        # Just show stats
        metrics = optimizer.get_current_metrics()
        print(json.dumps({
            "node": optimizer.local_node_id,
            "cpu_percent": metrics.cpu_percent,
            "memory_percent": metrics.memory_percent,
            "load_1m": metrics.load_average_1m,
            "load_5m": metrics.load_average_5m,
            "load_15m": metrics.load_average_15m,
            "active_tasks": metrics.active_tasks
        }, indent=2))
        return

    if args.daemon:
        # Run as background daemon
        print("Starting performance optimizer daemon...")
        # TODO: Proper daemonization
        optimizer.run()
    else:
        # Run in foreground
        optimizer.run()


if __name__ == "__main__":
    main()
>>>>>>> origin/main
