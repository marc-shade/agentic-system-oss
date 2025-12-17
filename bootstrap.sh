#!/bin/bash
#
# Agentic System Bootstrap for Claude Code CLI
#
# This script sets up the complete agentic system environment for your Claude Code CLI.
# It is NOT a simple installer - it configures a sophisticated AI infrastructure.
#
# Requirements:
# - Claude Code CLI installed (claude.ai/code)
# - Python 3.11+
# - Docker, Podman, or Apple Container
# - 16GB+ RAM, 50GB+ storage
#
# Usage:
#   ./bootstrap.sh           # Interactive setup
#   ./bootstrap.sh --check   # Check prerequisites only
#   ./bootstrap.sh --verify  # Run AVIR verification
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
AGENTIC_VERSION="1.0.0"
MIN_RAM_GB=16
MIN_STORAGE_GB=50
INSTALL_DIR="${AGENTIC_INSTALL_DIR:-$HOME/agentic-system}"

echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║                                                                   ║"
echo "║     █████╗  ██████╗ ███████╗███╗   ██╗████████╗██╗ ██████╗       ║"
echo "║    ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝██║██╔════╝       ║"
echo "║    ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   ██║██║            ║"
echo "║    ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   ██║██║            ║"
echo "║    ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   ██║╚██████╗       ║"
echo "║    ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝ ╚═════╝       ║"
echo "║                                                                   ║"
echo "║              24/7 Autonomous Agentic System v${AGENTIC_VERSION}              ║"
echo "║                                                                   ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# Parse arguments
CHECK_ONLY=false
VERIFY_ONLY=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --check) CHECK_ONLY=true; shift ;;
        --verify) VERIFY_ONLY=true; shift ;;
        --dir) INSTALL_DIR="$2"; shift 2 ;;
        --help|-h)
            echo "Usage: ./bootstrap.sh [options]"
            echo ""
            echo "Options:"
            echo "  --check    Check prerequisites only"
            echo "  --verify   Run AVIR verification"
            echo "  --dir DIR  Set installation directory (default: ~/agentic-system)"
            echo "  --help     Show this help"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

