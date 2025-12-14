# Scripts - Context

**Location:** `/mnt/agentic-system/scripts/`
**Purpose:** System management, deployment, monitoring scripts

## Categories

### Deployment
- `deploy-to-node.sh` - Deploy components to cluster nodes
- `sync-cluster.sh` - Synchronize across nodes

### Monitoring
- `health-check.sh` - System health verification
- `service-status.sh` - Service state monitoring

### Database
- `backup-databases.sh` - Backup SQLite, Qdrant
- `restore-databases.sh` - Restore from backup

### Maintenance
- `cleanup-logs.sh` - Log rotation
- `prune-docker.sh` - Docker cleanup

## Common Operations

**Deploy to Cluster:**
```bash
./deploy-to-node.sh [node] [component]
# Nodes: macpro51, mac-studio, macbook-air
```

**Check Health:**
```bash
./health-check.sh
# Returns: RAID, services, memory, disk
```

**Backup:**
```bash
./backup-databases.sh
# Outputs to: /mnt/agentic-system/backups/
```

## Script Conventions

- All scripts use `#!/bin/bash`
- Error handling: `set -euo pipefail`
- Logging to stdout/stderr
- Exit codes: 0=success, 1=error

## Adding Scripts

1. Follow naming: `verb-noun.sh`
2. Add header documentation
3. Use error handling
4. Test locally before deploying
