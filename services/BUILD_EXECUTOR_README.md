# Build Executor - Production Build Orchestration Engine

The Build Executor is a production-quality build orchestration engine for the Builder node (macpro51). It provides isolated Docker-based builds, artifact management, real-time monitoring, and webhook notifications.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Build Executor Flow                      │
└─────────────────────────────────────────────────────────────┘

1. Job Queue (Redis)
   ↓
2. Worker fetches job
   ↓
3. Create workspace
   ↓
4. Clone repository (optional)
   ↓
5. Pull Docker image
   ↓
6. Execute build in container
   ↓
7. Capture logs → Artifact Manager
   ↓
8. Collect artifacts → Artifact Manager
   ↓
9. Update metrics (Prometheus)
   ↓
10. Send webhook (Orchestrator)
    ↓
11. Cleanup workspace
```

## Features

### Core Capabilities

- **Docker Isolation**: All builds run in isolated Docker containers with resource limits
- **Multi-Environment**: Supports Node.js, Python, Rust, Go, Alpine, Ubuntu environments
- **Git Integration**: Clone repositories, checkout branches, pin to specific commits
- **Artifact Management**: Automatic artifact collection, classification, and storage
- **Real-time Monitoring**: Redis status updates, Prometheus metrics
- **Webhook Notifications**: Build started/completed/failed callbacks
- **Timeout Handling**: Configurable build timeouts with graceful termination
- **Error Recovery**: Comprehensive error handling and workspace cleanup
- **Graceful Shutdown**: Waits for active builds to complete before stopping

### Build Job Schema

```json
{
  "build_id": "uuid",
  "project_id": "project-name",
  "git_repo": "https://github.com/user/repo",
  "git_commit": "abc123",
  "git_branch": "main",
  "build_type": "release",
  "build_command": "npm run build",
  "build_env": "node:20",
  "build_env_vars": {
    "NODE_ENV": "production"
  },
  "webhook_url": "http://orchestrator/callback",
  "tags": ["production"],
  "timeout_seconds": 7200
}
```

## Installation

### Prerequisites

1. **Docker**: Container runtime
   ```bash
   sudo dnf install docker
   sudo systemctl start docker
   sudo usermod -aG docker marc
   ```

2. **Redis**: Job queue (running on DB 2)
   ```bash
   sudo dnf install redis
   sudo systemctl start redis
   ```

3. **Python Dependencies**:
   ```bash
   cd /home/marc/agentic-system
   python3 -m venv .venv
   source .venv/bin/activate
   pip install redis docker
   ```

### File Structure

```
services/
├── build_executor.py           # Main executor engine
├── build-executor-daemon.sh    # Daemon control script
├── build-executor.service      # Systemd service unit
├── test_build_executor.py      # Test suite
├── artifact_manager.py         # Artifact storage (Phase 3)
└── webhook_delivery.py         # Webhook notifications (Phase 3)
```

## Usage

### Daemon Control

Start the executor:
```bash
cd /home/marc/agentic-system/services
./build-executor-daemon.sh start
```

Stop the executor:
```bash
./build-executor-daemon.sh stop
```

Restart the executor:
```bash
./build-executor-daemon.sh restart
```

Check status:
```bash
./build-executor-daemon.sh status
```

View logs:
```bash
./build-executor-daemon.sh logs
```

Health check:
```bash
./build-executor-daemon.sh health
```

### Systemd Service

Install as systemd service:
```bash
sudo cp build-executor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable build-executor
sudo systemctl start build-executor
```

View logs:
```bash
journalctl -u build-executor -f
```

### Submitting Build Jobs

#### Python API

```python
import json
import redis
import uuid

r = redis.Redis(host='localhost', port=6379, db=2)

job = {
    "build_id": str(uuid.uuid4()),
    "project_id": "my-app",
    "git_repo": "https://github.com/user/repo",
    "git_branch": "main",
    "build_type": "release",
    "build_command": "npm install && npm run build",
    "build_env": "node:20",
    "webhook_url": "http://orchestrator:9000/api/v1/build/callback",
    "tags": ["production"],
    "timeout_seconds": 3600
}

r.lpush("build_queue", json.dumps(job))
print(f"Submitted build: {job['build_id']}")
```

#### Redis CLI

```bash
redis-cli -n 2 LPUSH build_queue '{
  "build_id": "test-123",
  "project_id": "test",
  "build_command": "echo Hello",
  "build_env": "alpine:latest",
  "timeout_seconds": 300
}'
```

### Monitoring Build Status

```python
import redis
import json

r = redis.Redis(host='localhost', port=6379, db=2)

build_id = "your-build-id"
status_key = f"build:{build_id}:status"

status_data = r.get(status_key)
if status_data:
    status = json.loads(status_data)
    print(f"Status: {status['status']}")
    print(f"Metadata: {json.dumps(status['metadata'], indent=2)}")
```

## Supported Build Environments

| Environment | Docker Image | Best For |
|-------------|--------------|----------|
| `node:20` | `node:20-alpine` | Node.js 20 projects |
| `node:18` | `node:18-alpine` | Node.js 18 projects |
| `python:3.12` | `python:3.12-slim` | Python 3.12 projects |
| `python:3.11` | `python:3.11-slim` | Python 3.11 projects |
| `rust:latest` | `rust:latest` | Rust projects |
| `golang:1.21` | `golang:1.21-alpine` | Go 1.21 projects |
| `ubuntu:22.04` | `ubuntu:22.04` | General Linux builds |
| `alpine:latest` | `alpine:latest` | Minimal builds |

## Build Workspace Structure

```
/tmp/builds/{build_id}/
├── source/           # Git repository clone
│   └── ...
├── output/           # Build artifacts (copied to artifact storage)
│   ├── binaries/
│   ├── packages/
│   └── documentation/
└── logs/
    └── build.log     # Build stdout/stderr
