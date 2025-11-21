#!/usr/bin/env python3
"""
<<<<<<< HEAD
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

# Add cluster-deployment to path for TOON imports
sys.path.insert(0, str(Path(__file__).parent))
from toon_serialization import encode_task, decode_toon
=======
Submit Cluster Task - GitMQ Pattern

Submit tasks to remote cluster nodes via GitHub message broker.
Tasks are submitted as git commits on task branches.
"""

import argparse
import json
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

import logging

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
>>>>>>> origin/main


class ClusterTaskSubmitter:
    """Submit tasks to cluster nodes via GitHub"""

<<<<<<< HEAD
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
=======
    def __init__(self, repo: str):
        self.repo = repo  # Format: "username/repo-name"
        self.repo_path = Path.home() / "agentic-system" / "agentic-cluster-comms"

        # Ensure repository exists
        if not self.repo_path.exists():
            raise RuntimeError(
                f"Repository not found at {self.repo_path}. "
                "Run github_node_daemon.py first to clone it."
            )

        logger.info(f"Using repository: {self.repo}")

    def git_command(self, *args) -> subprocess.CompletedProcess:
>>>>>>> origin/main
        """Execute git command"""
        cmd = ["git"] + list(args)
        result = subprocess.run(
            cmd,
<<<<<<< HEAD
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

        # Create empty commit with task as message (TOON encoded)
        message = encode_task(task)
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
                # Try TOON decode first, fallback to JSON
                result_data = decode_toon(message)
                result_data['commit_hash'] = commit_hash
                results.append(result_data)
            except (json.JSONDecodeError, ValueError):
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
=======
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            logger.error(f"Git command failed: {' '.join(cmd)}")
            logger.error(f"Error: {result.stderr}")
            raise RuntimeError(f"Git command failed: {result.stderr}")

        return result

    def submit_task(
        self,
        target_node: str,
        task_type: str,
        task_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Submit a task to a target node

        Args:
            target_node: Node ID to send task to (e.g., "scott-remote", "macpro51")
            task_type: Type of task ("health_check", "code_execution", "build")
            task_data: Additional task parameters

        Returns:
            Task ID
        """
        # Generate task ID
        task_id = str(uuid.uuid4())

        # Create task payload
        task = {
            "task_id": task_id,
            "type": task_type,
            "timestamp": datetime.now().isoformat(),
            **(task_data or {}),
        }

        # Task branch for target node
        task_branch = f"tasks/{target_node}"

        logger.info(f"Submitting {task_type} task to {target_node}")
        logger.info(f"Task ID: {task_id}")

        try:
            # Fetch latest changes
            self.git_command("fetch", "--all")

            # Create/checkout task branch
            self.git_command("checkout", "-B", task_branch)

            # Try to pull if branch exists remotely
            try:
                self.git_command("pull", "origin", task_branch)
            except:
                logger.debug(f"Branch {task_branch} doesn't exist remotely yet")

            # Create task file
            task_dir = self.repo_path / "tasks" / target_node
            task_dir.mkdir(parents=True, exist_ok=True)

            task_file = task_dir / f"{task_id}.json"
            with open(task_file, "w") as f:
                json.dump(task, f, indent=2)

            # Commit task as a message
            # Subject line + JSON body
            commit_message = f"{task_type} task for {target_node}\n\n{json.dumps(task, indent=2)}"

            self.git_command("add", str(task_file))
            self.git_command("commit", "-m", commit_message)

            # Push to GitHub
            self.git_command("push", "-u", "origin", task_branch)

            logger.info(f"✅ Task submitted successfully!")
            logger.info(f"   Task ID: {task_id}")
            logger.info(f"   Target: {target_node}")
            logger.info(f"   Type: {task_type}")

            return task_id

        except Exception as e:
            logger.error(f"Failed to submit task: {e}")
            raise

    def check_results(self, target_node: str) -> list:
        """Check results from a target node"""
        results_branch = f"results/{target_node}"

        logger.info(f"Checking results from {target_node}")

        try:
            # Fetch latest
            self.git_command("fetch", "--all")

            # Checkout results branch
            try:
                self.git_command("checkout", results_branch)
                self.git_command("pull", "origin", results_branch)
            except:
                logger.info(f"No results branch found for {target_node}")
                return []

            # List result files
            results_dir = self.repo_path / "results"
            if not results_dir.exists():
                return []

            results = []
            for result_file in results_dir.glob("*.json"):
                try:
                    with open(result_file) as f:
                        result = json.load(f)
                    results.append(result)
                except Exception as e:
                    logger.warning(f"Failed to read {result_file}: {e}")

            logger.info(f"Found {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Failed to check results: {e}")
            return []

    def check_heartbeat(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Check heartbeat status of a node"""
        logger.info(f"Checking heartbeat for {node_id}")

        try:
            # Fetch latest
            self.git_command("fetch", "--all")

            # Checkout heartbeat branch
            try:
                self.git_command("checkout", "heartbeat")
                self.git_command("pull", "origin", "heartbeat")
            except:
                logger.info("No heartbeat branch found")
                return None

            # Read heartbeat file
            heartbeat_file = self.repo_path / "heartbeat" / f"{node_id}.json"
            if not heartbeat_file.exists():
                logger.info(f"No heartbeat found for {node_id}")
                return None

            with open(heartbeat_file) as f:
                heartbeat = json.load(f)

            logger.info(f"✅ Heartbeat found for {node_id}")
            logger.info(f"   Status: {heartbeat.get('status')}")
            logger.info(f"   Last update: {heartbeat.get('timestamp')}")

            return heartbeat

        except Exception as e:
            logger.error(f"Failed to check heartbeat: {e}")
            return None


def main():
    parser = argparse.ArgumentParser(description="Submit tasks to cluster nodes via GitHub")
    parser.add_argument("--repo", default="marc-shade/agentic-cluster-comms",
                        help="GitHub repository (username/repo)")
    parser.add_argument("--to", dest="target_node", help="Target node ID")
    parser.add_argument("--type", dest="task_type",
                        choices=["health_check", "code_execution", "build"],
                        help="Task type")
    parser.add_argument("--command", help="Command to execute (for code_execution)")
    parser.add_argument("--project", help="Project to build (for build)")
    parser.add_argument("--check-results", action="store_true",
                        help="Check results from target node")
    parser.add_argument("--check-heartbeat", action="store_true",
                        help="Check heartbeat from target node")

    args = parser.parse_args()

    # Create submitter
    try:
        submitter = ClusterTaskSubmitter(repo=args.repo)
    except RuntimeError as e:
        logger.error(str(e))
        logger.info("Tip: Run github_node_daemon.py first to clone the repository")
        sys.exit(1)

    # Check results
    if args.check_results:
        if not args.target_node:
            logger.error("--to <node-id> required when checking results")
            sys.exit(1)

        results = submitter.check_results(args.target_node)
        if results:
            print("\n" + "=" * 80)
            print(f"RESULTS FROM {args.target_node}")
            print("=" * 80)
            for result in results:
                print(json.dumps(result, indent=2))
                print("-" * 80)
        else:
            print(f"No results found for {args.target_node}")

        return

    # Check heartbeat
    if args.check_heartbeat:
        if not args.target_node:
            logger.error("--to <node-id> required when checking heartbeat")
            sys.exit(1)

        heartbeat = submitter.check_heartbeat(args.target_node)
        if heartbeat:
            print("\n" + "=" * 80)
            print(f"HEARTBEAT FROM {args.target_node}")
            print("=" * 80)
            print(json.dumps(heartbeat, indent=2))
        else:
            print(f"No heartbeat found for {args.target_node}")

        return

    # Submit task
    if not args.target_node or not args.task_type:
        logger.error("--to <node-id> and --type <task-type> required to submit task")
        parser.print_help()
        sys.exit(1)

    # Build task data
    task_data = {}
    if args.task_type == "code_execution":
        if not args.command:
            logger.error("--command required for code_execution tasks")
            sys.exit(1)
        task_data["command"] = args.command

    elif args.task_type == "build":
        if not args.project:
            logger.error("--project required for build tasks")
            sys.exit(1)
        task_data["project"] = args.project

    # Submit task
    task_id = submitter.submit_task(
        target_node=args.target_node,
        task_type=args.task_type,
        task_data=task_data,
    )

    print("\n" + "=" * 80)
    print("TASK SUBMITTED")
    print("=" * 80)
    print(f"Task ID: {task_id}")
    print(f"Target: {args.target_node}")
    print(f"Type: {args.task_type}")
    print("\nCheck results with:")
    print(f"  python3 submit_cluster_task.py --to {args.target_node} --check-results")
>>>>>>> origin/main


if __name__ == "__main__":
    main()
