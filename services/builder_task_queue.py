#!/usr/bin/env python3.14
"""
Builder Task Queue System

Manages compilation, testing, and deployment tasks for the Builder node.
Integrates with Redis for distributed task queuing and orchestrator API.

Builder Node Service - Version 1.0
"""

import json
import time
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import redis

# Import Builder skills
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "builder-node"))


class BuilderTaskQueue:
    """Distributed task queue for Builder node operations."""

    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379):
        """Initialize task queue with Redis connection."""
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=2,  # Use DB 2 for task queue
            decode_responses=True
        )
        self.node_id = "macpro51"
        self.queue_key = f"builder:queue:{self.node_id}"
        self.active_key = f"builder:active:{self.node_id}"
        self.results_key = "builder:results"

    def enqueue_task(self, task: Dict) -> str:
        """
        Add a task to the queue.

        Args:
            task: Task specification dict with type, params, priority

        Returns:
            str: Task ID
        """
        task_id = f"task_{int(time.time() * 1000)}"
        task["task_id"] = task_id
        task["status"] = "queued"
        task["created_at"] = datetime.now().isoformat()
        task["node_id"] = self.node_id

        # Store task
        self.redis_client.hset(f"task:{task_id}", mapping=task)

        # Add to queue with priority
        priority = task.get("priority", 5)
        self.redis_client.zadd(self.queue_key, {task_id: -priority})

        return task_id

    def get_next_task(self) -> Optional[Dict]:
        """Get next task from queue (highest priority)."""
        # Get highest priority task
        tasks = self.redis_client.zrange(self.queue_key, 0, 0)

        if not tasks:
            return None

        task_id = tasks[0]

        # Move to active
        self.redis_client.zrem(self.queue_key, task_id)
        self.redis_client.sadd(self.active_key, task_id)

        # Get task data
        task = self.redis_client.hgetall(f"task:{task_id}")
        task["status"] = "running"
        task["started_at"] = datetime.now().isoformat()

        self.redis_client.hset(f"task:{task_id}", mapping=task)

        return task

    def execute_task(self, task: Dict) -> Dict:
        """
        Execute a Builder task.

        Args:
            task: Task specification

        Returns:
            dict: Execution result
        """
        task_type = task.get("type")
        task_id = task.get("task_id")

        result = {
            "task_id": task_id,
            "success": False,
            "output": None,
            "error": None,
            "duration": 0
        }

        start_time = time.time()

        try:
            if task_type == "compile":
                exec_result = self._execute_compile(task)
            elif task_type == "test":
                exec_result = self._execute_test(task)
            elif task_type == "build_container":
                exec_result = self._execute_container_build(task)
            elif task_type == "benchmark":
                exec_result = self._execute_benchmark(task)
            elif task_type == "cross_compile":
                exec_result = self._execute_cross_compile(task)
            elif task_type == "cicd_pipeline":
                exec_result = self._execute_cicd(task)
            else:
                result["error"] = f"Unknown task type: {task_type}"
                exec_result = None

            # Merge execution result with base result
            if exec_result:
                # Infer success if execution result doesn't provide it
                if "success" not in exec_result:
                    exec_result["success"] = not exec_result.get("error")
                result.update(exec_result)

        except Exception as e:
            result["error"] = str(e)
            result["success"] = False

        result["duration"] = time.time() - start_time
        result["completed_at"] = datetime.now().isoformat()

        return result

    def _execute_compile(self, task: Dict) -> Dict:
        """Execute compilation task."""
        project_dir = task.get("project_dir")
        build_system = task.get("build_system", "auto")

        # Detect build system
        project_path = Path(project_dir)

        if build_system == "auto":
            if (project_path / "Cargo.toml").exists():
                build_system = "cargo"
            elif (project_path / "CMakeLists.txt").exists():
                build_system = "cmake"
            elif (project_path / "Makefile").exists():
                build_system = "make"
            elif (project_path / "pyproject.toml").exists():
                build_system = "python"
            elif list(project_path.glob("*.cpp")) or list(project_path.glob("*.cxx")):
                build_system = "g++"
            elif list(project_path.glob("*.c")):
                build_system = "gcc"
            elif list(project_path.glob("*.rs")):
                build_system = "rustc"
            elif list(project_path.glob("*.go")):
                build_system = "go"

        # Execute build
        if build_system == "cargo":
            cmd = ["cargo", "build", "--release", "-j24"]
        elif build_system == "cmake":
            cmd = ["cmake", "-B", "build", "-G", "Ninja", "&&", "ninja", "-C", "build", "-j24"]
        elif build_system == "make":
            cmd = ["make", "-j24"]
        elif build_system == "python":
            cmd = ["python3.14", "-m", "build"]
        elif build_system == "g++":
            # Direct C++ compilation
            cpp_files = list(project_path.glob("*.cpp")) + list(project_path.glob("*.cxx"))
            output_name = cpp_files[0].stem if cpp_files else "a.out"
            cmd = ["ccache", "g++", "-std=c++20", "-O2"] + [str(f) for f in cpp_files] + ["-o", output_name]
        elif build_system == "gcc":
            # Direct C compilation
            c_files = list(project_path.glob("*.c"))
            output_name = c_files[0].stem if c_files else "a.out"
            cmd = ["ccache", "gcc", "-std=c17", "-O2"] + [str(f) for f in c_files] + ["-o", output_name]
        elif build_system == "rustc":
            # Direct Rust compilation
            rs_files = list(project_path.glob("*.rs"))
            output_name = rs_files[0].stem if rs_files else "main"
            cmd = ["rustc", "-O"] + [str(f) for f in rs_files] + ["-o", output_name]
        elif build_system == "go":
            # Direct Go compilation
            cmd = ["go", "build", "-o", "main"]
        else:
            return {"success": False, "error": f"Unsupported build system: {build_system}"}

        result = subprocess.run(
            cmd if isinstance(cmd, list) else cmd.split(),
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=3600
        )

        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None
        }

    def _execute_test(self, task: Dict) -> Dict:
        """Execute test task."""
        from parallel_test_execution import parallel_test_execution

        return parallel_test_execution(
            project_dir=task.get("project_dir"),
            test_framework=task.get("framework", "auto"),
            max_workers=task.get("max_workers", 24),
            coverage=task.get("coverage", True)
        )

    def _execute_container_build(self, task: Dict) -> Dict:
        """Execute container build task."""
        from multi_stage_docker_build import multi_stage_docker_build

        return multi_stage_docker_build(
            source_dir=task.get("source_dir"),
            image_name=task.get("image_name"),
            target_stage=task.get("target_stage", "production"),
            enable_cache=task.get("enable_cache", True),
            scan_security=task.get("scan_security", True)
        )

    def _execute_benchmark(self, task: Dict) -> Dict:
        """Execute benchmark task."""
        from performance_regression_detection import benchmark_with_regression_detection

        return benchmark_with_regression_detection(
            command=task.get("command"),
            runs=task.get("runs", 10),
            warmup=task.get("warmup", 3),
            regression_threshold=task.get("threshold", 0.10)
        )

    def _execute_cross_compile(self, task: Dict) -> Dict:
        """Execute cross-compilation task."""
        language = task.get("language", "rust")

        if language == "rust":
            from cross_compilation_workflow import cross_compile_rust
            return cross_compile_rust(
                project_dir=task.get("project_dir"),
                targets=task.get("targets", ["x86_64-unknown-linux-gnu"]),
                release=task.get("release", True)
            )
        elif language == "go":
            from cross_compilation_workflow import cross_compile_go
            return cross_compile_go(
                project_dir=task.get("project_dir"),
                platforms=task.get("platforms", [("linux", "amd64")])
            )
        else:
            return {"success": False, "error": f"Unsupported language: {language}"}

    def _execute_cicd(self, task: Dict) -> Dict:
        """Execute CI/CD pipeline task."""
        from cicd_pipeline_executor import execute_cicd_pipeline

        return execute_cicd_pipeline(
            project_dir=task.get("project_dir"),
            pipeline_config=task.get("pipeline_config")
        )

    def complete_task(self, task_id: str, result: Dict):
        """Mark task as complete and store result."""
        # Remove from active
        self.redis_client.srem(self.active_key, task_id)

        # Update task status
        task = self.redis_client.hgetall(f"task:{task_id}")
        task.update({
            "status": "completed" if result.get("success") else "failed",
            "completed_at": datetime.now().isoformat(),
            "result": json.dumps(result)
        })

        self.redis_client.hset(f"task:{task_id}", mapping=task)

        # Store in results (with TTL of 7 days)
        self.redis_client.setex(
            f"{self.results_key}:{task_id}",
            604800,  # 7 days
            json.dumps(result)
        )

    def worker_loop(self):
        """Main worker loop - process tasks from queue."""
        print(f"Builder Worker started on {self.node_id}")
        print("Waiting for tasks...")

        while True:
            try:
                task = self.get_next_task()

                if task:
                    print(f"\n=== Processing Task {task['task_id']} ===")
                    print(f"Type: {task['type']}")

                    result = self.execute_task(task)

                    print(f"Result: {'SUCCESS' if result.get('success') else 'FAILED'}")
                    if result.get('duration'):
                        print(f"Duration: {result['duration']:.2f}s")

                    self.complete_task(task['task_id'], result)
                else:
                    # No tasks, wait a bit
                    time.sleep(1)

            except KeyboardInterrupt:
                print("\nWorker shutting down...")
                break
            except Exception as e:
                print(f"Error processing task: {e}")
                time.sleep(5)

    def get_queue_status(self) -> Dict:
        """Get current queue status."""
        queued = self.redis_client.zcard(self.queue_key)
        active = self.redis_client.scard(self.active_key)

        return {
            "node_id": self.node_id,
            "queued_tasks": queued,
            "active_tasks": active,
            "total_capacity": 24,  # 24 threads
            "utilization": min(100, (active / 24) * 100)
        }


def main():
    """Main entry point for Builder task worker."""
    import argparse

    parser = argparse.ArgumentParser(description="Builder Task Queue Worker")
    parser.add_argument("--redis-host", default="localhost", help="Redis host")
    parser.add_argument("--redis-port", type=int, default=6379, help="Redis port")
    parser.add_argument("--status", action="store_true", help="Show queue status")

    args = parser.parse_args()

    queue = BuilderTaskQueue(args.redis_host, args.redis_port)

    if args.status:
        status = queue.get_queue_status()
        print(json.dumps(status, indent=2))
    else:
        queue.worker_loop()


if __name__ == "__main__":
    main()
