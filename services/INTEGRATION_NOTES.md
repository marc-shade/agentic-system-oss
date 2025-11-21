# Build Executor - Integration Notes

## Quick Start

### 1. Install Dependencies

```bash
cd /home/marc/agentic-system
source .venv/bin/activate
pip install redis docker
```

### 2. Start Services

```bash
# Start Redis (if not running)
sudo systemctl start redis

# Start Docker (if not running)
sudo systemctl start docker

# Start Build Executor
cd services
./build-executor-daemon.sh start
```

### 3. Submit Test Build

```bash
./test_build_executor.py
```

## Integration Points

### With Artifact Manager (Phase 3)

The build executor automatically integrates with `artifact_manager.py`:

```python
from artifact_manager import ArtifactManager

# Called automatically during build
manager.create_build(...)           # Initialize build storage
manager.add_artifact(...)            # Store build artifacts
manager.update_build_status(...)     # Update build status
```

Artifacts are stored at:
```
/home/marc/agentic-system/artifacts/builds/{project_id}/{build_id}/
```

### With Webhook Delivery (Phase 3)

The build executor automatically sends webhooks via `webhook_delivery.py`:

```python
from webhook_delivery import WebhookDelivery

# Called automatically during build
webhook.send_build_started(...)      # Notify build start
webhook.send_build_completed(...)    # Notify build success
webhook.send_build_failed(...)       # Notify build failure
```

Webhook logs are stored at:
```
/home/marc/agentic-system/logs/webhooks.log
```

### With Redis Queue (Phase 2)

Build jobs are submitted to Redis queue (DB 2):

```python
import redis
import json

r = redis.Redis(host='localhost', port=6379, db=2)
r.lpush("build_queue", json.dumps(job))
```

Build status is tracked in Redis:
```python
status = r.get(f"build:{build_id}:status")
```

### With Prometheus Metrics (Phase 4)

Metrics are stored in Redis for Prometheus scraping:

```bash
# Build counters
redis-cli -n 2 GET metrics:builds:success
redis-cli -n 2 GET metrics:builds:failed

# Duration histograms (last 100 builds)
redis-cli -n 2 LRANGE metrics:build_duration:success 0 -1
```

Add to Prometheus config:
```yaml
# TODO: Add Redis exporter for build metrics
```

### With Loki Logs (Phase 4)

Build logs are stored in:
```
/home/marc/agentic-system/logs/build_executor.log
/home/marc/agentic-system/logs/build_executor.error.log
```

Configure Loki Promtail to scrape these logs.

## API Integration

### Submit Build (Python)

```python
import redis
import json
import uuid

def submit_build(project_id: str, git_repo: str, build_command: str):
    r = redis.Redis(host='localhost', port=6379, db=2)

    job = {
        "build_id": str(uuid.uuid4()),
        "project_id": project_id,
        "git_repo": git_repo,
        "git_branch": "main",
        "build_type": "release",
        "build_command": build_command,
        "build_env": "node:20",
        "webhook_url": "http://orchestrator:9000/api/v1/build/callback",
        "tags": ["production"],
        "timeout_seconds": 3600
    }

    r.lpush("build_queue", json.dumps(job))
    return job['build_id']

# Usage
build_id = submit_build(
    project_id="my-app",
    git_repo="https://github.com/user/repo",
    build_command="npm install && npm run build"
)
print(f"Build submitted: {build_id}")
```

### Monitor Build Status (Python)

```python
import redis
import json
import time

def wait_for_build(build_id: str, timeout: int = 3600):
    r = redis.Redis(host='localhost', port=6379, db=2)

    start = time.time()
    while time.time() - start < timeout:
        status_data = r.get(f"build:{build_id}:status")

        if status_data:
            status = json.loads(status_data)

            if status['status'] in ['success', 'failed']:
                return status

        time.sleep(5)

    return None

# Usage
status = wait_for_build(build_id)
if status and status['status'] == 'success':
    print("Build succeeded!")
else:
    print("Build failed or timeout")
```