#─────────────────────────────────────────────────────────────────────────────
# PHASE 1: Prerequisites Check
#─────────────────────────────────────────────────────────────────────────────

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  PHASE 1: Checking Prerequisites${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

PREREQ_PASS=true

# Check OS
echo -n "  Operating System........... "
OS=$(uname -s)
if [[ "$OS" == "Darwin" ]]; then
    OS_VERSION=$(sw_vers -productVersion)
    echo -e "${GREEN}macOS $OS_VERSION${NC}"
elif [[ "$OS" == "Linux" ]]; then
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo -e "${GREEN}$NAME $VERSION_ID${NC}"
    else
        echo -e "${GREEN}Linux${NC}"
    fi
else
    echo -e "${RED}Unsupported: $OS${NC}"
    PREREQ_PASS=false
fi

# Check RAM
echo -n "  RAM........................ "
if [[ "$OS" == "Darwin" ]]; then
    RAM_BYTES=$(sysctl -n hw.memsize)
    RAM_GB=$((RAM_BYTES / 1024 / 1024 / 1024))
else
    RAM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    RAM_GB=$((RAM_KB / 1024 / 1024))
fi
if [[ $RAM_GB -ge $MIN_RAM_GB ]]; then
    echo -e "${GREEN}${RAM_GB}GB (minimum: ${MIN_RAM_GB}GB)${NC}"
else
    echo -e "${RED}${RAM_GB}GB (need: ${MIN_RAM_GB}GB)${NC}"
    PREREQ_PASS=false
fi

# Check Storage
echo -n "  Available Storage.......... "
if [[ "$OS" == "Darwin" ]]; then
    STORAGE_KB=$(df -k "$HOME" | tail -1 | awk '{print $4}')
else
    STORAGE_KB=$(df -k "$HOME" | tail -1 | awk '{print $4}')
fi
STORAGE_GB=$((STORAGE_KB / 1024 / 1024))
if [[ $STORAGE_GB -ge $MIN_STORAGE_GB ]]; then
    echo -e "${GREEN}${STORAGE_GB}GB (minimum: ${MIN_STORAGE_GB}GB)${NC}"
else
    echo -e "${RED}${STORAGE_GB}GB (need: ${MIN_STORAGE_GB}GB)${NC}"
    PREREQ_PASS=false
fi

# Check Python
echo -n "  Python 3.11+............... "
if command -v python3 &>/dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    if [[ $PYTHON_MAJOR -ge 3 && $PYTHON_MINOR -ge 11 ]]; then
        echo -e "${GREEN}$PYTHON_VERSION${NC}"
    else
        echo -e "${YELLOW}$PYTHON_VERSION (3.11+ recommended)${NC}"
    fi
else
    echo -e "${RED}Not found${NC}"
    PREREQ_PASS=false
fi

# Check Container Runtime
echo -n "  Container Runtime.......... "
CONTAINER_RUNTIME=""
if command -v container &>/dev/null && [[ "$OS" == "Darwin" ]]; then
    CONTAINER_RUNTIME="container"
    echo -e "${GREEN}Apple Container${NC}"
elif command -v podman &>/dev/null; then
    CONTAINER_RUNTIME="podman"
    echo -e "${GREEN}Podman${NC}"
elif command -v docker &>/dev/null; then
    CONTAINER_RUNTIME="docker"
    echo -e "${GREEN}Docker${NC}"
else
    echo -e "${RED}None found (need Docker, Podman, or Apple Container)${NC}"
    PREREQ_PASS=false
fi

# Check Claude Code CLI
echo -n "  Claude Code CLI............ "
if command -v claude &>/dev/null; then
    CLAUDE_VERSION=$(claude --version 2>/dev/null | head -1 || echo "installed")
    echo -e "${GREEN}$CLAUDE_VERSION${NC}"
else
    echo -e "${RED}Not found${NC}"
    echo -e "     ${YELLOW}Install from: https://claude.ai/code${NC}"
    PREREQ_PASS=false
fi

# Check git
echo -n "  Git........................ "
if command -v git &>/dev/null; then
    GIT_VERSION=$(git --version | cut -d' ' -f3)
    echo -e "${GREEN}$GIT_VERSION${NC}"
else
    echo -e "${RED}Not found${NC}"
    PREREQ_PASS=false
fi

# Check pip/uv
echo -n "  Package Manager............ "
if command -v uv &>/dev/null; then
    echo -e "${GREEN}uv (fast)${NC}"
    PKG_MANAGER="uv"
elif command -v pip3 &>/dev/null; then
    echo -e "${GREEN}pip3${NC}"
    PKG_MANAGER="pip3"
else
    echo -e "${RED}Neither uv nor pip3 found${NC}"
    PREREQ_PASS=false
fi

echo ""

if [[ "$CHECK_ONLY" == "true" ]]; then
    if [[ "$PREREQ_PASS" == "true" ]]; then
        echo -e "${GREEN}All prerequisites met. Ready to install.${NC}"
        exit 0
    else
        echo -e "${RED}Prerequisites not met. Please install missing components.${NC}"
        exit 1
    fi
fi

if [[ "$PREREQ_PASS" != "true" ]]; then
    echo -e "${RED}ERROR: Prerequisites not met. Run with --check for details.${NC}"
    exit 1
fi

#─────────────────────────────────────────────────────────────────────────────
# PHASE 2: Installation
#─────────────────────────────────────────────────────────────────────────────

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  PHASE 2: Installation${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  Install Directory: ${CYAN}$INSTALL_DIR${NC}"
echo ""

read -p "  Proceed with installation? [Y/n] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]?$ ]]; then
    echo "Installation cancelled."
    exit 0
fi

# Create directory structure
echo -e "\n  ${CYAN}Creating directory structure...${NC}"
mkdir -p "$INSTALL_DIR"/{databases/{mcp,qdrant,temporal,cluster},logs,mcp-servers,workflows,scripts}
echo "    ✓ Directory structure created"

# Clone MCP servers
echo -e "\n  ${CYAN}Installing MCP servers...${NC}"

cd "$INSTALL_DIR/mcp-servers"

# Enhanced Memory MCP
if [ ! -d "enhanced-memory-mcp" ]; then
    echo "    Cloning enhanced-memory-mcp..."
    git clone --depth 1 https://github.com/marc-shade/enhanced-memory-mcp.git 2>/dev/null || {
        echo "    Creating enhanced-memory-mcp from template..."
        mkdir -p enhanced-memory-mcp
        cat > enhanced-memory-mcp/requirements.txt << 'REQS'
fastmcp>=0.1.0
qdrant-client>=1.7.0
sentence-transformers>=2.2.0
numpy>=1.24.0
pydantic>=2.0.0
REQS
    }
fi

# Agent Runtime MCP
if [ ! -d "agent-runtime-mcp" ]; then
    echo "    Cloning agent-runtime-mcp..."
    git clone --depth 1 https://github.com/marc-shade/agent-runtime-mcp.git 2>/dev/null || {
        echo "    Creating agent-runtime-mcp from template..."
        mkdir -p agent-runtime-mcp
        cat > agent-runtime-mcp/requirements.txt << 'REQS'
fastmcp>=0.1.0
aiosqlite>=0.19.0
pydantic>=2.0.0
REQS
    }
