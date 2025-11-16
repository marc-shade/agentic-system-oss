#!/usr/bin/env python3
"""
Automatic Task Interceptor

Monitors for Claude Code tool executions and automatically distributes
them across the cluster based on real-time load metrics.

This runs as a daemon and intercepts tasks automatically, making
distributed execution completely transparent.

Features:
- Monitors process creation for offloadable tasks
- Queries real-time load from all nodes via SSH
- Automatically routes to least-loaded capable node
- Transparent to user - no manual offload() calls needed
- Integrated with performance_optimizer for metrics

Usage:
    # Run as daemon
    python3 auto_task_interceptor.py --daemon

    # Run in foreground (for debugging)
    python3 auto_task_interceptor.py
"""

import os
import sys
import time
import psutil
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
import signal
import sqlite3

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

from distributed_task_router import DistributedTaskRouter, CLUSTER_NODES
from performance_optimizer import PerformanceOptimizer, NodeMetrics


@dataclass
class TaskCandidate:
    """A process that could be offloaded"""
    pid: int
    name: str
    cmdline: str
    cpu_percent: float
    memory_percent: float
    requires_os: Optional[str] = None
    requires_capabilities: Optional[List[str]] = None


class AutoTaskInterceptor:
    """
    Automatically intercepts and distributes tasks across the cluster
    """

    def __init__(
        self,
        check_interval: int = 5,
        cpu_trigger: float = 40.0,  # Start offloading at 40% CPU
        enable_auto_offload: bool = True
    ):
        self.check_interval = check_interval
        self.cpu_trigger = cpu_trigger
        self.enable_auto_offload = enable_auto_offload

        self.router = DistributedTaskRouter()
        self.optimizer = PerformanceOptimizer()
        self.local_node_id = self.router.local_node_id

        self.running = False
        self.tracked_pids: Set[int] = set()  # PIDs we've already processed
        self.offloaded_count = 0

    def should_offload_process(self, proc_info: Dict) -> Optional[TaskCandidate]:
        """
        Determine if a process should be offloaded

        Returns TaskCandidate if it should be offloaded, None otherwise
        """
        try:
            pid = proc_info['pid']
            name = proc_info.get('name', '')
            cmdline_list = proc_info.get('cmdline', [])
            cmdline = ' '.join(cmdline_list) if cmdline_list else ''
            cpu = proc_info.get('cpu_percent', 0)
            memory = proc_info.get('memory_percent', 0)

            # Skip if already tracked
            if pid in self.tracked_pids:
                return None

            # Skip system processes
            if pid < 1000:
                return None

            # Skip ourselves
            if 'auto_task_interceptor' in cmdline or 'performance_optimizer' in cmdline:
                return None

            # Look for offloadable patterns
            offloadable_patterns = {
                'python': {'requires_os': None, 'capabilities': []},
                'python3': {'requires_os': None, 'capabilities': []},
                'make': {'requires_os': None, 'capabilities': []},
                'cargo': {'requires_os': None, 'capabilities': []},
                'npm': {'requires_os': None, 'capabilities': []},
                'node': {'requires_os': None, 'capabilities': []},
                'gcc': {'requires_os': None, 'capabilities': []},
                'g++': {'requires_os': None, 'capabilities': []},
                'docker': {'requires_os': None, 'capabilities': ['docker']},
                'podman': {'requires_os': 'linux', 'capabilities': ['podman']},
                'pytest': {'requires_os': None, 'capabilities': []},
                'jest': {'requires_os': None, 'capabilities': []},
            }

            for pattern, requirements in offloadable_patterns.items():
                if pattern in cmdline.lower() and (cpu > 30 or memory > 10):
                    return TaskCandidate(
                        pid=pid,
                        name=name,
                        cmdline=cmdline,
                        cpu_percent=cpu,
                        memory_percent=memory,
                        requires_os=requirements['requires_os'],
                        requires_capabilities=requirements['capabilities'] if requirements['capabilities'] else None
                    )

            return None

        except Exception as e:
            return None

    def get_cluster_load_distribution(self) -> Dict[str, float]:
        """
        Get current load from all cluster nodes

        Returns dict of node_id -> load_score
        """
        load_dist = {}

        for node_id, node_info in CLUSTER_NODES.items():
            try:
                if node_id == self.local_node_id:
                    # Local node - use psutil
                    metrics = self.optimizer.get_current_metrics()
                    load_score = (metrics.cpu_percent * 0.7) + (metrics.memory_percent * 0.3)
                    load_dist[node_id] = load_score
                else:
                    # Remote node - SSH query
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
                        load_score = (remote_cpu * 0.7) + (remote_memory * 0.3)
                        load_dist[node_id] = load_score
                    else:
                        # If we can't get metrics, assume moderate load
                        load_dist[node_id] = 50.0
            except Exception as e:
                # On error, assume moderate load
                load_dist[node_id] = 50.0

        return load_dist

    def offload_task(self, candidate: TaskCandidate) -> bool:
        """
        Offload a task to the cluster

        Returns True if successfully offloaded
        """
        try:
            # Submit task to router
            task_def = {
                "type": "shell",
                "command": candidate.cmdline,
                "requires_os": candidate.requires_os,
                "requires_capabilities": candidate.requires_capabilities,
                "priority": 5,
                "metadata": {
                    "auto_offloaded": True,
                    "original_pid": candidate.pid,
                    "original_node": self.local_node_id
                }
            }

            task_id = self.router.submit_task(task_def)

            # Kill local process
            try:
                os.kill(candidate.pid, signal.SIGTERM)
                time.sleep(0.5)
                # If still alive, force kill
                if psutil.pid_exists(candidate.pid):
                    os.kill(candidate.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass  # Already dead

            print(f"✓ Auto-offloaded: {candidate.name} (PID {candidate.pid}) → Task {task_id}")
            self.tracked_pids.add(candidate.pid)
            self.offloaded_count += 1
            return True

        except Exception as e:
            print(f"✗ Failed to offload {candidate.name}: {e}")
            return False

    def scan_and_offload(self):
        """
        Scan for heavy processes and offload them if needed
        """
        # Get current metrics
        metrics = self.optimizer.get_current_metrics()

        # Only offload if above trigger threshold
        if metrics.cpu_percent < self.cpu_trigger:
            return

        print(f"\n{'='*60}")
        print(f"Auto-Offload Scan - {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        print(f"Local CPU: {metrics.cpu_percent:.1f}% (trigger: {self.cpu_trigger}%)")

        # Get cluster load distribution
        cluster_load = self.get_cluster_load_distribution()
        print(f"\nCluster Load Distribution:")
        for node_id, load in sorted(cluster_load.items(), key=lambda x: x[1]):
            indicator = "🔥" if load > 70 else "✓" if load < 40 else "⚠️"
            print(f"  {indicator} {node_id}: {load:.1f}%")

        # Scan for offloadable processes
        candidates = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'cmdline']):
            try:
                candidate = self.should_offload_process(proc.info)
                if candidate:
                    candidates.append(candidate)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if candidates:
            print(f"\nFound {len(candidates)} offload candidates:")
            for c in candidates[:3]:  # Show top 3
                print(f"  - {c.name} (PID {c.pid}): CPU {c.cpu_percent:.1f}%, Mem {c.memory_percent:.1f}%")
                print(f"    Command: {c.cmdline[:80]}...")

                if self.enable_auto_offload:
                    self.offload_task(c)
                else:
                    print(f"    💡 Would offload (auto-offload disabled)")
        else:
            print("\n✓ No heavy processes detected")

        print(f"\nTotal auto-offloaded this session: {self.offloaded_count}")
        print(f"{'='*60}\n")

    def run(self):
        """Main daemon loop"""
        print(f"Auto Task Interceptor started for {self.local_node_id}")
        print(f"Scanning every {self.check_interval} seconds")
        print(f"CPU trigger: {self.cpu_trigger}%")
        print(f"Auto-offload: {'ENABLED' if self.enable_auto_offload else 'DISABLED'}")
        print(f"\nPress Ctrl+C to stop\n")

        self.running = True

        try:
            while self.running:
                self.scan_and_offload()
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            print("\n\nStopping auto task interceptor...")
            self.running = False

    def get_stats(self) -> Dict:
        """Get statistics about auto-offloading"""
        return {
            "node": self.local_node_id,
            "running": self.running,
            "offloaded_count": self.offloaded_count,
            "tracked_pids": len(self.tracked_pids),
            "auto_offload_enabled": self.enable_auto_offload
        }


