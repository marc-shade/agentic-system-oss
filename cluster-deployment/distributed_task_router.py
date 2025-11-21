#!/usr/bin/env python3
"""
<<<<<<< HEAD
Distributed Task Router for Cluster Execution

Routes tasks to optimal nodes in the cluster based on:
- Node capabilities (OS, architecture)
- Current load and availability
- Task requirements

Integrates with GitHub-based message queue for cross-network communication.
"""

import os
import json
import socket
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass
import subprocess
import time
import sys

# Add cluster-deployment to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from toon_serialization import encode_task, decode_toon, encode_result


# Cluster node definitions
CLUSTER_NODES = {
    "mac-studio": {
        "ip": "192.168.1.16",
        "hostname": "mac-studio.local",
        "os": "darwin",
        "arch": "arm64",
        "role": "orchestrator",
        "capabilities": ["python", "node", "docker"]
    },
=======
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
>>>>>>> origin/main
    "macpro51": {
        "ip": "192.168.1.183",
        "hostname": "macpro51.local",
        "os": "linux",
        "arch": "x86_64",
<<<<<<< HEAD
        "role": "builder",
        "capabilities": ["gcc", "g++", "clang", "python3.12", "docker", "podman"]
    },
    "macbook-air": {
        "ip": "192.168.1.76",
        "hostname": "macbook-air.local",
        "os": "darwin",
        "arch": "arm64",
        "role": "researcher",
        "capabilities": ["python", "node", "research"]
    },
    "completeu-server": {
        "ip": "192.168.1.186",
        "hostname": "completeu-server",
        "os": "linux",
        "arch": "x86_64",
        "role": "production",
        "capabilities": ["python", "node", "docker", "production"]
    }
}


@dataclass
class TaskResult:
    """Result from task execution"""
    status: str  # pending, running, completed, failed
    assigned_to: Optional[str] = None
    result: Optional[Dict] = None
    error: Optional[str] = None


class DistributedTaskRouter:
    """Routes tasks across cluster nodes"""

    def __init__(self):
        self.local_node_id = self._detect_local_node()
        self.task_counter = 0
