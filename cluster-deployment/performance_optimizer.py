#!/usr/bin/env python3
"""
Performance Optimizer for Cluster Execution

Monitors system performance and provides optimization recommendations:
- CPU usage tracking
- Memory utilization
- Load average monitoring
- Overload detection

Now includes TOON serialization for 50% token reduction on metrics broadcasts.
"""

import os
import sys
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
    cpu_percent: float
    memory_percent: float
    load_average_1m: float
    load_average_5m: float
    load_average_15m: float
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