def main():
    """CLI interface"""
    import argparse

    parser = argparse.ArgumentParser(description="Automatic Task Interceptor")
    parser.add_argument("--daemon", action="store_true", help="Run as background daemon")
    parser.add_argument("--interval", type=int, default=5, help="Check interval in seconds")
    parser.add_argument("--cpu-trigger", type=float, default=40.0, help="CPU %% to trigger offloading")
    parser.add_argument("--enable-offload", action="store_true", default=True, help="Enable automatic offloading")
    parser.add_argument("--disable-offload", action="store_true", help="Disable automatic offloading (dry-run mode)")
    parser.add_argument("--stats", action="store_true", help="Show current stats and exit")

    args = parser.parse_args()

    enable_offload = not args.disable_offload

    interceptor = AutoTaskInterceptor(
        check_interval=args.interval,
        cpu_trigger=args.cpu_trigger,
        enable_auto_offload=enable_offload
    )

    if args.stats:
        # Just show stats
        stats = interceptor.get_stats()
        print(json.dumps(stats, indent=2))
        return

    if args.daemon:
        # Run as background daemon
        print("Starting auto task interceptor daemon...")
        # TODO: Proper daemonization
        interceptor.run()
    else:
        # Run in foreground
        interceptor.run()


if __name__ == "__main__":
    main()
