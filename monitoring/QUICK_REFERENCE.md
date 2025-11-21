# Monitoring Stack Quick Reference

## Service URLs
```
Prometheus:   http://macpro51.local:9700
Grafana:      http://macpro51.local:9500  (admin/admin)
Alertmanager: http://macpro51.local:9093
Promtail:     http://macpro51.local:9080
```

## Common Commands

### Start/Stop Services
```bash
cd /home/marc/agentic-system/monitoring

# Start all
docker compose up -d

# Start specific service
docker compose up -d prometheus
docker compose up -d promtail
docker compose up -d alertmanager

# Stop all
docker compose down

# Restart service
docker compose restart prometheus
```

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker logs prometheus --tail 50 -f
docker logs promtail --tail 50 -f
docker logs alertmanager --tail 50 -f
```

### Verify Status
```bash
# Quick verification
./verify-monitoring.sh

# Check containers
docker ps --filter name=prometheus --filter name=loki --filter name=grafana

# Check Prometheus targets
curl -s http://localhost:9700/api/v1/targets | jq -r '.data.activeTargets[] | "\(.labels.job): \(.health)"'

# Check alerts
curl http://localhost:9700/api/v1/alerts | jq '.data.alerts'
```

### Query Metrics
```bash
# Prometheus query API
curl -s 'http://localhost:9700/api/v1/query?query=up' | jq

# Get metric names
curl -s http://localhost:9700/api/v1/label/__name__/values | jq

# Query specific metric
curl -s 'http://localhost:9700/api/v1/query?query=node_cpu_seconds_total' | jq
```

### Query Logs
```bash
# List log labels
curl -s 'http://localhost:9900/loki/api/v1/labels' | jq

# Query logs
curl -s 'http://localhost:9900/loki/api/v1/query_range?query={job="monitoring-logs"}&limit=100' | jq

# Follow logs (like tail -f)
curl -s 'http://localhost:9900/loki/api/v1/tail?query={job="docker"}&limit=10'
```

### Manage Alerts
```bash
# View active alerts in Prometheus
curl http://localhost:9700/api/v1/alerts | jq '.data.alerts'

# View alerts in Alertmanager
curl http://localhost:9093/api/v2/alerts | jq

# Silence an alert
curl -X POST http://localhost:9093/api/v2/silences \
  -H "Content-Type: application/json" \
  -d '{
    "matchers": [{"name": "alertname", "value": "HighCPU", "isRegex": false}],
    "startsAt": "2025-11-14T00:00:00Z",
    "endsAt": "2025-11-15T00:00:00Z",
    "comment": "Planned maintenance"
  }'
```

## Enable Docker Metrics

**One-time setup** (requires sudo):
```bash
cd /home/marc/agentic-system/monitoring
sudo ./enable-docker-metrics.sh
```

This will:
1. Backup existing Docker config
2. Enable metrics on port 9323
3. Restart Docker daemon
4. Verify metrics endpoint

## Configuration Files

```
monitoring/
├── docker-compose.yml                    # Service definitions
├── prometheus/config/prometheus.yml      # Scrape targets
├── prometheus/config/rules/*.yml         # Alert rules
├── loki/config/loki.yml                  # Log retention
├── promtail/config/promtail.yml          # Log sources
├── alertmanager/config/alertmanager.yml  # Alert routing
└── grafana/provisioning/                 # Dashboards & datasources
```

## Troubleshooting

### Container won't start
```bash
# Check logs
docker logs <container_name>

# Check compose file syntax
docker compose config

# Recreate container
docker compose up -d --force-recreate <service_name>
```

### Prometheus target down
```bash
# Check target URL is accessible
curl http://localhost:9100/metrics  # node-exporter
curl http://localhost:6333/metrics  # qdrant
curl http://localhost:9323/metrics  # docker (if enabled)

# Check Prometheus scrape config
cat prometheus/config/prometheus.yml

# Reload Prometheus config
docker compose restart prometheus
```

### Promtail not shipping logs
```bash
# Check Promtail status
curl http://localhost:9080/ready

# Check targets
docker logs promtail | grep "Adding target"

# Check for errors
docker logs promtail | grep -i error

# Verify Loki is receiving
curl -s 'http://localhost:9900/loki/api/v1/labels' | jq
```

### Alertmanager not routing
```bash
# Check Alertmanager config
curl http://localhost:9093/api/v2/status | jq

# Check if Prometheus is sending
curl http://localhost:9700/api/v1/alertmanagers | jq

# View Alertmanager logs
docker logs alertmanager
```

## Useful Queries

### Prometheus (PromQL)
```promql
# CPU usage
100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Memory usage
100 - ((node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100)

# Disk usage
100 - ((node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100)

# Container count
count(count by (container) (rate(container_cpu_usage_seconds_total[5m])))
```

### Loki (LogQL)
```logql
# All logs from monitoring
{job="monitoring-logs"}

# Docker container logs
{job="docker"}

# Logs with specific level
{job="monitoring-logs"} |= "ERROR"

# Count log entries
count_over_time({job="docker"}[1h])

# Parse JSON logs
{job="docker"} | json | level="ERROR"
```

## Data Retention

- **Prometheus**: 30 days (configurable in prometheus.yml)
- **Loki**: 7 days (configurable in loki.yml)
- **Alertmanager**: 120 hours (default retention)

To change Prometheus retention:
```yaml
# In docker-compose.yml
command:
  - '--storage.tsdb.retention.time=30d'  # Change this
```

## Backup

Important directories to backup:
```bash
/home/marc/agentic-system/monitoring/prometheus/config/
/home/marc/agentic-system/monitoring/alertmanager/config/
/home/marc/agentic-system/monitoring/promtail/config/
/home/marc/agentic-system/monitoring/grafana/provisioning/
```

Optional (can be rebuilt):
```bash
/home/marc/agentic-system/monitoring/prometheus/data/
/home/marc/agentic-system/monitoring/loki/data/
/home/marc/agentic-system/monitoring/grafana/data/
```

## Performance Tuning

### Reduce Prometheus memory usage
```yaml
# In prometheus.yml
global:
  scrape_interval: 30s  # Increase from 15s
```

### Reduce Loki storage
```yaml
# In loki.yml
limits_config:
  retention_period: 3d  # Reduce from 7d
```

### Disable unused scrapers
```yaml
# In promtail.yml
# Comment out jobs you don't need
```

## Integration with Builder Node

The monitoring stack is integrated with:
- **Builder API**: Metrics on port 9000 (when running)
- **Build Executor**: Logs in artifacts directory
- **Qdrant**: Metrics on port 6333
- **System**: Node exporter metrics

Alert webhooks route to mac-studio orchestrator for central management.
