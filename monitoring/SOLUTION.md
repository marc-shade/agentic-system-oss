# OpenTelemetry Statusline - Final Solution

## ✅ What's Working

1. **Session Time Tracking**: Shows elapsed time (e.g., "💻 10:35")
   - Tracks from `/tmp/claude_session_start.json`
   - Updates dynamically every 3 seconds

2. **Weekly Usage Tracking**: Shows weekly percentage (e.g., "📊 54%")
   - Source: `~/.claude/weekly_budget.json` (manual update)
   - Matches `/usage` command output

3. **Prometheus Integration**: Collects real-time OpenTelemetry metrics
   - Claude Code exports to http://localhost:9464
   - Prometheus scrapes every 3 seconds
   - Stores 7 days of historical data

## ⚠️ Known Limitations

### Session Context Not Accurate
The 📝 metric shows cache creation tokens, which are cumulative and don't represent current context window size. 

**Why**: Claude Code doesn't expose context window data via OpenTelemetry.

**Solution**: Ignore the session % for now, or hide it. Session time is the useful metric.

### Weekly Tracking Requires Manual Update
Prometheus metrics reset when Claude Code restarts, so weekly tracking across sessions requires manual updates.

**How to update**:
```bash
# 1. Run /usage in Claude Code
# 2. Run update script
~/agentic-system/monitoring/update-usage.sh

# 3. Enter the weekly percentage when prompted
```

## 📊 Current Metrics

### From Prometheus (Real-time)
- Token usage by type (input, output, cacheRead, cacheCreation)
- Cost metrics (in USD)
- Active time tracking
- Model usage breakdown

### From Manual Tracking
- Weekly budget percentage (matches `/usage`)
- Weekly token estimate

## 🔧 Maintenance

### Update Weekly Usage
Run this after checking `/usage`:
```bash
~/agentic-system/monitoring/update-usage.sh
```

### Check Prometheus Status
```bash
podman ps | grep prometheus  # Should be running
curl http://localhost:9090   # Should respond
```

### Restart Prometheus
```bash
~/agentic-system/monitoring/start-prometheus.sh
```

## 📈 Future Improvements

1. **Auto-sync weekly usage**: Parse `/usage` command output automatically
2. **Accurate context tracking**: Find a way to track real context window size
3. **Historical session tracking**: Store session totals across restarts
4. **Grafana dashboards**: Visualize metrics over time

## 🎯 Summary

**Original Issue**: Statusline stuck on "idle" instead of tracking session time

**Solution**: 
- ✅ OpenTelemetry enabled in Claude Code
- ✅ Prometheus collecting metrics
- ✅ Statusline shows session time (dynamic)
- ✅ Statusline shows weekly usage (manual update)

**Result**: Weekly counter now works, just needs manual updates from `/usage` command!
