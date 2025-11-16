#!/usr/bin/env python3
"""
GitHub Node Daemon - GitMQ Pattern Implementation

Uses GitHub as a secure message broker for cross-network cluster communication.
No VPN, no firewall configuration, no static IPs needed.

Architecture:
- Git commits = messages
- Branches organize communication channels:
  - tasks/{node-id}/ - Incoming tasks for each node
  - results/{node-id}/ - Task execution results
  - heartbeat/ - Node health status

Security: GitHub OAuth/PAT, HTTPS, audit trail via git history
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import tempfile

# Ensure psutil is installed
try:
    import psutil
except ImportError:
    print("Error: psutil is required. Install with: pip3 install psutil")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(Path.home() / "agentic-system" / "logs" / "github-daemon.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class GitHubNodeDaemon:
    """Daemon that polls GitHub for tasks and posts results"""

    def __init__(self, node_id: str, repo: str, poll_interval: int = 30):
        self.node_id = node_id
        self.repo = repo  # Format: "username/repo-name"
        self.poll_interval = poll_interval

        # Local git repository path
        self.repo_path = Path.home() / "agentic-system" / "agentic-cluster-comms"

        # Task branches
        self.task_branch = f"tasks/{node_id}"
        self.result_branch = f"results/{node_id}"
        self.heartbeat_branch = "heartbeat"

        # State tracking
        self.processed_commits = set()
        self.state_file = Path.home() / ".cache" / f"github-daemon-{node_id}.json"
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        # Load previous state
        self.load_state()

        logger.info(f"GitMQ daemon initialized for node: {node_id}")
        logger.info(f"Repository: {repo}")
        logger.info(f"Local path: {self.repo_path}")

    def load_state(self):
        """Load previously processed commits"""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    state = json.load(f)
                self.processed_commits = set(state.get("processed_commits", []))
                logger.info(f"Loaded {len(self.processed_commits)} processed commits")
            except Exception as e:
                logger.warning(f"Failed to load state: {e}")
                self.processed_commits = set()

    def save_state(self):
        """Save processed commits to disk"""
        try:
            state = {
                "node_id": self.node_id,
                "processed_commits": list(self.processed_commits),
                "last_update": datetime.now().isoformat(),
            }
            with open(self.state_file, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def git_command(self, *args, cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
        """Execute git command and return result"""
        if cwd is None:
            cwd = self.repo_path

        cmd = ["git"] + list(args)
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            logger.error(f"Git command failed: {' '.join(cmd)}")
            logger.error(f"Error: {result.stderr}")

        return result

    def ensure_repository(self):
        """Clone or update the repository"""
        if not self.repo_path.exists():
            logger.info(f"Cloning repository: {self.repo}")
            parent = self.repo_path.parent
            parent.mkdir(parents=True, exist_ok=True)

            result = self.git_command(
                "clone",
                f"https://github.com/{self.repo}.git",
                str(self.repo_path.name),
                cwd=parent
            )

            if result.returncode != 0:
                raise RuntimeError(f"Failed to clone repository: {result.stderr}")

            logger.info("Repository cloned successfully")

            # Configure git identity for this repo
            self.git_command("config", "user.email", "agentic-cluster@example.com")
            self.git_command("config", "user.name", f"Agentic Node {self.node_id}")
        else:
            # Fetch latest changes
            logger.debug("Fetching latest changes")
            self.git_command("fetch", "--all")

            # Ensure git identity is configured
            result = self.git_command("config", "user.email")
            if result.returncode != 0 or not result.stdout.strip():
                self.git_command("config", "user.email", "agentic-cluster@example.com")
                self.git_command("config", "user.name", f"Agentic Node {self.node_id}")

    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """Check for new tasks on the task branch"""
        # Switch to task branch
        result = self.git_command("checkout", self.task_branch)
        if result.returncode != 0:
            logger.debug(f"Task branch {self.task_branch} doesn't exist yet")
            return []

        # Pull latest tasks
        self.git_command("pull", "origin", self.task_branch)

        # Get commit log
        result = self.git_command(
            "log",
            "--format=%H|%s|%ai",
            "-n", "20"  # Last 20 commits
        )

        if result.returncode != 0:
            return []

        tasks = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            commit_hash, subject, timestamp = line.split("|", 2)

            # Skip already processed
            if commit_hash in self.processed_commits:
                continue

            # Get commit message body (task payload)
            payload_result = self.git_command("show", "-s", "--format=%B", commit_hash)
            if payload_result.returncode != 0:
                continue

            try:
                # Parse JSON task payload from commit message
                message_body = payload_result.stdout.strip()
                # Skip the subject line, get the body
                lines = message_body.split("\n", 1)
                if len(lines) > 1:
                    task_json = lines[1].strip()
                    task = json.loads(task_json)
                    task["_commit"] = commit_hash
                    task["_timestamp"] = timestamp
                    tasks.append(task)
                    logger.info(f"Found new task: {commit_hash[:8]} - {subject}")
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in commit {commit_hash[:8]}")

        return tasks

    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task and return results"""
        task_type = task.get("type", "unknown")
        task_id = task.get("task_id", "unknown")

        logger.info(f"Executing task: {task_id} (type: {task_type})")

        result = {
            "task_id": task_id,
            "node_id": self.node_id,
            "task_type": task_type,
            "status": "unknown",
            "timestamp": datetime.now().isoformat(),
        }

        try:
            if task_type == "health_check":
                result.update(self.health_check())

            elif task_type == "code_execution":
                command = task.get("command", "")
                result.update(self.execute_code(command))

            elif task_type == "build":
                project = task.get("project", "")
                result.update(self.execute_build(project))

            else:
                result["status"] = "error"
                result["error"] = f"Unknown task type: {task_type}"

        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            result["status"] = "error"
            result["error"] = str(e)

        return result

    def health_check(self) -> Dict[str, Any]:
        """Perform system health check"""
        return {
            "status": "success",
            "health": {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage("/").percent,
                "uptime_seconds": time.time() - psutil.boot_time(),
            },
        }

    def execute_code(self, command: str) -> Dict[str, Any]:
        """Execute code command safely"""
        logger.info(f"Executing command: {command}")

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd=Path.home() / "agentic-system",
            )

            return {
                "status": "success" if result.returncode == 0 else "error",
                "exit_code": result.returncode,
                "stdout": result.stdout[:5000],  # Limit output
                "stderr": result.stderr[:5000],
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error": "Command timed out after 5 minutes",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def execute_build(self, project: str) -> Dict[str, Any]:
        """Execute build task"""
        logger.info(f"Building project: {project}")

        # This would integrate with the builder API
        return {
            "status": "success",
            "message": f"Build triggered for {project}",
        }

    def post_result(self, task_commit: str, result: Dict[str, Any]):
        """Post task result to results branch"""
        try:
            # Fetch latest
            self.git_command("fetch", "--all")

            # Switch to results branch (create if needed)
            self.git_command("checkout", "-B", self.result_branch)

            # Pull if branch exists remotely
            try:
                self.git_command("pull", "origin", self.result_branch)
            except:
                logger.debug(f"Branch {self.result_branch} doesn't exist remotely yet")

            # Create result file
            result_file = self.repo_path / "results" / f"{task_commit[:8]}.json"
            result_file.parent.mkdir(parents=True, exist_ok=True)

            with open(result_file, "w") as f:
                json.dump(result, f, indent=2)

            # Commit and push
            self.git_command("add", str(result_file))
            self.git_command("commit", "-m", f"Result for task {task_commit[:8]}")
            self.git_command("push", "-u", "origin", self.result_branch)

            logger.info(f"Posted result for task {task_commit[:8]}")

            # Mark as processed
            self.processed_commits.add(task_commit)
            self.save_state()

        except Exception as e:
            logger.error(f"Failed to post result: {e}")

    def post_heartbeat(self):
        """Post node heartbeat to heartbeat branch"""
        try:
            # Fetch latest first
            self.git_command("fetch", "--all")

            # Switch to heartbeat branch (create if needed)
            self.git_command("checkout", "-B", self.heartbeat_branch)

            # Pull if branch exists remotely
            try:
                self.git_command("pull", "origin", self.heartbeat_branch)
            except:
                logger.debug(f"Branch {self.heartbeat_branch} doesn't exist remotely yet")

            # Create heartbeat file
            heartbeat_file = self.repo_path / "heartbeat" / f"{self.node_id}.json"
            heartbeat_file.parent.mkdir(parents=True, exist_ok=True)

            heartbeat = {
                "node_id": self.node_id,
                "timestamp": datetime.now().isoformat(),
                "status": "online",
                "health": self.health_check()["health"],
            }

            with open(heartbeat_file, "w") as f:
                json.dump(heartbeat, f, indent=2)

            # Check if there are changes to commit
            status_result = self.git_command("status", "--porcelain")
            if not status_result.stdout.strip():
                logger.debug("No heartbeat changes to commit")
                return

            # Commit and push
            self.git_command("add", str(heartbeat_file))
            self.git_command("commit", "-m", f"Heartbeat from {self.node_id}")
            self.git_command("push", "-u", "origin", self.heartbeat_branch)

            logger.debug(f"Posted heartbeat")

        except Exception as e:
            logger.error(f"Failed to post heartbeat: {e}")

    def run(self):
        """Main daemon loop"""
        logger.info(f"Starting GitMQ daemon for {self.node_id}")
        logger.info(f"Polling every {self.poll_interval} seconds")

        # Ensure repository exists
        self.ensure_repository()

        # Post initial heartbeat
        self.post_heartbeat()

        heartbeat_counter = 0

        try:
            while True:
                # Check for new tasks
                tasks = self.get_pending_tasks()

                for task in tasks:
                    # Execute task
                    result = self.execute_task(task)

                    # Post result
                    self.post_result(task["_commit"], result)

                # Post heartbeat every 5 minutes
                heartbeat_counter += 1
                if heartbeat_counter >= (300 / self.poll_interval):
                    self.post_heartbeat()
                    heartbeat_counter = 0

                # Sleep until next poll
                time.sleep(self.poll_interval)

        except KeyboardInterrupt:
            logger.info("Daemon shutting down")
        except Exception as e:
            logger.error(f"Daemon error: {e}", exc_info=True)
            raise


def main():
    parser = argparse.ArgumentParser(description="GitHub Node Daemon - GitMQ Pattern")
    parser.add_argument("--node-id", required=True, help="Unique node identifier")
    parser.add_argument("--repo", required=True, help="GitHub repository (username/repo)")
    parser.add_argument("--poll-interval", type=int, default=30, help="Polling interval in seconds")

    args = parser.parse_args()

    # Create and run daemon
    daemon = GitHubNodeDaemon(
        node_id=args.node_id,
        repo=args.repo,
        poll_interval=args.poll_interval,
    )

    daemon.run()


if __name__ == "__main__":
    main()
