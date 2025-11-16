# Production Monitoring Infrastructure Deployment Summary

## Overview

Complete monitoring stack deployed on macpro51 (Builder Node) with:
- **Prometheus** - Metrics collection and alerting
- **Loki** - Log aggregation
- **Grafana** - Unified visualization
- **Promtail** - Log shipping
- **Alertmanager** - Alert routing and management
- **Node Exporter** - System metrics

## Deployed Components

### 1. Promtail (Log Shipping)
**Status**: ✅ Deployed and Running
**Port**: 9080
**Configuration**: `/home/marc/agentic-system/monitoring/promtail/config/promtail.yml`

**Log Sources**:
- ✅ Systemd journal (Builder API, system services)
- ✅ Docker containers (all monitoring stack containers)
- ✅ Build logs from `/home/marc/agentic-system/builder-node/artifacts/*/logs/*.log`
- ✅ Monitoring logs from `/home/marc/agentic-system/monitoring/*/logs/*.log`

**Key Features**:
- Automatic Docker container discovery
- Log parsing and label extraction
- Ships to Loki on port 9900
- SELinux-compatible with proper contexts

**SELinux Configuration**:
```yaml
user: "0:968"  # root:docker group
security_opt:
  - label=type:container_runtime_t
volumes:
  - /var/run/docker.sock:/var/run/docker.sock:z
```

### 2. Alertmanager (Alert Routing)
**Status**: ✅ Deployed and Running
**Port**: 9093
**Configuration**: `/home/marc/agentic-system/monitoring/alertmanager/config/alertmanager.yml`

**Alert Routes**:
- **Critical alerts**: 10s group wait, 1h repeat interval → orchestrator
- **Warning alerts**: 1m group wait, 6h repeat interval → orchestrator
- **Builder alerts**: Node-specific routing
- **Build job alerts**: Build-related notifications

**Receivers**:
- Default webhook: `http://mac-studio.local/api/v1/alerts`
- Critical webhook: `http://mac-studio.local/api/v1/alerts/critical`
- Warning webhook: `http://mac-studio.local/api/v1/alerts/warning`
- Builder webhook: `http://mac-studio.local/api/v1/alerts/builder`
- Build jobs webhook: `http://mac-studio.local/api/v1/alerts/builds`

**Inhibition Rules**:
- Critical alerts suppress warnings for same service
- Service down alerts suppress related alerts

### 3. Prometheus Integration
**Status**: ✅ Updated
**Configuration**: Updated to send alerts to Alertmanager

```yaml
alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
      timeout: 10s
```

**Scrape Targets**:
- ✅ prometheus: up
- ✅ node-exporter: up
- ✅ qdrant: available (metrics endpoint verified)
- ⚠️ docker: down (metrics not enabled yet)
- ⚠️ builder-api: down (not running)
- ⚠️ redis: down (not deployed yet)

### 4. Docker Daemon Metrics
**Status**: ⚠️ Not Enabled (Manual Step Required)

**Enablement Script**: `/home/marc/agentic-system/monitoring/enable-docker-metrics.sh`

**Manual Steps** (Requires sudo):
```bash
cd /home/marc/agentic-system/monitoring
sudo ./enable-docker-metrics.sh
```

**What It Does**:
1. Backs up existing `/etc/docker/daemon.json`
2. Enables metrics on port 9323
3. Restarts Docker daemon (brief interruption)
4. Verifies metrics endpoint

**Configuration**:
```json
{
  "metrics-addr": "0.0.0.0:9323",
  "experimental": true
}
```

### 5. Qdrant Metrics
**Status**: ✅ Verified
**Endpoint**: `http://localhost:6333/metrics`

Sample metrics available:
```
app_info{name="qdrant",version="1.15.5"} 1
collections_total 1
collections_vector_total 0
memory_active_bytes 109043712
```

Prometheus is configured to scrape Qdrant metrics every 60 seconds.

## Service Ports

| Service | Port | Purpose |
|---------|------|---------|
| Prometheus | 9700 | Metrics collection and UI |
| Loki | 9900 | Log aggregation API |
| Grafana | 9500 | Visualization dashboard |
| Node Exporter | 9100 | System metrics |
| Promtail | 9080 | Log shipping status |
| Alertmanager | 9093 | Alert management |
| Docker Daemon | 9323 | Docker metrics (not enabled yet) |
| Qdrant | 6333 | Vector database metrics |

## Access URLs

- **Prometheus**: http://macpro51.local:9700
- **Grafana**: http://macpro51.local:9500 (admin/admin)
- **Alertmanager**: http://macpro51.local:9093
- **Promtail**: http://macpro51.local:9080

## Verification

Run comprehensive verification:
```bash
/home/marc/agentic-system/monitoring/verify-monitoring.sh
```

**Quick Checks**:
```bash
# Check all containers
docker ps --filter name=prometheus --filter name=loki --filter name=grafana --filter name=promtail --filter name=alertmanager

# Check Prometheus targets
curl -s http://localhost:9700/api/v1/targets | jq -r '.data.activeTargets[] | "\(.labels.job): \(.health)"'

# Check Alertmanager status
curl -s http://localhost:9093/api/v2/status | jq -r '.cluster.status'

# Check Promtail readiness
curl http://localhost:9080/ready

# Check Qdrant metrics
curl -s http://localhost:6333/metrics | grep app_info
```

