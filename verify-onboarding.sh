#!/bin/bash
# Verify Agentic System Onboarding - Complete Health Check
# Run this after onboarding to ensure everything is working

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "🔍 Agentic System - Onboarding Verification"
echo "==========================================="
echo ""

# Track results
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNINGS=0

# Helper functions
check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    CHECKS_FAILED=$((CHECKS_FAILED + 1))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    CHECKS_WARNINGS=$((CHECKS_WARNINGS + 1))
}

check_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# === 1. Prerequisites ===
echo -e "${BLUE}1. Prerequisites${NC}"
echo "━━━━━━━━━━━━━━━━"

# Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
        check_pass "Python $PYTHON_VERSION"
    else
        check_fail "Python $PYTHON_VERSION (need 3.10+)"
    fi
else
    check_fail "Python not found"
fi

# Git
if command -v git &> /dev/null; then
    GIT_VERSION=$(git --version | awk '{print $3}')
    check_pass "Git $GIT_VERSION"
else
    check_fail "Git not found"
fi

# Node.js (optional)
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    check_pass "Node.js $NODE_VERSION"
else
    check_warn "Node.js not found (needed for Gemini CLI)"
fi

echo ""

# === 2. AI Platforms ===
echo -e "${BLUE}2. AI Platforms${NC}"
echo "━━━━━━━━━━━━━━━━"

# Claude Code
if command -v claude-code &> /dev/null; then
    check_pass "Claude Code installed"
else
    check_fail "Claude Code not found"
fi

# Ollama
if command -v ollama &> /dev/null; then
    OLLAMA_VERSION=$(ollama --version 2>/dev/null || echo "unknown")
    check_pass "Ollama $OLLAMA_VERSION"

    # Check if Ollama is running
    if curl -s http://localhost:11434 > /dev/null 2>&1; then
        check_pass "  Ollama service running (port 11434)"
    else
        check_warn "  Ollama service not running (run 'ollama serve')"
    fi
else
    check_warn "Ollama not found (optional)"
fi

# OpenAI Codex
if command -v codex &> /dev/null; then
    check_pass "OpenAI Codex installed"

    # Check auth status
    if codex login status &> /dev/null; then
        check_pass "  Codex authenticated"
    else
        check_warn "  Codex not authenticated"
    fi
else
    check_warn "OpenAI Codex not found (optional)"
fi

# Gemini CLI
if command -v gemini &> /dev/null; then
    check_pass "Gemini CLI installed"

    # Check for credentials
    if [ -n "$GEMINI_API_KEY" ] || [ -f "$HOME/.gemini/.env" ] || [ -n "$GOOGLE_CLOUD_PROJECT" ]; then
        check_pass "  Gemini credentials configured"
    else
        check_warn "  Gemini credentials not configured"
    fi
else
    check_warn "Gemini CLI not found (optional)"
fi

echo ""

# === 3. Core Infrastructure ===
echo -e "${BLUE}3. Core Infrastructure${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━"

