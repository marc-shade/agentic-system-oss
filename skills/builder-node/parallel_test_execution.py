"""
Parallel Test Execution Skill

Optimized parallel test running across multiple test frameworks
with intelligent load balancing and result aggregation.

Builder Node Skill - Version 1.0
"""

def parallel_test_execution(
    project_dir: str,
    test_framework: str = "auto",
    max_workers: int = 24,
    coverage: bool = True,
    benchmark: bool = False,
    fail_fast: bool = False
) -> dict:
    """
    Execute tests in parallel with optimal resource utilization.

    Args:
        project_dir: Project root directory
        test_framework: pytest, jest, cargo, or auto-detect
        max_workers: Maximum parallel workers (default: 24 for Xeon)
        coverage: Generate coverage report
        benchmark: Run performance benchmarks
        fail_fast: Stop on first failure

    Returns:
        dict: Test results with timing, coverage, failures
    """
    import subprocess
    import json
    import time
    from pathlib import Path

    results = {
        "success": False,
        "framework": test_framework,
        "total_tests": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "duration": 0,
        "coverage": None,
        "benchmarks": None
    }

    # Auto-detect test framework
    if test_framework == "auto":
        if (Path(project_dir) / "pytest.ini").exists() or \
           (Path(project_dir) / "setup.py").exists():
            test_framework = "pytest"
        elif (Path(project_dir) / "package.json").exists():
            test_framework = "jest"
        elif (Path(project_dir) / "Cargo.toml").exists():
            test_framework = "cargo"
        else:
            results["error"] = "Could not auto-detect test framework"
            return results

    results["framework"] = test_framework

    start_time = time.time()

    try:
        if test_framework == "pytest":
            cmd = [
                "python3.14", "-m", "pytest",
                "-n", str(max_workers),  # pytest-xdist parallel
                "--tb=short",
                "--color=yes",
                "--json-report",
                "--json-report-file=/tmp/pytest_report.json"
            ]

            if coverage:
                cmd.extend(["--cov", "--cov-report=json"])
            if benchmark:
                cmd.append("--benchmark-only")
            if fail_fast:
                cmd.append("-x")

            cmd.append(project_dir)

        elif test_framework == "jest":
            cmd = [
                "npm", "test", "--",
                "--maxWorkers", str(max_workers),
                "--json",
                "--outputFile=/tmp/jest_report.json"
            ]

            if coverage:
                cmd.extend(["--coverage", "--coverageReporters=json"])
            if fail_fast:
                cmd.append("--bail")

        elif test_framework == "cargo":
            cmd = [
                "cargo", "test",
                "--jobs", str(max_workers),
                "--",
                "--test-threads", str(max_workers)
            ]

            if fail_fast:
                cmd.insert(2, "--no-fail-fast")

        # Execute tests
        result = subprocess.run(
            cmd,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )

        results["duration"] = time.time() - start_time
        results["success"] = result.returncode == 0

        # Parse results based on framework
        if test_framework == "pytest":
            try:
                with open("/tmp/pytest_report.json") as f:
                    report = json.load(f)
                    results["total_tests"] = report["summary"]["total"]
                    results["passed"] = report["summary"]["passed"]
                    results["failed"] = report["summary"]["failed"]
                    results["skipped"] = report["summary"]["skipped"]
            except:
                # Fallback to stdout parsing
                pass

            if coverage:
                try:
                    with open(Path(project_dir) / "coverage.json") as f:
                        cov_data = json.load(f)
                        results["coverage"] = {
                            "total": cov_data["totals"]["percent_covered"]
                        }
                except:
                    pass

        elif test_framework == "jest":
            try:
                with open("/tmp/jest_report.json") as f:
                    report = json.load(f)
                    results["total_tests"] = report["numTotalTests"]
                    results["passed"] = report["numPassedTests"]
                    results["failed"] = report["numFailedTests"]
            except:
                pass

        results["output"] = result.stdout if results["success"] else result.stderr

    except subprocess.TimeoutExpired:
        results["error"] = "Tests timed out after 1 hour"
    except Exception as e:
        results["error"] = str(e)

    return results


def run_test_matrix(
    project_dir: str,
    python_versions: list = ["3.12", "3.14"],
    parallel: bool = True
) -> dict:
    """
    Run tests across multiple Python versions.

    Args:
        project_dir: Project directory
        python_versions: List of Python versions to test
        parallel: Run versions in parallel

    Returns:
        dict: Results for each Python version
    """
    import concurrent.futures
    import subprocess

    results = {}

    def test_version(version):
        cmd = [
            f"python{version}", "-m", "pytest",
            "-n", "auto",
            "--tb=short",
            project_dir
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800
        )

        return {
            "version": version,
            "success": result.returncode == 0,
            "output": result.stdout if result.returncode == 0 else result.stderr
        }

    if parallel:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(python_versions)) as executor:
            futures = {executor.submit(test_version, v): v for v in python_versions}
            for future in concurrent.futures.as_completed(futures):
                version = futures[future]
                results[version] = future.result()
    else:
        for version in python_versions:
            results[version] = test_version(version)

    return results


# Example usage
if __name__ == "__main__":
    # Run pytest with coverage and benchmarks
    result = parallel_test_execution(
        project_dir="/home/marc/agentic-system",
        test_framework="pytest",
        max_workers=24,
        coverage=True,
        benchmark=False
    )

    print(f"Tests {'passed' if result['success'] else 'failed'}")
    print(f"Total: {result['total_tests']}, Passed: {result['passed']}, Failed: {result['failed']}")
    print(f"Duration: {result['duration']:.2f}s")
    if result['coverage']:
        print(f"Coverage: {result['coverage']['total']:.1f}%")
