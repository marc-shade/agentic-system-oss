# Agentic System - Cross-Network Cluster Onboarding

**24/7 Autonomous Agentic System - Complete Self-Onboarding for Multiple Platforms**

## 🚀 Claude Code Orchestrated Onboarding (Recommended)

This repository contains **everything** needed to join the agentic cluster network. The onboarding process is orchestrated by Claude Code, which will guide you through authentication and setup via voice interaction.

### AI-Assisted Setup (Claude Code Required)

```bash
# 1. Clone the repository
git clone https://github.com/marc-shade/agentic-system.git
cd agentic-system

# 2. Start Claude Code onboarding (if Claude Code is installed)
chmod +x onboard-with-claude.sh
./onboard-with-claude.sh
```

**Claude Code will**:
- 🎤 Communicate with you via voice
- 🔍 Check which platforms you have installed
- 🤖 **Automatically install** missing infrastructure (Ollama, Temporal, AutoKitteh, Qdrant)
- 📋 Guide you through manual installations if needed (OpenAI Codex, Gemini CLI)
- 🔐 Walk you through authentication for each platform
- ⚙️ Configure MCP servers across all platforms automatically
- ✅ Verify everything is working

**You will**:
- Follow Claude Code's voice instructions
- Install any missing platforms when prompted
- Complete OAuth flows or provide API keys
- Confirm when steps are done

### System Requirements

Your system needs multiple components. Claude Code will **automatically install** most of them:

**AI Platforms** (Primary orchestrators):
- ✅ **Claude Code** - Primary orchestrator (must be installed first)
- ✅ **Ollama** - Local LLM server (auto-installed)
- ⚠️ **OpenAI Codex** - OpenAI's code assistant (optional, manual)
- ⚠️ **Gemini CLI** - Google's AI (auto-installed if npm available)

**Infrastructure** (Auto-installed by Claude Code):
- ✅ **Qdrant** - Vector database for memory
- ✅ **Temporal** - Workflow engine
- ✅ **AutoKitteh** - Event-driven workflows
- ✅ **Monitoring** - Prometheus, Loki, Grafana (optional)

**📖 Complete Requirements**: See `SYSTEM_REQUIREMENTS.md` for detailed component list and installation methods

### Prerequisites

**Required**:
- **Python 3.10+** - [Download](https://www.python.org/)
- **Git** - [Download](https://git-scm.com/)
- **GitHub Account** - [Sign up](https://github.com/join)
- **GitHub Personal Access Token** - [Create one](https://github.com/settings/tokens/new)
  - Scopes: `repo`, `read:org`, `workflow`

**AI Platforms** (all required):
- **Claude Code** - [Download](https://code.claude.com)
- **Ollama** - [Download](https://ollama.ai/download)
- **OpenAI Codex** - [Installation Guide](https://developers.openai.com/codex/cli/)
- **Gemini CLI** - `npm install -g @google/generative-ai-cli`

**Authentication Credentials**:
- OpenAI API key (for Codex) - [Get one](https://platform.openai.com/api-keys)
- Gemini API key (for Gemini CLI) - [Get one](https://aistudio.google.com/app/apikey)
- OR Google Cloud credentials (for Gemini with ADC)

### Manual Setup (Without Claude Code)

If you don't have Claude Code or prefer manual setup:

1. **Check platform status**:
```bash
./check-platforms.sh
```

2. **Install missing platforms** (follow instructions from check script)

3. **Run traditional bootstrap**:
```bash
./bootstrap.sh  # Interactive authentication setup
```

4. **Configure MCP servers**:
```bash
export NODE_ID="your-node-id"
export CLUSTER_REPO="marc-shade/agentic-cluster-comms"
./configure-all-mcps.sh
```

5. **Start cluster daemon**:
```bash
cd cluster-deployment
export GITHUB_PERSONAL_ACCESS_TOKEN="your_token_here"
./start_daemon.sh
```

For detailed manual setup, see: `cluster-deployment/CROSS_NETWORK_DEPLOYMENT_GUIDE.md`

### For Claude Code (Onboarding Guide)

If you are Claude Code orchestrating an onboarding, see: `claude-onboarding-guide.md`

## What's Included

### Bootstrap System
- **`bootstrap.sh`** - Automated setup script with platform detection
- **`requirements.txt`** - All Python dependencies
- **`config-templates/`** - Platform-specific configuration templates
  - `claude-code-config.json` - Claude Code MCP configuration
  - `openai-codex-config.json` - OpenAI Codex MCP configuration
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
- Multi-platform support (Claude Code, OpenAI Codex, Gemini CLI)

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
