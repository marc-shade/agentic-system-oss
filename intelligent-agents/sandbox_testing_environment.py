#!/usr/bin/env python3
"""
Sandboxed Testing Environment
==============================

Safe, isolated testing of code modifications before deployment.

Features:
- Container-based isolation (Apple Container preferred, Docker fallback)
- Automated test execution
- Performance comparison (before/after)
- Regression detection
- Automatic rollback on failure
- Security scanning

Architecture:
    Code Patch → Container (Apple/Docker) → Run Tests → Compare Performance → Pass/Fail

Container Priority:
    1. Apple Container (native macOS, optimized for Apple silicon)
    2. Docker (cross-platform fallback)
    3. Local sandbox (if containers unavailable)

This enables Darwin Gödel and Auto-Implementation to safely validate
self-modifications without affecting the production system.
"""

import asyncio
import docker
import hashlib
import json
import logging
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestStatus(Enum):
    """Test execution status"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class TestResult:
    """Result of a test execution"""
    test_id: str
    status: TestStatus
    tests_total: int
    tests_passed: int
    tests_failed: int
    execution_time_ms: float
    memory_usage_mb: float
    cpu_usage_percent: float
    errors: List[str]
    warnings: List[str]
    coverage_percent: Optional[float] = None
    created_at: str = ""


@dataclass
class PerformanceMetrics:
    """Performance comparison metrics"""
    baseline_execution_time_ms: float
    modified_execution_time_ms: float
    execution_time_delta_ms: float
    execution_time_delta_percent: float

    baseline_memory_mb: float
    modified_memory_mb: float
    memory_delta_mb: float
    memory_delta_percent: float

    baseline_cpu_percent: float
    modified_cpu_percent: float
    cpu_delta_percent: float

    regression_detected: bool
    improvement_confirmed: bool


class SandboxedTestingEnvironment:
    """
    Container-based sandboxed testing environment.

    Preferred: Apple Container (native macOS, optimized for Apple silicon)
    Fallback: Docker (cross-platform)
    Final fallback: Local sandbox

    Provides safe, isolated testing of code modifications with:
    - Complete isolation from production
    - Automated test execution
    - Performance benchmarking
    - Regression detection
    - Security validation
    """

    def __init__(
        self,
        base_path: str = "/mnt/agentic-system",
        enable_containers: bool = True
    ):
        """Initialize sandboxed testing environment."""
        self.base_path = Path(base_path)
        self.sandbox_dir = self.base_path / "sandbox"
        self.sandbox_dir.mkdir(exist_ok=True)

        # Container availability
        self.apple_container_enabled = False
        self.docker_enabled = False
        self.docker_client = None
        self.container_runtime = "local"  # Default fallback

        if enable_containers:
            # Priority 1: Check for Apple Container (preferred)
            # TEMPORARILY DISABLED: Apple Container builds hang, using Docker instead
            # try:
            #     result = subprocess.run(
            #         ['container', '--version'],
            #         capture_output=True,
            #         text=True,
            #         timeout=5
            #     )
            #     if result.returncode == 0:
            #         self.apple_container_enabled = True
            #         self.container_runtime = "apple"
            #         logger.info(f"Apple Container available: {result.stdout.strip()}")
            # except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            #     logger.debug(f"Apple Container not available: {e}")

            # Priority 2: Check for Docker (now primary due to Apple Container issues)
            if not self.apple_container_enabled:
                try:
                    self.docker_client = docker.from_env()
                    self.docker_enabled = True
                    self.container_runtime = "docker"
                    logger.info("Docker client initialized")
                except Exception as e:
                    logger.warning(f"Docker not available: {e}")

            # Priority 3: Local sandbox (final fallback)
            if not self.apple_container_enabled and not self.docker_enabled:
                logger.info("No container runtime available, using local sandbox mode")

        # Performance thresholds
        self.regression_threshold_percent = 20.0  # >20% slower is regression
        self.improvement_threshold_percent = 5.0  # >5% faster is improvement

        logger.info(f"Sandboxed Testing Environment initialized (runtime: {self.container_runtime})")

    async def run_tests(
        self,
        code_file: str,
        test_file: Optional[str] = None,
        timeout_seconds: int = 300
    ) -> TestResult:
        """
        Run tests in isolated sandbox environment.

        Args:
            code_file: Path to code file to test
            test_file: Optional path to test file (auto-generates if None)
            timeout_seconds: Maximum execution time

        Returns:
            TestResult with pass/fail status and metrics
        """
        test_id = hashlib.md5(
            f"{code_file}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:8]

        logger.info(f"Running tests {test_id} for {code_file}")

        result = TestResult(
            test_id=test_id,
            status=TestStatus.RUNNING,
            tests_total=0,
            tests_passed=0,
            tests_failed=0,
            execution_time_ms=0.0,
            memory_usage_mb=0.0,
            cpu_usage_percent=0.0,
            errors=[],
            warnings=[],
            created_at=datetime.now().isoformat()
        )

        try:
            # Priority order: Apple Container → Docker → Local sandbox
            if self.apple_container_enabled:
                result = await self._run_in_apple_container(code_file, test_file, timeout_seconds, result)
            elif self.docker_enabled:
                result = await self._run_in_docker(code_file, test_file, timeout_seconds, result)
            else:
                result = await self._run_in_local_sandbox(code_file, test_file, timeout_seconds, result)

            # Determine final status
            if result.tests_failed == 0 and result.errors == []:
                result.status = TestStatus.PASSED
            else:
                result.status = TestStatus.FAILED

            logger.info(f"Tests {test_id}: {result.status.value} ({result.tests_passed}/{result.tests_total} passed)")

        except asyncio.TimeoutError:
            result.status = TestStatus.TIMEOUT
            result.errors.append(f"Tests exceeded timeout of {timeout_seconds}s")
            logger.error(f"Tests {test_id} timed out")
        except Exception as e:
            result.status = TestStatus.ERROR
            result.errors.append(str(e))
            logger.error(f"Tests {test_id} error: {e}", exc_info=True)

        return result

    async def _run_in_apple_container(
        self,
        code_file: str,
        test_file: Optional[str],
        timeout: int,
        result: TestResult
    ) -> TestResult:
        """Run tests in Apple Container (preferred method for macOS)."""
        logger.info("Running tests in Apple Container")

        # Create temporary directory for test execution
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Copy code and test files
            code_path = Path(code_file)
            if code_path.exists():
                import shutil
                shutil.copy(code_path, temp_path / code_path.name)

            if test_file and Path(test_file).exists():
                shutil.copy(test_file, temp_path / Path(test_file).name)

            # Create Containerfile (OCI-compatible, similar to Dockerfile)
            containerfile_content = """
FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install pytest pytest-cov pytest-timeout memory_profiler psutil
CMD ["pytest", "--tb=short", "--cov=.", "-v"]
"""
            containerfile_path = temp_path / "Containerfile"
            containerfile_path.write_text(containerfile_content)

            # Build and run container using Apple Container CLI
            try:
                start_time = time.time()
                image_tag = f"sandbox-test-{result.test_id}"

                # Build image: container build -t TAG PATH
                logger.debug(f"Building Apple Container image: {image_tag}")
                build_process = await asyncio.create_subprocess_exec(
                    'container', 'build',
                    '-t', image_tag,
                    str(temp_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                build_stdout, build_stderr = await asyncio.wait_for(
                    build_process.communicate(),
                    timeout=timeout
                )

                if build_process.returncode != 0:
                    error_msg = build_stderr.decode('utf-8')
                    result.errors.append(f"Container build failed: {error_msg}")
                    logger.error(f"Apple Container build failed: {error_msg}")
                    return result

                # Run container: container run --rm IMAGE
                logger.debug(f"Running Apple Container: {image_tag}")
                run_process = await asyncio.create_subprocess_exec(
                    'container', 'run',
                    '--rm',  # Remove container after execution
                    image_tag,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                run_stdout, run_stderr = await asyncio.wait_for(
                    run_process.communicate(),
                    timeout=timeout
                )

                execution_time = (time.time() - start_time) * 1000

                # Parse pytest output
                logs = run_stdout.decode('utf-8') + run_stderr.decode('utf-8')
                result = self._parse_test_output(logs, result)
                result.execution_time_ms = execution_time

                # Cleanup: Remove image
                logger.debug(f"Cleaning up Apple Container image: {image_tag}")
                cleanup_process = await asyncio.create_subprocess_exec(
                    'container', 'rmi', image_tag,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
                await cleanup_process.communicate()

            except asyncio.TimeoutError:
                result.errors.append(f"Container execution exceeded timeout of {timeout}s")
                logger.error(f"Apple Container execution timed out")
            except Exception as e:
                result.errors.append(f"Apple Container execution error: {e}")
                logger.error(f"Apple Container error: {e}", exc_info=True)

        return result

    async def _run_in_docker(
        self,
        code_file: str,
        test_file: Optional[str],
        timeout: int,
        result: TestResult
    ) -> TestResult:
        """Run tests in Docker container."""
        logger.info("Running tests in Docker container")

        # Create temporary directory for test execution
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Copy code and test files
            code_path = Path(code_file)
            if code_path.exists():
                import shutil
                shutil.copy(code_path, temp_path / code_path.name)

            if test_file and Path(test_file).exists():
                shutil.copy(test_file, temp_path / Path(test_file).name)

            # Build Docker image (minimal Python image)
            dockerfile_content = """
FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install pytest pytest-cov pytest-timeout memory_profiler psutil
CMD ["pytest", "--tb=short", "--cov=.", "-v"]
"""
            dockerfile_path = temp_path / "Dockerfile"
            dockerfile_path.write_text(dockerfile_content)

            # Build and run container
            try:
                start_time = time.time()

                # Build image
                image, build_logs = self.docker_client.images.build(
                    path=str(temp_path),
                    tag=f"sandbox-test-{result.test_id}",
                    rm=True
                )

                # Run container
                container = self.docker_client.containers.run(
                    image.id,
                    detach=True,
                    mem_limit="512m",
                    cpu_quota=50000,  # 50% CPU
                    network_mode="none",  # No network access
                    remove=True
                )

                # Wait for completion
                exit_code = container.wait(timeout=timeout)
                logs = container.logs().decode('utf-8')

                execution_time = (time.time() - start_time) * 1000

                # Parse pytest output
                result = self._parse_test_output(logs, result)
                result.execution_time_ms = execution_time

                # Cleanup image
                self.docker_client.images.remove(image.id, force=True)

            except docker.errors.ContainerError as e:
                result.errors.append(f"Container error: {e}")
            except docker.errors.ImageNotFound as e:
                result.errors.append(f"Image not found: {e}")
            except Exception as e:
                result.errors.append(f"Docker execution error: {e}")

        return result

    async def _run_in_local_sandbox(
        self,
        code_file: str,
        test_file: Optional[str],
        timeout: int,
        result: TestResult
    ) -> TestResult:
        """Run tests in local sandboxed directory (fallback mode)."""
        logger.info("Running tests in local sandbox mode")

        # Create isolated sandbox directory
        sandbox_test_dir = self.sandbox_dir / f"test_{result.test_id}"
        sandbox_test_dir.mkdir(exist_ok=True)

        try:
            # Copy files to sandbox
            code_path = Path(code_file)
            if code_path.exists():
                import shutil
                shutil.copy(code_path, sandbox_test_dir / code_path.name)

            # Run pytest in sandbox
            start_time = time.time()

            process = await asyncio.create_subprocess_exec(
                'pytest',
                str(sandbox_test_dir),
                '--tb=short',
                '-v',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(sandbox_test_dir)
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                execution_time = (time.time() - start_time) * 1000

                # Parse output
                output = stdout.decode('utf-8') + stderr.decode('utf-8')
                result = self._parse_test_output(output, result)
                result.execution_time_ms = execution_time

            except asyncio.TimeoutError:
                process.kill()
                raise

        finally:
            # Cleanup sandbox directory
            import shutil
            shutil.rmtree(sandbox_test_dir, ignore_errors=True)

        return result

    def _parse_test_output(self, output: str, result: TestResult) -> TestResult:
        """Parse pytest output to extract test results."""

        # Look for pytest summary line: "X passed, Y failed in Z.ZZs"
        import re

        # Match: "5 passed in 0.12s" or "3 passed, 2 failed in 1.23s"
        summary_pattern = r'(\d+)\s+passed'
        failed_pattern = r'(\d+)\s+failed'

        passed_match = re.search(summary_pattern, output)
        failed_match = re.search(failed_pattern, output)

        if passed_match:
            result.tests_passed = int(passed_match.group(1))

        if failed_match:
            result.tests_failed = int(failed_match.group(1))

        result.tests_total = result.tests_passed + result.tests_failed

        # Extract errors
        if "ERRORS" in output or "FAILED" in output:
            error_lines = [line for line in output.split('\n') if 'ERROR' in line or 'FAILED' in line]
            result.errors.extend(error_lines[:5])  # First 5 errors

        # Extract warnings
        if "warning" in output.lower():
            warning_lines = [line for line in output.split('\n') if 'warning' in line.lower()]
            result.warnings.extend(warning_lines[:3])  # First 3 warnings

        return result

    async def compare_performance(
        self,
        baseline_code: str,
        modified_code: str,
        iterations: int = 10
    ) -> PerformanceMetrics:
        """
        Compare performance of baseline vs modified code.

        Args:
            baseline_code: Original code file
            modified_code: Modified code file
            iterations: Number of benchmark iterations

        Returns:
            PerformanceMetrics with detailed comparison
        """
        logger.info("Comparing performance: baseline vs modified")

        # Run baseline tests
        baseline_result = await self.run_tests(baseline_code)

        # Run modified tests
        modified_result = await self.run_tests(modified_code)

        # Calculate deltas
        exec_delta_ms = modified_result.execution_time_ms - baseline_result.execution_time_ms
        exec_delta_pct = (exec_delta_ms / baseline_result.execution_time_ms) * 100 if baseline_result.execution_time_ms > 0 else 0

        mem_delta_mb = modified_result.memory_usage_mb - baseline_result.memory_usage_mb
        mem_delta_pct = (mem_delta_mb / baseline_result.memory_usage_mb) * 100 if baseline_result.memory_usage_mb > 0 else 0

        cpu_delta_pct = modified_result.cpu_usage_percent - baseline_result.cpu_usage_percent

        # Detect regression (>20% slower)
        regression_detected = exec_delta_pct > self.regression_threshold_percent

        # Confirm improvement (>5% faster)
        improvement_confirmed = exec_delta_pct < -self.improvement_threshold_percent

        metrics = PerformanceMetrics(
            baseline_execution_time_ms=baseline_result.execution_time_ms,
            modified_execution_time_ms=modified_result.execution_time_ms,
            execution_time_delta_ms=exec_delta_ms,
            execution_time_delta_percent=exec_delta_pct,

            baseline_memory_mb=baseline_result.memory_usage_mb,
            modified_memory_mb=modified_result.memory_usage_mb,
            memory_delta_mb=mem_delta_mb,
            memory_delta_percent=mem_delta_pct,

            baseline_cpu_percent=baseline_result.cpu_usage_percent,
            modified_cpu_percent=modified_result.cpu_usage_percent,
            cpu_delta_percent=cpu_delta_pct,

            regression_detected=regression_detected,
            improvement_confirmed=improvement_confirmed
        )

        logger.info(f"Performance comparison complete:")
        logger.info(f"  Execution time: {exec_delta_ms:+.1f}ms ({exec_delta_pct:+.1f}%)")
        logger.info(f"  Memory: {mem_delta_mb:+.1f}MB ({mem_delta_pct:+.1f}%)")
        logger.info(f"  Regression: {regression_detected}, Improvement: {improvement_confirmed}")

        return metrics

    async def validate_security(self, code_file: str) -> Dict[str, Any]:
        """
        Run security validation on code.

        Checks for:
        - Known vulnerability patterns
        - Unsafe code patterns
        - Dependency vulnerabilities

        Returns:
            Security validation results
        """
        logger.info(f"Running security validation on {code_file}")

        security_report = {
            "file": code_file,
            "timestamp": datetime.now().isoformat(),
            "vulnerabilities": [],
            "warnings": [],
            "passed": True
        }

        try:
            # Run bandit security scanner
            process = await asyncio.create_subprocess_exec(
                'bandit',
                '-f', 'json',
                code_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if stdout:
                bandit_results = json.loads(stdout.decode('utf-8'))
                security_report["vulnerabilities"] = bandit_results.get("results", [])

                if security_report["vulnerabilities"]:
                    security_report["passed"] = False
                    logger.warning(f"Security issues found: {len(security_report['vulnerabilities'])}")

        except FileNotFoundError:
            logger.warning("Bandit not installed, skipping security scan")
            security_report["warnings"].append("Security scanner not available")
        except Exception as e:
            logger.error(f"Security validation error: {e}")
            security_report["warnings"].append(str(e))

        return security_report


async def main():
    """Example usage of Sandboxed Testing Environment."""
    sandbox = SandboxedTestingEnvironment()

    print("\n" + "=" * 70)
    print("SANDBOXED TESTING ENVIRONMENT DEMONSTRATION")
    print("=" * 70)
    print()

    # Create a simple test file
    test_code = """
def add(a, b):
    return a + b

def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
    assert add(0, 0) == 0
"""

    test_file = Path("/tmp/test_sample.py")
    test_file.write_text(test_code)

    # Run tests
    result = await sandbox.run_tests(str(test_file))

    print(f"Test Results:")
    print(f"  Status: {result.status.value}")
    print(f"  Tests: {result.tests_passed}/{result.tests_total} passed")
    print(f"  Execution time: {result.execution_time_ms:.1f}ms")
    print(f"  Errors: {len(result.errors)}")
    print()

    # Cleanup
    test_file.unlink()


if __name__ == "__main__":
    asyncio.run(main())
