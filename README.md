# Agentic System - Cross-Network Cluster Onboarding

**24/7 Autonomous Agentic System - Complete Self-Onboarding for Multiple Platforms**

## 🚀 Automated Bootstrap (Recommended)

This repository contains **everything** needed to join the agentic cluster network. The bootstrap script automatically detects your CLI platform and sets up your complete node environment.

### One-Command Setup

```bash
# Clone and bootstrap in one go
git clone https://github.com/marc-shade/agentic-system.git
cd agentic-system
chmod +x bootstrap.sh
./bootstrap.sh
```

The bootstrap script will:
- ✅ Auto-detect your CLI platform (Claude Code, OpenAI Code, or Gemini CLI)
- ✅ Verify all prerequisites
- ✅ Set up GitHub authentication
- ✅ Install Python dependencies
- ✅ Install and configure MCP servers
- ✅ Configure platform-specific settings
- ✅ Install and start the cluster daemon
- ✅ Create system services for auto-start

### Supported Platforms

- **Claude Code** - Anthropic's official CLI
- **OpenAI Code** - OpenAI's code assistant (via pip)
- **Gemini CLI** - Google's Gemini command-line tool

The bootstrap automatically detects which platform you have installed and configures accordingly.

### Prerequisites

- **Python 3.10+** - [Download](https://www.python.org/)
- **Git** - [Download](https://git-scm.com/)
- **GitHub Account** - [Sign up](https://github.com/join)
- **GitHub Personal Access Token** - [Create one](https://github.com/settings/tokens/new)
  - Required scopes: `repo`, `read:org`, `workflow`
- **One of**: Claude Code, OpenAI Code, or Gemini CLI

### Manual Setup (If Bootstrap Fails)

If the automatic bootstrap doesn't work on your system:

1. **Clone repository**:
```bash
git clone https://github.com/marc-shade/agentic-system.git
cd agentic-system
```

2. **Install Python dependencies**:
```bash
pip3 install -r requirements.txt
```

3. **Configure MCP servers**:
- Choose template from `config-templates/` for your platform
- Copy to appropriate location (`~/.claude.json`, `~/.openai.json`, etc.)
- Replace placeholders with your actual values

4. **Start daemon**:
```bash
cd cluster-deployment
export GITHUB_PERSONAL_ACCESS_TOKEN="your_token_here"
./start_daemon.sh
```

For detailed manual setup, see: `cluster-deployment/CROSS_NETWORK_DEPLOYMENT_GUIDE.md`

## What's Included

### Bootstrap System
- **`bootstrap.sh`** - Automated setup script with platform detection
- **`requirements.txt`** - All Python dependencies
- **`config-templates/`** - Platform-specific configuration templates
  - `claude-code-config.json` - Claude Code MCP configuration
  - `openai-code-config.json` - OpenAI Code MCP configuration
  - `gemini-cli-config.json` - Gemini CLI MCP configuration

### MCP Servers (`mcp-servers/`)
- **`enhanced-memory-mcp/`** - 4-tier memory architecture with RAG
- **`agent-runtime-mcp/`** - Persistent task and goal management
- Installation scripts for automated setup
- See `mcp-servers/README.md` for details

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
- Multi-platform support (Claude Code, OpenAI Code, Gemini CLI)

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
