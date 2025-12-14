#!/bin/bash
#
# MacBook Air M3 - Hive Mind Integration Setup
# Complete setup for researcher node to participate in cluster
#
# Run this on the MacBook Air to enable full cluster features:
#   ./setup_macbook_air_hive_mind.sh
#

set -e


# Platform-aware storage detection
detect_storage_base() {
    if [ -n "$AGENTIC_SYSTEM_PATH" ] && [ -d "$AGENTIC_SYSTEM_PATH" ]; then
        echo "$AGENTIC_SYSTEM_PATH"
        return
    fi
    case "$(uname -s)" in
        Darwin)
            if [ -d "/Volumes/SSDRAID0/agentic-system" ]; then
                echo "/Volumes/SSDRAID0/agentic-system"
            elif [ -d "/Volumes/FILES/agentic-system" ]; then
                echo "/Volumes/FILES/agentic-system"
            fi
            ;;
        Linux)
            if [ -d "/home/marc/agentic-system" ]; then
                echo "/home/marc/agentic-system"
            elif [ -d "/mnt/agentic-system" ]; then
                echo "/mnt/agentic-system"
            fi
            ;;
    esac
}

STORAGE_BASE=$(detect_storage_base)

NODE_ID="macbook-air-m3"
NODE_ROLE="researcher"
NODE_IP="192.168.1.76"

echo "🧠 MacBook Air M3 - Hive Mind Integration Setup"
echo "================================================"
echo ""
echo "Node ID: $NODE_ID"
echo "Role: $NODE_ROLE"
echo "IP: $NODE_IP"
echo ""

# Step 1: Create directory structure
echo "Step 1: Creating directory structure..."
mkdir -p ~/agentic-system/cluster-deployment
mkdir -p ~/agentic-system/databases/cluster
mkdir -p ~/agentic-system/logs
echo "✅ Directories created"
echo ""

# Step 2: Copy core hive mind module
echo "Step 2: Installing hive mind integration..."
if [ -f "$STORAGE_BASE/cluster-deployment/orchestrator_hive_mind.py" ]; then
    cp $STORAGE_BASE/cluster-deployment/orchestrator_hive_mind.py \
       ~/agentic-system/cluster-deployment/
    echo "✅ Hive mind module installed"
else
    echo "⚠️  Source not accessible. Will need manual copy."
    echo "   Copy orchestrator_hive_mind.py from mac-studio"
fi
echo ""

# Step 3: Copy supporting modules
echo "Step 3: Installing supporting modules..."
for module in distributed_task_router.py orchestrator_remote_exec.py toon_serialization.py cluster_memory.py; do
    if [ -f "$STORAGE_BASE/cluster-deployment/$module" ]; then
        cp "$STORAGE_BASE/cluster-deployment/$module" \
           ~/agentic-system/cluster-deployment/
        echo "  ✅ $module"
    else
        echo "  ⚠️  $module not accessible"
    fi
done
echo ""

# Step 4: Copy cluster configuration
echo "Step 4: Installing cluster configuration..."
if [ -f "$STORAGE_BASE/cluster-deployment/cluster-nodes.json" ]; then
    cp $STORAGE_BASE/cluster-deployment/cluster-nodes.json \
       ~/agentic-system/cluster-deployment/
    echo "✅ Cluster nodes configuration installed"
else
    echo "⚠️  Configuration not accessible"
fi
echo ""

# Step 5: Create node-specific configuration
echo "Step 5: Creating node configuration..."
cat > ~/.claude/macbook-air-node-config.json <<'EOF'
{
  "node_id": "macbook-air-m3",
  "node_role": "researcher",
  "node_ip": "192.168.1.76",
  "capabilities": [
    "research",
    "documentation",
    "analysis",
    "lightweight-processing"
  ],
  "storage": {
    "base": "$STORAGE_BASE",
    "databases": "$STORAGE_BASE/databases",
    "logs": "$STORAGE_BASE/logs"
  },
  "cluster": {
    "orchestrator": {
      "node_id": "mac-studio",
      "ip": "192.168.1.16"
    },
    "message_db": "$STORAGE_BASE/databases/cluster/node_messages.db",
    "registry_db": "$STORAGE_BASE/databases/cluster/node_registry.db",
    "shared_memory_db": "$STORAGE_BASE/databases/cluster/shared_memories.db"
  }
}
EOF
echo "✅ Node configuration created at ~/.claude/macbook-air-node-config.json"
echo ""

# Step 6: Create adapted hive mind for researcher node
echo "Step 6: Creating researcher-specific hive mind wrapper..."
cat > ~/agentic-system/cluster-deployment/researcher_hive_mind.py <<'EOF'
#!/usr/bin/env python3
"""
Researcher Node - Hive Mind Integration
Adapted for MacBook Air M3 researcher node

Usage in Claude Code:
    from cluster_deployment.researcher_hive_mind import hive

    # Send message to orchestrator
    hive.send_message("mac-studio", "Research task complete")

    # Query shared knowledge
    papers = hive.query_shared_memory("research papers")

    # Store research findings
    hive.store_shared_memory("research_finding", "New optimization pattern discovered")
"""

