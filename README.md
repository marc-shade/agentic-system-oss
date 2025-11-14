# Agentic System - Cross-Network Cluster Onboarding

**24/7 Autonomous Agentic System - Node Deployment & Cluster Communication**

## Quick Start

This repository contains everything needed to join the agentic cluster network.

### Prerequisites

- Python 3.10+
- Git
- GitHub account
- GitHub Personal Access Token

### Onboarding New Node

1. **Clone this repository**:
```bash
git clone https://github.com/marc-shade/agentic-system.git
cd agentic-system
```

2. **Follow the deployment guide**:
- See: `cluster-deployment/CROSS_NETWORK_DEPLOYMENT_GUIDE.md`
- Complete guide for cross-network node setup
- Works across different networks (no VPN required)

3. **Start your daemon**:
```bash
cd cluster-deployment
export GITHUB_PERSONAL_ACCESS_TOKEN="your_token_here"
./start_daemon.sh
```

## What's Included

### Cluster Deployment (`cluster-deployment/`)

**Core Daemon**:
- `github_node_daemon.py` - Background daemon for task execution
- `submit_cluster_task.py` - Helper for submitting tasks
- `check_daemon_status.sh` - Monitoring script
- `start_daemon.sh` - Daemon startup script

**Documentation**:
- `CROSS_NETWORK_DEPLOYMENT_GUIDE.md` - Complete deployment guide
- `DEPLOYMENT_COMPLETE.md` - Status and next steps
- `SYSTEM_OPERATIONAL.md` - Live system status

**Features**:
- Cross-network communication (no VPN required)
- GitHub as secure message broker
- Task execution (health checks, code execution, node cloning)
- Complete audit trail via git history

## Architecture

```
GitHub (Message Broker)
marc-shade/agentic-cluster-comms
  ├── tasks/{node-id}     ← Incoming tasks
  ├── results/{node-id}   ← Execution results
  └── heartbeat/          ← Node health

Your Node
  ├── Daemon (polls GitHub every 30s)
  ├── Task execution
  └── Result submission
```

## Security

- HTTPS transport (GitHub infrastructure)
- Private repository access only
- GitHub PAT authentication
- Complete git history for audit trail
- Rate limiting via GitHub API

## Communication

- Round-trip latency: ~60-120 seconds
- Poll interval: 30 seconds (configurable)
- GitHub API rate limit: 5000 req/hour
- Task types: health_check, code_execution, clone_node, custom

## Support

- Issues: https://github.com/marc-shade/agentic-system/issues
- Documentation: See `cluster-deployment/` directory
- Main repo: https://github.com/marc-shade/agentic-system

## License

Private - Authorized collaborators only
