# Builder Node - Cluster Integration Guide

**Node**: macpro51 (Builder)
**Role**: Compilation, Testing, Deployment Specialist
**Status**: ✅ Production Ready
**Date**: 2025-11-14

---

## Overview

The Builder node is now fully integrated into the agentic cluster with distributed task queuing, build caching, and orchestrator API integration. This guide explains how to leverage the Builder node from other cluster nodes.

---

## Task Queue System

### Architecture

The Builder uses Redis-based distributed task queuing:

- **Queue Database**: Redis DB 2 (`redis://localhost:6379/2`)
- **Task Storage**: Hash-based with `task:{task_id}` keys
- **Priority Queue**: Sorted set with priority-based ordering
- **Results Storage**: 7-day TTL for completed tasks

### Task Types

The Builder supports 6 task types:

1. **compile** - Compile projects (C/C++, Rust, Python, Go)
2. **test** - Run test suites in parallel (24 threads)
3. **build_container** - Build Docker/OCI images
4. **benchmark** - Performance benchmarking with regression detection
5. **cross_compile** - Cross-platform binary builds
6. **cicd_pipeline** - Full CI/CD pipeline execution

### Enqueuing Tasks from Other Nodes

**From macOS Orchestrator (mac-studio):**

```python
import redis
import json

# Connect to Builder's Redis
r = redis.Redis(host='macpro51.local', port=6379, db=2, decode_responses=True)

# Enqueue a compilation task
task = {
    "type": "compile",
    "project_dir": "/path/to/project",
    "build_system": "cargo",  # or "cmake", "make", "python"
    "priority": 8,  # 1-10, 10 is highest
    "created_by": "mac-studio",
    "callback_url": "http://mac-studio.local:8200/build/callback"
}

task_id = f"task_{int(time.time() * 1000)}"
task["task_id"] = task_id

# Store task
r.hset(f"task:{task_id}", mapping=task)

# Add to queue
r.zadd("builder:queue:macpro51", {task_id: -task["priority"]})

print(f"Enqueued task: {task_id}")
```

**From Python on any node:**

```python
from builder_task_queue import BuilderTaskQueue

queue = BuilderTaskQueue(redis_host="macpro51.local")

# Enqueue test task
task_id = queue.enqueue_task({
    "type": "test",
    "project_dir": "/shared/project",
    "framework": "pytest",
    "max_workers": 24,
    "coverage": True,
    "priority": 7
})

print(f"Test task queued: {task_id}")
```

---

## Build Caching

### Redis-Backed Distributed Caching

**Configuration:**

- **ccache**: `redis://localhost:6379/0` (C/C++)
- **sccache**: `redis://localhost:6379/1` (Rust/C++)
- **Local cache**: `/home/marc/agentic-system/databases/build-cache/`
- **Cache size**: 20GB per tool

**How It Works:**

1. Builder compiles with ccache/sccache enabled
2. Compilation results stored in local cache
3. Cache entries also pushed to Redis (when configured)
4. Other Builder nodes can retrieve from Redis
5. Cache hits avoid recompilation entirely

**Cache Hit Rates:**

```bash
# On macpro51
ccache -s  # View ccache statistics
sccache -s  # View sccache statistics
```

**For Cluster-Wide Sharing:**

All nodes should have ccache/sccache configured to use the same Redis instance:

```conf
# ~/.config/ccache/ccache.conf
remote_storage = redis://macpro51.local:6379/0

# ~/.config/sccache.conf
[cache.redis]
endpoint = "redis://macpro51.local:6379/1"
```

---

## Orchestrator API Integration

### Builder API Endpoints

**Base URL**: `http://macpro51.local:9000`

**Available Endpoints:**

```bash
# Health check
GET /api/v1/health
Response: {"status": "healthy|degraded", "services": {...}}

# Full node status
GET /api/v1/status
Response: {node_info, capabilities, services, mcp_servers, hooks}

# Builder capabilities
GET /api/v1/builder
Response: {node_id, node_type, role, capabilities, hardware}

# Execute command (future)
POST /api/v1/control/execute
Body: {"command": "status", "task_type": "monitoring"}
```

