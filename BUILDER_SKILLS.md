# Builder Node - Complete Skills Documentation

**Node**: macpro51 (Builder)
**Created**: 2025-11-14
**Skills Version**: 1.0

---

## Overview

The Builder node has **5 comprehensive procedural skills** designed for production-grade compilation, testing, and deployment workflows. All skills are optimized for the Builder node's 24-thread Xeon CPU and RAID10 storage.

---

## Skill 1: Multi-Stage Docker Build

**Category**: Containerization
**File**: `skills/builder-node/multi_stage_docker_build.py`
**Stored in Memory**: Yes (skill_id: 1)

### Purpose
Build optimized, secure OCI-compliant container images using Buildah with multi-stage builds, security scanning, and minimal final image size.

### Key Features
- **Buildah-based**: Rootless, OCI-compliant builds
- **Multi-stage support**: development, testing, production targets
- **Security scanning**: Integrated Trivy vulnerability detection
- **Layer caching**: Faster iterative builds
- **Template generation**: Auto-generate Dockerfiles for Python 3.14, Rust, Node.js

### Usage Example
```python
from multi_stage_docker_build import multi_stage_docker_build

result = multi_stage_docker_build(
    source_dir="/path/to/project",
    image_name="myapp:latest",
    target_stage="production",
    enable_cache=True,
    scan_security=True
)

print(f"Image size: {result['image_size'] / (1024*1024):.2f} MB")
print(f"Vulnerabilities: {result['vulnerabilities']}")
```

### Success Criteria
- ✅ Image builds without errors
- ✅ No critical security vulnerabilities
- ✅ Runs as non-root user
- ✅ Optimized layer count

---

## Skill 2: Parallel Test Execution

**Category**: Testing
**File**: `skills/builder-node/parallel_test_execution.py`
**Stored in Memory**: Yes (skill_id: 2)

### Purpose
Execute test suites in parallel using all 24 cores with intelligent load balancing, coverage reporting, and result aggregation.

### Key Features
- **Auto-detection**: pytest, jest, cargo test
- **24-worker parallelization**: Maximum CPU utilization
- **Coverage reporting**: Integrated code coverage
- **Benchmark mode**: Performance test support
- **Test matrix**: Run across multiple Python versions
- **Fail-fast option**: Stop on first failure

### Usage Example
```python
from parallel_test_execution import parallel_test_execution

result = parallel_test_execution(
    project_dir="/home/marc/agentic-system",
    test_framework="pytest",  # or "auto"
    max_workers=24,
    coverage=True,
    fail_fast=True
)

print(f"Tests: {result['passed']}/{result['total_tests']}")
print(f"Coverage: {result['coverage']['total']:.1f}%")
print(f"Duration: {result['duration']:.2f}s")
```

### Success Criteria
- ✅ All tests executed
- ✅ Results properly aggregated
- ✅ Coverage data generated
- ✅ Execution time reduced via parallelization

---

## Skill 3: Performance Regression Detection

**Category**: Performance
**File**: `skills/builder-node/performance_regression_detection.py`
**Stored in Memory**: Yes (skill_id: 3)

### Purpose
Automated performance benchmarking with regression detection, baseline management, and historical trend analysis using hyperfine.

### Key Features
- **Hyperfine integration**: Statistical benchmarking
- **Baseline management**: Track performance over time
- **Regression detection**: Alert on >10% slowdowns
- **Improvement tracking**: Celebrate >5% speedups
- **Historical data**: Time-series performance storage
- **A/B comparison**: Compare two builds directly

### Usage Example
```python
from performance_regression_detection import benchmark_with_regression_detection

result = benchmark_with_regression_detection(
    command="make -j24 clean all",
    runs=10,
    warmup=3,
    regression_threshold=0.10
)

if result["regression"]:
    print(f"⚠️  REGRESSION: {result['change_percent']:.1f}% slower")
elif result["improvement"]:
    print(f"✓ IMPROVEMENT: {abs(result['change_percent']):.1f}% faster")
```

### Success Criteria
- ✅ Benchmark completes
- ✅ Performance data recorded
- ✅ Regression/improvement detected correctly
- ✅ Baseline updated appropriately

---

## Skill 4: Cross-Compilation Workflow

**Category**: Compilation
**File**: `skills/builder-node/cross_compilation_workflow.py`
**Stored in Memory**: Yes (skill_id: 4)

### Purpose
Build binaries for multiple architectures and platforms (Rust, Go, Python) with optimization and compression.

### Key Features
- **Rust cross-compilation**: Multiple target triples with sccache
- **Go cross-compilation**: GOOS/GOARCH combinations, static linking
- **Python wheels**: Multi-version, multi-platform builds
- **Symbol stripping**: Smaller release binaries
- **UPX compression**: Optional binary compression (Go)

