#!/usr/bin/env python3
"""
Unified Cluster Health Dashboard
Real-time monitoring of cluster nodes, workflows, services, and system health

Displays:
- Cluster node health and heartbeat status
- Temporal workflow execution status
- Service health (Redis, Qdrant, Temporal, MCP servers)
- System resources (CPU, memory, disk)
- Recent alerts and health events

STATUS: Production Ready - Phase 1 Week 1
"""

import subprocess
import sqlite3
import json
import time
import platform
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional


def get_storage_base() -> Path:
    """Detect correct storage base path for current platform"""
    system = platform.system()

    if system == "Darwin":  # macOS
        ssd_path = Path("/Volumes/SSDRAID0/agentic-system")
        if ssd_path.exists():
            return ssd_path
        files_path = Path("/Volumes/FILES/agentic-system")
        if files_path.exists():
            return files_path
        return Path.home() / "agentic-system"
    elif system == "Linux":
        return Path("/home/marc/agentic-system")
    else:
        return Path.home() / "agentic-system"


STORAGE_BASE = get_storage_base()


def run_command(cmd: str) -> tuple:
    """Run a command and return output and success status"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout.strip(), result.returncode == 0
    except Exception as e:
        return str(e), False


def check_process(name: str) -> bool:
    """Check if a process is running"""
    output, success = run_command(f"ps aux | grep -E '{name}' | grep -v grep")
    return bool(output.strip())


def check_port(port: int) -> bool:
    """Check if a port is in use"""
    output, success = run_command(f"lsof -i :{port} -sTCP:LISTEN 2>/dev/null")
    return bool(output.strip())


def get_cluster_node_health() -> Dict:
    """Get cluster node health from node registry database"""
    try:
        db_path = STORAGE_BASE / "databases/cluster/node_registry.db"

        if not db_path.exists():
            return {"error": "Node registry not found"}

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT node_id, node_name, role, status, last_seen, metadata
            FROM nodes
            ORDER BY node_id
        """)

        nodes = []
        now = datetime.now()

        for row in cursor.fetchall():
            node_id, node_name, role, status, last_seen_str, metadata_str = row

            try:
                last_seen = datetime.fromisoformat(last_seen_str)
                age = now - last_seen

                # Parse metadata for additional info
                try:
                    metadata = json.loads(metadata_str) if metadata_str else {}
                except:
                    metadata = {}

                nodes.append({
                    "node_id": node_id,
                    "node_name": node_name,
                    "role": role,
                    "status": status,
                    "last_seen": last_seen_str,
                    "age_seconds": age.total_seconds(),
                    "age_human": str(age),
                    "metadata": metadata
                })
            except (ValueError, TypeError):
                nodes.append({
                    "node_id": node_id,
                    "node_name": node_name,
                    "role": role,
                    "status": "unknown",
                    "error": "Invalid timestamp"
                })

        conn.close()

        # Count by status
        status_counts = {
            "active": sum(1 for n in nodes if n.get("status") == "active"),
            "degraded": sum(1 for n in nodes if n.get("status") == "degraded"),
            "offline": sum(1 for n in nodes if n.get("status") == "offline"),
            "unknown": sum(1 for n in nodes if n.get("status") == "unknown")
        }

        return {
            "nodes": nodes,
            "counts": status_counts,
            "total": len(nodes)
        }

    except Exception as e:
        return {"error": str(e)}


def get_temporal_workflows() -> List[Dict]:
    """Get status of all Temporal workflows"""
    try:
        # Get workflow list from Temporal
        output, success = run_command("temporal workflow list --limit 20 2>&1")

        if not success or "Error" in output:
            return []

        workflows = []
        lines = output.split('\n')

        for line in lines:
            if 'WorkflowId' in line or 'Status' in line or not line.strip():
                continue

            # Parse workflow line
            parts = line.split()
            if len(parts) >= 4:
                workflows.append({
                    "workflow_id": parts[0],
                    "type": parts[1],
                    "status": parts[2]
                })

        return workflows

    except Exception as e:
        return []


