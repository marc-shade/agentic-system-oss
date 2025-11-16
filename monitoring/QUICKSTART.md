# Quick Start: OpenTelemetry Monitoring for Claude Code

## ✅ Setup Complete!

Your Claude Code statusline is now configured to use **real-time usage metrics from OpenTelemetry** via Prometheus!

## What's Running

- **Prometheus**: Container `claude-prometheus` on `localhost:9090`
  - Status: ✅ Running
  - Scrapes metrics every 3 seconds
  
- **Statusline Integration**: ✅ Configured
  - Queries Prometheus for real usage data
  - Falls back to `weekly_budget.json` if needed

## ⚠️ Important: Restart Required

**Claude Code needs to restart** to start exporting OpenTelemetry metrics.

The current session was started before telemetry was enabled, so metrics won't flow until you restart Claude Code.

### To Activate:

1. **Exit this Claude session** (Ctrl+D or type `exit`)
2. **Start a new session**:
   ```bash
   claude
   ```

3. **Verify metrics are flowing** (in a separate terminal):
   ```bash
   # Check Claude is exposing metrics
   curl -s http://localhost:9464/metrics | grep claude_code | head -5
   
   # Should show lines like:
   # claude_code_token_usage_total{type="input"} 1234
   # claude_code_cost_usage_total 0.05
   ```

4. **Check your statusline** - it should now show accurate, real-time usage!

## Commands

```bash
# View Prometheus UI
open http://127.0.0.1:9090   # (or visit in browser)

# Stop Prometheus
podman stop claude-prometheus

# Start Prometheus
~/agentic-system/monitoring/start-prometheus.sh

# Test statusline
/home/marc/.claude/agentic-statusline.sh

# Test Prometheus client
python3 ~/agentic-system/intelligent-self-healing/prometheus_metrics.py
```

## What Changed

1. **`~/.claude/settings.json`**: Added OpenTelemetry configuration
   - `CLAUDE_CODE_ENABLE_TELEMETRY=1`
   - `OTEL_METRICS_EXPORTER=prometheus`

2. **Statusline Updated**: Now queries Prometheus for real metrics
   - Session usage: From actual token counters
   - Weekly usage: From cost metrics
   - Falls back to manual `weekly_budget.json` if Prometheus unavailable

3. **Prometheus Running**: Scraping Claude Code metrics every 3 seconds

## Troubleshooting

### Metrics not showing after restart?
```bash
# 1. Verify Claude is exporting on port 9464
ss -tuln | grep 9464

# 2. Check Prometheus is scraping
curl -s "http://localhost:9090/api/v1/query?query=claude_code_token_usage_total"

# 3. Check Prometheus logs
podman logs claude-prometheus | tail -20
```

### Prometheus not running?
```bash
~/agentic-system/monitoring/start-prometheus.sh
```

## Next Steps

After restarting Claude Code, your statusline will display:
- ✅ **Accurate session usage** matching `/usage` command
- ✅ **Real-time weekly budget** tracking
- ✅ **Dynamic updates** every 3-5 seconds

See `~/agentic-system/monitoring/README.md` for full documentation.