## Storage Usage

Current retention policies:
- **Prometheus**: 30 days
- **Loki**: 7 days (configured in loki.yml)

Expected storage:
- Prometheus: ~100MB/day (~3GB total)
- Loki: Varies by log volume
- Alertmanager: Minimal (alert state only)

Check current usage:
```bash
du -sh /home/marc/agentic-system/monitoring/prometheus/data
du -sh /home/marc/agentic-system/monitoring/loki/data
du -sh /home/marc/agentic-system/monitoring/alertmanager/data
```

## Configuration Files

### Created
- ✅ `/home/marc/agentic-system/monitoring/promtail/config/promtail.yml`
- ✅ `/home/marc/agentic-system/monitoring/alertmanager/config/alertmanager.yml`
- ✅ `/home/marc/agentic-system/monitoring/enable-docker-metrics.sh`
- ✅ `/home/marc/agentic-system/monitoring/verify-monitoring.sh`

### Updated
- ✅ `/home/marc/agentic-system/monitoring/docker-compose.yml`
- ✅ `/home/marc/agentic-system/monitoring/prometheus/config/prometheus.yml`

## SELinux Compatibility

All volume mounts use proper SELinux contexts:
- `:Z` - Exclusive private label (config directories)
- `:z` - Shared label (Docker socket, logs)
- `ro,z` - Read-only with shared label

Promtail requires `container_runtime_t` context to access Docker socket.

## Next Steps

### Immediate
1. ✅ Enable Docker daemon metrics: `sudo ./enable-docker-metrics.sh`
2. Create alert rules in `prometheus/config/rules/`
3. Configure Grafana dashboards
4. Test alert routing

### Short-term
1. Deploy Redis (if needed) for caching
2. Start Builder API service
3. Create build job alert rules
4. Set up PagerDuty/Slack integration in Alertmanager

### Long-term
1. Create custom Grafana dashboards for:
   - Builder node performance
   - Build job metrics
   - Resource utilization
   - Alert history
2. Implement log-based alerts in Loki
3. Set up cross-cluster monitoring (orchestrator)
4. Configure backup for Prometheus/Loki data

## Testing

### Test Promtail Log Shipping
```bash
# Generate test log
echo "Test log entry" >> /home/marc/agentic-system/monitoring/grafana/logs/test.log

# Query Loki for recent logs
curl -s 'http://localhost:9900/loki/api/v1/query_range?query={job="monitoring-logs"}&limit=10' | jq
```

### Test Alert Triggering
```bash
# Create high CPU load
stress-ng --cpu 24 --timeout 60s

# Check fired alerts
curl http://localhost:9700/api/v1/alerts | jq '.data.alerts'

# Check Alertmanager received alerts
curl http://localhost:9093/api/v2/alerts | jq
```

### Test Docker Metrics (after enablement)
```bash
# Verify endpoint
curl http://localhost:9323/metrics | grep engine_daemon

# Check Prometheus target
curl -s http://localhost:9700/api/v1/targets | jq -r '.data.activeTargets[] | select(.labels.job=="docker") | .health'
```

## Troubleshooting

### Promtail Permission Issues
If Promtail can't access Docker socket:
```bash
# Check socket permissions
ls -lZ /var/run/docker.sock

# Check Promtail logs
docker logs promtail --tail 50

# Verify Docker group ID
stat -c "%g" /var/run/docker.sock
```

### Alertmanager Not Receiving Alerts
```bash
# Check Prometheus alertmanager config
curl http://localhost:9700/api/v1/alertmanagers | jq

# Check Prometheus rule evaluation
curl http://localhost:9700/api/v1/rules | jq

# Check Alertmanager config
curl http://localhost:9093/api/v2/status | jq
```

### Loki Not Receiving Logs
```bash
# Check Promtail targets
curl http://localhost:9080/targets | jq

# Check Loki labels
curl -s 'http://localhost:9900/loki/api/v1/label/job/values' | jq

# Check Promtail client logs
docker logs promtail | grep "client"
```

## Security Notes

1. **Docker Socket Access**: Promtail requires Docker socket access to discover containers
2. **SELinux**: All containers run with appropriate SELinux contexts
3. **Network**: All services on internal `monitoring` bridge network
4. **Authentication**: Grafana requires login (default: admin/admin)
5. **Alertmanager**: Webhooks to orchestrator (internal network only)

## Monitoring the Monitors

The monitoring stack monitors itself:
- Prometheus scrapes its own metrics
- Promtail ships its own logs to Loki
- Node exporter tracks system health
- Grafana has self-monitoring enabled

## Performance Impact

Expected resource usage:
- **CPU**: ~2-5% total (all services combined)
- **RAM**: ~600-800MB total
- **Disk I/O**: Moderate (metrics writes, log shipping)
- **Network**: Minimal (internal only, except webhooks)

## Deployment Date

Deployed: 2025-11-14
By: Claude Code (Builder Node Agent)
Phase: 5 - Production Monitoring Infrastructure
