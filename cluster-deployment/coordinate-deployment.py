#!/usr/bin/env python3
"""
Cluster Deployment Coordinator

This script helps coordinate deployment across all nodes in the cluster.
It creates shared memories and tracks deployment status.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add the deployment directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from cluster_memory import ClusterMemoryManager
    CLUSTER_AVAILABLE = True
except ImportError:
    CLUSTER_AVAILABLE = False
    print("⚠️  Cluster memory not available - basic coordination mode")

def get_deployment_status():
    """Check deployment status on this node"""
    status = {
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }

    # Check if cluster_memory.py exists in MCP directory
    mcp_cluster_file = Path.home() / "Documents" / "Cline" / "MCP" / "enhanced-memory-mcp" / "cluster_memory.py"
    status["checks"]["cluster_memory_installed"] = mcp_cluster_file.exists()

    # Check if node configuration exists
    node_config = Path.home() / ".claude" / "node-config.json"
    status["checks"]["node_config_exists"] = node_config.exists()

    if node_config.exists():
        with open(node_config) as f:
            config = json.load(f)
            status["node_id"] = config.get("node_id", "unknown")
            status["persona"] = config.get("persona_config", "").split("/")[-1].replace(".json", "")
    else:
        status["node_id"] = "unconfigured"
        status["persona"] = "none"

    # Check if databases exist
    if node_config.exists():
        with open(node_config) as f:
            config = json.load(f)
            personal_db = Path(config["memory"]["personal_db"])
            shared_db = Path(config["memory"]["shared_db"])

            status["checks"]["personal_db_exists"] = personal_db.exists()
            status["checks"]["shared_db_exists"] = shared_db.exists()

            if personal_db.exists():
                status["checks"]["personal_db_size"] = personal_db.stat().st_size
            if shared_db.exists():
                status["checks"]["shared_db_size"] = shared_db.stat().st_size

    # Determine overall status
    all_checks = status["checks"]
    if all_checks.get("cluster_memory_installed") and all_checks.get("node_config_exists"):
        if all_checks.get("personal_db_exists") and all_checks.get("shared_db_exists"):
            if all_checks.get("personal_db_size", 0) > 0 or all_checks.get("shared_db_size", 0) > 0:
                status["deployment_status"] = "COMPLETE"
            else:
                status["deployment_status"] = "CONFIGURED"
        else:
            status["deployment_status"] = "PARTIAL"
    else:
        status["deployment_status"] = "NOT_STARTED"

    return status

def announce_deployment():
    """Create a shared memory announcing the deployment package"""
    if not CLUSTER_AVAILABLE:
        print("❌ Cluster memory not available - cannot announce")
        return False

    try:
        node_config_path = Path.home() / ".claude" / "node-config.json"
        if not node_config_path.exists():
            print("❌ Node configuration not found")
            return False

        manager = ClusterMemoryManager(node_config_path)

        # Create deployment announcement
        announcement = {
            "deployment_package_ready": True,
            "location": "/Volumes/SSDRAID0/agentic-system/cluster-deployment",
            "created_by": manager.node_id,
            "created_at": datetime.now().isoformat(),
            "instructions": "Run: /Volumes/SSDRAID0/agentic-system/cluster-deployment/deploy-to-node.sh",
            "status": {
                "macbook-air": "COMPLETE",
                "mac-studio": "PENDING",
                "macbook-pro": "PENDING"
            }
        }

        success = manager.create_entity(
            name="cluster-deployment-announcement",
            entity_type="coordination",
            observations=[
                "🌐 Cluster memory deployment package is ready",
                f"📦 Location: {announcement['location']}",
                f"👤 Prepared by: {manager.node_id} (Researcher)",
                "📋 Deployment instructions and scripts available",
                "🎯 Next: Deploy to mac-studio (Orchestrator) and macbook-pro (Developer)",
                f"⏰ Created: {announcement['created_at']}"
            ],
            scope="shared"
        )

        if success:
            print(f"✅ Deployment announcement created by {manager.node_id}")
            print(f"📡 Other nodes can now see the deployment package is ready")
            return True
        else:
            print("❌ Failed to create announcement")
            return False

    except Exception as e:
        print(f"❌ Error announcing deployment: {e}")
        return False

def check_cluster_readiness():
    """Check if all nodes are ready for cluster operations"""
    if not CLUSTER_AVAILABLE:
        print("⚠️  Cluster memory not available")
        return None

    try:
        node_config_path = Path.home() / ".claude" / "node-config.json"
        if not node_config_path.exists():
            print("⚠️  Node configuration not found")
            return None

        manager = ClusterMemoryManager(node_config_path)

        # Search for deployment status from all nodes
        results = manager.search_entities("deployment-status", scope="shared")

        print(f"\n🌐 Cluster Readiness Check")
        print("=" * 60)
        print(f"Current node: {manager.node_id}")
        print(f"Shared memories found: {len(results)}")

        # Get stats
        stats = manager.get_cluster_stats()
        print(f"\nMemory Statistics:")
        print(f"  Personal: {stats['personal']['entities']} entities, {stats['personal']['relations']} relations")
        print(f"  Shared: {stats['shared']['entities']} entities, {stats['shared']['relations']} relations")

        return {
            "current_node": manager.node_id,
            "shared_memories": len(results),
            "stats": stats
        }

    except Exception as e:
        print(f"❌ Error checking cluster: {e}")
        return None

def main():
    """Main coordination function"""
    import argparse

    parser = argparse.ArgumentParser(description="Cluster Deployment Coordinator")
    parser.add_argument("command", choices=["status", "announce", "check-cluster"],
                      help="Command to execute")

    args = parser.parse_args()

    if args.command == "status":
        status = get_deployment_status()
        print(json.dumps(status, indent=2))

    elif args.command == "announce":
        success = announce_deployment()
        sys.exit(0 if success else 1)

    elif args.command == "check-cluster":
        result = check_cluster_readiness()
        if result:
            print("\n✅ Cluster check complete")
        else:
            print("\n⚠️  Cluster check incomplete")

if __name__ == "__main__":
    main()