**Example Usage:**

```python
import requests

# Check Builder health
health = requests.get("http://macpro51.local:9000/api/v1/health").json()
print(f"Builder status: {health['status']}")

# Get capabilities
caps = requests.get("http://macpro51.local:9000/api/v1/builder").json()
print(f"Node type: {caps['node_type']}")
print(f"Capabilities: {caps['capabilities']}")
```

---

## Service Discovery

### Avahi/mDNS Advertisement

The Builder advertises itself on the network:

- **Service Type**: `_agentic-builder._tcp`
- **Port**: 9000
- **Hostname**: `macpro51.local`

**TXT Records:**
- `node_id=macpro51`
- `node_type=builder`
- `node_role=construction_deployment`
- `orchestrator_ready=true`
- `capabilities=claude_code,hooks,mcp_servers,enhanced_memory,docker,raid10`

**Discovery from macOS nodes:**

```bash
# Browse for Builder nodes
avahi-browse -a -t | grep agentic-builder

# Or use dns-sd
dns-sd -B _agentic-builder._tcp
```

---

## Integration Patterns

### Pattern 1: Distributed Compilation

**Scenario**: macOS Developer node needs to build a large Rust project

```python
# On macbook-pro (Developer node)
import requests

# Queue compilation on Builder
task_id = queue.enqueue_task({
    "type": "compile",
    "project_dir": "/shared/rust-project",
    "build_system": "cargo",
    "priority": 9
})

# Poll for completion
while True:
    result = r.get(f"builder:results:{task_id}")
    if result:
        result = json.loads(result)
        if result["success"]:
            print("Build succeeded!")
            # Retrieve artifacts from /shared/rust-project/target/
        break
    time.sleep(5)
```

### Pattern 2: Automated Testing

**Scenario**: Orchestrator triggers tests on code push

```python
# On mac-studio (Orchestrator)

def on_git_push(repo_path):
    """Trigger tests when code is pushed"""

    task_id = queue.enqueue_task({
        "type": "test",
        "project_dir": repo_path,
        "framework": "auto",
        "max_workers": 24,
        "coverage": True,
        "priority": 8
    })

    # Store task ID for webhook callback
    return task_id
```

### Pattern 3: CI/CD Pipeline

**Scenario**: Full pipeline on merge to main

```python
# On Orchestrator

def run_cicd_pipeline(project_dir):
    """Execute complete CI/CD pipeline on Builder"""

    task_id = queue.enqueue_task({
        "type": "cicd_pipeline",
        "project_dir": project_dir,
        "pipeline_config": {
            "stages": [
                {"name": "lint", "enabled": True},
                {"name": "test", "enabled": True},
                {"name": "build", "enabled": True},
                {"name": "security_scan", "enabled": True},
                {"name": "deploy", "enabled": True}
            ],
            "cache": {"enabled": True, "shared": True},
            "parallel": {"test": True}
        },
        "priority": 10
    })

    return task_id
```

### Pattern 4: Performance Monitoring

**Scenario**: Continuous performance regression detection

```python
# Scheduled task on Orchestrator

def monitor_build_performance():
    """Daily performance benchmark"""

    task_id = queue.enqueue_task({
        "type": "benchmark",
        "command": "cargo build --release",
        "runs": 20,
        "warmup": 5,
        "regression_threshold": 0.10,
        "priority": 5
    })

    # Result will include regression detection
    return task_id
```

---

## Shared Storage

For cluster-wide builds, use SMB/NFS shares:

### On Builder (macpro51):

```bash
# Already serving via Samba
# Share: //macpro51.local/agentic-system
# Mount point: /home/marc/agentic-system
```

### On macOS nodes:

