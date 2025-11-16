#!/usr/bin/env python3
"""
Autonomous Metrics Collector
Collects real performance metrics every 15 minutes
"""

import json
import time
import psutil
from datetime import datetime
from pathlib import Path

METRICS_FILE = Path("/tmp/claude_performance_metrics.json")

def collect_metrics():
    """Collect real system metrics"""
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "system": {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent
        },
        "processes": {
            "total": len(psutil.pids()),
            "qdrant_running": any('qdrant' in p.name().lower() for p in psutil.process_iter(['name']) if p.info['name']),
            "temporal_running": any('temporal' in p.name().lower() for p in psutil.process_iter(['name']) if p.info['name'])
        },
        "metrics_version": "1.0"
    }

    # Write to file
    METRICS_FILE.write_text(json.dumps(metrics, indent=2))
    print(f"Metrics collected at {metrics['timestamp']}")
    return metrics

if __name__ == "__main__":
    print("Starting metrics collection...")
    while True:
        try:
            collect_metrics()
        except Exception as e:
            print(f"Error collecting metrics: {e}")
        time.sleep(900)  # 15 minutes