### Receive Webhook (Flask Example)

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/api/v1/build/callback', methods=['POST'])
def build_callback():
    event = request.json

    print(f"Received: {event['event']}")
    print(f"Build ID: {event['build_id']}")
    print(f"Status: {event.get('status', 'N/A')}")

    if event['event'] == 'build.completed':
        # Handle successful build
        artifacts = event['artifacts']
        print(f"Artifacts: {artifacts['count']} ({artifacts['size_bytes']} bytes)")

    elif event['event'] == 'build.failed':
        # Handle failed build
        print(f"Error: {event['error']}")

    return jsonify({'received': True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000)
```

## Monitoring Integration

### Health Check Endpoint

```bash
# Direct health check
/home/marc/agentic-system/services/build-executor-daemon.sh health

# JSON output
{
  "status": "healthy",
  "active_builds": 1,
  "max_concurrent_builds": 2,
  "workspace": "/tmp/builds",
  "docker_connected": true,
  "redis_connected": true
}
```

Add to monitoring stack:
```bash
# Prometheus scrape config
curl -s http://localhost:9000/health | jq .
```

### Log Aggregation

Loki configuration (`/home/marc/agentic-system/monitoring/loki/promtail-config.yaml`):

```yaml
scrape_configs:
  - job_name: build-executor
    static_configs:
      - targets:
          - localhost
        labels:
          job: build-executor
          __path__: /home/marc/agentic-system/logs/build_executor*.log
```

### Metrics Collection

Redis metrics for Prometheus:

```python
# Add to Prometheus exporter
from prometheus_client import Counter, Histogram

builds_total = Counter('builds_total', 'Total builds', ['status'])
build_duration = Histogram('build_duration_seconds', 'Build duration')

# Export from Redis
r = redis.Redis(host='localhost', port=6379, db=2)

success_count = int(r.get('metrics:builds:success') or 0)
failed_count = int(r.get('metrics:builds:failed') or 0)

builds_total.labels(status='success')._value.set(success_count)
builds_total.labels(status='failed')._value.set(failed_count)
```

## Systemd Integration

### Install Service

```bash
sudo cp /home/marc/agentic-system/services/build-executor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable build-executor
sudo systemctl start build-executor
```

### Service Management

```bash
# Status
sudo systemctl status build-executor

# Logs
journalctl -u build-executor -f

# Restart
sudo systemctl restart build-executor

# Stop
sudo systemctl stop build-executor
```

### Service Dependencies

The service requires:
- `docker.service` (required)
- `redis.service` (optional, will retry if not available)

Ensure Docker and Redis start on boot:
```bash
sudo systemctl enable docker
sudo systemctl enable redis
```

## Environment Configuration

### Docker Configuration

Ensure user has Docker permissions:
```bash
sudo usermod -aG docker marc
# Log out and back in
```

Test Docker access:
```bash
docker ps
docker images
```

### Redis Configuration

For production, enable authentication:

```bash
# /etc/redis.conf
requirepass yourpassword
```

Update executor environment:
```bash
export REDIS_PASSWORD=yourpassword
```

### Resource Limits

Adjust concurrency based on available resources:

```bash
# For macpro51 (24 threads, 126GB RAM)
export MAX_CONCURRENT_BUILDS=4

# For lighter nodes
export MAX_CONCURRENT_BUILDS=1
```

## Next Integration Steps

### 1. Orchestrator API

Create endpoint to receive webhooks:
```python
# In orchestrator
@app.route('/api/v1/build/callback', methods=['POST'])
def receive_build_webhook():
    event = request.json
    # Process build completion
    # Update cluster state
    # Trigger next workflow step
```

### 2. Grafana Dashboard

Create build metrics dashboard:
- Build success/failure rates
- Build duration trends
- Active builds gauge
- Queue depth
- Resource usage

### 3. Build Triggers

Implement automatic build triggers:
- Git webhook integration
- Scheduled builds (cron)
- Manual API triggers
- Dependency-based triggers

### 4. Artifact Distribution

Distribute artifacts to other nodes:
- HTTP API for artifact download
- SMB/NFS sharing
- Registry integration (Docker, NPM, PyPI)

### 5. Build Caching

Implement caching for faster rebuilds:
- Layer caching (Docker)
- Dependency caching (npm, pip, cargo)
- ccache/sccache integration

## Troubleshooting

### Build executor won't start

```bash
# Check dependencies
docker --version
redis-cli ping

# Check logs
tail -f /home/marc/agentic-system/logs/build_executor.log

# Verify permissions
ls -la /tmp/builds
```

### Builds not executing

```bash
# Check queue
redis-cli -n 2 LLEN build_queue

# Check active builds
redis-cli -n 2 KEYS "build:*:status"

# Check worker status
./build-executor-daemon.sh status
```

### Webhook delivery failures

```bash
# Check webhook logs
tail -f /home/marc/agentic-system/logs/webhooks.log

# Test webhook endpoint
curl -X POST http://orchestrator:9000/api/v1/build/callback \
  -H "Content-Type: application/json" \
  -d '{"event": "build.test"}'
```

### Docker container issues

```bash
# List running containers
docker ps

# Check container logs
docker logs build-{build_id}

# Clean up stopped containers
docker container prune

# Clean up images
docker image prune
```

## Performance Tuning

### Optimal Concurrency

For macpro51 (24 threads, 126GB RAM):
- **Light builds** (Node.js, Python): 4-6 concurrent
- **Heavy builds** (Rust, C++): 2-3 concurrent
- **Mixed workload**: 2-4 concurrent

### Workspace Optimization

Use tmpfs for faster I/O:
```bash
sudo mount -t tmpfs -o size=20G tmpfs /tmp/builds
```

Add to `/etc/fstab`:
```
tmpfs /tmp/builds tmpfs size=20G 0 0
```

### Docker Optimization

Pre-pull common images:
```bash
docker pull node:20-alpine
docker pull python:3.12-slim
docker pull rust:latest
docker pull golang:1.21-alpine
```

Enable BuildKit for faster builds:
```bash
export DOCKER_BUILDKIT=1
```

## Security Hardening

### Container Isolation

Already implemented:
- No privileged containers
- Resource limits (CPU, memory)
- Volume mounts (limited to workspace)
- No host network access

### Additional Hardening

```bash
# Enable AppArmor/SELinux for containers
docker run --security-opt apparmor=docker-default ...

# Use read-only root filesystem
docker run --read-only ...

# Drop capabilities
docker run --cap-drop=ALL ...
```

### Network Isolation

Create isolated network for builds:
```bash
docker network create --internal build-network
docker run --network build-network ...
```

### Secret Management

Never pass secrets in build commands. Use:
- Docker secrets
- Environment variables (encrypted in Redis)
- External secret stores (Vault)

## Maintenance

### Daily Tasks

```bash
# Check service status
systemctl status build-executor

# Review logs
journalctl -u build-executor --since today

# Check disk usage
df -h /tmp/builds
du -sh /home/marc/agentic-system/artifacts
```

### Weekly Tasks

```bash
# Clean old artifacts
cd /home/marc/agentic-system/services
./artifact-cleanup.py --age-days 7 --keep-last 5

# Clean Docker
docker system prune -f

# Verify metrics
redis-cli -n 2 GET metrics:builds:success
```

### Monthly Tasks

```bash
# Review performance metrics
# Analyze build trends
# Update Docker images
# Review resource allocation
```

## Support

For issues or questions:
1. Check logs: `/home/marc/agentic-system/logs/build_executor.log`
2. Run health check: `./build-executor-daemon.sh health`
3. Run test suite: `./test_build_executor.py`
4. Review this integration guide
