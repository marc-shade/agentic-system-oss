#!/usr/bin/env python3
"""
Cluster Audit and Improvement Workflow
Proactive monitoring and autonomous improvement for distributed agentic cluster

Run this periodically (e.g., hourly) to:
1. Audit all node statuses
2. Check service health
3. Identify improvement opportunities
4. Store findings in enhanced-memory
5. Suggest or auto-apply optimizations
"""

import os
import platform
import sqlite3
import requests
import json
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
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()

CLUSTER_DB = _STORAGE_BASE / "databases" / "cluster" / "node_chat.db"
MEMORY_DB = Path.home() / ".claude" / "enhanced_memories" / "memory.db"

NODES = {
    "mac-studio": {
        "role": "orchestrator",
        "priority": 1,
        "apis": ["http://localhost:8233"],  # Temporal UI
    },
    "macpro51": {
        "role": "builder",
        "priority": 3,
        "apis": [
            "http://macpro51.local:9000/api/v1/status",  # Builder API
            "http://macpro51.local:8888/api/all",  # Hardware info
        ],
    },
    "macbook-air-m3": {
        "role": "researcher",
        "priority": 2,
        "apis": [],  # No known API yet
    },
    "completeu-server": {
        "role": "app_server",
        "priority": 2,
        "apis": ["http://completeu-server.local:5000"],  # Application
    },
}


def audit_node(node_id, config):
    """Audit a single node's health and services"""
    result = {
        "node_id": node_id,
        "role": config["role"],
        "priority": config["priority"],
        "timestamp": datetime.now().isoformat(),
        "reachable": False,
        "services": [],
        "issues": [],
        "recommendations": [],
    }

    # Try to reach node APIs
    for api_url in config["apis"]:
        try:
            resp = requests.get(api_url, timeout=2)
            if resp.status_code == 200:
                result["reachable"] = True
                result["services"].append(
                    {"url": api_url, "status": "healthy", "data": resp.json()}
                )
        except Exception as e:
            result["issues"].append(f"API {api_url} unreachable: {str(e)}")

    # Node-specific checks
    if node_id == "macpro51" and result["reachable"]:
        # Check if builder is idle and could be used
        for svc in result["services"]:
            if "queue_size" in svc.get("data", {}):
                queue_size = svc["data"]["queue_size"]
                if queue_size == 0:
                    result["recommendations"].append(
                        "Builder node is idle - consider offloading tasks"
                    )

    return result


def check_cluster_messages():
    """Check for unread cluster messages"""
    if not CLUSTER_DB.exists():
        return []

    conn = sqlite3.connect(CLUSTER_DB)
    c = conn.cursor()

    # Get unread messages
    c.execute(
        """SELECT from_node, to_node, content, timestamp
                 FROM messages
                 WHERE delivered = 0
                 ORDER BY timestamp DESC
                 LIMIT 10"""
    )

    messages = []
    for row in c.fetchall():
        messages.append(
            {
                "from": row[0],
                "to": row[1],
                "content": row[2][:100] + "..." if len(row[2]) > 100 else row[2],
                "timestamp": row[3],
            }
        )

    conn.close()
    return messages


def store_audit_results(audit_data):
    """Store audit results in enhanced-memory for learning"""
    if not MEMORY_DB.exists():
        return

    # This would integrate with enhanced-memory MCP
    # For now, just log to file
    audit_log = _STORAGE_BASE / "logs" / "cluster-audit.log"
    audit_log.parent.mkdir(parents=True, exist_ok=True)

    with open(audit_log, "a") as f:
        f.write(f"\n=== Cluster Audit {datetime.now()} ===\n")
        f.write(json.dumps(audit_data, indent=2))
        f.write("\n")


def run_audit():
    """Run complete cluster audit"""
    print("🔍 Starting cluster audit...")

    results = {
        "timestamp": datetime.now().isoformat(),
        "nodes": {},
        "cluster_health": {"online": 0, "offline": 0, "issues": []},
        "unread_messages": [],
        "recommendations": [],
    }

    # Audit each node
    for node_id, config in NODES.items():
        print(f"  Auditing {node_id}...")
        node_result = audit_node(node_id, config)
        results["nodes"][node_id] = node_result

        if node_result["reachable"]:
            results["cluster_health"]["online"] += 1
        else:
            results["cluster_health"]["offline"] += 1
            results["cluster_health"]["issues"].append(
                f"{node_id} ({config['role']}) is offline"
            )

        # Collect recommendations
        results["recommendations"].extend(node_result["recommendations"])

    # Check cluster messages
    print("  Checking cluster messages...")
    results["unread_messages"] = check_cluster_messages()

    # Store results
    store_audit_results(results)

    # Print summary
    print("\n📊 Audit Summary:")
    print(f"  Nodes online: {results['cluster_health']['online']}/4")
    print(f"  Nodes offline: {results['cluster_health']['offline']}/4")
    print(f"  Unread messages: {len(results['unread_messages'])}")
    print(f"  Recommendations: {len(results['recommendations'])}")

    if results["recommendations"]:
        print("\n💡 Recommendations:")
        for rec in results["recommendations"]:
            print(f"  - {rec}")

    if results["cluster_health"]["issues"]:
        print("\n⚠️  Issues:")
        for issue in results["cluster_health"]["issues"]:
            print(f"  - {issue}")

    return results


if __name__ == "__main__":
    run_audit()
