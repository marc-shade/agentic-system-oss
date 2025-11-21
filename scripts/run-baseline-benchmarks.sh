#!/bin/bash
# Automated Baseline Benchmark Suite for Builder Node
# Establishes performance baselines for common build operations

set -euo pipefail

BENCHMARK_DIR="/home/marc/agentic-system/databases/benchmarks"
BASELINE_FILE="$BENCHMARK_DIR/baseline.json"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
REPORT_FILE="$BENCHMARK_DIR/reports/baseline_$TIMESTAMP.json"

mkdir -p "$BENCHMARK_DIR/reports"

echo "=== Builder Node Baseline Benchmarks ==="
echo "Timestamp: $TIMESTAMP"
echo ""

# Initialize baseline structure if it doesn't exist
if [ ! -f "$BASELINE_FILE" ]; then
    echo '{"benchmarks": [], "hardware": {}, "created_at": "'$TIMESTAMP'"}' > "$BASELINE_FILE"
fi

# Hardware info
echo "Recording hardware configuration..."
cat > /tmp/hw_info.json << EOF
{
  "cpu": "$(lscpu | grep 'Model name' | cut -d: -f2 | xargs)",
  "cores": $(nproc),
  "memory_gb": $(free -g | awk '/^Mem:/{print $2}'),
  "storage": "RAID10 NVMe"
}
EOF

# Benchmark 1: Python 3.14 import time
echo "Benchmarking Python 3.14 import speed..."
hyperfine --runs 20 --warmup 5 \
  --export-json /tmp/bench_python_import.json \
  'python3.14 -c "import sys"' > /dev/null 2>&1 || true

# Benchmark 2: Compilation speed (small C++ program)
echo "Benchmarking C++ compilation..."
cat > /tmp/test.cpp << 'CPPEOF'
#include <iostream>
int main() { std::cout << "test" << std::endl; return 0; }
CPPEOF

hyperfine --runs 20 --warmup 5 \
  --export-json /tmp/bench_cpp_compile.json \
  --prepare 'rm -f /tmp/test.o' \
  'g++ -c /tmp/test.cpp -o /tmp/test.o' > /dev/null 2>&1 || true

# Benchmark 3: Rust compilation (if cargo available)
if command -v cargo &> /dev/null; then
    echo "Benchmarking Rust compilation..."
    TEMP_RUST=$(mktemp -d)
    cd "$TEMP_RUST"
    cargo init --bin --name bench_test > /dev/null 2>&1

    hyperfine --runs 10 --warmup 2 \
      --export-json /tmp/bench_rust_compile.json \
      --prepare 'cargo clean' \
      'cargo build --release' > /dev/null 2>&1 || true

    cd - > /dev/null
    rm -rf "$TEMP_RUST"
fi

# Benchmark 4: Container build speed
if command -v buildah &> /dev/null; then
    echo "Benchmarking container build..."
    TEMP_CONTAINER=$(mktemp -d)
    cat > "$TEMP_CONTAINER/Dockerfile" << 'DOCKEREOF'
FROM alpine:latest
RUN echo "test"
DOCKEREOF

    hyperfine --runs 5 --warmup 1 \
      --export-json /tmp/bench_container_build.json \
      --cleanup 'podman rmi test-bench:latest' \
      'buildah bud -t test-bench:latest '"$TEMP_CONTAINER" > /dev/null 2>&1 || true

    rm -rf "$TEMP_CONTAINER"
fi

# Aggregate results
echo "Aggregating benchmark results..."
python3.14 << 'PYEOF'
import json
from pathlib import Path
from datetime import datetime

results = {
    "timestamp": datetime.now().isoformat(),
    "benchmarks": []
}

# Load hardware info
with open("/tmp/hw_info.json") as f:
    results["hardware"] = json.load(f)

# Load benchmark results
bench_files = {
    "python_import": "/tmp/bench_python_import.json",
    "cpp_compile": "/tmp/bench_cpp_compile.json",
    "rust_compile": "/tmp/bench_rust_compile.json",
    "container_build": "/tmp/bench_container_build.json"
}

for name, filepath in bench_files.items():
    if Path(filepath).exists():
        with open(filepath) as f:
            data = json.load(f)
            if data.get("results"):
                result = data["results"][0]
                results["benchmarks"].append({
                    "name": name,
                    "mean": result["mean"],
                    "stddev": result["stddev"],
                    "median": result["median"],
                    "min": result["min"],
                    "max": result["max"]
                })

# Save report
with open("'$REPORT_FILE'", "w") as f:
    json.dump(results, f, indent=2)

# Update baseline (only if better or first run)
baseline_file = "'$BASELINE_FILE'"
with open(baseline_file) as f:
    baseline = json.load(f)

baseline["hardware"] = results["hardware"]
baseline["last_updated"] = results["timestamp"]

for bench in results["benchmarks"]:
    # Find existing benchmark
    existing = None
    for i, b in enumerate(baseline["benchmarks"]):
        if b["name"] == bench["name"]:
            existing = i
            break

    if existing is not None:
        # Update if faster
        if bench["mean"] < baseline["benchmarks"][existing]["mean"]:
            baseline["benchmarks"][existing] = bench
    else:
        # Add new benchmark
        baseline["benchmarks"].append(bench)

with open(baseline_file, "w") as f:
    json.dump(baseline, f, indent=2)

print("\n=== Benchmark Results ===")
for bench in results["benchmarks"]:
    print(f"{bench['name']}: {bench['mean']:.4f}s (± {bench['stddev']:.4f}s)")

PYEOF

echo ""
echo "✓ Baseline benchmarks complete"
echo "Report: $REPORT_FILE"
echo "Baseline: $BASELINE_FILE"
