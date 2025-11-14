#!/usr/bin/env python3
"""
Submit tasks to remote nodes via GitHub message queue

Usage:
    # Execute command on Scott's node
    python3 submit_cluster_task.py \
        --to scott-remote \
        --type code_execution \
        --command "python3 analyze_data.py" \
        --timeout 300

    # Clone node configuration to Scott's machine
    python3 submit_cluster_task.py \
        --to scott-remote \
        --type clone_node \
        --config-template standard

    # Health check
    python3 submit_cluster_task.py \
        --to scott-remote \
        --type health_check
"""

import os
import sys
import json
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
import uuid


class ClusterTaskSubmitter:
    """Submit tasks to cluster nodes via GitHub"""

    def __init__(
        self,
        repo: str = "marc-shade/agentic-cluster-comms",
        local_path: str = "/tmp/agentic-cluster-comms",
        from_node: str = "mac-studio"
    ):
        self.repo = repo
        self.local_path = Path(local_path)
        self.from_node = from_node
        self.github_token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")

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
            sys.exit(1)
        return result

    def setup(self):
        """Ensure repo is cloned and up to date"""
        repo_dir = self.local_path / "repo"

        if not repo_dir.exists():
            print("Cloning repository...")
            clone_url = f"https://{self.github_token}@github.com/{self.repo}.git"
            subprocess.run(
                ["git", "clone", clone_url, str(repo_dir)],
                check=True,
                capture_output=True
            )
        else:
            print("Pulling latest changes...")
            self._git("pull", cwd=repo_dir)

    def submit_task(
        self,
        to_node: str,
        task_type: str,
        payload: Dict,
        priority: int = 5
    ) -> str:
        """Submit a task to a remote node"""

        task_id = f"task_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        task = {
            "task_id": task_id,
            "from_node": self.from_node,
            "to_node": to_node,
            "task_type": task_type,
            "priority": priority,
            "payload": payload,
            "created_at": datetime.utcnow().isoformat()
        }

        # Checkout task branch
        task_branch = f"tasks/{to_node}"
        repo_dir = self.local_path / "repo"

        self._git("fetch", "origin", cwd=repo_dir)

        # Try to checkout existing branch or create new one
        result = self._git("checkout", task_branch, cwd=repo_dir)
        if result.returncode != 0:
            self._git("checkout", "-b", task_branch, cwd=repo_dir)

        # Create empty commit with task as message
        message = json.dumps(task, indent=2)
        self._git("commit", "--allow-empty", "-m", message, cwd=repo_dir)
        self._git("push", "-u", "origin", task_branch, cwd=repo_dir)

        print(f"✓ Task {task_id} submitted to {to_node}")
        print(f"  Type: {task_type}")
        print(f"  Branch: {task_branch}")

        return task_id

    def check_results(self, from_node: str, task_id: Optional[str] = None):
        """Check results from a node"""

        result_branch = f"results/{from_node}"
        repo_dir = self.local_path / "repo"

        # Checkout result branch
        self._git("checkout", result_branch, cwd=repo_dir)
        self._git("pull", "origin", result_branch, cwd=repo_dir)

        # Get recent commits
        if task_id:
            # Search for specific task
            result = self._git(
                "log",
                "--all",
                "--grep", task_id,
                "--pretty=format:%H|%s",
                cwd=repo_dir
            )
        else:
            # Get last 10 results
            result = self._git(
                "log",
                "-10",
                "--pretty=format:%H|%s",
                cwd=repo_dir
            )

        if not result.stdout.strip():
            print(f"No results found from {from_node}")
            return []

        # Parse results
        results = []
        for line in result.stdout.strip().split('\n'):
            if '|' not in line:
                continue
            commit_hash, message = line.split('|', 1)

            try:
                result_data = json.loads(message)
                result_data['commit_hash'] = commit_hash
                results.append(result_data)
            except json.JSONDecodeError:
                continue

        return results


def main():
    parser = argparse.ArgumentParser(description="Submit cluster task via GitHub")
    parser.add_argument("--to", required=True, help="Target node ID")
    parser.add_argument("--from-node", default="mac-studio", help="Source node ID")
    parser.add_argument("--type", required=True,
                       choices=["code_execution", "clone_node", "health_check", "custom"],
                       help="Task type")
    parser.add_argument("--command", help="Command to execute (for code_execution)")
    parser.add_argument("--timeout", type=int, default=300, help="Timeout in seconds")
    parser.add_argument("--config-template", help="Config template name (for clone_node)")
    parser.add_argument("--payload", help="Custom JSON payload")
    parser.add_argument("--priority", type=int, default=5, help="Task priority (1-10)")
    parser.add_argument("--check-results", action="store_true", help="Check results instead of submitting")
    parser.add_argument("--task-id", help="Specific task ID to check")

    args = parser.parse_args()

    submitter = ClusterTaskSubmitter(from_node=args.from_node)
    submitter.setup()

    if args.check_results:
        # Check results
        results = submitter.check_results(args.to, args.task_id)

        if not results:
            print("No results found")
            return

        print(f"\n=== Results from {args.to} ===\n")
        for result in results:
            print(f"Task ID: {result.get('task_id')}")
            print(f"Status: {result.get('status')}")
            print(f"Completed: {result.get('completed_at')}")
            if result.get('output'):
                print(f"Output: {json.dumps(result['output'], indent=2)}")
            if result.get('error'):
                print(f"Error: {result['error']}")
            print("-" * 60)
    else:
        # Submit task
        if args.type == "code_execution":
            if not args.command:
                print("Error: --command required for code_execution")
                sys.exit(1)
            payload = {
                "command": args.command,
                "timeout": args.timeout
            }
        elif args.type == "clone_node":
            payload = {
                "template": args.config_template or "standard"
            }
        elif args.type == "health_check":
            payload = {}
        elif args.type == "custom":
            if not args.payload:
                print("Error: --payload required for custom task")
                sys.exit(1)
            payload = json.loads(args.payload)
        else:
            payload = {}

        task_id = submitter.submit_task(
            to_node=args.to,
            task_type=args.type,
            payload=payload,
            priority=args.priority
        )

        print(f"\nTo check results, run:")
        print(f"  python3 submit_cluster_task.py --to {args.to} --check-results --task-id {task_id}")


if __name__ == "__main__":
    main()
