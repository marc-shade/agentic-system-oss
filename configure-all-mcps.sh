#!/bin/bash
# Configure MCP servers across all AI platforms
# This script is run by Claude Code during onboarding

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🔧 Configuring MCP Servers Across All Platforms"
echo "==============================================="
echo ""

# Get absolute path to this repository
REPO_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Node configuration (should be set before running this script)
if [ -z "$NODE_ID" ]; then
    echo -e "${YELLOW}⚠ NODE_ID not set, using hostname${NC}"
    NODE_ID=$(hostname | tr '[:upper:]' '[:lower:]' | tr ' ' '-')
fi

if [ -z "$CLUSTER_REPO" ]; then
    CLUSTER_REPO="marc-shade/agentic-cluster-comms"
fi

if [ -z "$POLL_INTERVAL" ]; then
    POLL_INTERVAL=30
fi

echo "Configuration:"
echo "  Node ID: $NODE_ID"
echo "  Cluster Repo: $CLUSTER_REPO"
echo "  Repository: $REPO_DIR"
echo ""

# 1. Configure Claude Code MCP
echo "1. Configuring Claude Code MCP..."
echo "-----------------------------------"

CLAUDE_CONFIG="$HOME/.claude.json"

if [ -f "$CLAUDE_CONFIG" ]; then
    echo -e "${YELLOW}⚠ Existing Claude Code config found, backing up...${NC}"
    cp "$CLAUDE_CONFIG" "$CLAUDE_CONFIG.backup.$(date +%Y%m%d_%H%M%S)"
fi

# Use template and replace placeholders
sed "s|{{INSTALL_DIR}}|$REPO_DIR|g" "$REPO_DIR/config-templates/claude-code-config.json" | \
sed "s|{{NODE_ID}}|$NODE_ID|g" | \
sed "s|{{CLUSTER_REPO}}|$CLUSTER_REPO|g" | \
sed "s|{{POLL_INTERVAL}}|$POLL_INTERVAL|g" | \
sed "s|{{GITHUB_TOKEN}}|${GITHUB_PERSONAL_ACCESS_TOKEN}|g" \
> "$CLAUDE_CONFIG"

echo -e "${GREEN}✓ Claude Code MCP configured${NC}"
echo "  Config: $CLAUDE_CONFIG"

# 2. Configure Ollama (if installed)
if command -v ollama &> /dev/null; then
    echo ""
    echo "2. Configuring Ollama..."
    echo "------------------------"

    OLLAMA_CONFIG="$HOME/.ollama/config.json"
    mkdir -p "$HOME/.ollama"

    # Use template and replace placeholders
    if [ -f "$REPO_DIR/config-templates/ollama-config.json" ]; then
        sed "s|{{INSTALL_DIR}}|$REPO_DIR|g" "$REPO_DIR/config-templates/ollama-config.json" | \
        sed "s|{{NODE_ID}}|$NODE_ID|g" | \
        sed "s|{{OLLAMA_HOST}}|${OLLAMA_HOST:-http://localhost:11434}|g" \
        > "$OLLAMA_CONFIG"

        echo -e "${GREEN}✓ Ollama configured${NC}"
        echo "  Config: $OLLAMA_CONFIG"
    else
        echo -e "${YELLOW}⚠ Ollama template not found, skipping${NC}"
    fi
else
    echo ""
    echo "2. Ollama not installed, skipping..."
fi

# 3. Configure OpenAI Codex (if installed)
if command -v codex &> /dev/null; then
    echo ""
    echo "3. Configuring OpenAI Codex..."
    echo "------------------------------"

    # Note: OpenAI Codex may not support MCP yet
    # This is a placeholder for future compatibility
    CODEX_CONFIG="$HOME/.codex/mcp.json"
    mkdir -p "$HOME/.codex"

    if [ -f "$REPO_DIR/config-templates/openai-codex-config.json" ]; then
        sed "s|{{INSTALL_DIR}}|$REPO_DIR|g" "$REPO_DIR/config-templates/openai-codex-config.json" | \
        sed "s|{{NODE_ID}}|$NODE_ID|g" \
        > "$CODEX_CONFIG"

        echo -e "${GREEN}✓ OpenAI Codex configured${NC}"
        echo "  Config: $CODEX_CONFIG"
        echo -e "  ${YELLOW}Note: MCP support in Codex may be limited${NC}"
    else
        echo -e "${YELLOW}⚠ Codex MCP template not found${NC}"
        echo "  Codex may not yet support MCP protocol"
    fi
else
    echo ""
    echo "3. OpenAI Codex not installed, skipping..."
fi

# 4. Configure Gemini CLI (if installed)
if command -v gemini &> /dev/null; then
    echo ""
    echo "4. Configuring Gemini CLI..."
    echo "----------------------------"

    # Gemini CLI may use different config location
    GEMINI_CONFIG="$HOME/.gemini/mcp.json"
    mkdir -p "$HOME/.gemini"

    if [ -f "$REPO_DIR/config-templates/gemini-cli-config.json" ]; then
        sed "s|{{INSTALL_DIR}}|$REPO_DIR|g" "$REPO_DIR/config-templates/gemini-cli-config.json" | \
        sed "s|{{NODE_ID}}|$NODE_ID|g" \
        > "$GEMINI_CONFIG"

        echo -e "${GREEN}✓ Gemini CLI configured${NC}"
        echo "  Config: $GEMINI_CONFIG"
        echo -e "  ${YELLOW}Note: MCP support in Gemini may be limited${NC}"
    else
        echo -e "${YELLOW}⚠ Gemini MCP template not found${NC}"
        echo "  Gemini may not yet support MCP protocol"
    fi
else
    echo ""
    echo "4. Gemini CLI not installed, skipping..."
fi

echo ""
echo "========================================="
echo -e "${GREEN}✓ MCP Configuration Complete${NC}"
echo "========================================="
echo ""
echo "Summary:"
echo "  ✓ Claude Code: MCP fully configured"

if command -v ollama &> /dev/null; then
    echo "  ✓ Ollama: Configuration created"
else
    echo "  ⊘ Ollama: Not installed"
fi

if command -v codex &> /dev/null; then
    echo "  ⚠ Codex: Configuration created (MCP support may be limited)"
else
    echo "  ⊘ Codex: Not installed"
fi

if command -v gemini &> /dev/null; then
    echo "  ⚠ Gemini: Configuration created (MCP support may be limited)"
else
    echo "  ⊘ Gemini: Not installed"
fi

echo ""
echo "📝 Next Steps:"
echo "  1. Restart Claude Code to load new MCP configuration"
echo "  2. Verify MCP servers are running: claude-code status"
echo "  3. Test cluster communication: ./test-cluster-connection.sh"
echo ""
