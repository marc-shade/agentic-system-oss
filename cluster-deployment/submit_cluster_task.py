#!/usr/bin/env python3
"""
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


class ClusterTaskSubmitter:
    """Submit tasks to cluster nodes via GitHub"""

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
        """Execute git command"""
        cmd = ["git"] + list(args)
        result = subprocess.run(
            cmd,
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


if __name__ == "__main__":
    main()
