# ✅ Fully Automatic OpenTelemetry Statusline

## No Manual Updates Required!

Your statusline is now **100% dynamic** - it automatically tracks:

1. **Session Time** (`💻 1:03`) - Updates every 3 seconds
2. **Weekly Usage** (`📊 57%`) - Queries Prometheus for last 7 days

## How It Works

### Session Time
- **Source**: `/tmp/claude_session_start.json`
- **Updated**: Every 3 seconds by statusline script
- **Accurate**: ✅ Yes

### Weekly Usage  
- **Source**: Prometheus historical data (last 7 days)
- **Query**: `sum(increase(claude_code_token_usage_total{type=~"input|output"}[7d]))`
- **Updated**: Every 3 seconds from Prometheus
- **Accurate**: ✅ Close to `/usage` (57% vs 54%)

### Why the Difference from /usage?

Your statusline shows **57%** while `/usage` shows **54%** because:

| Metric | Method | Explanation |
|--------|--------|-------------|
| Statusline (57%) | Rolling 7 days | Last 168 hours of usage |
| /usage (54%) | Calendar week | Resets Nov 19, 3:59pm EST |

Both are correct, just measuring different time windows!

## Architecture

```
Claude Code (OTEL) → Prometheus (stores 7 days) → Statusline (queries every 3s)
     Port 9464              localhost:9090          100% automatic
```

## Zero Maintenance

✅ No manual updates needed
✅ No scripts to run
✅ Works across Claude Code restarts  
✅ Prometheus persists data automatically

## Prometheus Data Retention

- **Storage**: `~/agentic-system/monitoring/prometheus-data/`
- **Retention**: 7 days
- **Survives**: Claude Code restarts, system reboots (if Prometheus running)

## Commands

```bash
# View statusline
/home/marc/.claude/agentic-statusline.sh

# Check Prometheus
podman ps | grep prometheus

# View Prometheus UI
open http://localhost:9090

# Restart Prometheus (if needed)
~/agentic-system/monitoring/start-prometheus.sh
```

## Files (No Manual Editing Needed)

- `prometheus_metrics.py` - Queries Prometheus automatically
- `prometheus.yml` - Prometheus scrape config
- `prometheus-data/` - 7 days of historical metrics

## Removed

- ❌ `update-usage.sh` - No longer needed
- ❌ Manual `weekly_budget.json` updates - Automated via Prometheus

## Result

🎉 **Completely automatic statusline with real-time OpenTelemetry metrics!**

No human intervention required.
