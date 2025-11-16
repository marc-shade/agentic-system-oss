"""
Performance Regression Detection Skill

Automated performance benchmarking with regression detection,
baseline management, and historical trend analysis.

Builder Node Skill - Version 1.0
"""

def benchmark_with_regression_detection(
    command: str,
    baseline_file: str = "/home/marc/agentic-system/databases/benchmarks/baseline.json",
    runs: int = 10,
    warmup: int = 3,
    regression_threshold: float = 0.10  # 10% slower = regression
) -> dict:
    """
    Run performance benchmark and detect regressions.

    Args:
        command: Command to benchmark
        baseline_file: Path to baseline performance data
        runs: Number of benchmark runs
        warmup: Number of warmup runs
        regression_threshold: Threshold for regression detection (0.10 = 10%)

    Returns:
        dict: Benchmark results with regression analysis
    """
    import subprocess
    import json
    import statistics
    from pathlib import Path

    results = {
        "command": command,
        "runs": runs,
        "current": {},
        "baseline": {},
        "regression": False,
        "improvement": False,
        "change_percent": 0
    }

    # Run hyperfine benchmark
    hyperfine_cmd = [
        "hyperfine",
        "--runs", str(runs),
        "--warmup", str(warmup),
        "--export-json", "/tmp/benchmark_result.json",
        "--show-output",
        command
    ]

    try:
        subprocess.run(hyperfine_cmd, check=True, timeout=600)

        # Load current results
        with open("/tmp/benchmark_result.json") as f:
            data = json.load(f)
            current_result = data["results"][0]

            results["current"] = {
                "mean": current_result["mean"],
                "stddev": current_result["stddev"],
                "median": current_result["median"],
                "min": current_result["min"],
                "max": current_result["max"]
            }

        # Load baseline if exists
        baseline_path = Path(baseline_file)
        if baseline_path.exists():
            with open(baseline_path) as f:
                baseline_data = json.load(f)

                # Find matching command in baseline
                for entry in baseline_data.get("benchmarks", []):
                    if entry["command"] == command:
                        results["baseline"] = entry["performance"]
                        baseline_mean = entry["performance"]["mean"]
                        current_mean = results["current"]["mean"]

                        # Calculate change
                        change = (current_mean - baseline_mean) / baseline_mean
                        results["change_percent"] = change * 100

                        # Detect regression/improvement
                        if change > regression_threshold:
                            results["regression"] = True
                        elif change < -0.05:  # 5% faster
                            results["improvement"] = True

                        break

        # Update baseline if no regression or if improving
        if not results["regression"]:
            _update_baseline(baseline_file, command, results["current"])

        # Store in performance history
        _store_performance_history(command, results["current"])

    except subprocess.CalledProcessError as e:
        results["error"] = f"Benchmark failed: {e}"
    except Exception as e:
        results["error"] = str(e)

    return results


def _update_baseline(baseline_file: str, command: str, performance: dict):
    """Update baseline performance data."""
    import json
    from pathlib import Path
    from datetime import datetime

    baseline_path = Path(baseline_file)
    baseline_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing baseline
    if baseline_path.exists():
        with open(baseline_path) as f:
            baseline_data = json.load(f)
    else:
        baseline_data = {"benchmarks": []}

    # Update or add entry
    found = False
    for entry in baseline_data["benchmarks"]:
        if entry["command"] == command:
            entry["performance"] = performance
            entry["updated_at"] = datetime.now().isoformat()
            found = True
            break

    if not found:
        baseline_data["benchmarks"].append({
            "command": command,
            "performance": performance,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        })

    # Save baseline
    with open(baseline_path, 'w') as f:
        json.dump(baseline_data, f, indent=2)


def _store_performance_history(command: str, performance: dict):
    """Store performance data in time-series database."""
    import json
    from pathlib import Path
    from datetime import datetime

    history_file = Path("/home/marc/agentic-system/databases/benchmarks/history.jsonl")
    history_file.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now().isoformat(),
        "command": command,
        "performance": performance
    }

    with open(history_file, 'a') as f:
        f.write(json.dumps(entry) + '\n')


def compare_builds(
    build_a: str,
    build_b: str,
    test_command: str
) -> dict:
    """
    Compare performance between two builds.

    Args:
        build_a: First build command or binary path
        build_b: Second build command or binary path
        test_command: Test command pattern (use {BUILD} placeholder)

    Returns:
        dict: Comparison results with statistical significance
    """
    import subprocess
    import json

    cmd_a = test_command.replace("{BUILD}", build_a)
    cmd_b = test_command.replace("{BUILD}", build_b)

    hyperfine_cmd = [
        "hyperfine",
        "--runs", "20",
        "--warmup", "5",
        "--export-json", "/tmp/comparison.json",
        cmd_a,
        cmd_b
    ]

    subprocess.run(hyperfine_cmd, check=True)

    with open("/tmp/comparison.json") as f:
        data = json.load(f)

        result_a = data["results"][0]
        result_b = data["results"][1]

        faster = "A" if result_a["mean"] < result_b["mean"] else "B"
        speedup = max(result_a["mean"], result_b["mean"]) / min(result_a["mean"], result_b["mean"])

        return {
            "build_a": {
                "command": cmd_a,
                "mean": result_a["mean"],
                "stddev": result_a["stddev"]
            },
            "build_b": {
                "command": cmd_b,
                "mean": result_b["mean"],
                "stddev": result_b["stddev"]
            },
            "faster": faster,
            "speedup": speedup,
            "significant": speedup > 1.05  # >5% difference
        }


# Example usage
if __name__ == "__main__":
    # Benchmark a build command
    result = benchmark_with_regression_detection(
        command="make -j24 clean all",
        runs=10,
        warmup=3,
        regression_threshold=0.10
    )

    if result["regression"]:
        print(f"⚠️  REGRESSION DETECTED: {result['change_percent']:.1f}% slower")
    elif result["improvement"]:
        print(f"✓ IMPROVEMENT: {abs(result['change_percent']):.1f}% faster")
    else:
        print(f"✓ Performance stable: {result['current']['mean']:.3f}s")
