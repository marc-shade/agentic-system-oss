# Builder Node API - Quick Reference

## Start/Stop API

```bash
# Start
cd /home/marc/agentic-system/services
./start-builder-api.sh

# Or with systemd
sudo systemctl start builder-node-api

# Stop
pkill -f builder-node-api.py

# Or with systemd
sudo systemctl stop builder-node-api

# Status
curl http://localhost:9000/health | jq .
```

## Common Commands

```bash
# Submit a build
curl -X POST http://localhost:9000/api/v1/build \
  -H "Content-Type: application/json" \
  -d '{"project_id":"my-app","priority":8}'

# Get build status
curl http://localhost:9000/api/v1/build/{build_id} | jq .

# View metrics
curl http://localhost:9000/api/v1/metrics | grep builder_

# Run tests
./test_builder_api.py

# Check logs
tail -f /home/marc/agentic-system/logs/builder-api.log
```

## Key Metrics

```prometheus
builder_active_builds              # Current builds
builder_builds_total{status}       # Total builds (success/failed/cancelled)
builder_build_duration_seconds     # Build duration histogram
builder_artifact_storage_bytes     # Total storage
builder_total_artifacts            # Total artifacts
builder_api_requests_total         # API requests
builder_api_request_duration_seconds  # API latency
```

## Prometheus Integration

Add to `monitoring/prometheus.yml`:
```yaml
scrape_configs:
  - job_name: 'builder-api'
    static_configs:
      - targets: ['localhost:9000']
    metrics_path: '/api/v1/metrics'
```

Reload: `curl -X POST http://localhost:9700/-/reload`

## Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/ready` | GET | Readiness |
| `/api/v1/build` | POST | Submit build |
| `/api/v1/build/{id}` | GET | Build status |
| `/api/v1/build/{id}/logs` | GET | Build logs |
| `/api/v1/artifacts/{id}/download` | GET | Artifacts |
| `/api/v1/metrics` | GET | Prometheus |

## Troubleshooting

```bash
# Check if running
lsof -i :9000

# Check dependencies
python3 -c "import fastapi, uvicorn, prometheus_client, aiofiles"

# Check Redis
redis-cli -n 2 ping

# Verify installation
./verify_builder_api.sh

# View errors
tail -20 /home/marc/agentic-system/logs/builder-api.log
```

## Files

- `/home/marc/agentic-system/services/builder-node-api.py` - Main server
- `/home/marc/agentic-system/services/test_builder_api.py` - Test suite
- `/home/marc/agentic-system/logs/builder-api.log` - Application log
- `/home/marc/agentic-system/services/BUILDER_API_SETUP.md` - Full docs