import sys
import json
from pathlib import Path

# Use local installation of orchestrator_hive_mind
sys.path.insert(0, str(Path.home() / "agentic-system/cluster-deployment"))

# Load node configuration
config_path = Path.home() / ".claude/macbook-air-node-config.json"
if config_path.exists():
    with open(config_path) as f:
        node_config = json.load(f)
else:
    # Default configuration
    node_config = {
        "node_id": "macbook-air-m3",
        "storage": {
            "base": str(Path.home() / "agentic-system")
        }
    }

# Override database paths for local storage
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid

class ResearcherHiveMind:
    """Hive mind integration adapted for researcher node"""

    def __init__(self):
        self.node_id = node_config["node_id"]
        self.node_role = node_config.get("node_role", "researcher")

        # Local database paths
        db_base = Path(node_config["storage"]["base"]) / "databases/cluster"
        db_base.mkdir(parents=True, exist_ok=True)

        self.messages_db = db_base / "node_messages.db"
        self.shared_memory_db = db_base / "shared_memories.db"
        self.registry_db = db_base / "node_registry.db"

        self._init_databases()

    def _init_databases(self):
        """Initialize local copies of cluster databases"""

        # Messages DB
        conn = sqlite3.connect(self.messages_db)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                message_id TEXT PRIMARY KEY,
                from_node TEXT NOT NULL,
                to_node TEXT NOT NULL,
                message_type TEXT NOT NULL,
                priority INTEGER DEFAULT 5,
                subject TEXT NOT NULL,
                body TEXT,
                metadata TEXT,
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                requires_action BOOLEAN DEFAULT 0,
                action_taken BOOLEAN DEFAULT 0,
                action_result TEXT,
                processed_at TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sent_messages (
                message_id TEXT PRIMARY KEY,
                to_node TEXT NOT NULL,
                subject TEXT NOT NULL,
                body TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

        # Shared Memory DB
        conn = sqlite3.connect(self.shared_memory_db)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                name TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                observations TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                node_id TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def send_message(
        self,
        to_node: str,
        message: str,
        subject: str = "Message from researcher",
        priority: int = 5,
        message_type: str = "notification",
        metadata: Optional[Dict] = None
    ) -> str:
        """Send a message to another node"""

        message_id = str(uuid.uuid4())

        # Store in sent_messages for local tracking
        conn = sqlite3.connect(self.messages_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sent_messages
            (message_id, to_node, subject, body, sent_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (message_id, to_node, subject, message))
        conn.commit()
        conn.close()

        print(f"[RESEARCHER] Message queued for {to_node}: {subject}")
        print(f"  Message ID: {message_id}")
        print(f"  NOTE: Message will be synced to cluster database")

        return message_id

    def store_shared_memory(
        self,
        name: str,
        observations: Any,
        entity_type: str = "research_finding"
    ):
        """Store research finding in shared cluster memory"""

        conn = sqlite3.connect(self.shared_memory_db)
        cursor = conn.cursor()

        # Convert observations to JSON
        if not isinstance(observations, str):
            obs_json = json.dumps(observations if isinstance(observations, list) else [observations])
        else:
            obs_json = json.dumps([observations])

        cursor.execute("""
            INSERT OR REPLACE INTO entities
            (name, entity_type, observations, node_id, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (name, entity_type, obs_json, self.node_id))

        conn.commit()
        conn.close()

        print(f"[RESEARCHER] Stored shared memory: {name}")
        print(f"  Type: {entity_type}")

    def query_shared_memory(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Query shared cluster memory"""

        conn = sqlite3.connect(self.shared_memory_db)
        cursor = conn.cursor()

        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='entities'")
        if not cursor.fetchone():
            conn.close()
            return []

        cursor.execute("""
            SELECT name, entity_type, observations, node_id, created_at
            FROM entities
            WHERE observations LIKE ?
            ORDER BY updated_at DESC
            LIMIT ?
        """, (f"%{query}%", limit))

        results = []
        for row in cursor.fetchall():
            results.append({
                "name": row[0],
                "type": row[1],
                "observations": json.loads(row[2]),
                "source_node": row[3],
                "created_at": row[4]
            })

        conn.close()

        return results

    def get_recent_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages received"""

        conn = sqlite3.connect(self.messages_db)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT message_id, from_node, subject, body, message_type,
                   priority, received_at, action_taken
            FROM messages
            WHERE to_node = ?
            ORDER BY received_at DESC
            LIMIT ?
        """, (self.node_id, limit))

        messages = []
        for row in cursor.fetchall():
            messages.append({
                "message_id": row[0],
                "from": row[1],
                "subject": row[2],
                "body": row[3],
                "type": row[4],
                "priority": row[5],
                "received_at": row[6],
                "action_taken": bool(row[7])
            })

        conn.close()

        return messages

    def get_sync_status(self) -> Dict[str, Any]:
        """Check sync status with cluster"""

        conn = sqlite3.connect(self.messages_db)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM sent_messages")
        sent_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM messages")
        received_count = cursor.fetchone()[0]

        conn.close()

        conn = sqlite3.connect(self.shared_memory_db)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM entities WHERE node_id = ?", (self.node_id,))
        my_memories = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM entities WHERE node_id != ?", (self.node_id,))
        cluster_memories = cursor.fetchone()[0]

        conn.close()

        return {
            "node_id": self.node_id,
            "role": self.node_role,
            "messages_sent": sent_count,
            "messages_received": received_count,
            "my_shared_memories": my_memories,
            "cluster_shared_memories": cluster_memories,
            "total_shared_memories": my_memories + cluster_memories,
            "timestamp": datetime.now().isoformat()
        }

    def __repr__(self):
        return f"<ResearcherHiveMind node={self.node_id} role={self.node_role}>"


# Convenience instance
hive = ResearcherHiveMind()


if __name__ == "__main__":
    print("Researcher Node - Hive Mind Integration")
    print("=" * 60)

    print(f"\nNode: {hive.node_id}")
    print(f"Role: {hive.node_role}")

    print("\nSync Status:")
    status = hive.get_sync_status()
    print(json.dumps(status, indent=2))

    print("\nRecent Messages:")
    messages = hive.get_recent_messages(5)
    if messages:
        for msg in messages:
            print(f"  [{msg['from']}] {msg['subject']}")
    else:
        print("  No messages yet")

    print("\nShared Memories:")
    memories = hive.query_shared_memory("", limit=5)
    if memories:
        for mem in memories:
            print(f"  {mem['name']} ({mem['source_node']})")
    else:
        print("  No shared memories yet")
EOF
chmod +x ~/agentic-system/cluster-deployment/researcher_hive_mind.py
echo "✅ Researcher hive mind created"
echo ""

# Step 7: Test the integration
echo "Step 7: Testing hive mind integration..."
cd ~/agentic-system/cluster-deployment
python3 researcher_hive_mind.py
echo ""

# Step 8: Create quick reference
echo "Step 8: Creating quick reference..."
cat > ~/agentic-system/RESEARCHER_HIVE_MIND.md <<'EOF'
# Researcher Node - Hive Mind Quick Reference

## Setup Complete!

The MacBook Air M3 is now integrated into the cluster hive mind as a researcher node.

## Python API

```python
from cluster_deployment.researcher_hive_mind import hive

# Check sync status
status = hive.get_sync_status()

# Send message to orchestrator
hive.send_message(
    "mac-studio",
    "Research task completed",
    subject="Research Update"
)

# Store research findings
hive.store_shared_memory(
    "paper_summary_2025_11_20",
    "Discovered new optimization pattern in distributed systems",
    entity_type="research_finding"
)

# Query shared knowledge
findings = hive.query_shared_memory("optimization")

# Check messages
messages = hive.get_recent_messages(10)
```

## Database Locations

- Messages: `~/agentic-system/databases/cluster/node_messages.db`
- Shared Memory: `~/agentic-system/databases/cluster/shared_memories.db`
- Registry: `~/agentic-system/databases/cluster/node_registry.db`

## Sync with Cluster

The researcher node maintains local copies of cluster databases. To sync:

1. Messages are queued locally and synced via GitHub daemon
2. Shared memories replicate automatically
3. Run `hive.get_sync_status()` to check sync state

## Capabilities

As a researcher node, you specialize in:
- Research and documentation
- Analysis tasks
- Lightweight processing
- Mobile operations

## Next Steps

1. Import hive mind in Claude Code sessions
2. Store research findings as you work
3. Query cluster knowledge before starting new research
4. Send updates to orchestrator on task completion
EOF
echo "✅ Quick reference created at ~/agentic-system/RESEARCHER_HIVE_MIND.md"
echo ""

echo "================================================"
echo "✅ MacBook Air M3 Hive Mind Integration Complete!"
echo "================================================"
echo ""
echo "Your researcher node can now:"
echo "  • Send messages to other cluster nodes"
echo "  • Store and query shared cluster memory"
echo "  • Access cluster-wide knowledge"
echo "  • Participate in coordinated operations"
echo ""
echo "Quick test:"
echo "  python3 ~/agentic-system/cluster-deployment/researcher_hive_mind.py"
echo ""
echo "In Claude Code:"
echo "  from cluster_deployment.researcher_hive_mind import hive"
echo "  status = hive.get_sync_status()"
echo ""
