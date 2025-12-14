#!/usr/bin/env python3
"""
Cluster Brain Integration Script

Run this on any node to integrate with the unified cluster brain.
Handles both local access (when running on macpro51) and remote access (via SMB).

Usage:
    python3 cluster-brain-integrate.py [--test] [--status] [--heartbeat]
"""

import sys
import os
import argparse
import socket
from pathlib import Path

# Detect node identity
def detect_node_id():
    """Detect current node from hostname."""
    hostname = socket.gethostname().lower()
    node_map = {
        'macpro51': 'macpro51',
        'mac-studio': 'mac-studio',
        'macbook-air': 'macbook-air-m3',
        'macbookair': 'macbook-air-m3',
        'completeu': 'completeu-server',
    }
    for key, node_id in node_map.items():
        if key in hostname:
            return node_id
    return hostname

# Database paths for different nodes
def get_db_path():
    """Get cluster brain database path for this node."""
    node_id = detect_node_id()

    # Local path on macpro51 (builder node)
    local_path = Path("/mnt/agentic-system/databases/cluster/cluster_brain.db")

    # SMB mount paths for other nodes
    smb_paths = [
        Path("/Volumes/agentic-system/databases/cluster/cluster_brain.db"),  # macOS
        Path(os.path.expanduser("~/mnt/macpro51/databases/cluster/cluster_brain.db")),  # Manual mount
        Path("/mnt/macpro51/databases/cluster/cluster_brain.db"),  # Linux mount
    ]

    if local_path.exists():
        return local_path

    for path in smb_paths:
        if path.exists():
            return path

    return local_path  # Return default and let connection fail with clear error

def test_connection():
    """Test cluster brain connectivity."""
    import sqlite3

    node_id = detect_node_id()
    db_path = get_db_path()

    print(f"🧠 Cluster Brain Integration Test")
    print(f"=" * 50)
    print(f"Node ID: {node_id}")
    print(f"Database Path: {db_path}")
    print(f"Path Exists: {db_path.exists()}")

    if not db_path.exists():
        print(f"\n❌ Database not found!")
        print(f"\nTo access from macOS nodes, mount SMB share:")
        print(f"  mkdir -p ~/mnt/macpro51")
        print(f"  mount_smbfs //marc@macpro51.local/agentic-system ~/mnt/macpro51")
        return False

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Get counts
        cursor.execute("SELECT COUNT(*) FROM shared_knowledge")
        knowledge_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM cluster_goals WHERE status='active'")
        goals_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM shared_learnings")
        learnings_count = cursor.fetchone()[0]

        cursor.execute("SELECT node_id, role, status FROM node_status")
        nodes = cursor.fetchall()

        conn.close()

        print(f"\n✅ Connection successful!")
        print(f"\n📊 Cluster Brain Status:")
        print(f"  Knowledge entries: {knowledge_count}")
        print(f"  Active goals: {goals_count}")
        print(f"  Shared learnings: {learnings_count}")

        print(f"\n🖥️  Registered Nodes:")
        for node in nodes:
            status_icon = "🟢" if node[2] == "online" else "🟡"
            print(f"  {status_icon} {node[0]}: {node[1]} ({node[2]})")

        return True

    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        return False

def send_heartbeat():
    """Send heartbeat to update this node's status."""
    import sqlite3

    node_id = detect_node_id()
    db_path = get_db_path()

    if not db_path.exists():
        print(f"❌ Database not accessible")
        return False

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE node_status
            SET status = 'online', last_heartbeat = datetime('now')
            WHERE node_id = ?
        """, (node_id,))

        if cursor.rowcount == 0:
            # Node not registered, insert it
            cursor.execute("""
                INSERT INTO node_status (node_id, role, status, last_heartbeat)
                VALUES (?, 'unknown', 'online', datetime('now'))
            """, (node_id,))

        conn.commit()
        conn.close()

        print(f"✅ Heartbeat sent for {node_id}")
        return True

    except Exception as e:
        print(f"❌ Heartbeat failed: {e}")
        return False

def show_status():
    """Show current cluster brain status."""
    import sqlite3

    db_path = get_db_path()

    if not db_path.exists():
        print(f"❌ Database not accessible at {db_path}")
        return

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    print(f"🧠 CLUSTER BRAIN STATUS")
    print(f"=" * 60)

    # Recent knowledge
    print(f"\n📚 Recent Knowledge:")
    cursor.execute("SELECT concept, category, contributed_by FROM shared_knowledge ORDER BY created_at DESC LIMIT 5")
    for row in cursor.fetchall():
        print(f"  • {row[0]} [{row[1]}] by {row[2]}")

    # Active goals
    print(f"\n🎯 Active Goals:")
    cursor.execute("SELECT goal, priority, progress FROM cluster_goals WHERE status='active' ORDER BY priority DESC")
    for row in cursor.fetchall():
        progress_bar = "█" * int(row[2] * 10) + "░" * (10 - int(row[2] * 10))
        print(f"  P{row[1]}: {row[0]} [{progress_bar}] {row[2]*100:.0f}%")

    # Recent learnings
    print(f"\n💡 Recent Learnings:")
    cursor.execute("SELECT learning, learned_by FROM shared_learnings ORDER BY created_at DESC LIMIT 3")
    for row in cursor.fetchall():
        learning = row[0][:80] + "..." if len(row[0]) > 80 else row[0]
        print(f"  • {learning} (by {row[1]})")

    # Node status
    print(f"\n🖥️  Node Status:")
    cursor.execute("SELECT node_id, role, status, current_task, last_heartbeat FROM node_status")
    for row in cursor.fetchall():
        status_icon = "🟢" if row[2] == "online" else "🟡" if row[2] == "pending" else "🔴"
        task = row[3][:40] + "..." if row[3] and len(row[3]) > 40 else (row[3] or "idle")
        print(f"  {status_icon} {row[0]}: {row[1]} - {task}")

    conn.close()

def main():
    parser = argparse.ArgumentParser(description="Cluster Brain Integration")
    parser.add_argument("--test", action="store_true", help="Test connectivity")
    parser.add_argument("--status", action="store_true", help="Show cluster status")
    parser.add_argument("--heartbeat", action="store_true", help="Send heartbeat")

    args = parser.parse_args()

    if args.test:
        test_connection()
    elif args.heartbeat:
        send_heartbeat()
    elif args.status:
        show_status()
    else:
        # Default: test + status
        if test_connection():
            print()
            show_status()

if __name__ == "__main__":
    main()
