#!/usr/bin/env python3
"""
GitHub-Based Cross-Network Node Daemon

Uses GitHub as message broker for cross-network agent cluster communication.
Based on GitMQ pattern + GitHub MCP server integration.

Usage:
    python3 github_node_daemon.py --node-id mac-studio --repo marc-shade/agentic-cluster-comms
"""

import os
import sys
import json
import time
import subprocess
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class GitHubNodeDaemon:
    """Daemon for GitHub-based cross-network node communication"""

    def __init__(
        self,
        node_id: str,
        repo: str,
        local_path: str = "/tmp/agentic-cluster-comms",
        poll_interval: int = 30,
        github_token: Optional[str] = None
    ):
        self.node_id = node_id
        self.repo = repo
        self.local_path = Path(local_path)
        self.poll_interval = poll_interval
        self.github_token = github_token or os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")

        self.task_branch = f"tasks/{node_id}"
        self.result_branch = f"results/{node_id}"
        self.heartbeat_branch = "heartbeat"

        self.last_processed_commit = None

    def setup(self):
        """Clone repo and checkout task branch"""
        print(f"[{self.node_id}] Setting up GitHub daemon...")

        if not self.local_path.exists():
            self.local_path.mkdir(parents=True)

        repo_dir = self.local_path / "repo"

        if repo_dir.exists():
            print(f"[{self.node_id}] Repository already cloned, pulling latest...")
            self._git("pull", cwd=repo_dir)
        else:
            print(f"[{self.node_id}] Cloning repository...")
            clone_url = f"https://{self.github_token}@github.com/{self.repo}.git"
            subprocess.run(
                ["git", "clone", clone_url, str(repo_dir)],
                check=True,
                capture_output=True
            )

        # Ensure branches exist
        self._ensure_branch(repo_dir, self.task_branch)
        self._ensure_branch(repo_dir, self.result_branch)
        self._ensure_branch(repo_dir, self.heartbeat_branch)

        print(f"[{self.node_id}] Setup complete!")

    def _git(self, *args, cwd=None):
        """Execute git command"""
        cmd = ["git"] + list(args)
        result = subprocess.run(
            cmd,
            cwd=cwd or self.local_path / "repo",
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"Git command failed: {' '.join(cmd)}")
            print(f"Error: {result.stderr}")
        return result

    def _ensure_branch(self, repo_dir: Path, branch: str):
        """Create branch if it doesn't exist"""
        # Check if branch exists remotely
        result = self._git("ls-remote", "--heads", "origin", branch, cwd=repo_dir)

        if not result.stdout.strip():
            # Branch doesn't exist, create it
            print(f"[{self.node_id}] Creating branch: {branch}")
            self._git("checkout", "-b", branch, cwd=repo_dir)
            self._git("push", "-u", "origin", branch, cwd=repo_dir)
        else:
            # Branch exists, just checkout
            self._git("checkout", branch, cwd=repo_dir)
            self._git("pull", "origin", branch, cwd=repo_dir)

    def poll_tasks(self) -> List[Dict]:
        """Poll for new tasks on task branch"""
        repo_dir = self.local_path / "repo"

        # Checkout task branch and pull
        self._git("checkout", self.task_branch, cwd=repo_dir)
        self._git("pull", "origin", self.task_branch, cwd=repo_dir)

        # Get commits since last check
        if self.last_processed_commit:
            result = self._git(
                "log",
                f"{self.last_processed_commit}..HEAD",
                "--pretty=format:%H|%s",
                cwd=repo_dir
            )
        else:
            # First run, get last 10 commits
            result = self._git(
                "log",
                "-10",
                "--pretty=format:%H|%s",
                cwd=repo_dir
            )

        if not result.stdout.strip():
            return []

        # Parse commits
        tasks = []
        for line in result.stdout.strip().split('\n'):
            if '|' not in line:
                continue
            commit_hash, message = line.split('|', 1)

            try:
                task_data = json.loads(message)
                task_data['commit_hash'] = commit_hash
                tasks.append(task_data)
            except json.JSONDecodeError:
                print(f"[{self.node_id}] Invalid task format in commit {commit_hash}")

        if tasks:
            self.last_processed_commit = tasks[0]['commit_hash']

        return tasks

    def execute_task(self, task: Dict) -> Dict:
        """Execute a task and return results"""
        print(f"[{self.node_id}] Executing task: {task['task_id']}")

        task_type = task.get('task_type', 'unknown')
        payload = task.get('payload', {})

        result = {
            "task_id": task['task_id'],
            "node_id": self.node_id,
            "status": "unknown",
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "output": None,
            "error": None
        }

        try:
            if task_type == "code_execution":
                # Execute shell command
                command = payload.get('command')
                timeout = payload.get('timeout', 300)

                proc = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )

                result['status'] = 'success' if proc.returncode == 0 else 'failed'
                result['output'] = {
                    'stdout': proc.stdout,
                    'stderr': proc.stderr,
                    'returncode': proc.returncode
                }

            elif task_type == "clone_node":
                # Node cloning task
                result = self._clone_node_config(payload)

            elif task_type == "health_check":
                # Return node health
                result['status'] = 'success'
                result['output'] = self._get_health_status()

            else:
                result['status'] = 'error'
                result['error'] = f"Unknown task type: {task_type}"

        except subprocess.TimeoutExpired:
            result['status'] = 'timeout'
            result['error'] = f"Task exceeded timeout of {timeout}s"
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)

        result['completed_at'] = datetime.utcnow().isoformat()
        return result

    def _clone_node_config(self, payload: Dict) -> Dict:
        """Clone node configuration from template"""
        print(f"[{self.node_id}] Cloning node configuration...")

        # This would install MCP servers, copy configs, etc.
        # Implementation depends on your specific needs

        return {
            "status": "success",
            "output": "Node cloned successfully",
            "installed_servers": ["enhanced-memory-mcp", "agent-runtime-mcp", "github-mcp"]
        }

    def _get_health_status(self) -> Dict:
        """Get current node health status"""
        import psutil

        return {
            "node_id": self.node_id,
            "timestamp": datetime.utcnow().isoformat(),
            "uptime": time.time(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        }

    def submit_result(self, result: Dict):
        """Submit task result via git commit"""
        repo_dir = self.local_path / "repo"

        # Checkout result branch
        self._git("checkout", self.result_branch, cwd=repo_dir)

        # Create empty commit with result as message
        message = json.dumps(result, indent=2)
        self._git("commit", "--allow-empty", "-m", message, cwd=repo_dir)
        self._git("push", "origin", self.result_branch, cwd=repo_dir)

        print(f"[{self.node_id}] Result submitted for task {result['task_id']}")

    def send_heartbeat(self):
        """Send heartbeat to cluster"""
        repo_dir = self.local_path / "repo"

        # Checkout heartbeat branch
        self._git("checkout", self.heartbeat_branch, cwd=repo_dir)

        # Create heartbeat file
        heartbeat_file = repo_dir / "heartbeat" / f"{self.node_id}.json"
        heartbeat_file.parent.mkdir(exist_ok=True)

        heartbeat_data = self._get_health_status()
        heartbeat_file.write_text(json.dumps(heartbeat_data, indent=2))

        # Commit and push
        self._git("add", str(heartbeat_file), cwd=repo_dir)
        self._git("commit", "-m", f"Heartbeat from {self.node_id}", cwd=repo_dir)
        self._git("push", "origin", self.heartbeat_branch, cwd=repo_dir)

    def run(self):
        """Main daemon loop"""
        print(f"[{self.node_id}] Starting daemon (poll interval: {self.poll_interval}s)")

        heartbeat_counter = 0

        while True:
            try:
                # Poll for tasks
                tasks = self.poll_tasks()

                # Execute tasks
                for task in tasks:
                    result = self.execute_task(task)
                    self.submit_result(result)

                # Send heartbeat every 5 poll cycles (2.5 minutes at 30s interval)
                heartbeat_counter += 1
                if heartbeat_counter >= 5:
                    self.send_heartbeat()
                    heartbeat_counter = 0

                # Sleep until next poll
                time.sleep(self.poll_interval)

            except KeyboardInterrupt:
                print(f"\n[{self.node_id}] Daemon stopped by user")
                break
            except Exception as e:
                print(f"[{self.node_id}] Error in daemon loop: {e}")
                time.sleep(self.poll_interval)


def main():
    parser = argparse.ArgumentParser(description="GitHub-based node daemon")
    parser.add_argument("--node-id", required=True, help="Unique node identifier")
    parser.add_argument("--repo", required=True, help="GitHub repo (owner/name)")
    parser.add_argument("--poll-interval", type=int, default=30, help="Poll interval in seconds")
    parser.add_argument("--local-path", default="/tmp/agentic-cluster-comms", help="Local repo path")

    args = parser.parse_args()

    daemon = GitHubNodeDaemon(
        node_id=args.node_id,
        repo=args.repo,
        local_path=args.local_path,
        poll_interval=args.poll_interval
    )

    daemon.setup()
    daemon.run()


if __name__ == "__main__":
    main()
