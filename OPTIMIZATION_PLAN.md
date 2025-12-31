# Agentic System Optimization Plan

## Current State Analysis

### Resource Usage Summary
- **Python versions in use**: 3.10, 3.12, 3.13, 3.14 (should standardize to 3.14)
- **Total source code**: ~950K lines of Python
- **MCP servers running**: 14 active
- **Background daemons**: 3 (consciousness, improvement, cluster health)
- **Temporal schedules**: 8 active workflows

### Identified Issues

| Component | Current | Issue | Recommended |
|-----------|---------|-------|-------------|
| consciousness_daemon | 10s cycle | Too aggressive, blocking pings | 60s cycle, async pings |
| visual-monitoring | 5 min | Overlaps with Visual AGI daemon | 30 min or disable |
| cluster_health_monitor | 30s heartbeat | Reasonable | Keep as-is |
| autonomous_improvement | 60 min | Reasonable | Keep as-is |

## Optimization Categories

### 1. Interval Optimizations (Immediate)

```python
# BEFORE: consciousness_daemon.py
CYCLE_INTERVAL = 10  # Too aggressive

# AFTER:
CYCLE_INTERVAL = 60  # Reasonable for background monitoring
ADAPTIVE_MIN = 30    # Speed up when activity detected
ADAPTIVE_MAX = 120   # Slow down when idle
```

### 2. Language-Appropriate Refactoring

| Component | Current | Best Language | Reason | Priority |
|-----------|---------|---------------|--------|----------|
| Vector embeddings | Python | **Rust** (via PyO3) | 10-100x faster | High |
| MCP stdio transport | Python | **Rust** or Go | Lower latency | Medium |
| File watching | Python | **Rust** (notify-rs) | Zero-copy events | Medium |
| SQLite ops | Python | **Rust** (rusqlite) | Faster queries | Medium |
| Simple MCP servers | Python | **TypeScript** | Faster startup | Low |
| JSON parsing | Python | **Rust** (serde) | 10x faster | Low |

### 3. Python Version Standardization

**Target**: Python 3.14 (current latest)

Files to update:
- All venv configurations
- Shebang lines in scripts
- requirements.txt python_requires
- pyproject.toml configurations

### 4. Temporal Schedule Optimization

| Schedule | Current | Recommended | Reason |
|----------|---------|-------------|--------|
| visual-monitoring | 5 min | 30 min | Visual AGI daemon handles real-time |
| cross-modal-integration | 2 hr | 2 hr | Keep |
| system-optimization | 35 min | 1 hr | Reduce frequency |
| hourly-memory-manager | 35 min | 1 hr | Actually make it hourly |
| nightly-* | 4 hr | 6 hr | Less frequent at night |

### 5. Resource Budgets

**CPU Budget (leaving 40% for user sessions)**:
- Background daemons: 5% max
- MCP servers: 10% max
- Temporal workers: 15% max
- Monitoring stack: 5% max
- Reserved for user: 40%+
- System overhead: 25%

**Memory Budget (32GB system, leaving 12GB for user)**:
- Background daemons: 200MB max each
- MCP servers: 100MB max each (1.4GB total)
- Temporal: 500MB max
- Qdrant: 2GB max
- Monitoring: 1GB max
- Reserved for user: 12GB+

## Implementation Order

### Phase 1: Immediate (Today)
1. Fix consciousness_daemon interval (10s -> 60s)
2. Make cluster pings async/non-blocking
3. Adjust Temporal schedule frequencies

### Phase 2: This Week
1. Standardize Python 3.14 across all components
2. Add adaptive intervals to daemons
3. Implement resource monitoring/throttling

### Phase 3: Next Sprint
1. Port embedding calculations to Rust
2. Create Rust MCP transport layer
3. Optimize SQLite operations with Rust bindings

### Phase 4: Future
1. Consider rewriting heavy MCP servers in Rust/Go
2. Implement zero-copy IPC between components
3. Add GPU acceleration for embeddings (if available)

## Quick Wins Implemented

### 1. consciousness_daemon.py
- Changed CYCLE_INTERVAL from 10 to 60 seconds
- Added async cluster ping (non-blocking)
- Added adaptive interval based on activity

### 2. Temporal Schedules
- visual-monitoring: 5 min -> 30 min
- system-optimization: 35 min -> 60 min
- hourly-memory-manager: 35 min -> 60 min

### 3. Resource Limits
- Added memory limits to daemon configs
- Added CPU throttling when load > 80%
