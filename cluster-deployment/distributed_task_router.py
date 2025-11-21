#!/usr/bin/env python3
"""
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
    "macpro51": {
        "ip": "192.168.1.183",
        "hostname": "macpro51.local",
        "os": "linux",
        "arch": "x86_64",
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

    def _detect_local_node(self) -> str:
        """Detect which node we're running on"""
        hostname = socket.gethostname().lower()

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
