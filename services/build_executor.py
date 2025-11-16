#!/usr/bin/env python3
"""
Build Execution Engine for Builder Node
Orchestrates build jobs with Docker isolation, artifact management, and webhooks
"""

import json
import os
import shutil
import time
import threading
import signal
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List
import redis
import docker
from docker.errors import DockerException, NotFound, APIError
from artifact_manager import ArtifactManager
from webhook_delivery import WebhookDelivery

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/home/marc/agentic-system/logs/build_executor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BuildExecutor:
    """Executes build jobs in isolated Docker containers"""

    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 2,
        workspace_base: str = "/tmp/builds",
        max_concurrent_builds: int = 2,
    ):
        # Redis connection for job queue
        self.redis = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True
        )

        # Docker client
        try:
            self.docker = docker.from_env()
            logger.info("Docker connection established")
        except DockerException as e:
            logger.error(f"Failed to connect to Docker: {e}")
            raise

        # Artifact manager for storage
        self.artifact_manager = ArtifactManager()

        # Webhook delivery for notifications
        self.webhook_delivery = WebhookDelivery()

        # Workspace configuration
        self.workspace_base = Path(workspace_base)
        self.workspace_base.mkdir(parents=True, exist_ok=True)

        # Concurrency control
        self.max_concurrent_builds = max_concurrent_builds
        self.active_builds = {}  # build_id -> container
        self.active_builds_lock = threading.Lock()

        # Shutdown flag
        self.shutdown_flag = threading.Event()

        # Environment image mappings
        self.build_environments = {
            "node:20": "node:20-alpine",
            "node:18": "node:18-alpine",
            "node:16": "node:16-alpine",
            "python:3.12": "python:3.12-slim",
            "python:3.11": "python:3.11-slim",
            "python:3.10": "python:3.10-slim",
            "rust:latest": "rust:latest",
            "golang:1.21": "golang:1.21-alpine",
            "golang:1.20": "golang:1.20-alpine",
            "ubuntu:22.04": "ubuntu:22.04",
            "alpine:latest": "alpine:latest",
        }

    def start_worker(self):
        """Start the build worker daemon"""

        logger.info("=== Build Executor Started ===")
        logger.info(f"Max concurrent builds: {self.max_concurrent_builds}")
        logger.info(f"Workspace base: {self.workspace_base}")
        logger.info(f"Listening on Redis DB {self.redis.connection_pool.connection_kwargs['db']}")

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        # Main worker loop
        while not self.shutdown_flag.is_set():
            try:
                # Check if we can accept more builds
                with self.active_builds_lock:
                    active_count = len(self.active_builds)

                if active_count >= self.max_concurrent_builds:
                    logger.debug(
                        f"Max concurrent builds reached ({active_count}/{self.max_concurrent_builds}), "
                        "waiting..."
                    )
                    time.sleep(5)
                    continue

                # Try to fetch a build job (blocking with timeout)
                job_data = self.redis.brpop("build_queue", timeout=5)

                if job_data is None:
                    # No jobs available
                    continue

                _, job_json = job_data
                job = json.loads(job_json)

                logger.info(f"Fetched build job: {job['build_id']} for {job['project_id']}")

                # Start build in separate thread
                build_thread = threading.Thread(
                    target=self._execute_build_thread,
                    args=(job,),
                    daemon=True
                )
                build_thread.start()

            except Exception as e:
                logger.error(f"Error in worker loop: {e}", exc_info=True)
                time.sleep(5)

        logger.info("Build executor shutting down gracefully...")
        self._wait_for_active_builds()
        logger.info("Build executor stopped")

    def _execute_build_thread(self, job: Dict):
        """Execute a build job in a separate thread"""

        build_id = job['build_id']

        try:
            self._execute_build(job)
        except Exception as e:
            logger.error(f"Build {build_id} failed with exception: {e}", exc_info=True)
            self._handle_build_failure(job, str(e))
        finally:
            # Remove from active builds
            with self.active_builds_lock:
                self.active_builds.pop(build_id, None)

    def _execute_build(self, job: Dict):
        """Execute a build job with full orchestration"""

        build_id = job['build_id']
        project_id = job['project_id']

        logger.info(f"[{build_id}] Starting build execution")

        # Create build workspace
        workspace = self.workspace_base / build_id
        workspace.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        source_dir = workspace / "source"
        output_dir = workspace / "output"
        logs_dir = workspace / "logs"

        for directory in [source_dir, output_dir, logs_dir]:
            directory.mkdir(exist_ok=True)

        # Initialize artifact storage
        build_metadata = self.artifact_manager.create_build(
            project_id=project_id,
            git_commit=job.get('git_commit'),
            git_branch=job.get('git_branch'),
            build_type=job.get('build_type', 'release'),
            build_command=job.get('build_command'),
            webhook_url=job.get('webhook_url'),
            tags=job.get('tags', []),
        )

        # Update Redis with build status
        self._update_build_status(build_id, "running", build_metadata)

        # Send webhook notification (build started)
        if job.get('webhook_url'):
            self.webhook_delivery.send_build_started(
                webhook_url=job['webhook_url'],
                build_id=build_id,
                project_id=project_id,
                metadata={
                    'build_number': build_metadata['build_number'],
                    'git_commit': job.get('git_commit'),
                    'git_branch': job.get('git_branch'),
                }
            )

        try:
            # Clone repository if provided
            if job.get('git_repo'):
                logger.info(f"[{build_id}] Cloning repository: {job['git_repo']}")
                self._clone_repository(
                    repo_url=job['git_repo'],
                    branch=job.get('git_branch', 'main'),
                    commit=job.get('git_commit'),
                    target_dir=source_dir,
                )

            # Pull Docker image
            build_env = job.get('build_env', 'ubuntu:22.04')
            docker_image = self.build_environments.get(build_env, build_env)

            logger.info(f"[{build_id}] Pulling Docker image: {docker_image}")
            self._pull_docker_image(docker_image)

            # Execute build in Docker container
            logger.info(f"[{build_id}] Starting build container")
            exit_code, build_logs = self._run_build_container(
                build_id=build_id,
                image=docker_image,
                command=job['build_command'],
                workspace=workspace,
                source_dir=source_dir,
                output_dir=output_dir,
                timeout_seconds=job.get('timeout_seconds', 7200),
                environment=job.get('build_env_vars', {}),
            )

            # Save build logs
            log_file = logs_dir / "build.log"
            with open(log_file, 'w') as f:
                f.write(build_logs)

            logger.info(f"[{build_id}] Build completed with exit code {exit_code}")

            # Store build logs as artifact
            self.artifact_manager.add_artifact(
                build_id=build_id,
                source_path=str(log_file),
                artifact_type="documentation",
                name="build.log",
            )

            # Determine build status
            if exit_code == 0:
                status = "success"

                # Collect and store artifacts
                logger.info(f"[{build_id}] Collecting build artifacts")
                artifact_count = self._collect_artifacts(build_id, output_dir)

                logger.info(f"[{build_id}] Collected {artifact_count} artifacts")

            else:
                status = "failed"
                logger.warning(f"[{build_id}] Build failed with exit code {exit_code}")

            # Update build metadata
            updated_metadata = self.artifact_manager.update_build_status(
                build_id=build_id,
                status=status,
                exit_code=exit_code,
            )

            # Update Redis
            self._update_build_status(build_id, status, updated_metadata)

            # Update Prometheus metrics
            self._update_metrics(status, updated_metadata['duration_seconds'])

            # Send webhook notification (build completed)
            if job.get('webhook_url'):
                if status == "success":
                    self.webhook_delivery.send_build_completed(
                        webhook_url=job['webhook_url'],
                        build_id=build_id,
                        project_id=project_id,
                        status=status,
                        duration_seconds=updated_metadata['duration_seconds'],
                        artifacts={
                            'count': updated_metadata['artifacts_count'],
                            'size_bytes': updated_metadata['artifacts_size_bytes'],
                        },
                        metadata=updated_metadata,
                    )
                else:
                    self.webhook_delivery.send_build_failed(
                        webhook_url=job['webhook_url'],
                        build_id=build_id,
                        project_id=project_id,
                        error_message=f"Build failed with exit code {exit_code}",
                        exit_code=exit_code,
                    )

            logger.info(f"[{build_id}] Build execution completed: {status}")

        except Exception as e:
            logger.error(f"[{build_id}] Build execution failed: {e}", exc_info=True)
            self._handle_build_failure(job, str(e))
            raise

        finally:
            # Cleanup workspace
            logger.info(f"[{build_id}] Cleaning up workspace")
            self._cleanup_workspace(workspace)

    def _clone_repository(
        self,
        repo_url: str,
        branch: str,
        commit: Optional[str],
        target_dir: Path,
    ):
        """Clone git repository to target directory"""

        import subprocess

        # Clone with specific branch
        cmd = ["git", "clone", "--depth", "1", "--branch", branch, repo_url, str(target_dir)]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"Git clone failed: {result.stderr}")

        # Checkout specific commit if provided
        if commit:
            checkout_cmd = ["git", "checkout", commit]
            result = subprocess.run(
                checkout_cmd,
                cwd=target_dir,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                raise RuntimeError(f"Git checkout failed: {result.stderr}")

    def _pull_docker_image(self, image: str):
        """Pull Docker image if not already present"""

        try:
            self.docker.images.get(image)
            logger.debug(f"Docker image already present: {image}")
        except NotFound:
            logger.info(f"Pulling Docker image: {image}")
            self.docker.images.pull(image)

    def _run_build_container(
        self,
        build_id: str,
        image: str,
        command: str,
        workspace: Path,
        source_dir: Path,
        output_dir: Path,
        timeout_seconds: int,
        environment: Dict[str, str],
    ) -> tuple[int, str]:
        """Run build command in Docker container"""

        # Prepare volumes
        volumes = {
            str(source_dir): {'bind': '/workspace', 'mode': 'rw'},
            str(output_dir): {'bind': '/output', 'mode': 'rw'},
        }

        # Prepare environment variables
        env = {
            'BUILD_ID': build_id,
            'BUILD_TYPE': 'release',
            **environment,
        }

        # Resource limits
        mem_limit = "2g"  # 2GB RAM limit
        cpu_quota = 100000  # 1 CPU core

        try:
            # Create container
            container = self.docker.containers.run(
                image=image,
                command=f"sh -c 'cd /workspace && {command}'",
                volumes=volumes,
                environment=env,
                working_dir="/workspace",
                detach=True,
                mem_limit=mem_limit,
                cpu_quota=cpu_quota,
                name=f"build-{build_id[:8]}",
                remove=False,  # Don't auto-remove so we can get logs
            )

            # Track active container
            with self.active_builds_lock:
                self.active_builds[build_id] = container

            logger.info(f"[{build_id}] Container started: {container.short_id}")

            # Wait for container with timeout
            start_time = time.time()

            try:
                result = container.wait(timeout=timeout_seconds)
                exit_code = result['StatusCode']

            except Exception as e:
                # Timeout or other error
                elapsed = time.time() - start_time

                if elapsed >= timeout_seconds:
                    logger.warning(f"[{build_id}] Build timeout after {elapsed}s, killing container")
                    container.kill()
                    exit_code = -1
                else:
                    logger.error(f"[{build_id}] Container wait error: {e}")
                    raise

            # Collect logs
            logs = container.logs(stdout=True, stderr=True).decode('utf-8', errors='replace')

            # Remove container
            container.remove(force=True)

            # Remove from active builds
            with self.active_builds_lock:
                self.active_builds.pop(build_id, None)

            return exit_code, logs

        except APIError as e:
            logger.error(f"[{build_id}] Docker API error: {e}")
            raise RuntimeError(f"Docker execution failed: {e}")

    def _collect_artifacts(self, build_id: str, output_dir: Path) -> int:
        """Collect build artifacts from output directory"""

        artifact_count = 0

        # Scan output directory for artifacts
        for item in output_dir.rglob('*'):
            if item.is_file():
                # Determine artifact type
                artifact_type = self._classify_artifact(item)

                # Add to artifact storage
                try:
                    self.artifact_manager.add_artifact(
                        build_id=build_id,
                        source_path=str(item),
                        artifact_type=artifact_type,
                        name=item.name,
                    )
                    artifact_count += 1

                except Exception as e:
                    logger.warning(f"Failed to add artifact {item.name}: {e}")

        return artifact_count

    def _classify_artifact(self, path: Path) -> str:
        """Classify artifact type based on file extension"""

        suffix = path.suffix.lower()

        # Binary executables
        if suffix in ['', '.exe', '.bin', '.app', '.so', '.dll', '.dylib']:
            return 'binary'

        # Packages
        elif suffix in ['.tar', '.gz', '.zip', '.tgz', '.deb', '.rpm', '.pkg', '.dmg']:
            return 'package'

        # Documentation
        elif suffix in ['.md', '.txt', '.pdf', '.html']:
            return 'documentation'

        else:
            return 'binary'

    def _update_build_status(self, build_id: str, status: str, metadata: Dict):
        """Update build status in Redis"""

        key = f"build:{build_id}:status"

        self.redis.setex(
            key,
            86400,  # 24 hour expiry
            json.dumps({
                'status': status,
                'updated_at': datetime.now().isoformat(),
                'metadata': metadata,
            })
        )

    def _update_metrics(self, status: str, duration_seconds: int):
        """Update Prometheus metrics (via Redis shared state)"""

        # Increment build counter
        metric_key = f"metrics:builds:{status}"
        self.redis.incr(metric_key)

        # Update duration histogram (store in Redis for Prometheus scraping)
        duration_key = f"metrics:build_duration:{status}"
        self.redis.rpush(duration_key, duration_seconds)
        self.redis.ltrim(duration_key, -100, -1)  # Keep last 100 values

    def _cleanup_workspace(self, workspace: Path):
        """Clean up build workspace"""

        try:
            if workspace.exists():
                shutil.rmtree(workspace)
                logger.debug(f"Cleaned up workspace: {workspace}")
        except Exception as e:
            logger.warning(f"Failed to clean up workspace {workspace}: {e}")

    def _handle_build_failure(self, job: Dict, error_message: str):
        """Handle build failure"""

        build_id = job['build_id']
        project_id = job['project_id']

        logger.error(f"[{build_id}] Build failed: {error_message}")

        # Update build status
        try:
            self.artifact_manager.update_build_status(
                build_id=build_id,
                status="failed",
                exit_code=-1,
            )
        except Exception as e:
            logger.error(f"Failed to update build status: {e}")

        # Update Redis
        self._update_build_status(build_id, "failed", {'error': error_message})

        # Update metrics
        self._update_metrics("failed", 0)

        # Send webhook notification
        if job.get('webhook_url'):
            self.webhook_delivery.send_build_failed(
                webhook_url=job['webhook_url'],
                build_id=build_id,
                project_id=project_id,
                error_message=error_message,
                exit_code=-1,
            )

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals"""

        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_flag.set()

    def _wait_for_active_builds(self):
        """Wait for active builds to complete"""

        with self.active_builds_lock:
            active_count = len(self.active_builds)

        if active_count > 0:
            logger.info(f"Waiting for {active_count} active builds to complete...")

            while True:
                with self.active_builds_lock:
                    if len(self.active_builds) == 0:
                        break

                time.sleep(2)

            logger.info("All active builds completed")

    def health_check(self) -> Dict:
        """Health check endpoint for monitoring"""

        with self.active_builds_lock:
            active_count = len(self.active_builds)

        return {
            'status': 'healthy',
            'active_builds': active_count,
            'max_concurrent_builds': self.max_concurrent_builds,
            'workspace': str(self.workspace_base),
            'docker_connected': self.docker.ping(),
            'redis_connected': self.redis.ping(),
        }


def main():
    """Main entry point"""

    # Configuration from environment
    redis_host = os.getenv('REDIS_HOST', 'localhost')
    redis_port = int(os.getenv('REDIS_PORT', '6379'))
    redis_db = int(os.getenv('REDIS_DB', '2'))
    max_concurrent = int(os.getenv('MAX_CONCURRENT_BUILDS', '2'))

    # Create executor
    executor = BuildExecutor(
        redis_host=redis_host,
        redis_port=redis_port,
        redis_db=redis_db,
        max_concurrent_builds=max_concurrent,
    )

    # Health check mode
    if len(sys.argv) > 1 and sys.argv[1] == 'health':
        health = executor.health_check()
        print(json.dumps(health, indent=2))
        sys.exit(0 if health['status'] == 'healthy' else 1)

    # Start worker
    executor.start_worker()


if __name__ == "__main__":
    main()
