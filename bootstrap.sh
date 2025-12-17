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

# Check Node.js (for TypeScript MCP servers)
echo -n "  Node.js.................... "
if command -v node &>/dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}$NODE_VERSION${NC}"
else
    echo -e "${YELLOW}Not found (optional, for ember-mcp)${NC}"
fi

# Check npm
echo -n "  npm........................ "
if command -v npm &>/dev/null; then
    NPM_VERSION=$(npm --version)
    echo -e "${GREEN}$NPM_VERSION${NC}"
else
    echo -e "${YELLOW}Not found (optional, for ember-mcp)${NC}"
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

# Copy MCP servers from OSS repo
echo -e "\n  ${CYAN}Installing MCP servers...${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Enhanced Memory MCP
echo "    Installing enhanced-memory-mcp..."
mkdir -p "$INSTALL_DIR/mcp-servers/enhanced-memory-mcp"
cp -r "$SCRIPT_DIR/mcp-servers/enhanced-memory-mcp/"* "$INSTALL_DIR/mcp-servers/enhanced-memory-mcp/"
echo "    ✓ enhanced-memory-mcp installed"

# Agent Runtime MCP
echo "    Installing agent-runtime-mcp..."
mkdir -p "$INSTALL_DIR/mcp-servers/agent-runtime-mcp"
cp -r "$SCRIPT_DIR/mcp-servers/agent-runtime-mcp/"* "$INSTALL_DIR/mcp-servers/agent-runtime-mcp/"
echo "    ✓ agent-runtime-mcp installed"

# SAFLA MCP (Hybrid Memory)
echo "    Installing safla-mcp..."
mkdir -p "$INSTALL_DIR/mcp-servers/safla-mcp"
cp -r "$SCRIPT_DIR/mcp-servers/safla-mcp/"* "$INSTALL_DIR/mcp-servers/safla-mcp/"
echo "    ✓ safla-mcp installed"

# Research Paper MCP
echo "    Installing research-paper-mcp..."
mkdir -p "$INSTALL_DIR/mcp-servers/research-paper-mcp"
cp -r "$SCRIPT_DIR/mcp-servers/research-paper-mcp/"* "$INSTALL_DIR/mcp-servers/research-paper-mcp/"
echo "    ✓ research-paper-mcp installed"

# Video Transcript MCP
echo "    Installing video-transcript-mcp..."
mkdir -p "$INSTALL_DIR/mcp-servers/video-transcript-mcp"
cp -r "$SCRIPT_DIR/mcp-servers/video-transcript-mcp/"* "$INSTALL_DIR/mcp-servers/video-transcript-mcp/"
echo "    ✓ video-transcript-mcp installed"

# LLM Council MCP
echo "    Installing llm-council-mcp..."
mkdir -p "$INSTALL_DIR/mcp-servers/llm-council-mcp"
cp -r "$SCRIPT_DIR/mcp-servers/llm-council-mcp/"* "$INSTALL_DIR/mcp-servers/llm-council-mcp/"
echo "    ✓ llm-council-mcp installed"

# Ember MCP (TypeScript - requires Node.js)
if command -v npm &>/dev/null; then
    echo "    Installing ember-mcp..."
    mkdir -p "$INSTALL_DIR/mcp-servers/ember-mcp"
    cp -r "$SCRIPT_DIR/mcp-servers/ember-mcp/"* "$INSTALL_DIR/mcp-servers/ember-mcp/"
    cd "$INSTALL_DIR/mcp-servers/ember-mcp"
    npm install --quiet 2>/dev/null || echo "    (npm install will complete on first use)"
    npm run build --quiet 2>/dev/null || echo "    (build will complete on first use)"
    echo "    ✓ ember-mcp installed"
else
    echo "    ⊘ Skipping ember-mcp (Node.js not found)"
fi

# Install MCP server dependencies
echo -e "\n  ${CYAN}Installing MCP server dependencies...${NC}"

# Python MCP servers with requirements.txt
for server in enhanced-memory-mcp agent-runtime-mcp safla-mcp research-paper-mcp video-transcript-mcp llm-council-mcp; do
    if [ -f "$INSTALL_DIR/mcp-servers/$server/requirements.txt" ]; then
        echo "    Installing $server dependencies..."
        cd "$INSTALL_DIR/mcp-servers/$server"
        if [[ "$PKG_MANAGER" == "uv" ]]; then
            uv pip install -r requirements.txt --quiet 2>/dev/null || pip3 install -r requirements.txt -q
        else
            pip3 install -r requirements.txt -q
        fi
    fi
done

echo "    ✓ MCP server dependencies installed"

# Install Python dependencies
echo -e "\n  ${CYAN}Installing Python dependencies...${NC}"
cd "$INSTALL_DIR"

cat > requirements.txt << 'REQS'
# Core MCP Framework (required)
fastmcp>=0.1.0