=======
        "capabilities": ["docker", "podman", "raid", "nvme", "compilation", "testing"],
        "specialties": ["compilation", "testing", "containerization", "benchmarking"],
        "max_tasks": 10,
        "priority": 3  # Lower = higher priority for offloading
    },
    "mac-studio": {
        "ip": "192.168.1.176",
        "hostname": "Marcs-Mac-Studio.local",
        "os": "macos",
        "arch": "arm64",
        "capabilities": ["orchestration", "coordination", "temporal"],
        "specialties": ["orchestration", "coordination", "monitoring"],
        "max_tasks": 5,
        "priority": 1  # Keep this free - orchestrator
    },
    "macbook-air": {
        "ip": "192.168.1.76",
        "hostname": "Mac.fios-router.home",
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
>>>>>>> origin/main

    def _detect_local_node(self) -> str:
        """Detect which node we're running on"""
        hostname = socket.gethostname().lower()

<<<<<<< HEAD
        # Check hostname patterns
        if "mac-studio" in hostname or hostname == "marc":
            return "mac-studio"
        elif "macpro" in hostname:
            return "macpro51"
        elif "macbook" in hostname or "air" in hostname:
            return "macbook-air"
        elif "completeu" in hostname:
            return "completeu-server"

        # Fallback to mac-studio
        return "mac-studio"

    def select_node(
        self,
        requires_os: Optional[str] = None,
        requires_arch: Optional[str] = None,
        force_node: Optional[str] = None
    ) -> str:
        """Select optimal node for task execution"""

        if force_node:
            if force_node in CLUSTER_NODES:
                return force_node
            else:
                raise ValueError(f"Unknown node: {force_node}")

        # Filter by requirements
        candidates = []
        for node_id, node_info in CLUSTER_NODES.items():
            if requires_os and node_info["os"] != requires_os:
                continue
            if requires_arch and node_info["arch"] != requires_arch:
                continue
            candidates.append(node_id)

        if not candidates:
            # Fallback to local node
            return self.local_node_id

        # For now, prefer macpro51 for Linux builds, otherwise use first candidate
        if requires_os == "linux" and "macpro51" in candidates:
            return "macpro51"

        return candidates[0]

    def submit_task(self, task_def: Dict) -> str:
        """Submit task for execution"""

        # Generate task ID
        self.task_counter += 1
        task_id = f"task_{int(time.time())}_{self.task_counter}"

        # Select target node
        target_node = self.select_node(
            requires_os=task_def.get("requires_os"),
            requires_arch=task_def.get("requires_arch"),
            force_node=task_def.get("force_node")
        )

        # If target is local, execute directly
        if target_node == self.local_node_id:
            return self._execute_local(task_id, task_def)

        # Execute on remote node via SSH
        return self._execute_remote(task_id, task_def, target_node)

    def _execute_local(self, task_id: str, task_def: Dict) -> str:
        """Execute task locally"""
        # Store task for later retrieval using TOON format
        task_file = Path(f"/tmp/cluster_task_{task_id}.toon")
        task_data = {
            "task_id": task_id,
            "task_def": task_def,
            "status": "pending",
            "assigned_to": self.local_node_id
        }
        task_file.write_text(encode_task(task_data))

        return task_id

    def _execute_remote(self, task_id: str, task_def: Dict, target_node: str) -> str:
        """Execute task on remote node via SSH"""
        node_info = CLUSTER_NODES[target_node]
        ip = node_info["ip"]

        # Store task with remote assignment
        task_file = Path(f"/tmp/cluster_task_{task_id}.toon")
        task_data = {
            "task_id": task_id,
            "task_def": task_def,
            "status": "pending",
            "assigned_to": target_node,
            "remote_ip": ip
        }
        task_file.write_text(encode_task(task_data))

        return task_id

    def _ssh_execute(self, ip: str, command: str, timeout: int = 300) -> Dict:
        """Execute command on remote node via SSH"""
        import shlex
        ssh_cmd = f"ssh -o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=no marc@{ip} {shlex.quote(command)}"
        try:
            result = subprocess.run(
                ssh_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"stdout": "", "stderr": "SSH timeout", "return_code": -1}
        except Exception as e:
            return {"stdout": "", "stderr": str(e), "return_code": -1}

    def wait_for_result(self, task_id: str, timeout: int = 300) -> Dict:
        """Wait for task to complete and return result"""

        # Try TOON format first, then JSON fallback
        task_file_toon = Path(f"/tmp/cluster_task_{task_id}.toon")
        task_file_json = Path(f"/tmp/cluster_task_{task_id}.json")

        if task_file_toon.exists():
            task_data = decode_toon(task_file_toon.read_text())
        elif task_file_json.exists():
            task_data = json.loads(task_file_json.read_text())
        else:
            return {
                "status": "failed",
                "error": f"Task {task_id} not found"
            }

        task_def = task_data["task_def"]
        assigned_to = task_data.get("assigned_to", self.local_node_id)
        remote_ip = task_data.get("remote_ip")

        # Execute the task now
        if task_def.get("type") == "shell":
            try:
                # Check if remote execution needed
                if remote_ip and assigned_to != self.local_node_id:
                    result = self._ssh_execute(remote_ip, task_def["command"], timeout)
                else:
                    proc = subprocess.run(
                        task_def["command"],
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=timeout
                    )
                    result = {
                        "stdout": proc.stdout,
                        "stderr": proc.stderr,
                        "return_code": proc.returncode
                    }

                return {
                    "status": "completed",
                    "assigned_to": assigned_to,
                    "result": result
                }
            except subprocess.TimeoutExpired:
                return {
                    "status": "failed",
                    "assigned_to": assigned_to,
                    "error": f"Task timed out after {timeout}s"
                }
            except Exception as e:
                return {
                    "status": "failed",
                    "assigned_to": assigned_to,
                    "error": str(e)
                }

        return {
            "status": "failed",
            "error": f"Unknown task type: {task_def.get('type')}"
        }
=======
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
            base = Path("/home/marc/agentic-system")
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
        node_info = CLUSTER_NODES[target_node]

        # Build remote execution command
        if task.command:
            remote_cmd = f"ssh -o ConnectTimeout=5 marc@{node_info['ip']} '{task.command}'"
        elif task.script:
            # Transfer script and execute
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
                f.write(task.script)
                local_script = f.name

            remote_script = f"/tmp/task_{task.task_id}.sh"

            # SCP script to remote node
            subprocess.run(
                f"scp -o ConnectTimeout=5 {local_script} marc@{node_info['ip']}:{remote_script}",
                shell=True,
                capture_output=True
            )

            remote_cmd = f"ssh -o ConnectTimeout=5 marc@{node_info['ip']} 'chmod +x {remote_script} && {remote_script} && rm {remote_script}'"
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
            # Execute remotely
            result = subprocess.run(
                remote_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300
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
>>>>>>> origin/main
