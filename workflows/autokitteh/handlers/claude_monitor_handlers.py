"""
Claude Performance Monitor Handlers
Monitors Claude Code execution patterns, performance, and learns optimization opportunities
Runs continuously to improve Claude's effectiveness
"""
import os
import platform
import subprocess
import json
import time
import requests
from datetime import datetime
from pathlib import Path


def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path("/Volumes/SSDRAID0/agentic-system").exists():
            return Path("/Volumes/SSDRAID0/agentic-system")
        elif Path("/Volumes/FILES/agentic-system").exists():
            return Path("/Volumes/FILES/agentic-system")
    elif system == "Linux":
        if Path("/home/marc/agentic-system").exists():
            return Path("/home/marc/agentic-system")
        elif Path("/mnt/agentic-system").exists():
            return Path("/mnt/agentic-system")
    return Path(__file__).parent.parent.parent.parent


_STORAGE_BASE = _get_storage_base()


def monitor_claude_execution(event):
    """Monitor Claude Code execution patterns using real metrics collector"""
    print("=" * 60)
    print(f"Claude Performance Monitor - {datetime.now()}")
    print("=" * 60)

    # Run the advanced metrics collector Python script
    try:
        result = subprocess.run(
            ["python3", str(_STORAGE_BASE / "scripts" / "claude_metrics_collector.py")],
            capture_output=True,
            text=True,
            timeout=30
        )

        print(result.stdout)

        if result.returncode != 0:
            print(f"ERROR: {result.stderr}")
            return {"status": "error", "message": result.stderr}

        # Metrics are now saved to /tmp/claude_performance_metrics.json
        with open("/tmp/claude_performance_metrics.json") as f:
            metrics = json.load(f)

        # Alert if error rate is high
        if metrics.get("error_rate_percent", 0) > 10:
            send_alert(f"High error rate detected: {metrics['error_rate_percent']:.2f}%")

        return metrics

    except Exception as e:
        print(f"Metrics collection failed: {e}")
        return {"status": "error", "message": str(e)}


def analyze_patterns(event):
    """Analyze patterns using advanced detection algorithms"""
    print("\n" + "=" * 60)
    print("Advanced Pattern Analysis")
    print("=" * 60)

    try:
        # Run pattern detector
        result = subprocess.run(
            ["python3", str(_STORAGE_BASE / "scripts" / "pattern_detector.py")],
            capture_output=True,
            text=True,
            timeout=60
        )

        print(result.stdout)

        if result.returncode != 0:
            print(f"ERROR: {result.stderr}")
            return {"status": "error"}

        # Run cost tracker
        cost_result = subprocess.run(
            ["python3", str(_STORAGE_BASE / "scripts" / "cost_tracker.py")],
            capture_output=True,
            text=True,
            timeout=60
        )

        print("\n" + "=" * 60)
        print("Cost Analysis")
        print("=" * 60)
        print(cost_result.stdout)

        # Run predictive maintenance
        maint_result = subprocess.run(
            ["python3", str(_STORAGE_BASE / "scripts" / "predictive_maintenance.py")],
            capture_output=True,
            text=True,
            timeout=60
        )

        print("\n" + "=" * 60)
        print("Predictive Maintenance")
        print("=" * 60)
        print(maint_result.stdout)

        # Load pattern analysis results
        with open("/tmp/claude_pattern_analysis.json") as f:
            patterns = json.load(f)

        # Trigger deep learning if critical issues found
        with open("/tmp/claude_maintenance_alerts.json") as f:
            alerts = json.load(f)

        if alerts.get("alerts_by_severity", {}).get("critical", 0) > 0:
            print("\n🚨 Critical alerts found - triggering deep learning")
            trigger_deep_learning(patterns)
        elif len(patterns.get("optimization_opportunities", [])) > 0:
            print("\n🔍 Optimization opportunities found - triggering deep learning")
            trigger_deep_learning(patterns)

        return patterns

    except Exception as e:
        print(f"Pattern analysis failed: {e}")
        return {"status": "error", "message": str(e)}


def deep_learning(event):
    """Deep learning cycle - analyze, learn, improve using advanced optimization"""
    print("\n" + "=" * 60)
    print("Deep Learning & Self-Improvement")
    print("=" * 60)

    try:
        # Run code optimizer to apply improvements
        result = subprocess.run(
            ["python3", str(_STORAGE_BASE / "scripts" / "code_optimizer.py")],
            capture_output=True,
            text=True,
            timeout=120
        )

        print(result.stdout)

        if result.returncode != 0:
            print(f"ERROR: {result.stderr}")
            return {"status": "error"}

        # Run knowledge graph builder to store learnings
        kg_result = subprocess.run(
            ["python3", str(_STORAGE_BASE / "scripts" / "knowledge_graph_builder.py")],
            capture_output=True,
            text=True,
            timeout=60
        )

        print("\n" + "=" * 60)
        print("Knowledge Graph Building")
        print("=" * 60)
        print(kg_result.stdout)

        # Run performance benchmarking
        bench_result = subprocess.run(
            ["python3", str(_STORAGE_BASE / "scripts" / "performance_benchmarker.py")],
            capture_output=True,
            text=True,
            timeout=60
        )

        print("\n" + "=" * 60)
        print("Performance Benchmarking")
        print("=" * 60)
        print(bench_result.stdout)

        # Load optimization results
        with open("/tmp/claude_optimizations_applied.json") as f:
            optimizations = json.load(f)

        # Load learning summary
        with open("/tmp/claude_learning_summary.json") as f:
            summary = json.load(f)

        # Send voice notification about improvements
        if optimizations.get("total_applied", 0) > 0:
            notify_improvements(optimizations["details"])

        return {
            "timestamp": datetime.now().isoformat(),
            "optimizations_applied": optimizations.get("total_applied", 0),
            "learning_summary": summary
        }

    except Exception as e:
        print(f"Deep learning failed: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


def send_alert(message):
    """Send alert via voice mode"""
    try:
        # Would use voice-mode MCP in production
        print(f"ALERT: {message}")
        return True
    except Exception as e:
        print(f"Alert failed: {e}")
        return False


def trigger_deep_learning(patterns):
    """Trigger Temporal deep learning workflow"""
    try:
        response = requests.post(
            "http://localhost:7233/api/v1/workflows/start",
            json={
                "workflow_id": f"deep-learning-{int(time.time())}",
                "workflow_type": "ClaudeDeepLearningWorkflow",
                "task_queue": "claude-learning-queue",
                "input": {"patterns": patterns}
            },
            timeout=10
        )
        print(f"Deep learning workflow triggered: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"Failed to trigger deep learning: {e}")
        return False


def notify_improvements(improvements):
    """Send voice notification about improvements"""
    try:
        # Extract improvement names
        improvement_names = [imp.get('optimization', 'unknown') for imp in improvements]

        message = f"Claude self-improvement complete. Applied {len(improvements)} optimizations: {', '.join(improvement_names[:3])}"

        if len(improvement_names) > 3:
            message += f" and {len(improvement_names) - 3} more"

        print(f"NOTIFICATION: {message}")

        # In production, would use voice-mode MCP
        # For now, just log the notification
        return True
    except Exception as e:
        print(f"Notification failed: {e}")
        return False
