# Claude Code OpenTelemetry Monitoring Setup

## Overview
This monitoring setup integrates Claude Code with Prometheus to provide real-time, accurate usage metrics in your statusline.

## Architecture
```
Claude Code (with OTEL) → Prometheus (metrics DB) → Statusline (queries Prometheus)
       ↓                        ↓
  Port 9464              Port 9090 (localhost only)
```

## Setup Complete ✓

### 1. OpenTelemetry Enabled
- Added to `~/.claude/settings.json`:
  - `CLAUDE_CODE_ENABLE_TELEMETRY=1`
  - `OTEL_METRICS_EXPORTER=prometheus`
  - `OTEL_METRIC_EXPORT_INTERVAL=5000` (5 seconds for real-time updates)

### 2. Prometheus Running
- Container: `claude-prometheus`
- Web UI: http://127.0.0.1:9090
- Scrapes metrics from Claude Code every 3 seconds

### 3. Statusline Updated
- Now queries Prometheus for real usage data
- Falls back to manual `weekly_budget.json` if Prometheus unavailable

## Next Steps

### Start Using
1. **Restart Claude Code** to activate OpenTelemetry export:
   ```bash
   # Exit current session and start new one
   claude
   ```

2. **Verify metrics are being collected**:
   ```bash
   # Check if Claude Code is exposing metrics
   curl -s http://localhost:9464/metrics | grep claude_code
   
   # Check Prometheus is scraping them
   curl -s http://localhost:9090/api/v1/query?query=claude_code_token_usage_total
   ```

3. **View in Prometheus UI**:
   - Open: http://127.0.0.1:9090
   - Query: `claude_code_token_usage_total`
   - Query: `claude_code_cost_usage_total`

### Auto-start Prometheus on Boot (Optional)

Create systemd user service:
```bash
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/claude-prometheus.service << 'SERVICE'
[Unit]
Description=Prometheus for Claude Code Monitoring
After=network.target

[Service]
Type=forking
ExecStart=/home/marc/agentic-system/monitoring/start-prometheus.sh
ExecStop=/usr/bin/podman stop claude-prometheus
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
SERVICE

# Enable and start
systemctl --user enable claude-prometheus
systemctl --user start claude-prometheus
```

## Available Metrics

### Token Usage
- `claude_code_token_usage_total{type="input"}` - Input tokens
- `claude_code_token_usage_total{type="output"}` - Output tokens  
- `claude_code_token_usage_total{type="cacheRead"}` - Cache reads
- `claude_code_token_usage_total{type="cacheCreation"}` - Cache writes

### Cost
- `claude_code_cost_usage_total` - Total cost in USD

### Activity
- `claude_code_session_count` - Number of sessions
- `claude_code_active_time_total` - Active usage time

## Troubleshooting

### Metrics not showing in statusline?
```bash
# 1. Check Claude Code is exporting metrics
netstat -tuln | grep 9464

# 2. Check Prometheus is running
podman ps | grep prometheus

# 3. Check Prometheus logs
podman logs claude-prometheus

# 4. Restart Prometheus
podman restart claude-prometheus
```

### Statusline still showing old data?
- Statusline caches may take 3-5 seconds to update
- Prometheus scrapes every 3 seconds
- If you just restarted Claude, wait 10 seconds for first scrape

## Commands

```bash
# Start Prometheus
~/agentic-system/monitoring/start-prometheus.sh

# Stop Prometheus  
podman stop claude-prometheus

# View Prometheus logs
podman logs -f claude-prometheus

# Test statusline
/home/marc/.claude/agentic-statusline.sh

# Test Prometheus client directly
python3 ~/agentic-system/intelligent-self-healing/prometheus_metrics.py
```

## What Changed

1. **settings.json**: Added `env` section with OpenTelemetry config
2. **intelligent_statusline.py**: Updated `_get_token_usage()` to query Prometheus
3. **prometheus_metrics.py**: New module to query Prometheus API
4. **Prometheus container**: Runs on localhost:9090, scrapes Claude metrics

## Benefits

✓ **Real-time accuracy**: Matches `/usage` command exactly
✓ **No manual updates**: Metrics update automatically every 3 seconds
✓ **Historical data**: Prometheus stores 7 days of metrics
✓ **Grafana ready**: Can add Grafana dashboards later
✓ **Fallback support**: Still works with manual `weekly_budget.json` if Prometheus down