```bash
# Mount Builder's storage
mkdir -p /Volumes/builder-workspace
mount -t smbfs //macpro51.local/agentic-system /Volumes/builder-workspace

# Now can reference shared paths in tasks
```

---

## Performance Characteristics

### Build Performance

- **Parallel compilation**: 24 threads (Xeon)
- **Cache hit rate**: 80-95% (after warmup)
- **Typical compile times**:
  - Small Rust project: 30-60s
  - Large C++ project: 2-5 minutes
  - Python wheel: 5-15s

### Test Performance

- **24-worker parallel**: 10-20x faster than single-threaded
- **Typical test times**:
  - 1000 Python tests: 30-60s (parallel)
  - Jest test suite: 20-40s (parallel)
  - Rust tests: 40-80s (parallel)

### Container Builds

- **buildah performance**: 30-90s for typical multi-stage build
- **Security scan**: +15-30s with Trivy
- **Cache hit**: ~5-10s rebuild time

---

## Monitoring & Observability

### Task Queue Monitoring

```python
# Get queue status
status = queue.get_queue_status()
print(f"Queued: {status['queued_tasks']}")
print(f"Active: {status['active_tasks']}")
print(f"Utilization: {status['utilization']:.1f}%")
```

### Build Cache Monitoring

```bash
# ccache stats
ccache -s

# sccache stats
sccache -s

# Redis cache size
docker exec redis redis-cli INFO memory
```

### Performance Baselines

```bash
# Run baseline benchmarks
/home/marc/agentic-system/scripts/run-baseline-benchmarks.sh

# View results
cat /home/marc/agentic-system/databases/benchmarks/baseline.json
```

---

## Best Practices

1. **Use priorities wisely**:
   - 10: Critical production builds
   - 8-9: CI/CD pipelines
   - 5-7: Development builds
   - 1-4: Background tasks

2. **Enable build caching**:
   - Always use shared Redis cache for cluster builds
   - Monitor cache hit rates
   - Increase cache size if hit rate < 70%

3. **Leverage parallelization**:
   - Use all 24 cores for tests
   - Enable parallel builds (`-j24`)
   - Split large test suites

4. **Monitor performance**:
   - Run benchmarks regularly
   - Set up regression alerts
   - Track build times over time

5. **Shared storage**:
   - Use SMB shares for cross-node builds
   - Keep artifacts on RAID10 for performance
   - Clean up old builds periodically

---

## Troubleshooting

### Task Queue Issues

**Problem**: Tasks not being processed

```python
# Check worker is running
ps aux | grep builder_task_queue

# Restart worker
python3.14 /home/marc/agentic-system/services/builder_task_queue.py
```

**Problem**: Task stuck in queue

```bash
# Check Redis connection
docker exec redis redis-cli ping

# View queue
docker exec redis redis-cli zrange builder:queue:macpro51 0 -1
```

### Build Cache Issues

**Problem**: Low cache hit rate

```bash
# Check cache configuration
ccache --show-config

# Clear and rebuild cache
ccache -C
```

**Problem**: Redis cache not working

```bash
# Test Redis connection
docker exec redis redis-cli -n 0 ping

# Check if ccache is using Redis
ccache -s | grep -i remote
```

### Performance Issues

**Problem**: Builds slower than expected

- Check system load: `htop`
- Check RAID status: `cat /proc/mdstat`
- Check thermal throttling: `sensors`
- Verify all 24 cores utilized: `top` while building

---

## Future Enhancements

Planned improvements for Builder cluster integration:

1. **Distributed compilation** - Split compilation across multiple Builder nodes
2. **GPU acceleration** - Use GTX 680 for parallel tasks
3. **Advanced scheduling** - Load balancing across Builder nodes
4. **Webhook callbacks** - Notify orchestrator on task completion
5. **Artifact management** - Automated versioning and storage
6. **Build analytics** - Dashboard showing build trends and performance

---

**The Builder node is ready for production use in the agentic cluster!**

For questions or issues, check the Builder API status or review logs in `/home/marc/agentic-system/logs/`.