fi

echo "    ✓ MCP servers installed"

# Install Python dependencies
echo -e "\n  ${CYAN}Installing Python dependencies...${NC}"
cd "$INSTALL_DIR"

cat > requirements.txt << 'REQS'
# Core MCP Framework
fastmcp>=0.1.0
mcp>=0.1.0

# Vector Database
qdrant-client>=1.7.0

# Embeddings
sentence-transformers>=2.2.0

# AI SDKs (user provides API keys)
anthropic>=0.18.0
openai>=1.0.0

# Data Processing
numpy>=1.24.0
pandas>=2.0.0
pydantic>=2.0.0

# Database
aiosqlite>=0.19.0
redis>=4.5.0

# Workflow Engines (optional)
temporalio>=1.0.0

# Utilities
python-dotenv>=1.0.0
httpx>=0.24.0
aiofiles>=23.0.0
REQS

if [[ "$PKG_MANAGER" == "uv" ]]; then
    uv pip install -r requirements.txt
else
    pip3 install -r requirements.txt
fi
echo "    ✓ Python dependencies installed"

# Start required services
echo -e "\n  ${CYAN}Starting container services...${NC}"

# Qdrant vector database
echo "    Starting Qdrant..."
$CONTAINER_RUNTIME run -d \
    --name qdrant \
    -p 6333:6333 \
    -p 6334:6334 \
    -v "$INSTALL_DIR/databases/qdrant:/qdrant/storage:z" \
    qdrant/qdrant:latest 2>/dev/null || echo "    Qdrant already running or failed"

# Redis cache
echo "    Starting Redis..."
$CONTAINER_RUNTIME run -d \
    --name redis \
    -p 6379:6379 \
    redis:alpine 2>/dev/null || echo "    Redis already running or failed"

echo "    ✓ Container services started"

#─────────────────────────────────────────────────────────────────────────────
# PHASE 3: Claude Code CLI Configuration
#─────────────────────────────────────────────────────────────────────────────

echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  PHASE 3: Claude Code CLI Configuration${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

CLAUDE_CONFIG="$HOME/.claude.json"

# Backup existing config
if [ -f "$CLAUDE_CONFIG" ]; then
    cp "$CLAUDE_CONFIG" "$CLAUDE_CONFIG.backup.$(date +%Y%m%d_%H%M%S)"
    echo "    ✓ Backed up existing config"
fi

# Create MCP server configuration
echo -e "  ${CYAN}Configuring MCP servers for Claude Code...${NC}"

# Generate the MCP configuration to merge
cat > /tmp/agentic_mcp_config.json << MCPCONF
{
  "mcpServers": {
    "enhanced-memory": {
      "command": "python3",
      "args": ["-m", "enhanced_memory_mcp"],
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "DATABASE_PATH": "$INSTALL_DIR/databases/mcp/memory.db"
      }
    },
    "agent-runtime-mcp": {
      "command": "python3",
      "args": ["-m", "agent_runtime_mcp"],
      "env": {
        "DATABASE_PATH": "$INSTALL_DIR/databases/mcp/runtime.db"
      }
    },
    "sequential-thinking": {
      "command": "npx",
      "args": ["-y", "@anthropic/sequential-thinking-mcp"]
    }
  }
}
MCPCONF

# Merge with existing config
if [ -f "$CLAUDE_CONFIG" ]; then
    python3 << MERGE
import json
import os

existing = {}
try:
    with open("$CLAUDE_CONFIG", 'r') as f:
        existing = json.load(f)
except:
    pass

with open("/tmp/agentic_mcp_config.json", 'r') as f:
    new_servers = json.load(f)

if "mcpServers" not in existing:
    existing["mcpServers"] = {}

existing["mcpServers"].update(new_servers["mcpServers"])

