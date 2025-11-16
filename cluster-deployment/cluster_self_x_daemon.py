#!/usr/bin/env python3
"""
Cluster Self-X Daemon

Master orchestrator for all self-* systems:
- Self-Improvement: Autonomous cluster evolution
- Self-Optimization: Performance tuning and load balancing
- Self-Healing: Automatic problem detection and resolution
- Self-Discovery: Continuous node and capability discovery

This daemon runs on each node and coordinates all autonomous
background processes for distributed cluster intelligence.

Features:
- Unified orchestration of all self-X components
- Ollama-powered AI decision making
- Automatic task distribution and load balancing
- Continuous improvement cycles
- Health monitoring and self-repair

Usage:
    # Run as daemon (production)
    python3 cluster_self_x_daemon.py --daemon

    # Run in foreground (debugging)
    python3 cluster_self_x_daemon.py

    # Run specific module only
    python3 cluster_self_x_daemon.py --module improvement
    python3 cluster_self_x_daemon.py --module optimization
    python3 cluster_self_x_daemon.py --module discovery

Configuration:
    Edit ~/.claude/self-x-config.json to customize:
    - improvement_interval: How often to run improvement cycles (default: 3600s)
    - optimization_interval: How often to optimize performance (default: 300s)
    - discovery_interval: How often to discover nodes (default: 600s)
    - enable_auto_improve: Auto-apply improvements (default: true)
    - ollama_model: AI model for reasoning (default: llama3.2:latest)
"""

import os
import sys
import time
import json
import threading
import signal
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

from performance_optimizer import PerformanceOptimizer
from auto_task_interceptor import AutoTaskInterceptor
from node_discovery import NodeDiscovery
from autonomous_self_improvement_agent import AutonomousSelfImprovementAgent
from ollama_persistent_agent import OllamaPersistentAgent


@dataclass
class SelfXConfig:
    """Configuration for self-X daemon"""
    # Intervals (seconds)
    improvement_interval: int = 3600  # 1 hour
    optimization_interval: int = 300  # 5 minutes
    discovery_interval: int = 600  # 10 minutes

    # Auto-apply settings
    enable_auto_improve: bool = True
    enable_auto_optimize: bool = True
    enable_auto_offload: bool = True

    # Ollama settings
    ollama_model: str = "llama3.2:latest"
    ollama_host: str = "http://localhost:11434"

    # Thresholds
    cpu_trigger: float = 40.0
    memory_trigger: float = 70.0

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> 'SelfXConfig':
        """Load config from file or use defaults"""
        if config_path is None:
            config_path = Path.home() / ".claude" / "self-x-config.json"

        if config_path.exists():
            with open(config_path) as f:
                data = json.load(f)
                return cls(**data)
        else:
            # Create default config
            config = cls()
            config.save(config_path)
            return config

    def save(self, config_path: Path):
        """Save config to file"""
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(self.__dict__, f, indent=2)


