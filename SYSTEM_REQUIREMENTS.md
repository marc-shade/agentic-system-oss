# Agentic System - Complete Requirements

This document lists ALL components required for a fully functional autonomous agentic node.

## Platform Requirements (AI Assistants)

### 1. Claude Code (Primary Orchestrator) - REQUIRED
- **Purpose**: Primary AI orchestrator for onboarding and operation
- **Installation**: https://code.claude.com
- **Verification**: `claude-code --version`
- **Platform**: macOS, Linux, Windows
- **Notes**: Must be installed first - orchestrates everything else

### 2. Ollama (Local LLM Server)
- **Purpose**: Local language model inference
- **Installation**:
  - macOS: `brew install ollama`
  - Linux: `curl -fsSL https://ollama.ai/install.sh | sh`
  - Windows: Download from https://ollama.ai/download
- **Verification**: `ollama --version`
- **Default Models**: llama2, codellama, llava
- **Port**: 11434
- **Auto-start**: `ollama serve` (background service)

### 3. OpenAI Codex CLI
- **Purpose**: OpenAI code generation and analysis
- **Installation**: Follow OpenAI's installation guide
- **Verification**: `codex --version`
- **Authentication**: OAuth with ChatGPT account OR API key
- **Config Location**: `~/.codex/auth.json`

### 4. Gemini CLI
- **Purpose**: Google AI capabilities
- **Installation**: `npm install -g @google/generative-ai-cli`
- **Verification**: `gemini --version`
- **Authentication**: Google Cloud ADC OR API key
- **Config Location**: `~/.gemini/.env`
- **Prerequisites**: Node.js 18+ and npm

## Infrastructure Components

### 5. Temporal (Workflow Engine)
- **Purpose**: Long-running autonomous workflows with state persistence
- **Installation**:
  ```bash
  # macOS
  brew install temporal

  # Linux
  curl -sSf https://temporal.download/cli.sh | sh
  ```
- **Verification**: `temporal --version`
- **Ports**: 7233 (gRPC), 8233 (Web UI)
- **Database**: Embedded SQLite (production uses PostgreSQL)
- **Required For**: Multi-day autonomous operations

### 6. AutoKitteh (Event-Driven Workflows)
- **Purpose**: Event-driven automation and real-time orchestration
- **Installation**:
  ```bash
  # macOS/Linux
  curl -fsSL https://get.autokitteh.com | sh
  ```
- **Verification**: `ak version`
- **Port**: 9980
- **Required For**: Event-triggered workflows, GitHub webhooks

### 7. Qdrant (Vector Database)
- **Purpose**: Vector embeddings for semantic memory
- **Installation**:
  ```bash
  # macOS
  brew install qdrant

  # Docker (all platforms)
  docker run -p 6333:6333 qdrant/qdrant
  ```
- **Verification**: `curl http://localhost:6333`
- **Port**: 6333
- **Storage**: `./databases/qdrant/`
- **Required For**: enhanced-memory-mcp semantic search

### 8. n8n (Visual Workflow Automation)
- **Purpose**: Visual workflow design and automation
- **Installation**: `npm install -g n8n`
- **Verification**: `n8n --version`
- **Port**: 5678
- **Prerequisites**: Node.js 18+
- **Optional**: For visual workflow creation

## Monitoring Stack (Production Recommended)

### 9. Prometheus (Metrics Collection)
- **Purpose**: Time-series metrics database
- **Installation**:
  ```bash
  # macOS
  brew install prometheus

  # Linux
  wget https://github.com/prometheus/prometheus/releases/download/v2.47.0/prometheus-2.47.0.linux-amd64.tar.gz
  tar xvfz prometheus-*.tar.gz
  ```
- **Verification**: `prometheus --version`
- **Port**: 9700
- **Retention**: 30 days
- **Storage**: ~100MB/day

### 10. Loki (Log Aggregation)
- **Purpose**: Centralized log collection and querying
- **Installation**:
  ```bash
  # macOS
  brew install loki

  # Docker
  docker run -p 9900:9900 grafana/loki:latest
  ```
- **Verification**: `loki --version`
- **Ports**: 9900 (HTTP), 9901 (gRPC)
- **Retention**: 7 days