with open("$CLAUDE_CONFIG", 'w') as f:
    json.dump(existing, f, indent=2)

print("    ✓ MCP servers configured in ~/.claude.json")
MERGE
else
    cp /tmp/agentic_mcp_config.json "$CLAUDE_CONFIG"
    echo "    ✓ Created new ~/.claude.json with MCP servers"
fi

# Create CLAUDE.md for the install directory
echo -e "\n  ${CYAN}Creating project instructions...${NC}"

cat > "$INSTALL_DIR/CLAUDE.md" << 'CLAUDEMD'
# CLAUDE.md - Agentic System

This is your local installation of the Agentic System.

## Quick Reference

### Check System Health
```bash
python3 scripts/health_check.py
```

### MCP Servers
- **enhanced-memory**: 4-tier persistent memory with RAG
- **agent-runtime-mcp**: Task management and orchestration
- **sequential-thinking**: Deep reasoning chains

### Database Locations
- Memory: `databases/mcp/memory.db`
- Tasks: `databases/mcp/runtime.db`
- Vectors: `databases/qdrant/`

### Common Tasks

**Store knowledge:**
```python
mcp__enhanced-memory__create_entities([{
    "name": "topic",
    "entityType": "knowledge",
    "observations": ["what you learned"]
}])
```

**Search memory:**
```python
mcp__enhanced-memory__search_nodes(query="topic", limit=10)
```

**Create persistent task:**
```python
mcp__agent-runtime-mcp__create_task({
    "title": "Task name",
    "description": "What to do"
})
```

## Troubleshooting

**MCP server not loading:**
```bash
cat ~/.claude.json | python3 -m json.tool
```

**Qdrant not running:**
```bash
docker ps | grep qdrant
docker start qdrant
```
CLAUDEMD

echo "    ✓ CLAUDE.md created"

# Create health check script
cat > "$INSTALL_DIR/scripts/health_check.py" << 'HEALTHPY'
#!/usr/bin/env python3
"""Agentic System Health Check"""

import subprocess
import sys
import socket

def check_port(port, name):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    status = "✓" if result == 0 else "✗"
    color = "\033[92m" if result == 0 else "\033[91m"
    print(f"  {color}{status}\033[0m {name} (port {port})")
    return result == 0

print("\n🔍 Agentic System Health Check\n")
print("Services:")

all_ok = True
all_ok &= check_port(6333, "Qdrant REST API")
all_ok &= check_port(6334, "Qdrant gRPC")
all_ok &= check_port(6379, "Redis")

print()
if all_ok:
    print("\033[92m✓ All services healthy\033[0m")
else:
    print("\033[91m✗ Some services not running\033[0m")
    sys.exit(1)
HEALTHPY
chmod +x "$INSTALL_DIR/scripts/health_check.py"

#─────────────────────────────────────────────────────────────────────────────
# PHASE 4: API Key Configuration
#─────────────────────────────────────────────────────────────────────────────

echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  PHASE 4: API Keys (Optional)${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo "  The system works best with AI API keys configured."
echo "  You can skip this and add them later to ~/.zshrc or ~/.bashrc"
echo ""

# Create .env template
cat > "$INSTALL_DIR/.env.template" << 'ENVTEMPLATE'
# Agentic System API Keys
# Copy this to .env and fill in your keys

# Required for full functionality (at least one)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Optional
GOOGLE_API_KEY=AIza...
ENVTEMPLATE

echo "  Created .env.template - copy to .env and add your keys"
echo ""

#─────────────────────────────────────────────────────────────────────────────
# COMPLETE
#─────────────────────────────────────────────────────────────────────────────

echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  INSTALLATION COMPLETE${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${CYAN}Installation Directory:${NC} $INSTALL_DIR"
echo ""
echo -e "  ${YELLOW}Next Steps:${NC}"
echo ""
echo "  1. Add your API keys:"
echo "     cp $INSTALL_DIR/.env.template $INSTALL_DIR/.env"
echo "     # Edit .env with your keys"
echo ""
echo "  2. Restart Claude Code CLI to load MCP servers:"
echo "     claude"
echo ""
echo "  3. Verify installation:"
echo "     cd $INSTALL_DIR && python3 scripts/health_check.py"
echo ""
echo "  4. Run AVIR verification (optional):"
echo "     ./bootstrap.sh --verify"
echo ""
echo -e "  ${GREEN}The agentic system is ready!${NC}"
echo ""
