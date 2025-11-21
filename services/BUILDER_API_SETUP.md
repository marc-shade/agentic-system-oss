# Builder Node API - Setup Guide

Production-quality FastAPI server for Builder node (macpro51) with comprehensive Prometheus metrics.

## Installation

### 1. Install Dependencies

```bash
pip3.14 install fastapi uvicorn prometheus-client aiofiles --user
```

### 2. Verify Installation

```bash
python3 -c "import fastapi, uvicorn, prometheus_client, aiofiles; print('✅ All dependencies installed')"
```

## Running the API

### Development Mode

```bash
cd /home/marc/agentic-system/services
./start-builder-api.sh
```

Or directly:

```bash
python3 builder-node-api.py
```

### Production Mode (systemd)

```bash
# Install systemd service
sudo cp builder-node-api.service /etc/systemd/system/
sudo systemctl daemon-reload

# Enable and start service
sudo systemctl enable builder-node-api
sudo systemctl start builder-node-api

# Check status
sudo systemctl status builder-node-api

# View logs
sudo journalctl -u builder-node-api -f
```

## Testing

### Run Test Suite

```bash
# Start API first (in another terminal)
./start-builder-api.sh

# Run tests
./test_builder_api.py
```

### Manual Testing

```bash
# Health check
curl http://localhost:9000/health

# Submit a build
curl -X POST http://localhost:9000/api/v1/build \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "my-project",
    "git_commit": "abc123",
    "git_branch": "main",
    "priority": 8
  }'

# Get build status
curl http://localhost:9000/api/v1/build/{build_id}

# Prometheus metrics
curl http://localhost:9000/api/v1/metrics
```

## API Endpoints

### Health & Info
- `GET /` - API information
- `GET /health` - Health check
- `GET /ready` - Readiness check

### Build Operations
- `POST /api/v1/build` - Submit build job
- `GET /api/v1/build/{build_id}` - Get build status
- `GET /api/v1/build/{build_id}/logs` - Stream build logs
- `POST /api/v1/build/callback` - Webhook from orchestrator

### Artifacts
- `GET /api/v1/artifacts/{build_id}/download` - Download artifacts
- `GET /api/v1/artifacts/{build_id}/download?artifact_name=foo.bin` - Download specific artifact

### Monitoring
- `GET /api/v1/metrics` - Prometheus metrics

## Prometheus Metrics

### Build Metrics
- `builder_active_builds` (Gauge) - Currently running builds
- `builder_builds_total{status}` (Counter) - Total builds by status (success/failed/cancelled)
- `builder_build_duration_seconds` (Histogram) - Build execution duration

### Artifact Metrics
- `builder_artifact_storage_bytes` (Gauge) - Total artifact storage
- `builder_artifact_storage_bytes_by_project{project_id}` (Gauge) - Storage per project
- `builder_total_artifacts` (Gauge) - Total artifact count

### API Metrics
- `builder_api_requests_total{method,endpoint,status}` (Counter) - API request count
- `builder_api_request_duration_seconds{method,endpoint}` (Histogram) - API request latency

## Integration with Prometheus

Add to Prometheus configuration (`/home/marc/agentic-system/monitoring/prometheus.yml`):

```yaml
scrape_configs:
  - job_name: 'builder-api'
    static_configs:
      - targets: ['localhost:9000']
        labels:
          node: 'macpro51'
          service: 'builder-api'
    metrics_path: '/api/v1/metrics'
    scrape_interval: 15s
```

Reload Prometheus:
```bash
curl -X POST http://localhost:9700/-/reload
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Builder Node API                       │
│                   (FastAPI + Uvicorn)                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐ │
│  │  Health  │  │  Build   │  │  Prometheus Metrics  │ │
│  │  Checks  │  │  Control │  │      Exporter        │ │
│  └──────────┘  └──────────┘  └──────────────────────┘ │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │         Artifact Manager Integration             │  │
│  │    (Storage, Versioning, Manifest, Cleanup)      │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │          Redis Queue Integration                 │  │
│  │        (Priority Queue, Task Metadata)           │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
           │                           │
           ▼                           ▼
    ┌─────────────┐          ┌─────────────────┐
    │   Artifact  │          │  Redis (DB 2)   │
    │   Storage   │          │  Build Queue    │
    │ /artifacts/ │          └─────────────────┘
    └─────────────┘
```

## Configuration

Environment variables:
- `REDIS_HOST` - Redis hostname (default: localhost)
- `REDIS_PORT` - Redis port (default: 6379)

## Logging

Logs are written to:
- `/home/marc/agentic-system/logs/builder-api.log` - Application logs
- `/home/marc/agentic-system/logs/builder-api-service.log` - Systemd service logs (if using systemd)

## Troubleshooting

### API won't start

```bash
# Check if port 9000 is already in use
lsof -i :9000

# Check Redis connectivity
redis-cli ping

# Check Python dependencies
python3 -c "import fastapi, uvicorn, prometheus_client, aiofiles"
```

### Metrics not appearing in Prometheus

```bash
# Verify metrics endpoint
curl http://localhost:9000/api/v1/metrics

# Check Prometheus targets
curl http://localhost:9700/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job=="builder-api")'

# Reload Prometheus config
curl -X POST http://localhost:9700/-/reload
```

### Build submission fails

```bash
# Check artifact storage permissions
ls -la /home/marc/agentic-system/artifacts/

# Check Redis queue
redis-cli -n 2 keys "builder:*"

# Check API logs
tail -f /home/marc/agentic-system/logs/builder-api.log
```

## Performance Tuning

### Uvicorn Workers

For production, run with multiple workers:

```bash
uvicorn builder-node-api:app \
  --host 0.0.0.0 \
  --port 9000 \
  --workers 4 \
  --log-level info
```

### Connection Pooling

Redis connection pooling is handled automatically by `redis.asyncio`.

### Rate Limiting

For production deployment, consider adding rate limiting:

```bash
pip3.14 install slowapi --user
```

Add to API:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/v1/build")
@limiter.limit("10/minute")
async def submit_build(request: Request, ...):
    ...
```

## Security Considerations

1. **CORS**: Currently allows all origins (`allow_origins=["*"]`). Configure based on orchestrator IP.
2. **Authentication**: Add API key or JWT authentication for production.
3. **Input Validation**: Pydantic models provide automatic validation.
4. **Rate Limiting**: Implement rate limiting for public endpoints.

## Next Steps

1. **Integrate with Prometheus**: Add scrape config for Builder API metrics
2. **Create Grafana Dashboard**: Visualize build metrics and API performance
3. **Set up Alerting**: Alert on build failures, API errors, queue overload
4. **Implement Authentication**: Add API key or OAuth for orchestrator access
5. **Add WebSocket Support**: Real-time build log streaming
6. **Implement Build Worker**: Worker process to execute builds from queue