class ClusterSelfXDaemon:
    """
    Master orchestrator for all cluster self-* systems
    """

    def __init__(self, config: Optional[SelfXConfig] = None):
        self.config = config or SelfXConfig.load()

        # Initialize components
        self.performance_optimizer = PerformanceOptimizer(
            check_interval=self.config.optimization_interval,
            cpu_threshold=self.config.cpu_trigger,
            memory_threshold=self.config.memory_trigger
        )

        self.task_interceptor = AutoTaskInterceptor(
            check_interval=self.config.optimization_interval,
            cpu_trigger=self.config.cpu_trigger,
            enable_auto_offload=self.config.enable_auto_offload
        )

        self.discovery = NodeDiscovery()

        self.improvement_agent = AutonomousSelfImprovementAgent(
            cycle_interval=self.config.improvement_interval,
            enable_auto_improve=self.config.enable_auto_improve
        )

        self.ai_agent = OllamaPersistentAgent(
            model=self.config.ollama_model,
            ollama_host=self.config.ollama_host
        )

        self.running = False
        self.threads = []

        # Statistics
        self.stats = {
            "start_time": 0,
            "cycles": {
                "improvement": 0,
                "optimization": 0,
                "discovery": 0
            },
            "improvements_applied": 0,
            "tasks_offloaded": 0
        }

    def _run_improvement_cycle(self):
        """Background thread for improvement cycles"""
        print(f"[Self-Improvement] Thread started")

        while self.running:
            try:
                print(f"\n[Self-Improvement] Starting cycle...")
                summary = self.improvement_agent.run_improvement_cycle(dry_run=False)

                self.stats["cycles"]["improvement"] += 1
                self.stats["improvements_applied"] += summary.get("improvements_applied", 0)

                print(f"[Self-Improvement] Cycle complete. Waiting {self.config.improvement_interval}s...")
                time.sleep(self.config.improvement_interval)

            except Exception as e:
                print(f"[Self-Improvement] Error: {e}")
                time.sleep(60)  # Wait a bit on error

    def _run_optimization_cycle(self):
        """Background thread for performance optimization"""
        print(f"[Self-Optimization] Thread started")

        while self.running:
            try:
                # Run performance monitoring
                self.performance_optimizer.run_optimization_cycle()

                # Run task interception
                if self.config.enable_auto_offload:
                    self.task_interceptor.scan_and_offload()

                self.stats["cycles"]["optimization"] += 1
                self.stats["tasks_offloaded"] = self.task_interceptor.offloaded_count

                time.sleep(self.config.optimization_interval)

            except Exception as e:
                print(f"[Self-Optimization] Error: {e}")
                time.sleep(30)

    def _run_discovery_cycle(self):
        """Background thread for node discovery"""
        print(f"[Self-Discovery] Thread started")

        while self.running:
            try:
                print(f"\n[Self-Discovery] Discovering cluster state...")

                # Discover all nodes
                inventories = {}
                inventories[self.discovery.node_id] = self.discovery.discover_local_inventory()

                from distributed_task_router import CLUSTER_NODES
                for node_id in CLUSTER_NODES.keys():
                    if node_id != self.discovery.node_id:
                        inv = self.discovery.discover_remote_inventory(node_id)
                        if inv:
                            inventories[node_id] = inv

                # Use AI to analyze cluster
                if len(inventories) > 1:
                    decision = self.ai_agent.analyze_cluster_state(inventories)
                    print(f"[Self-Discovery] AI Decision: {decision.decision_type}")
                    print(f"[Self-Discovery] Reasoning: {decision.reasoning}")

                    if decision.recommended_actions:
                        print(f"[Self-Discovery] Recommended actions: {len(decision.recommended_actions)}")

                self.stats["cycles"]["discovery"] += 1

                print(f"[Self-Discovery] Waiting {self.config.discovery_interval}s...")
                time.sleep(self.config.discovery_interval)

            except Exception as e:
                print(f"[Self-Discovery] Error: {e}")
                time.sleep(60)

    def start(self):
        """Start all self-X components"""
        print(f"{'='*60}")
        print(f"Cluster Self-X Daemon Starting")
        print(f"{'='*60}")
        print(f"Node: {self.discovery.node_id}")
        print(f"")
        print(f"Modules:")
        print(f"  ✓ Self-Improvement (interval: {self.config.improvement_interval}s)")
        print(f"  ✓ Self-Optimization (interval: {self.config.optimization_interval}s)")
        print(f"  ✓ Self-Discovery (interval: {self.config.discovery_interval}s)")
        print(f"  ✓ AI Agent (model: {self.config.ollama_model})")
        print(f"")
        print(f"Auto-apply:")
        print(f"  Improvements: {'ENABLED' if self.config.enable_auto_improve else 'DISABLED'}")
        print(f"  Optimization: {'ENABLED' if self.config.enable_auto_optimize else 'DISABLED'}")
        print(f"  Task Offload: {'ENABLED' if self.config.enable_auto_offload else 'DISABLED'}")
        print(f"")
        print(f"Press Ctrl+C to stop")
        print(f"{'='*60}\n")

        self.running = True
        self.stats["start_time"] = time.time()

        # Start background threads
        improvement_thread = threading.Thread(target=self._run_improvement_cycle, daemon=True)
        optimization_thread = threading.Thread(target=self._run_optimization_cycle, daemon=True)
        discovery_thread = threading.Thread(target=self._run_discovery_cycle, daemon=True)

        improvement_thread.start()
        optimization_thread.start()
        discovery_thread.start()

        self.threads = [improvement_thread, optimization_thread, discovery_thread]

        # Main loop - just keep alive and show stats
        try:
            while self.running:
                time.sleep(60)  # Update stats every minute

                # Show stats
                uptime = time.time() - self.stats["start_time"]
                print(f"\n[Stats] Uptime: {uptime/3600:.1f}h | "
                      f"Improvements: {self.stats['improvements_applied']} | "
                      f"Tasks Offloaded: {self.stats['tasks_offloaded']} | "
                      f"Cycles: I:{self.stats['cycles']['improvement']} "
                      f"O:{self.stats['cycles']['optimization']} "
                      f"D:{self.stats['cycles']['discovery']}")

        except KeyboardInterrupt:
            print("\n\nStopping Cluster Self-X Daemon...")
            self.running = False

            # Wait for threads to finish
            for thread in self.threads:
                thread.join(timeout=5)

            print("✓ All modules stopped")

    def get_stats(self) -> Dict:
        """Get daemon statistics"""
        uptime = time.time() - self.stats["start_time"] if self.stats["start_time"] > 0 else 0

        return {
            "node": self.discovery.node_id,
            "running": self.running,
            "uptime_seconds": uptime,
            "stats": self.stats,
            "config": self.config.__dict__
        }


def main():
    """CLI interface"""
    import argparse

    parser = argparse.ArgumentParser(description="Cluster Self-X Daemon")
    parser.add_argument("--daemon", action="store_true", help="Run as background daemon")
    parser.add_argument("--module", type=str, choices=["improvement", "optimization", "discovery"],
                        help="Run specific module only")
    parser.add_argument("--config", type=str, help="Path to config file")
    parser.add_argument("--stats", action="store_true", help="Show daemon statistics")
    parser.add_argument("--create-config", action="store_true", help="Create default config file")

    args = parser.parse_args()

    # Load config
    config_path = Path(args.config) if args.config else None
    config = SelfXConfig.load(config_path)

    if args.create_config:
        config_path = config_path or Path.home() / ".claude" / "self-x-config.json"
        config.save(config_path)
        print(f"✓ Created config at {config_path}")
        return

    # Create daemon
    daemon = ClusterSelfXDaemon(config)

    if args.stats:
        stats = daemon.get_stats()
        print(json.dumps(stats, indent=2))
        return

    if args.module:
        # Run specific module only
        print(f"Running {args.module} module only...")

        if args.module == "improvement":
            daemon.improvement_agent.run_continuous()
        elif args.module == "optimization":
            daemon.performance_optimizer.run()
        elif args.module == "discovery":
            daemon._run_discovery_cycle()
    else:
        # Run all modules
        daemon.start()


if __name__ == "__main__":
    main()
