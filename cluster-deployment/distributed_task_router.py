#!/usr/bin/env python3
"""
Distributed Task Router - Runs on every cluster node

Automatically routes tasks to the best available node based on:
- Task requirements (OS, arch, capabilities)
- Node current load
- Node specialties
- Priority to keep active node free

Usage:
    # On any node - route a task
    router = DistributedTaskRouter()
    task_id = router.submit_task({
        "type": "compile",
        "language": "c++",
        "requires_os": "linux",
        "source": "/path/to/code"
    })

    # Task automatically routes to best node (likely macpro51 for Linux builds)
    result = router.wait_for_result(task_id)
"""
import platform

import json
import os
import socket
import subprocess
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from pathlib import Path
import uuid
import sqlite3

# Cluster node registry
CLUSTER_NODES = {
    "macpro51": {
        "ip": "192.168.1.27",  # Fixed: was 192.168.1.183
        "hostname": "macpro51.local",
        "os": "linux",
        "arch": "x86_64",
        "capabilities": ["docker", "podman", "raid", "nvme", "compilation", "testing"],
        "specialties": ["compilation", "testing", "containerization", "benchmarking"],
        "max_tasks": 10,
        "priority": 3  # Lower = higher priority for offloading
    },
    "mac-studio": {
        "ip": "192.168.1.16",  # Auto-detected from current DHCP
        "hostname": "mac-studio.local",  # Fixed: normalized hostname
        "os": "macos",
        "arch": "arm64",
        "capabilities": ["orchestration", "coordination", "temporal"],
        "specialties": ["orchestration", "coordination", "monitoring"],
        "max_tasks": 5,
        "priority": 1  # Keep this free - orchestrator
    },
    "macbook-air": {
        "ip": "192.168.1.76",  # Auto-detected from network scan
        "hostname": "macbook-air.local",  # Fixed: normalized hostname
        "os": "macos",
        "arch": "arm64",
        "capabilities": ["research", "documentation", "analysis"],
        "specialties": ["research", "documentation", "analysis"],
        "max_tasks": 3,
        "priority": 2
    }
}

@dataclass
class Task:
    """Task definition for cluster execution"""
    task_id: str
    task_type: str
    command: Optional[str] = None
    script: Optional[str] = None
    requires_os: Optional[str] = None
    requires_arch: Optional[str] = None
    requires_capabilities: Optional[List[str]] = None
    priority: int = 5
    metadata: Optional[Dict[str, Any]] = None
    submitted_from: Optional[str] = None
    submitted_at: Optional[float] = None

    def to_dict(self) -> Dict:
        return asdict(self)