# Optional: AI SDKs (user provides API keys)
# anthropic>=0.18.0
# openai>=1.0.0
REQS

if [[ "$PKG_MANAGER" == "uv" ]]; then
    uv pip install -r requirements.txt
else
    pip3 install -r requirements.txt
fi
echo "    ✓ Python dependencies installed"

# Initialize databases
echo -e "\n  ${CYAN}Initializing databases...${NC}"

# Run database setup script
bash "$SCRIPT_DIR/scripts/setup-databases.sh"

echo "    ✓ Databases initialized"

# Optional: Start container services
echo ""
echo -e "  ${YELLOW}Optional: Vector search with Qdrant${NC}"
echo "  The system works with SQLite by default. For vector search, run:"
echo "    $CONTAINER_RUNTIME run -d --name qdrant -p 6333:6333 qdrant/qdrant:latest"

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
      "args": ["$INSTALL_DIR/mcp-servers/enhanced-memory-mcp/server.py"]
    },
    "agent-runtime": {
      "command": "python3",
      "args": ["$INSTALL_DIR/mcp-servers/agent-runtime-mcp/server.py"]
    },
    "safla-mcp": {
      "command": "python3",
      "args": ["$INSTALL_DIR/mcp-servers/safla-mcp/server.py"]
    },
    "research-paper-mcp": {
      "command": "python3",
      "args": ["$INSTALL_DIR/mcp-servers/research-paper-mcp/server.py"]
    },
    "video-transcript-mcp": {
      "command": "python3",
      "args": ["$INSTALL_DIR/mcp-servers/video-transcript-mcp/server.py"]
    },
    "llm-council": {
      "command": "python3",
      "args": ["$INSTALL_DIR/mcp-servers/llm-council-mcp/server.py"]
    },
    "sequential-thinking": {
      "command": "npx",
      "args": ["-y", "@anthropics/mcp-server-sequential-thinking"]
    }
  }
}
MCPCONF

# Add ember-mcp if Node.js is available
if command -v node &>/dev/null && [ -d "$INSTALL_DIR/mcp-servers/ember-mcp" ]; then
    python3 << EMBER
import json
with open("/tmp/agentic_mcp_config.json", 'r') as f:
    config = json.load(f)
config["mcpServers"]["ember-mcp"] = {
    "command": "node",
    "args": ["$INSTALL_DIR/mcp-servers/ember-mcp/dist/index.js"]
}
with open("/tmp/agentic_mcp_config.json", 'w') as f:
    json.dump(config, f, indent=2)
EMBER
fi

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

# Install Claude Code customizations
echo -e "\n  ${CYAN}Installing Claude Code customizations...${NC}"

CLAUDE_DIR="$HOME/.claude"
mkdir -p "$CLAUDE_DIR"/{agents,commands,skills,hooks}

# Copy agents
if [ -d "$SCRIPT_DIR/claude-config/agents" ]; then
    echo "    Installing agents..."
    cp -r "$SCRIPT_DIR/claude-config/agents/"* "$CLAUDE_DIR/agents/" 2>/dev/null || true
    echo "    ✓ Agents installed"
fi

# Copy commands (slash commands)
if [ -d "$SCRIPT_DIR/claude-config/commands" ]; then
    echo "    Installing slash commands..."
    cp -r "$SCRIPT_DIR/claude-config/commands/"* "$CLAUDE_DIR/commands/" 2>/dev/null || true
    echo "    ✓ Slash commands installed"
fi

# Copy skills
if [ -d "$SCRIPT_DIR/claude-config/skills" ]; then
    echo "    Installing skills..."
    cp -r "$SCRIPT_DIR/claude-config/skills/"* "$CLAUDE_DIR/skills/" 2>/dev/null || true
    echo "    ✓ Skills installed"
fi

# Copy hooks
if [ -d "$SCRIPT_DIR/claude-config/hooks" ]; then
    echo "    Installing hooks..."
    cp -r "$SCRIPT_DIR/claude-config/hooks/"* "$CLAUDE_DIR/hooks/" 2>/dev/null || true
    chmod +x "$CLAUDE_DIR/hooks/"*.py 2>/dev/null || true
    chmod +x "$CLAUDE_DIR/hooks/"*.sh 2>/dev/null || true
    echo "    ✓ Hooks installed"
fi

echo "    ✓ Claude Code customizations installed"

# Create health check script
cat > "$INSTALL_DIR/scripts/health_check.py" << 'HEALTHPY'
#!/usr/bin/env python3
"""Agentic System Health Check"""

import sys
from pathlib import Path

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
NC = "\033[0m"

def check_file(path, name):
    exists = Path(path).expanduser().exists()
    status = "✓" if exists else "✗"
    color = GREEN if exists else RED
    print(f"  {color}{status}{NC} {name}")
    return exists