```

## Docker Container Configuration

Each build runs with:
- **Memory Limit**: 2GB
- **CPU Quota**: 1 core
- **Volume Mounts**:
  - `/workspace` → source directory (read-write)
  - `/output` → output directory (read-write)
- **Environment Variables**:
  - `BUILD_ID`: Unique build identifier
  - `BUILD_TYPE`: release/debug
  - Custom env vars from job

## Artifact Classification

Artifacts are automatically classified by file extension:

- **Binary**: executables, `.so`, `.dll`, `.bin`, `.exe`
- **Package**: `.tar`, `.gz`, `.zip`, `.deb`, `.rpm`, `.pkg`
- **Documentation**: `.md`, `.txt`, `.pdf`, `.html`

## Webhook Events

### build.started

```json
{
  "event": "build.started",
  "timestamp": "2025-11-14T16:30:00Z",
  "node_id": "macpro51",
  "build_id": "uuid",
  "project_id": "project-name",
  "metadata": {
    "build_number": 42,
    "git_commit": "abc123",
    "git_branch": "main"
  }
}
```

### build.completed

```json
{
  "event": "build.completed",
  "timestamp": "2025-11-14T16:35:00Z",
  "node_id": "macpro51",
  "build_id": "uuid",
  "project_id": "project-name",
  "status": "success",
  "duration_seconds": 300,
  "artifacts": {
    "count": 5,
    "size_bytes": 1048576
  },
  "logs_url": "http://macpro51.local:9000/api/v1/artifacts/{build_id}/logs",
  "download_url": "http://macpro51.local:9000/api/v1/artifacts/{build_id}/download"
}
```

### build.failed

```json
{
  "event": "build.failed",
  "timestamp": "2025-11-14T16:32:00Z",
  "node_id": "macpro51",
  "build_id": "uuid",
  "project_id": "project-name",
  "error": "Build failed with exit code 1",
  "exit_code": 1,
  "logs_url": "http://macpro51.local:9000/api/v1/artifacts/{build_id}/logs"
}
```

## Configuration

Environment variables:

```bash
# Redis connection
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=2

# Concurrency
MAX_CONCURRENT_BUILDS=2

# Optional
PYTHONUNBUFFERED=1
```

## Testing

Run comprehensive test suite:

```bash
cd /home/marc/agentic-system/services

# Start executor first
./build-executor-daemon.sh start

# Run tests
./test_build_executor.py
```

Tests include:
1. Simple echo build (Alpine)
2. Node.js build with artifacts
3. Build timeout handling
4. Failed build detection
5. Python build with multiple artifacts

Expected output:
```
Test Summary
============================================================
  PASS: Simple Echo Build
  PASS: Node.js Build
  PASS: Build Timeout
  PASS: Failed Build
  PASS: Python Build

Total: 5/5 passed
```

## Prometheus Metrics

Metrics are stored in Redis for Prometheus scraping:

- `metrics:builds:success` - Successful build count
- `metrics:builds:failed` - Failed build count
- `metrics:build_duration:success` - Success duration histogram
- `metrics:build_duration:failed` - Failure duration histogram

## Troubleshooting

### Build executor won't start

Check Docker connection:
```bash
docker info
```

Check Redis connection:
```bash
redis-cli -n 2 PING
```

### Builds timing out

Increase timeout in build job:
```json
{
  "timeout_seconds": 7200  // 2 hours
}
```

Or increase max concurrent builds:
```bash
export MAX_CONCURRENT_BUILDS=4
./build-executor-daemon.sh restart
```

### Out of disk space

Clean up old workspaces:
```bash
rm -rf /tmp/builds/*
```

Run artifact cleanup:
```bash
cd /home/marc/agentic-system/services
./artifact-cleanup.py --age-days 7 --keep-last 3
```

### Container errors

Check Docker logs:
```bash
docker logs build-{build_id}
```

Pull images manually:
```bash
docker pull node:20-alpine
docker pull python:3.12-slim
```

## Integration with Other Components

### Phase 3: Artifact Manager
- Automatic artifact storage and classification
- Build metadata tracking
- Version history
- Download URLs

### Phase 4: Monitoring
- Prometheus metrics for build stats
- Loki logs for build output
- Grafana dashboards for visualization

### Phase 5: Orchestrator
- Webhook callbacks for build status
- Build queue management
- Distributed coordination

## Performance

**Typical Build Times**:
- Simple Node.js: 30-60s
- Python with dependencies: 60-120s
- Rust compilation: 5-15 minutes
- Go compilation: 30-90s

**Resource Usage**:
- Memory: ~100-200MB per build + container overhead
- Disk: ~500MB-2GB per build workspace
- CPU: Limited to 1 core per build

**Concurrency**:
- Default: 2 parallel builds
- Recommended: 2-4 builds on macpro51 (24 threads, 126GB RAM)
- Maximum: Limited by Docker and disk I/O

## Next Steps

1. **Implement Orchestrator API** to receive webhooks
2. **Add Grafana Dashboard** for build visualization
3. **Implement Build Caching** for faster rebuilds
4. **Add Multi-Architecture Support** (x86_64, arm64)
5. **Integrate with GitHub Actions** for CI/CD
6. **Add Build Triggers** (git webhooks, scheduled builds)

## Security Considerations

- Builds run in isolated containers (no host access)
- Resource limits prevent DoS
- No privileged containers
- Workspace cleanup after build
- Redis authentication (configure if exposed)
- Webhook signature verification (TODO)

## License

Part of the Agentic System - Builder Node infrastructure.