def get_service_health() -> Dict:
    """Check health of core services"""
    services = {
        "temporal": {
            "running": check_process("temporal server start"),
            "port": 7233,
            "ui_port": 8233,
            "description": "Workflow engine"
        },
        "redis": {
            "running": check_port(6379),
            "port": 6379,
            "description": "In-memory cache"
        },
        "qdrant": {
            "running": check_port(6333),
            "port": 6333,
            "description": "Vector database"
        },
        "prometheus": {
            "running": check_process("prometheus"),
            "port": 9700,
            "description": "Metrics collection"
        },
        "loki": {
            "running": check_process("loki"),
            "port": 9900,
            "description": "Log aggregation"
        },
        "grafana": {
            "running": check_process("grafana"),
            "port": 9500,
            "description": "Visualization"
        }
    }

    return services


def get_system_resources() -> Dict:
    """Get system resource usage"""
    resources = {}

    # Disk usage
    disk_output, _ = run_command(f"df -h {STORAGE_BASE} | tail -1 | awk '{{print $5}}'")
    if disk_output:
        resources["disk_usage"] = disk_output.strip()

    # Memory usage (platform-specific)
    if platform.system() == "Darwin":
        mem_output, _ = run_command("top -l 1 | grep PhysMem | awk '{print $2}'")
        resources["memory_usage"] = mem_output.strip() if mem_output else "N/A"
    else:
        mem_output, _ = run_command("free -h | grep Mem | awk '{print $3}'")
        resources["memory_usage"] = mem_output.strip() if mem_output else "N/A"

    # Load average
    load_output, _ = run_command("uptime | awk -F'load averages:' '{print $2}' || uptime | awk -F'load average:' '{print $2}'")
    resources["load_average"] = load_output.strip() if load_output else "N/A"

    # CPU count
    cpu_output, _ = run_command("sysctl -n hw.ncpu 2>/dev/null || nproc")
    resources["cpu_count"] = cpu_output.strip() if cpu_output else "N/A"

    return resources


def print_header():
    """Print dashboard header"""
    print("\033[2J\033[H")  # Clear screen
    print("=" * 100)
    print(f"  UNIFIED CLUSTER HEALTH DASHBOARD - {STORAGE_BASE}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Platform: {platform.system()} {platform.machine()}")
    print("=" * 100)
    print()


def print_section(title: str):
    """Print section header"""
    print(f"\n{title}")
    print("-" * 100)


def print_status(name: str, status: str, details: str = ""):
    """Print a status line"""
    print(f"  {name:<45} {status:<15} {details}")


def format_age(age_seconds: float) -> str:
    """Format age in human-readable format"""
    if age_seconds < 60:
        return f"{int(age_seconds)}s ago"
    elif age_seconds < 3600:
        return f"{int(age_seconds / 60)}m ago"
    elif age_seconds < 86400:
        return f"{int(age_seconds / 3600)}h ago"
    else:
        return f"{int(age_seconds / 86400)}d ago"


def status_icon(condition: bool) -> str:
    """Return status icon based on condition"""
    return "🟢" if condition else "🔴"


def health_icon(status: str) -> str:
    """Return health icon based on node status"""
    icons = {
        "active": "🟢",
        "degraded": "🟡",
        "offline": "🔴",
        "unknown": "⚪"
    }
    return icons.get(status, "⚪")