def check_import(module, name):
    try:
        __import__(module)
        print(f"  {GREEN}✓{NC} {name}")
        return True
    except ImportError:
        print(f"  {RED}✗{NC} {name}")
        return False

def check_mcp_server(servers, name, display_name):
    if name in servers:
        print(f"  {GREEN}✓{NC} {display_name}")
        return True
    else:
        print(f"  {RED}✗{NC} {display_name}")
        return False

print(f"\n{CYAN}═══════════════════════════════════════════════════════════════{NC}")
print(f"{CYAN}  Agentic System Health Check{NC}")
print(f"{CYAN}═══════════════════════════════════════════════════════════════{NC}\n")

all_ok = True

print("Python Environment:")
all_ok &= check_import("fastmcp", "fastmcp installed")

print("\nMCP Server Files:")
servers_dir = Path.home() / "agentic-system" / "mcp-servers"
required_servers = [
    ("enhanced-memory-mcp", "Enhanced Memory MCP"),
    ("agent-runtime-mcp", "Agent Runtime MCP"),
    ("safla-mcp", "SAFLA MCP"),
    ("research-paper-mcp", "Research Paper MCP"),
    ("video-transcript-mcp", "Video Transcript MCP"),
    ("llm-council-mcp", "LLM Council MCP"),
]
for server_dir, name in required_servers:
    path = servers_dir / server_dir / "server.py"
    all_ok &= check_file(str(path), name)

# Check ember-mcp (TypeScript)
ember_path = servers_dir / "ember-mcp" / "dist" / "index.js"
if ember_path.exists():
    print(f"  {GREEN}✓{NC} Ember MCP (TypeScript)")
else:
    print(f"  {YELLOW}⊘{NC} Ember MCP (optional, requires Node.js)")

print("\nClaude Code Config:")
config_path = Path.home() / ".claude.json"
if config_path.exists():
    import json
    with open(config_path) as f:
        config = json.load(f)
    servers = config.get("mcpServers", {})

    expected_servers = [
        ("enhanced-memory", "enhanced-memory"),
        ("agent-runtime", "agent-runtime"),
        ("safla-mcp", "safla-mcp"),
        ("research-paper-mcp", "research-paper-mcp"),
        ("video-transcript-mcp", "video-transcript-mcp"),
        ("llm-council", "llm-council"),
        ("sequential-thinking", "sequential-thinking"),
    ]
    for server_name, display in expected_servers:
        all_ok &= check_mcp_server(servers, server_name, display)

    # Optional: ember-mcp
    if "ember-mcp" in servers:
        print(f"  {GREEN}✓{NC} ember-mcp")
    else:
        print(f"  {YELLOW}⊘{NC} ember-mcp (optional)")
else:
    print(f"  {RED}✗{NC} ~/.claude.json not found")
    all_ok = False

print("\nClaude Code Customizations:")
claude_dir = Path.home() / ".claude"
customization_dirs = [
    ("agents", "Agents directory"),
    ("commands", "Commands directory"),
    ("skills", "Skills directory"),
    ("hooks", "Hooks directory"),
]
for dir_name, display in customization_dirs:
    path = claude_dir / dir_name
    exists = path.exists() and any(path.iterdir())
    if exists:
        count = len(list(path.glob("*")))
        print(f"  {GREEN}✓{NC} {display} ({count} items)")
    else:
        print(f"  {YELLOW}⊘{NC} {display} (empty)")

print()
if all_ok:
    print(f"{GREEN}✓ System healthy - restart Claude Code to use{NC}")
else:
    print(f"{RED}✗ Some checks failed{NC}")
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
echo -e "  ${CYAN}MCP Servers Installed:${NC}"
echo "    • enhanced-memory     - 4-tier persistent memory with RAG"
echo "    • agent-runtime       - Task management and orchestration"
echo "    • safla-mcp           - High-performance hybrid memory"
echo "    • research-paper-mcp  - arXiv/Semantic Scholar integration"
echo "    • video-transcript-mcp- YouTube transcript extraction"
echo "    • llm-council         - Multi-LLM deliberation system"
echo "    • sequential-thinking - Deep reasoning chains (npx)"
if command -v npm &>/dev/null && [ -d "$INSTALL_DIR/mcp-servers/ember-mcp" ]; then
echo "    • ember-mcp           - Production quality enforcement"
fi
echo ""
echo -e "  ${CYAN}Claude Code Customizations:${NC}"
echo "    • Agents: code-reviewer, debugger, explorer"
echo "    • Commands: memory-save, memory-search, check-todos, add-to-todos, quick-review"
echo "    • Skills: mcp-builder, skill-creator"
echo "    • Hooks: pre-tool-use, post-tool-use"
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
echo "  4. Try a slash command:"
echo "     /memory-save     # Save to knowledge graph"
echo "     /quick-review    # Code review"
echo ""
echo -e "  ${GREEN}The agentic system is ready!${NC}"
echo ""
