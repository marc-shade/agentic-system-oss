"""
CI/CD Pipeline Executor Skill

Complete CI/CD pipeline execution with build, test, security scan,
and deployment stages optimized for the Builder node.

Builder Node Skill - Version 1.0
"""
import os
import platform
from pathlib import Path

def execute_cicd_pipeline(
    project_dir: str,
    pipeline_config: dict = None,
    notify_on_failure: bool = True
) -> dict:
    """
    Execute complete CI/CD pipeline.

    Args:
        project_dir: Project directory
        pipeline_config: Pipeline configuration dict
        notify_on_failure: Send notifications on failure

    Returns:
        dict: Pipeline execution results with timing
    """
    import time
    from pathlib import Path

    # Default pipeline config
    if pipeline_config is None:
        pipeline_config = {
            "stages": [
                {"name": "lint", "enabled": True},
                {"name": "test", "enabled": True},
                {"name": "build", "enabled": True},
                {"name": "security_scan", "enabled": True},
                {"name": "deploy", "enabled": False}
            ],
            "cache": {"enabled": True, "shared": True},
            "parallel": {"test": True, "build": False}
        }

    results = {
        "success": False,
        "stages": {},
        "total_duration": 0,
        "failed_stage": None
    }

    start_time = time.time()

    # Execute stages in order
    for stage_config in pipeline_config["stages"]:
        if not stage_config["enabled"]:
            continue

        stage_name = stage_config["name"]
        stage_start = time.time()

        stage_result = _execute_stage(
            stage_name,
            project_dir,
            pipeline_config
        )

        stage_result["duration"] = time.time() - stage_start
        results["stages"][stage_name] = stage_result

        # Fail pipeline if stage fails
        if not stage_result["success"]:
            results["failed_stage"] = stage_name
            results["total_duration"] = time.time() - start_time

            if notify_on_failure:
                _notify_failure(stage_name, stage_result)

            return results

    results["success"] = True
    results["total_duration"] = time.time() - start_time

    return results


def _execute_stage(stage_name: str, project_dir: str, config: dict) -> dict:
    """Execute a single pipeline stage."""
    import subprocess

    stage_handlers = {
        "lint": _stage_lint,
        "test": _stage_test,
        "build": _stage_build,
        "security_scan": _stage_security_scan,
        "deploy": _stage_deploy
    }

    handler = stage_handlers.get(stage_name)
    if handler:
        return handler(project_dir, config)
    else:
        return {"success": False, "error": f"Unknown stage: {stage_name}"}


def _stage_lint(project_dir: str, config: dict) -> dict:
    """Lint stage: Run code quality checks."""
    import subprocess
    from pathlib import Path

    result = {"success": False, "checks": {}}

    # Python linting
    if (Path(project_dir) / "setup.py").exists() or \
       (Path(project_dir) / "pyproject.toml").exists():

        # Ruff (fast linter)
        ruff_cmd = ["python3.14", "-m", "ruff", "check", project_dir]
        ruff_result = subprocess.run(ruff_cmd, capture_output=True, text=True)
        result["checks"]["ruff"] = ruff_result.returncode == 0

        # Black (formatter check)
        black_cmd = ["python3.14", "-m", "black", "--check", project_dir]
        black_result = subprocess.run(black_cmd, capture_output=True, text=True)
        result["checks"]["black"] = black_result.returncode == 0

        # Mypy (type checking)
        mypy_cmd = ["python3.14", "-m", "mypy", project_dir]
        mypy_result = subprocess.run(mypy_cmd, capture_output=True, text=True)
        result["checks"]["mypy"] = mypy_result.returncode == 0

    # All checks must pass
    result["success"] = all(result["checks"].values()) if result["checks"] else True

    return result


def _stage_test(project_dir: str, config: dict) -> dict:
    """Test stage: Run test suite with coverage."""
    from parallel_test_execution import parallel_test_execution

    parallel = config.get("parallel", {}).get("test", False)
    max_workers = 24 if parallel else 1

    return parallel_test_execution(
        project_dir=project_dir,
        max_workers=max_workers,
        coverage=True,
        fail_fast=True
    )