class DistributedTaskRouter:
    """Routes tasks across cluster nodes automatically"""

    def __init__(self):
        self.local_node_id = self._detect_local_node()
        self.db_path = self._get_db_path()
        self._init_database()

    def _detect_local_node(self) -> str:
        """Detect which node we're running on"""
        hostname = socket.gethostname().lower()

        # Check against known nodes
        if "macpro51" in hostname:
            return "macpro51"
        elif "studio" in hostname:
            return "mac-studio"
        elif "mac" in hostname and os.path.exists("/Users/marc"):
            # Check if it's MacBook Air by IP
            try:
                result = subprocess.run(
                    ["hostname", "-I"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if "192.168.1.76" in result.stdout:
                    return "macbook-air"
            except:
                pass
            return "mac-studio"  # Default macOS node
        else:
            return "macpro51"  # Default Linux node

    def _get_db_path(self) -> Path:
        """Get path to task queue database"""
        if self.local_node_id == "macpro51":
            base = Path(str(_STORAGE_BASE))
        else:
            base = Path.home() / "agentic-system"

        db_dir = base / "databases" / "cluster"
        db_dir.mkdir(parents=True, exist_ok=True)
        return db_dir / "task_queue.db"

    def _init_database(self):
        """Initialize task queue database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_queue (
                task_id TEXT PRIMARY KEY,
                task_type TEXT NOT NULL,
                command TEXT,
                script TEXT,
                requires_os TEXT,
                requires_arch TEXT,
                requires_capabilities TEXT,
                priority INTEGER DEFAULT 5,
                metadata TEXT,
                submitted_from TEXT,
                submitted_at REAL,
                assigned_to TEXT,
                assigned_at REAL,
                status TEXT DEFAULT 'pending',
                result TEXT,
                completed_at REAL,
                error TEXT
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_status ON task_queue(status)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_assigned_to ON task_queue(assigned_to)
        """)

        conn.commit()
        conn.close()

    def submit_task(self, task_def: Dict[str, Any]) -> str:
        """
        Submit a task for execution

        Task automatically routes to best available node based on requirements
        """
        task_id = str(uuid.uuid4())

        task = Task(
            task_id=task_id,
            task_type=task_def.get("type", "generic"),
            command=task_def.get("command"),
            script=task_def.get("script"),
            requires_os=task_def.get("requires_os"),
            requires_arch=task_def.get("requires_arch"),
            requires_capabilities=task_def.get("requires_capabilities"),
            priority=task_def.get("priority", 5),
            metadata=task_def.get("metadata"),
            submitted_from=self.local_node_id,
            submitted_at=time.time()
        )

        # Find best node for this task
        # Support force_node to override routing
        if task_def.get("force_node") and task_def["force_node"] in CLUSTER_NODES:
            target_node = task_def["force_node"]
        else:
            target_node = self._route_task(task)

        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO task_queue (
                task_id, task_type, command, script,
                requires_os, requires_arch, requires_capabilities,
                priority, metadata, submitted_from, submitted_at,
                assigned_to, assigned_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task.task_id,
            task.task_type,
            task.command,
            task.script,
            task.requires_os,
            task.requires_arch,
            json.dumps(task.requires_capabilities) if task.requires_capabilities else None,
            task.priority,
            json.dumps(task.metadata) if task.metadata else None,
            task.submitted_from,
            task.submitted_at,
            target_node,
            time.time(),
            "assigned"
        ))

        conn.commit()
        conn.close()

        # Execute on target node
        if target_node == self.local_node_id:
            # Execute locally
            self._execute_local(task)
        else:
            # Execute remotely
            self._execute_remote(task, target_node)

        return task_id

    def _route_task(self, task: Task) -> str:
        """
        Determine best node for task execution

        Routing priority:
        1. Match OS requirement
        2. Match architecture
        3. Match capabilities
        4. Prefer specialized nodes
        5. Prefer less loaded nodes
        6. Avoid active node (aggressive offloading)
        """
        candidates = []

        for node_id, node_info in CLUSTER_NODES.items():
            # Filter by OS requirement
            if task.requires_os and node_info["os"] != task.requires_os:
                continue

            # Filter by architecture
            if task.requires_arch and node_info["arch"] != task.requires_arch:
                continue

            # Filter by capabilities
            if task.requires_capabilities:
                node_caps = set(node_info["capabilities"])
                required_caps = set(task.requires_capabilities)
                if not required_caps.issubset(node_caps):
                    continue

            # Calculate match score
            score = 0

            # Prefer specialized nodes
            if task.task_type in node_info["specialties"]:
                score += 100

            # Prefer higher priority (lower number)
            score += (5 - node_info["priority"]) * 20

            # Heavily penalize local node (aggressive offloading)
            if node_id == self.local_node_id:
                score -= 1000

            # Get current load (future: check actual load)
            # For now, simulate with fixed preference

            candidates.append((node_id, score))

        if not candidates:
            # No suitable nodes, run locally
            return self.local_node_id

        # Select node with highest score
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def _execute_local(self, task: Task):
        """Execute task on local node"""
        try:
            if task.command:
                result = subprocess.run(
                    task.command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                output = result.stdout
                error = result.stderr if result.returncode != 0 else None
            elif task.script:
                # Write script to temp file and execute
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
                    f.write(task.script)
                    script_path = f.name

                os.chmod(script_path, 0o755)
                result = subprocess.run(
                    [script_path],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                output = result.stdout
                error = result.stderr if result.returncode != 0 else None
                os.unlink(script_path)
            else:
                output = "No command or script provided"
                error = None

            # Update database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE task_queue
                SET status = 'completed', result = ?, error = ?, completed_at = ?
                WHERE task_id = ?
            """, (output, error, time.time(), task.task_id))
            conn.commit()
            conn.close()

        except Exception as e:
            # Update with error
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE task_queue
                SET status = 'failed', error = ?, completed_at = ?
                WHERE task_id = ?
            """, (str(e), time.time(), task.task_id))
            conn.commit()
            conn.close()

    def _execute_remote(self, task: Task, target_node: str):
        """Execute task on remote node via SSH"""
        import shlex
        node_info = CLUSTER_NODES[target_node]

        # Build remote execution command using list args for security
        if task.command:
            ssh_args = [
                "ssh",
                "-o", "ConnectTimeout=5",
                "-o", "StrictHostKeyChecking=accept-new",
                "-o", "BatchMode=yes",
                f"marc@{node_info['ip']}",
                task.command  # SSH handles this as a single argument
            ]
            use_list_args = True
        elif task.script:
            # Transfer script and execute
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
                f.write(task.script)
                local_script = f.name

            remote_script = f"/tmp/task_{task.task_id}.sh"

            # SCP script to remote node using list args
            subprocess.run(
                [
                    "scp",
                    "-o", "ConnectTimeout=5",
                    "-o", "StrictHostKeyChecking=accept-new",
                    "-o", "BatchMode=yes",
                    local_script,
                    f"marc@{node_info['ip']}:{remote_script}"
                ],
                capture_output=True,
                timeout=30
            )

            ssh_args = [
                "ssh",
                "-o", "ConnectTimeout=5",
                "-o", "StrictHostKeyChecking=accept-new",
                "-o", "BatchMode=yes",
                f"marc@{node_info['ip']}",
                f"chmod +x {remote_script} && {remote_script} && rm {remote_script}"
            ]
            use_list_args = True
            os.unlink(local_script)
        else:
            # No command, mark as failed
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE task_queue
                SET status = 'failed', error = 'No command or script', completed_at = ?
                WHERE task_id = ?
            """, (time.time(), task.task_id))
            conn.commit()
            conn.close()
            return

        try:
            # Execute remotely using list args (no shell=True for security)
            result = subprocess.run(
                ssh_args,
                capture_output=True,
                text=True,
                timeout=60  # Reduced from 300s - most commands should complete in 60s
            )

            output = result.stdout
            error = result.stderr if result.returncode != 0 else None

            # Update database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE task_queue
                SET status = 'completed', result = ?, error = ?, completed_at = ?
                WHERE task_id = ?
            """, (output, error, time.time(), task.task_id))
            conn.commit()
            conn.close()

        except Exception as e:
            # Update with error
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE task_queue
                SET status = 'failed', error = ?, completed_at = ?
                WHERE task_id = ?
            """, (str(e), time.time(), task.task_id))
            conn.commit()
            conn.close()

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get status of a task"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM task_queue WHERE task_id = ?
        """, (task_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))

    def wait_for_result(self, task_id: str, timeout: int = 300) -> Optional[Dict]:
        """Wait for task to complete and return result"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            status = self.get_task_status(task_id)

            if not status:
                return None

            if status["status"] in ["completed", "failed"]:
                return status

            time.sleep(0.5)

        return None  # Timeout

    def get_cluster_status(self) -> Dict[str, Any]:
        """Get status of all cluster nodes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Count tasks by node
        cursor.execute("""
            SELECT assigned_to, status, COUNT(*) as count
            FROM task_queue
            GROUP BY assigned_to, status
        """)

        node_stats = {}
        for row in cursor.fetchall():
            node_id, status, count = row
            if node_id not in node_stats:
                node_stats[node_id] = {"total": 0, "by_status": {}}
            node_stats[node_id]["total"] += count
            node_stats[node_id]["by_status"][status] = count

        conn.close()

        return {
            "local_node": self.local_node_id,
            "cluster_nodes": CLUSTER_NODES,
            "task_distribution": node_stats
        }