### 11. Grafana (Visualization Dashboard)
- **Purpose**: Unified monitoring dashboard
- **Installation**:
  ```bash
  # macOS
  brew install grafana

  # Linux
  wget https://dl.grafana.com/oss/release/grafana-10.2.0.linux-amd64.tar.gz
  tar -zxvf grafana-*.tar.gz
  ```
- **Verification**: `grafana-server --version`
- **Port**: 9500
- **Default Credentials**: admin/admin (change on first login)

## Development Tools

### 12. Python 3.10+
- **Purpose**: MCP servers, intelligent agents, automation
- **Installation**:
  - macOS: `brew install python@3.11`
  - Linux: `apt install python3.11` or `yum install python311`
- **Verification**: `python3 --version`
- **Required Packages**: See `requirements.txt`

### 13. Node.js 18+ and npm
- **Purpose**: JavaScript-based tools (Gemini CLI, n8n)
- **Installation**: https://nodejs.org/
- **Verification**: `node --version && npm --version`
- **Required For**: Gemini CLI, n8n, some MCP servers

### 14. Git
- **Purpose**: Version control and cluster communication
- **Installation**:
  - macOS: `xcode-select --install` or `brew install git`
  - Linux: `apt install git` or `yum install git`
- **Verification**: `git --version`
- **Required For**: GitHub-based cluster communication

### 15. Docker (Optional but Recommended)
- **Purpose**: Container-based service deployment
- **Installation**: https://docs.docker.com/get-docker/
- **Verification**: `docker --version`
- **Use Cases**: Qdrant, Loki, isolated testing

## MCP Servers (Bundled with Repository)

These are included in the agentic-system repository and installed automatically:

### 16. enhanced-memory-mcp
- **Purpose**: 4-tier memory architecture with RAG
- **Port**: 8101
- **Dependencies**: Python 3.10+, Qdrant
- **Storage**: `./databases/cluster/`

### 17. agent-runtime-mcp
- **Purpose**: Persistent task and goal management
- **Port**: 8102
- **Dependencies**: Python 3.10+, SQLite
- **Storage**: `./databases/agent_runtime.db`

### 18. sequential-thinking
- **Purpose**: Deep reasoning with chain-of-thought
- **Dependencies**: Python 3.10+
- **No external services required**

### 19. voice-mode
- **Purpose**: TTS/STT integration for voice communication
- **Dependencies**: Python 3.10+, Audio libraries
- **Optional**: Requires microphone and speakers

### 20. arduino-surface (Optional)
- **Purpose**: Physical hardware interface (LCD, LEDs, sensors)
- **Port**: 8200
- **Dependencies**: Python 3.10+, pyserial, Arduino UNO
- **Hardware**: Arduino UNO R3 with specific circuit

### 21. ember-mcp
- **Purpose**: Production-only policy enforcement
- **Dependencies**: Python 3.10+
- **Purpose**: Quality guardian and conscience keeper

## System Requirements

### Minimum Hardware
- **CPU**: 4 cores (8 recommended)
- **RAM**: 8GB (16GB recommended)
- **Storage**: 50GB free space
  - 20GB for databases (Temporal, Qdrant, memory)
  - 10GB for monitoring logs (Prometheus, Loki)
  - 10GB for models (Ollama)
  - 10GB for workspace and temp files

### Operating System
- **macOS**: 12.0+ (Monterey or later)
- **Linux**: Ubuntu 20.04+, Fedora 35+, Debian 11+
- **Windows**: 10/11 with WSL2 (Linux subsystem required)

### Network Requirements
- **Internet**: Required for GitHub API, model downloads
- **Ports**: Must not be blocked by firewall:
  - 6333 (Qdrant)
  - 7233, 8233 (Temporal)
  - 8101, 8102, 8200 (MCP servers)
  - 9500 (Grafana)
  - 9700 (Prometheus)
  - 9900, 9901 (Loki)
  - 9980 (AutoKitteh)
  - 11434 (Ollama)

## Authentication Requirements

### Required Credentials
1. **GitHub Personal Access Token**
   - Scopes: `repo`, `read:org`, `workflow`
   - Create at: https://github.com/settings/tokens/new
   - Used for cluster communication