### Usage Example
```python
from cross_compilation_workflow import cross_compile_rust

result = cross_compile_rust(
    project_dir="/path/to/rust/project",
    targets=["x86_64-unknown-linux-gnu", "aarch64-unknown-linux-gnu"],
    release=True,
    strip_symbols=True
)

for target, info in result["targets"].items():
    if info["success"]:
        size_mb = info["size_bytes"] / (1024 * 1024)
        print(f"{target}: {size_mb:.2f} MB")
```

### Success Criteria
- ✅ Binaries built for all targets
- ✅ No compilation errors
- ✅ Binary sizes optimized
- ✅ Static linking successful

---

## Skill 5: CI/CD Pipeline Executor

**Category**: Automation
**File**: `skills/builder-node/cicd_pipeline_executor.py`
**Stored in Memory**: Yes (skill_id: 5)

### Purpose
Execute complete CI/CD pipelines with lint, test, build, security scan, and deploy stages optimized for the Builder node.

### Key Features
- **5-stage pipeline**: lint → test → build → security scan → deploy
- **Python quality checks**: ruff, black, mypy
- **Parallel testing**: Uses Skill 2
- **Build caching**: ccache/sccache integration
- **Security scanning**: Dependency vulnerability checks
- **Failure notifications**: Alert on failures
- **Stage timing**: Track performance per stage

### Usage Example
```python
from cicd_pipeline_executor import execute_cicd_pipeline

result = execute_cicd_pipeline(
    project_dir="/home/marc/agentic-system",
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
    print(f"✗ Failed at {result['failed_stage']}")
```

### Success Criteria
- ✅ All stages complete successfully
- ✅ No security vulnerabilities
- ✅ Build artifacts generated
- ✅ Pipeline optimized via caching

---

## Build Caching Configuration

### ccache (C/C++)
- **Location**: `/home/marc/agentic-system/databases/build-cache/ccache`
- **Size**: 20GB
- **Config**: `~/.config/ccache/ccache.conf`
- **Usage**: Automatic via `CC="ccache gcc"` environment variable

### sccache (Rust)
- **Location**: `/home/marc/agentic-system/databases/build-cache/sccache`
- **Size**: 20GB
- **Config**: `~/.config/sccache.conf`
- **Usage**: Automatic via `RUSTC_WRAPPER="sccache"` environment variable

### Environment Setup
Source `~/.bashrc_builder` to enable:
- Python 3.14 as default
- Build caching (ccache/sccache)
- Parallel builds (24 threads)
- Optimized compiler flags

---

## Performance Baselines

### Baseline Database
- **Location**: `/home/marc/agentic-system/databases/benchmarks/baseline.json`
- **Script**: `scripts/run-baseline-benchmarks.sh`
- **Benchmarks**:
  - Python 3.14 import speed
  - C++ compilation time
  - Rust compilation time
  - Container build speed

### Running Benchmarks
```bash
cd /home/marc/agentic-system
./scripts/run-baseline-benchmarks.sh
```

---

## Integration with Orchestrator

The Builder node exposes these capabilities via the Builder API:

- **Health**: `GET http://localhost:9000/api/v1/health`
- **Status**: `GET http://localhost:9000/api/v1/status`
- **Capabilities**: `GET http://localhost:9000/api/v1/builder`

All skills can be invoked via the orchestrator for distributed build tasks.

---

## Best Practices

1. **Use Python 3.14** for all new development
2. **Enable build caching** for faster iterative builds
3. **Run tests in parallel** to utilize all 24 cores
4. **Benchmark regularly** to detect performance regressions
5. **Cross-compile** to validate multi-platform compatibility
6. **Security scan** all builds before deployment
7. **Use multi-stage** Docker builds for smaller images

---

## Future Enhancements

Potential improvements for the Builder skill set:

1. **Redis-backed distributed caching** - Share ccache/sccache across cluster nodes
2. **GPU acceleration** - Utilize NVIDIA GTX 680 for parallel compilation
3. **Remote execution** - Distribute compilation to other Builder nodes
4. **Advanced profiling** - CPU flame graphs, memory profiling integration
5. **Artifact management** - Automated artifact storage and versioning
6. **Notification system** - Integration with Voice Mode MCP (macOS) or notifications API

---

## Troubleshooting

**Build cache not working:**
```bash
ccache -s  # Check ccache stats
sccache -s  # Check sccache stats
source ~/.bashrc_builder  # Reload environment
```

**Tests failing to parallelize:**
- Ensure test framework supports parallelization
- Check for test interdependencies
- Verify sufficient system resources

**Benchmarks inconsistent:**
- Run more iterations (increase `runs` parameter)
- Ensure system is idle during benchmarking
- Check for thermal throttling

---

**All Builder skills are production-ready and stored in enhanced-memory for persistence across sessions.**
