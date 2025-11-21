# Deprecated: Calibration-Based Weekly Token Tracking

**Status**: Obsolete as of 2025-11-16
**Reason**: Replaced by direct Claude Code metrics endpoint (port 9464)

## Why This Was Deprecated

The calibration-based approach to tracking weekly token usage was fundamentally flawed:

1. **Prometheus tracks cumulative totals** since startup, not weekly usage
2. **No historical checkpoint** - We don't know what the counter was at the start of the user's weekly billing period
3. **Manual calibration required** - User had to manually sync with `/usage` output
4. **Inaccurate results** - Showed 135% when actual was 63%

## The Solution

Claude Code exposes its own Prometheus metrics on **port 9464** with:
- `claude_code_cost_usage_total` - Session cost in USD (accurate!)
- `claude_code_token_usage_total` - Token usage by type and model
- Session-specific accurate data

**New approach**:
- Query `http://localhost:9464/metrics` for authoritative session data
- Show session cost and context usage on statusline
- Remove weekly tracking (user uses `/usage` command for that)

## Files in This Directory

- `statusline-calibrate.py` - Interactive calibration tool (no longer needed)
- `weekly_usage_baseline.json` - Calibration checkpoint file (no longer needed)

## Migration

**Old Code**:
```python
# Query Prometheus (port 9090) for cumulative counters
# Try to calculate weekly usage with manual calibration
# Result: Inaccurate (135% vs actual 63%)
```

**New Code**:
```python
# Query Claude Code's own metrics (port 9464)
import requests
response = requests.get('http://localhost:9464/metrics')
# Parse claude_code_cost_usage_total
# Result: Accurate session data!
```

See `intelligent-self-healing/prometheus_metrics.py` for the new implementation.