def main():
    """Display the unified cluster health dashboard"""

    print_header()

    # Section 1: Cluster Node Health
    print_section("1. CLUSTER NODE HEALTH")

    node_health = get_cluster_node_health()

    if "error" in node_health:
        print_status("Error", "🔴", node_health["error"])
    else:
        counts = node_health["counts"]
        total = node_health["total"]

        print_status(
            "Cluster Status",
            f"{counts['active']}/{total} Active",
            f"Degraded: {counts['degraded']}, Offline: {counts['offline']}, Unknown: {counts['unknown']}"
        )

        print()
        for node in node_health["nodes"]:
            status_emoji = health_icon(node.get("status", "unknown"))
            age_str = format_age(node.get("age_seconds", 0)) if "age_seconds" in node else "N/A"

            print_status(
                f"  {node['node_id']} ({node['role']})",
                f"{status_emoji} {node['status']}",
                f"Last seen: {age_str}"
            )

    # Section 2: Temporal Workflows
    print_section("2. TEMPORAL WORKFLOWS")

    workflows = get_temporal_workflows()

    if not workflows:
        print_status("Workflows", "⚠️ Unable to query", "Check if Temporal is running")
    else:
        running_count = sum(1 for w in workflows if w["status"] == "Running")
        print_status("Active Workflows", f"{running_count}/{len(workflows)}", f"Total queried: {len(workflows)}")

        print()
        # Group workflows by type
        workflow_types = {}
        for workflow in workflows:
            wf_type = workflow["type"]
            if wf_type not in workflow_types:
                workflow_types[wf_type] = []
            workflow_types[wf_type].append(workflow)

        for wf_type, wf_list in sorted(workflow_types.items()):
            running = sum(1 for w in wf_list if w["status"] == "Running")
            icon = "🟢" if running > 0 else "🔴"
            print_status(f"  {wf_type}", f"{icon} {running} running", f"Total: {len(wf_list)}")

    # Section 3: Service Health
    print_section("3. SERVICE HEALTH")

    services = get_service_health()

    for service_name, service_info in services.items():
        status_emoji = status_icon(service_info["running"])
        status_text = "Running" if service_info["running"] else "Stopped"

        details = service_info.get("description", "")
        if "ui_port" in service_info and service_info["running"]:
            details += f" | UI: http://localhost:{service_info['ui_port']}"
        elif service_info["running"]:
            details += f" | Port: {service_info['port']}"

        print_status(
            service_name.capitalize(),
            f"{status_emoji} {status_text}",
            details
        )

    # Section 4: System Resources
    print_section("4. SYSTEM RESOURCES")

    resources = get_system_resources()

    print_status("Storage", "📊", f"{STORAGE_BASE}: {resources.get('disk_usage', 'N/A')} used")
    print_status("Memory", "💾", f"{resources.get('memory_usage', 'N/A')} used")
    print_status("CPU", "⚙️", f"{resources.get('cpu_count', 'N/A')} cores - Load: {resources.get('load_average', 'N/A')}")

    # Section 5: Critical Paths
    print_section("5. CRITICAL PATHS")

    critical_paths = [
        (STORAGE_BASE / "databases/cluster/node_registry.db", "Node Registry"),
        (STORAGE_BASE / "databases/cluster/shared_memories.db", "Shared Memories"),
        (STORAGE_BASE / "logs/temporal-workers.log", "Temporal Workers Log"),
        (STORAGE_BASE / "databases/temporal", "Temporal Database")
    ]

    for path, name in critical_paths:
        exists = path.exists()
        status_emoji = status_icon(exists)
        status_text = "✓ Exists" if exists else "✗ Missing"

        # Get size for existing paths
        size_str = ""
        if exists:
            try:
                if path.is_file():
                    size_bytes = path.stat().st_size
                    if size_bytes < 1024:
                        size_str = f"{size_bytes}B"
                    elif size_bytes < 1024 * 1024:
                        size_str = f"{size_bytes / 1024:.1f}KB"
                    else:
                        size_str = f"{size_bytes / (1024 * 1024):.1f}MB"
                elif path.is_dir():
                    size_str = "(directory)"
            except:
                size_str = ""

        print_status(name, f"{status_emoji} {status_text}", size_str)

    # Summary
    print_section("CLUSTER HEALTH SUMMARY")
    print()

    # Overall health assessment
    healthy_nodes = node_health.get("counts", {}).get("active", 0)
    total_nodes = node_health.get("total", 0)
    services_running = sum(1 for s in services.values() if s["running"])
    total_services = len(services)

    if healthy_nodes == total_nodes and services_running == total_services:
        print("  🎉 CLUSTER IS FULLY OPERATIONAL")
        health_status = "EXCELLENT"
    elif healthy_nodes >= total_nodes * 0.75 and services_running >= total_services * 0.75:
        print("  ✅ CLUSTER IS OPERATIONAL WITH MINOR ISSUES")
        health_status = "GOOD"
    elif healthy_nodes >= total_nodes * 0.5:
        print("  ⚠️ CLUSTER HAS DEGRADED PERFORMANCE")
        health_status = "DEGRADED"
    else:
        print("  🔴 CLUSTER HAS CRITICAL ISSUES")
        health_status = "CRITICAL"

    print()
    print(f"  Cluster Health: {health_status}")
    print(f"  Active Nodes: {healthy_nodes}/{total_nodes}")
    print(f"  Running Services: {services_running}/{total_services}")
    print(f"  Storage: {STORAGE_BASE}")
    print(f"  Platform: {platform.system()} {platform.machine()}")
    print()
    print("=" * 100)
    print()
    print("  Press Ctrl+C to stop monitoring | Refresh: 10s")
    print()


if __name__ == "__main__":
    try:
        while True:
            main()
            time.sleep(10)  # Refresh every 10 seconds
    except KeyboardInterrupt:
        print("\n\nCluster health monitoring stopped.")