2. **OpenAI API Key** (for Codex)
   - Get from: https://platform.openai.com/api-keys
   - OR use ChatGPT OAuth (recommended)

3. **Gemini API Key** OR **Google Cloud Credentials**
   - API Key: https://aistudio.google.com/app/apikey
   - Google Cloud: `gcloud auth application-default login`

### Optional Credentials
4. **Anthropic API Key** (if using Claude API directly)
5. **Custom Model Endpoints** (if using private LLM hosts)

## Installation Order (Recommended)

This is the order Claude Code will follow during onboarding:

1. **Prerequisites** (if missing)
   - Python 3.10+
   - Node.js 18+
   - Git
   - Docker (optional)

2. **AI Platforms**
   - Claude Code (must already be installed to run onboarding)
   - Ollama
   - OpenAI Codex
   - Gemini CLI

3. **Core Infrastructure**
   - Qdrant (required for memory)
   - Temporal (required for workflows)
   - AutoKitteh (required for events)

4. **Monitoring** (optional but recommended)
   - Prometheus
   - Loki
   - Grafana

5. **Repository Setup**
   - Clone agentic-system
   - Install Python dependencies (`pip install -r requirements.txt`)
   - Configure MCP servers
   - Start cluster daemon

6. **Verification**
   - Test all services
   - Verify connectivity
   - Submit test health check

## Quick Reference: Installation Commands

```bash
# macOS Complete Setup
brew install python@3.11 node git ollama temporal qdrant prometheus loki grafana
npm install -g @google/generative-ai-cli n8n
curl -fsSL https://get.autokitteh.com | sh

# Linux (Ubuntu/Debian) Complete Setup
apt update && apt install -y python3.11 python3-pip nodejs npm git docker.io
curl -fsSL https://ollama.ai/install.sh | sh
curl -sSf https://temporal.download/cli.sh | sh
curl -fsSL https://get.autokitteh.com | sh
npm install -g @google/generative-ai-cli n8n
docker run -d -p 6333:6333 qdrant/qdrant
docker run -d -p 9900:9900 grafana/loki:latest

# Python Dependencies (all platforms)
pip3 install -r requirements.txt
```

## Verification Checklist

After installation, verify all components:

```bash
# AI Platforms
claude-code --version      # Should show Claude Code version
ollama --version           # Should show Ollama version
codex --version            # Should show Codex version
gemini --version           # Should show Gemini CLI version

# Infrastructure
temporal --version         # Should show Temporal version
ak version                 # Should show AutoKitteh version
curl localhost:6333        # Should return Qdrant API response

# Monitoring (optional)
prometheus --version       # Should show Prometheus version
loki --version            # Should show Loki version
grafana-server --version  # Should show Grafana version

# Development Tools
python3 --version         # Should be 3.10+
node --version            # Should be 18+
npm --version             # Should show npm version
git --version             # Should show git version
```

## Post-Installation

After all components are installed:

1. **Configure Authentication**: Run `./bootstrap.sh` to set up credentials
2. **Start Services**: Core services start automatically, monitoring optional
3. **Configure MCP**: Run `./configure-all-mcps.sh` to set up MCP across all platforms
4. **Start Daemon**: `cd cluster-deployment && ./start_daemon.sh`
5. **Verify System**: `./verify-onboarding.sh` (checks all components)

## Minimal vs Full Installation

### Minimal (Development/Testing)
- Claude Code
- Python 3.10+
- Git
- GitHub Token
- MCP servers only

### Recommended (Production Node)
- All AI Platforms (Claude Code, Ollama, Codex, Gemini)
- All Infrastructure (Temporal, AutoKitteh, Qdrant)
- Monitoring Stack (Prometheus, Loki, Grafana)
- Full cluster integration

### Optional Components
- n8n (visual workflow design)
- Docker (container isolation)
- Arduino Surface (physical hardware interface)

## Troubleshooting

See `TROUBLESHOOTING.md` for common installation issues and solutions.

## Support

- Issues: https://github.com/marc-shade/agentic-system/issues
- Documentation: `cluster-deployment/` directory
- Main repo: https://github.com/marc-shade/agentic-system