def main():
    """CLI interface for task router"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: distributed_task_router.py <command>")
        print("\nCommands:")
        print("  submit <command>    - Submit a command for execution")
        print("  status <task_id>    - Get task status")
        print("  cluster-status      - Show cluster status")
        sys.exit(1)

    router = DistributedTaskRouter()
    command = sys.argv[1]

    if command == "submit":
        if len(sys.argv) < 3:
            print("Usage: distributed_task_router.py submit <command>")
            sys.exit(1)

        task_cmd = " ".join(sys.argv[2:])
        task_id = router.submit_task({"type": "shell", "command": task_cmd})
        print(f"Task submitted: {task_id}")
        print("Waiting for result...")

        result = router.wait_for_result(task_id)
        if result:
            print(f"\nStatus: {result['status']}")
            print(f"Executed on: {result['assigned_to']}")
            if result['result']:
                print(f"Output:\n{result['result']}")
            if result['error']:
                print(f"Error:\n{result['error']}")
        else:
            print("Timeout waiting for result")

    elif command == "status":
        if len(sys.argv) < 3:
            print("Usage: distributed_task_router.py status <task_id>")
            sys.exit(1)

        task_id = sys.argv[2]
        status = router.get_task_status(task_id)
        if status:
            print(json.dumps(status, indent=2))
        else:
            print(f"Task not found: {task_id}")

    elif command == "cluster-status":
        status = router.get_cluster_status()
        print(json.dumps(status, indent=2))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
