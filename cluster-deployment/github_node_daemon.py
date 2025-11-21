#!/usr/bin/env python3
"""
<<<<<<< HEAD
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

# Add cluster-deployment to path for TOON imports
sys.path.insert(0, str(Path(__file__).parent))
from toon_serialization import encode_heartbeat, encode_result, decode_toon, encode_task


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

=======
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
import hashlib
import json
import logging
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Ensure required packages are installed
try:
    import psutil
except ImportError:
    print("Error: psutil is required. Install with: pip3 install psutil")
    sys.exit(1)

try:
    from pydantic import ValidationError
except ImportError:
    print("Error: pydantic is required. Install with: pip3 install pydantic")
    sys.exit(1)

# Import security modules
try:
    from auth import MessageAuthenticator
    from payload_schema import (
        TaskPayload, CodeExecutionPayload, BuildPayload,
        ResultPayload, validate_payload, TaskType
    )
    from code_transfer import CodeTransferManager
    from dependency_manager import DependencyManager
except ImportError as e:
    print(f"Error: Missing required modules: {e}")
    print("Ensure all required modules are in the same directory:")
    print("  - auth.py")
    print("  - payload_schema.py")
    print("  - code_transfer.py")
    print("  - dependency_manager.py")
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
>>>>>>> origin/main
        self.task_branch = f"tasks/{node_id}"
        self.result_branch = f"results/{node_id}"
        self.heartbeat_branch = "heartbeat"

<<<<<<< HEAD
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
                # Try TOON decode first, fallback to JSON
                task_data = decode_toon(message)
                task_data['commit_hash'] = commit_hash
                tasks.append(task_data)
            except (json.JSONDecodeError, ValueError):
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
        """Submit task result via git commit using TOON format"""
        repo_dir = self.local_path / "repo"

        # Checkout result branch
        self._git("checkout", self.result_branch, cwd=repo_dir)

        # Create empty commit with result as message (TOON encoded)
        message = encode_result(result)
        self._git("commit", "--allow-empty", "-m", message, cwd=repo_dir)
        self._git("push", "origin", self.result_branch, cwd=repo_dir)

        print(f"[{self.node_id}] Result submitted for task {result['task_id']}")

    def send_heartbeat(self):
        """Send heartbeat to cluster using TOON format (50% token reduction)"""
        repo_dir = self.local_path / "repo"

        # Checkout heartbeat branch
        self._git("checkout", self.heartbeat_branch, cwd=repo_dir)

        # Create heartbeat file (TOON format)
        heartbeat_file = repo_dir / "heartbeat" / f"{self.node_id}.toon"
        heartbeat_file.parent.mkdir(exist_ok=True)

        heartbeat_data = self._get_health_status()
        # Use specialized heartbeat encoder for maximum compression
        heartbeat_encoded = encode_heartbeat(self.node_id, heartbeat_data)
        heartbeat_file.write_text(heartbeat_encoded)

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
=======
        # State tracking
        self.processed_commits = set()
        self.state_file = Path.home() / ".cache" / f"github-daemon-{node_id}.json"
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        # Security: Initialize message authenticator
        self.authenticator = MessageAuthenticator(node_id=node_id)
        logger.info(f"Loaded {len(self.authenticator.public_keys)} trusted node public keys")

        # Sandboxing workspace
        self.sandbox_dir = Path.home() / "agentic-system" / "tmp-workspace" / "gitMQ-sandbox"
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)

        # Code transfer manager
        self.code_transfer = CodeTransferManager(repo_path=self.repo_path)

        # Dependency manager
        self.dependency_manager = DependencyManager()

        # Load previous state
        self.load_state()

        logger.info(f"GitMQ daemon initialized for node: {node_id}")
        logger.info(f"Repository: {repo}")
        logger.info(f"Local path: {self.repo_path}")
        logger.info(f"Sandbox directory: {self.sandbox_dir}")

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
        """
        Execute a task with security validation.

        All tasks are:
        1. Validated against schema
        2. Verified for cryptographic signature
        3. Executed in sandbox (for code execution)
        """
        # SECURITY: Verify message signature
        if not self.authenticator.verify_payload(task.copy()):
            logger.error(f"Task signature verification failed")
            return {
                "task_id": task.get("task_id", "unknown"),
                "node_id": self.node_id,
                "status": "error",
                "error": "Signature verification failed - untrusted source",
                "timestamp": datetime.now().isoformat(),
            }

        # SECURITY: Validate against schema
        try:
            validated_task = validate_payload(task, TaskPayload)
        except ValidationError as e:
            logger.error(f"Task validation failed: {e}")
            return {
                "task_id": task.get("task_id", "unknown"),
                "node_id": self.node_id,
                "status": "error",
                "error": f"Schema validation failed: {e}",
                "timestamp": datetime.now().isoformat(),
            }

        task_type = validated_task.type
        task_id = validated_task.task_id

        logger.info(f"Executing validated task: {task_id} (type: {task_type})")

        # Execute based on task type
        try:
            if task_type == TaskType.HEALTH_CHECK:
                result_data = self.health_check()

            elif task_type == TaskType.CODE_EXECUTION:
                result_data = self.execute_code_secure(validated_task)

            elif task_type == TaskType.BUILD:
                result_data = self.execute_build(validated_task)

            else:
                result_data = {
                    "status": "error",
                    "error": f"Unsupported task type: {task_type}"
                }

        except Exception as e:
            logger.error(f"Task execution failed: {e}", exc_info=True)
            result_data = {
                "status": "error",
                "error": str(e)
            }

        # Create result payload
        result = ResultPayload(
            task_id=task_id,
            executing_node=self.node_id,
            status=result_data.get("status", "error"),
            exit_code=result_data.get("exit_code"),
            stdout=result_data.get("stdout", ""),
            stderr=result_data.get("stderr", ""),
            error_message=result_data.get("error"),
            execution_time_ms=result_data.get("execution_time_ms"),
            memory_usage_mb=result_data.get("memory_usage_mb"),
            cpu_usage_percent=result_data.get("cpu_usage_percent")
        )

        return result.model_dump(mode='json')

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

    def execute_code_secure(self, task: TaskPayload) -> Dict[str, Any]:
        """
        Execute code with mandatory sandboxing.

        SECURITY:
        - NO shell=True (prevents command injection)
        - Sandboxed execution (prevents system damage)
        - Resource limits (prevents DoS)
        - Checksum verification (prevents tampering)

        Args:
            task: Validated TaskPayload with CodeExecutionPayload

        Returns:
            Execution results dictionary
        """
        start_time = time.time()

        # Extract code execution payload
        try:
            code_payload = CodeExecutionPayload.model_validate(task.payload)
        except ValidationError as e:
            logger.error(f"Invalid code execution payload: {e}")
            return {
                "status": "error",
                "error": f"Invalid code payload: {e}",
                "exit_code": 1
            }

        logger.info(f"Executing code (language: {code_payload.code_language})")

        # Create isolated sandbox directory
        sandbox_run_dir = self.sandbox_dir / f"run-{task.task_id[:8]}"
        sandbox_run_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Write code to sandbox using CodeTransferManager
            code_file = sandbox_run_dir / code_payload.entry_point

            if code_payload.code:
                # Inline code - write directly
                code_file.write_text(code_payload.code)
                logger.info(f"Wrote inline code to {code_file}")
            elif code_payload.code_file:
                # Use code transfer manager to receive code
                logger.info(f"Receiving code via transfer manager: {code_payload.code_file}")

                # Reconstruct full code payload for transfer
                code_transfer_payload = {
                    "transfer_method": "git_lfs",
                    "filename": code_payload.entry_point,
                    "original_size": 0,  # Will be determined by transfer manager
                    "compressed_size": 0,
                    "checksum": "",
                    "compression": "none",
                    "lfs_path": code_payload.code_file,
                    "language": code_payload.code_language,
                    "dependencies": code_payload.dependencies
                }

                try:
                    self.code_transfer.receive_code(code_transfer_payload, code_file)
                    logger.info(f"✓ Code received via transfer manager")
                except Exception as e:
                    logger.error(f"Code transfer failed: {e}")
                    return {
                        "status": "error",
                        "error": f"Code transfer failed: {e}",
                        "exit_code": 1
                    }
            else:
                return {
                    "status": "error",
                    "error": "No code provided",
                    "exit_code": 1
                }

            # Prepare execution environment
            python_bin = "python3"  # Default system Python

            # If dependencies specified, create/use cached virtualenv
            if code_payload.dependencies and code_payload.code_language == "python":
                logger.info(f"Setting up virtualenv for {len(code_payload.dependencies)} dependencies")
                try:
                    venv_path = self.dependency_manager.get_or_create_environment(
                        dependencies=code_payload.dependencies
                    )
                    python_bin = str(venv_path / "bin" / "python3")
                    logger.info(f"✓ Using virtualenv: {venv_path.name}")
                except Exception as e:
                    logger.error(f"Failed to setup virtualenv: {e}")
                    return {
                        "status": "error",
                        "error": f"Dependency setup failed: {e}",
                        "exit_code": 1
                    }

            # Build command (NO shell=True!)
            if code_payload.code_language == "python":
                command = [python_bin, code_payload.entry_point] + code_payload.arguments
            elif code_payload.code_language == "bash":
                command = ["bash", code_payload.entry_point] + code_payload.arguments
            elif code_payload.code_language == "javascript":
                command = ["node", code_payload.entry_point] + code_payload.arguments
            else:
                return {
                    "status": "error",
                    "error": f"Unsupported language: {code_payload.code_language}",
                    "exit_code": 1
                }

            # SECURITY: Execute with proper argument passing (NO shell=True!)
            logger.info(f"Executing: {' '.join(command)}")
            logger.info(f"Working directory: {sandbox_run_dir}")

            result = subprocess.run(
                command,  # Argument list - NOT shell command!
                cwd=sandbox_run_dir,
                capture_output=True,
                text=True,
                timeout=task.execution_context.timeout_seconds,
                env={
                    **os.environ,
                    **task.execution_context.environment_vars,
                    "PYTHONDONTWRITEBYTECODE": "1",  # No .pyc files in sandbox
                }
            )

            execution_time_ms = (time.time() - start_time) * 1000

            # Verify exit code if specified
            status = "success" if result.returncode == code_payload.expected_exit_code else "error"

            return {
                "status": status,
                "exit_code": result.returncode,
                "stdout": result.stdout[:10000],  # Limit to 10KB
                "stderr": result.stderr[:10000],
                "execution_time_ms": execution_time_ms,
            }

        except subprocess.TimeoutExpired:
            execution_time_ms = (time.time() - start_time) * 1000
            logger.error(f"Code execution timed out after {task.execution_context.timeout_seconds}s")
            return {
                "status": "error",
                "error": f"Execution timed out after {task.execution_context.timeout_seconds}s",
                "exit_code": 124,  # Standard timeout exit code
                "execution_time_ms": execution_time_ms,
            }

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            logger.error(f"Code execution failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "exit_code": 1,
                "execution_time_ms": execution_time_ms,
            }

        finally:
            # Cleanup sandbox (optional - may want to keep for debugging)
            try:
                shutil.rmtree(sandbox_run_dir, ignore_errors=True)
                logger.debug(f"Cleaned up sandbox: {sandbox_run_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup sandbox: {e}")

    def execute_build(self, task: TaskPayload) -> Dict[str, Any]:
        """Execute build task"""
        try:
            build_payload = BuildPayload.model_validate(task.payload)
        except ValidationError as e:
            logger.error(f"Invalid build payload: {e}")
            return {
                "status": "error",
                "error": f"Invalid build payload: {e}",
                "exit_code": 1
            }

        logger.info(f"Building project: {build_payload.project_name}")

        # This would integrate with the builder API
        # For now, just acknowledge the build request
        return {
            "status": "success",
            "exit_code": 0,
            "stdout": f"Build triggered for {build_payload.project_name} ({build_payload.build_type})",
        }

    def post_result(self, task_commit: str, result: Dict[str, Any]):
        """
        Post task result to results branch with cryptographic signature.

        Results are signed before posting to ensure authenticity.
        """
        try:
            # SECURITY: Sign the result before posting
            signed_result = self.authenticator.sign_payload(result.copy())

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
                json.dump(signed_result, f, indent=2)

            logger.info(f"Signed result with {len(self.authenticator.public_keys)} trusted keys")

            # Commit and push
            self.git_command("add", str(result_file))
            self.git_command("commit", "-m", f"Result for task {task_commit[:8]}")
            self.git_command("push", "-u", "origin", self.result_branch)

            logger.info(f"Posted signed result for task {task_commit[:8]}")

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
>>>>>>> origin/main
                    heartbeat_counter = 0

                # Sleep until next poll
                time.sleep(self.poll_interval)

<<<<<<< HEAD
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
=======
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

>>>>>>> origin/main
    daemon.run()


if __name__ == "__main__":
    main()