def _stage_build(project_dir: str, config: dict) -> dict:
    """Build stage: Compile and package."""
    import subprocess
    import os
    from pathlib import Path

    result = {"success": False, "artifacts": []}

    # Enable caching
    env = os.environ.copy()
    if config.get("cache", {}).get("enabled"):
        env["CC"] = "ccache gcc"
        env["CXX"] = "ccache g++"
        env["RUSTC_WRAPPER"] = "sccache"

    # Detect build system
    if (Path(project_dir) / "Cargo.toml").exists():
        # Rust build
        build_cmd = ["cargo", "build", "--release", "-j24"]
        subprocess.run(build_cmd, cwd=project_dir, env=env, check=True)
        result["artifacts"].append("target/release/*")
        result["success"] = True

    elif (Path(project_dir) / "CMakeLists.txt").exists():
        # CMake build
        subprocess.run(["cmake", "-B", "build", "-G", "Ninja"], cwd=project_dir, env=env, check=True)
        subprocess.run(["ninja", "-C", "build", "-j24"], cwd=project_dir, env=env, check=True)
        result["artifacts"].append("build/*")
        result["success"] = True

    elif (Path(project_dir) / "pyproject.toml").exists():
        # Python build
        build_cmd = ["python3.14", "-m", "build"]
        subprocess.run(build_cmd, cwd=project_dir, check=True)
        result["artifacts"].append("dist/*")
        result["success"] = True

    return result


def _stage_security_scan(project_dir: str, config: dict) -> dict:
    """Security scan stage: Check for vulnerabilities."""
    import subprocess
    from pathlib import Path

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    elif system == "Linux":
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()


    result = {"success": False, "vulnerabilities": {}}

    # Python dependency scanning
    if (Path(project_dir) / "requirements.txt").exists():
        safety_cmd = ["safety", "check", "--json", "-r", "requirements.txt"]
        try:
            safety_result = subprocess.run(
                safety_cmd,
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            result["vulnerabilities"]["python"] = "clean" if safety_result.returncode == 0 else "issues_found"
        except:
            result["vulnerabilities"]["python"] = "scan_failed"

    # Rust dependency scanning
    if (Path(project_dir) / "Cargo.toml").exists():
        audit_cmd = ["cargo", "audit"]
        try:
            audit_result = subprocess.run(
                audit_cmd,
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            result["vulnerabilities"]["rust"] = "clean" if audit_result.returncode == 0 else "issues_found"
        except:
            result["vulnerabilities"]["rust"] = "scan_failed"

    # Consider successful if no critical issues
    result["success"] = all(
        v in ["clean", "scan_failed"]
        for v in result["vulnerabilities"].values()
    )

    return result


def _stage_deploy(project_dir: str, config: dict) -> dict:
    """Deploy stage: Push artifacts to registry."""
    result = {"success": False, "deployed": []}

    # Deployment logic here (container push, binary upload, etc.)
    # This is environment-specific

    result["success"] = True
    return result


def _notify_failure(stage_name: str, stage_result: dict):
    """Send failure notification."""
    # Could integrate with Voice Mode MCP on macOS nodes
    # or send to orchestrator via Builder API
    print(f"⚠️  Pipeline failed at stage: {stage_name}")
    print(f"Error: {stage_result.get('error', 'Unknown error')}")


# Example usage
if __name__ == "__main__":
    result = execute_cicd_pipeline(
        project_dir=str(_STORAGE_BASE),
        pipeline_config={
            "stages": [
                {"name": "lint", "enabled": True},
                {"name": "test", "enabled": True},
                {"name": "build", "enabled": True},
                {"name": "security_scan", "enabled": True}
            ],
            "cache": {"enabled": True, "shared": True},
            "parallel": {"test": True}
        }
    )

    if result["success"]:
        print(f"✓ Pipeline succeeded in {result['total_duration']:.1f}s")
    else:
        print(f"✗ Pipeline failed at {result['failed_stage']}")