# Qdrant
if curl -s http://localhost:6333 > /dev/null 2>&1; then
    QDRANT_VERSION=$(curl -s http://localhost:6333 | jq -r '.version' 2>/dev/null || echo "running")
    check_pass "Qdrant running (port 6333)"
else
    check_fail "Qdrant not running (port 6333)"
fi

# Temporal
if command -v temporal &> /dev/null; then
    TEMPORAL_VERSION=$(temporal --version 2>/dev/null | head -1 || echo "unknown")
    check_pass "Temporal CLI installed"

    # Check if Temporal server is running
    if curl -s http://localhost:8233 > /dev/null 2>&1; then
        check_pass "  Temporal server running (port 8233)"
    else
        check_warn "  Temporal server not running (run 'temporal server start-dev')"
    fi
else
    check_fail "Temporal not found"
fi

# AutoKitteh
if command -v ak &> /dev/null; then
    AK_VERSION=$(ak version 2>/dev/null || echo "unknown")
    check_pass "AutoKitteh installed"

    # Check if AutoKitteh is running
    if curl -s http://localhost:9980 > /dev/null 2>&1; then
        check_pass "  AutoKitteh running (port 9980)"
    else
        check_warn "  AutoKitteh not running (run 'ak up')"
    fi
else
    check_fail "AutoKitteh not found"
fi

echo ""

# === 4. Monitoring Stack (Optional) ===
echo -e "${BLUE}4. Monitoring Stack (Optional)${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Prometheus
if command -v prometheus &> /dev/null; then
    check_pass "Prometheus installed"

    if curl -s http://localhost:9700/-/healthy > /dev/null 2>&1; then
        check_pass "  Prometheus running (port 9700)"
    else
        check_info "  Prometheus not running (optional)"
    fi
else
    check_info "Prometheus not installed (optional)"
fi

# Loki
if command -v loki &> /dev/null; then
    check_pass "Loki installed"

    if curl -s http://localhost:9900/ready > /dev/null 2>&1; then
        check_pass "  Loki running (port 9900)"
    else
        check_info "  Loki not running (optional)"
    fi
else
    check_info "Loki not installed (optional)"
fi

# Grafana
if command -v grafana-server &> /dev/null; then
    check_pass "Grafana installed"

    if curl -s http://localhost:9500/api/health > /dev/null 2>&1; then
        check_pass "  Grafana running (port 9500)"
    else
        check_info "  Grafana not running (optional)"
    fi
else
    check_info "Grafana not installed (optional)"
fi

echo ""

# === 5. Python Dependencies ===
echo -e "${BLUE}5. Python Dependencies${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━"

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$REPO_DIR/requirements.txt" ]; then
    # Check key packages
    REQUIRED_PACKAGES=("psutil" "GitPython")
    ALL_INSTALLED=true

    for package in "${REQUIRED_PACKAGES[@]}"; do
        if python3 -c "import $package" 2>/dev/null; then
            check_pass "$package"
        else
            check_fail "$package (run 'pip3 install -r requirements.txt')"
            ALL_INSTALLED=false
        fi
    done

    if $ALL_INSTALLED; then
        check_info "Run 'pip3 list | grep -E \"psutil|GitPython|mcp|qdrant\"' to see all packages"
    fi
else
    check_warn "requirements.txt not found"
fi

echo ""

# === 6. MCP Configuration ===
echo -e "${BLUE}6. MCP Configuration${NC}"
echo "━━━━━━━━━━━━━━━━━━━━"

# Claude Code MCP
if [ -f "$HOME/.claude.json" ]; then
    check_pass "Claude Code MCP config exists (~/.claude.json)"

    # Check for expected MCP servers
    if grep -q "enhanced-memory" "$HOME/.claude.json" 2>/dev/null; then
        check_pass "  enhanced-memory-mcp configured"
    fi

    if grep -q "agent-runtime" "$HOME/.claude.json" 2>/dev/null; then
        check_pass "  agent-runtime-mcp configured"
    fi
else
    check_fail "Claude Code MCP config missing (run './configure-all-mcps.sh')"
fi

# Ollama config
if [ -f "$HOME/.ollama/config.json" ]; then
    check_pass "Ollama config exists"
else
    check_warn "Ollama config not found (optional)"
fi

echo ""

# === 7. Cluster Configuration ===
echo -e "${BLUE}7. Cluster Configuration${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━"

# GitHub Token
if [ -n "$GITHUB_PERSONAL_ACCESS_TOKEN" ]; then
    check_pass "GitHub token configured"
else
    check_warn "GitHub token not in environment (needed for cluster communication)"
fi

# Node ID
if [ -n "$NODE_ID" ]; then
    check_pass "Node ID set: $NODE_ID"
else
    NODE_ID_DEFAULT=$(hostname | tr '[:upper:]' '[:lower:]' | tr ' ' '-')
    check_warn "NODE_ID not set (will default to: $NODE_ID_DEFAULT)"
fi

# Cluster daemon
if [ -f "$REPO_DIR/cluster-deployment/daemon.pid" ]; then
    PID=$(cat "$REPO_DIR/cluster-deployment/daemon.pid")
    if ps -p $PID > /dev/null 2>&1; then
        check_pass "Cluster daemon running (PID: $PID)"
    else
        check_warn "Cluster daemon not running (stale PID file)"
    fi
else
    check_warn "Cluster daemon not started (run 'cd cluster-deployment && ./start_daemon.sh')"
fi

echo ""

# === 8. GitHub Connectivity ===
echo -e "${BLUE}8. GitHub Connectivity${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━"

if [ -n "$GITHUB_PERSONAL_ACCESS_TOKEN" ]; then
    # Test GitHub API
    if curl -s -H "Authorization: token $GITHUB_PERSONAL_ACCESS_TOKEN" \
            https://api.github.com/user > /dev/null 2>&1; then
        check_pass "GitHub API accessible"

        # Check cluster repo access
        if curl -s -H "Authorization: token $GITHUB_PERSONAL_ACCESS_TOKEN" \
                https://api.github.com/repos/marc-shade/agentic-cluster-comms > /dev/null 2>&1; then
            check_pass "Cluster repo accessible (marc-shade/agentic-cluster-comms)"
        else
            check_warn "Cluster repo not accessible (check permissions)"
        fi
    else
        check_fail "GitHub API not accessible (check token)"
    fi
else
    check_warn "GitHub token not configured (skipping connectivity test)"
fi

echo ""

# === Summary ===
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BLUE}Verification Summary${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

TOTAL_CHECKS=$((CHECKS_PASSED + CHECKS_FAILED + CHECKS_WARNINGS))

echo -e "${GREEN}✓ Passed:   $CHECKS_PASSED${NC}"
echo -e "${RED}✗ Failed:   $CHECKS_FAILED${NC}"
echo -e "${YELLOW}⚠ Warnings: $CHECKS_WARNINGS${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""

# Overall status
if [ $CHECKS_FAILED -eq 0 ]; then
    if [ $CHECKS_WARNINGS -eq 0 ]; then
        echo -e "${GREEN}🎉 Perfect! All checks passed.${NC}"
        echo ""
        echo "Your node is fully onboarded and ready to join the cluster!"
        echo ""
        echo "Next steps:"
        echo "  1. Start services if not running:"
        echo "     - Temporal: temporal server start-dev &"
        echo "     - AutoKitteh: ak up &"
        echo "     - Cluster daemon: cd cluster-deployment && ./start_daemon.sh"
        echo ""
        echo "  2. Submit a test health check:"
        echo "     cd cluster-deployment && ./submit_cluster_task.sh"
        echo ""
        exit 0
    else
        echo -e "${YELLOW}✓ Good! Core components working, some warnings.${NC}"
        echo ""
        echo "Your node is operational but some optional components"
        echo "or configurations could be improved. Review warnings above."
        echo ""
        exit 0
    fi
else
    echo -e "${RED}✗ Issues Found - Please Fix${NC}"
    echo ""
    echo "Your node has $CHECKS_FAILED critical issues that need to be resolved."
    echo "Review the failures above and:"
    echo ""
    echo "  1. Install missing components:"
    echo "     cd install-scripts && ./install-all.sh"
    echo ""
    echo "  2. Configure authentication:"
    echo "     ./bootstrap.sh"
    echo ""
    echo "  3. Configure MCP servers:"
    echo "     ./configure-all-mcps.sh"
    echo ""
    echo "  4. Re-run this verification:"
    echo "     ./verify-onboarding.sh"
    echo ""
    exit 1
fi
