# Convex Deployment Complete - macpro51

**Date**: December 4, 2025
**Status**: Operational

---

## Services Running

| Service | Port | Status | URL |
|---------|------|--------|-----|
| Convex Backend | 3210 | Healthy | http://macpro51.local:3210 |
| Convex HTTP Actions | 3211 | Healthy | http://macpro51.local:3211 |
| Convex Dashboard | 6791 | Running | http://macpro51.local:6791 |

## Credentials

```bash
# Add to .env or export
export CONVEX_URL="http://127.0.0.1:3210"
export CONVEX_ADMIN_KEY="convex-self-hosted|0151d95174e8f04d4cb67383c9b48ac2d91c0e31d5c23ba3cd5fceeb9370911f26bcfe5355"
```

## Benchmark Results

| Metric | Value | Comparison to Polling |
|--------|-------|----------------------|
| Query latency (avg) | **1.3ms** | 46,826x faster than 60s polling |
| Query latency (p50) | 0.7ms | - |
| Query latency (p99) | 24.0ms | - |
| Mutation latency (avg) | 132ms | Includes DB write |

## Cluster Nodes Registered

1. **orchestrator** (mac-studio) - coordination, memory, dispatch
2. **builder** (macpro51) - compilation, docker, testing, linux
3. **researcher** (macbook-air) - research, analysis, documentation

## Schema Deployed

### Tables
- `nodes` - Node status and heartbeats
- `tasks` - Task queue with ACID transactions
- `messages` - Inter-node messaging

### Functions
- `nodes:list` - Get all nodes (reactive)
- `nodes:listOnline` - Get online nodes (reactive)
- `nodes:clusterHealth` - Cluster health summary (reactive)
- `nodes:heartbeat` - Send node heartbeat (mutation)
- `tasks:listPending` - Pending tasks (reactive)
- `tasks:create` - Create task (mutation)
- `tasks:claim` - Atomic task claim (mutation)

## Usage

### Send Heartbeat
```bash
cd /mnt/agentic-system/services/convex-heartbeat
python3 heartbeat_client.py --node builder --send-heartbeat
```

### Monitor Cluster
```bash
python3 heartbeat_client.py --subscribe
```

### Run Benchmark
```bash
python3 heartbeat_client.py --benchmark
```

### Access Dashboard
```
http://macpro51.local:6791
```

## Container Management

```bash
# Check status
podman ps --filter "name=convex"

# View logs
podman logs -f convex_backend_1

# Restart
cd /mnt/agentic-system/services/convex
podman-compose restart

# Stop
podman-compose down

# Start
podman-compose up -d
```

## Next Steps

1. **Integration**: Connect other nodes to send heartbeats
2. **Replace Polling**: Migrate `cluster-memory-sync.py` to use Convex subscriptions
3. **Dashboard Integration**: Add Convex data to Kutira dashboard
4. **PostgreSQL**: Consider upgrading to Postgres for production workloads

## Files

```
/mnt/agentic-system/services/convex-heartbeat/
├── convex/
│   ├── schema.ts       # Database schema
│   ├── nodes.ts        # Node queries/mutations
│   ├── tasks.ts        # Task queries/mutations
│   └── _generated/     # Auto-generated types
├── heartbeat_client.py # Python client
├── .env.local          # Credentials
├── convex.json         # Convex config
└── package.json        # Node dependencies
```
