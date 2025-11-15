#!/bin/bash
# Agentic System Bootstrap
# Auto-detects CLI platform and sets up complete node environment

set -e  # Exit on error

echo "🚀 Agentic System Bootstrap"
echo "================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Detect CLI platform
detect_platform() {
    echo "Detecting CLI platform..."

    if command -v claude-code &> /dev/null; then
        echo -e "${GREEN}✓ Claude Code detected${NC}"
        export CLI_PLATFORM="claude-code"
        export CLI_CONFIG="$HOME/.claude.json"
        return 0
    fi

    if command -v codex &> /dev/null; then
        echo -e "${GREEN}✓ OpenAI Codex detected${NC}"
        export CLI_PLATFORM="openai-codex"
        export CLI_CONFIG="$HOME/.openai.json"
        return 0
    fi

    if command -v gemini &> /dev/null; then
        echo -e "${GREEN}✓ Gemini CLI detected${NC}"
        export CLI_PLATFORM="gemini-cli"
        export CLI_CONFIG="$HOME/.gemini.json"
        return 0
    fi

    echo -e "${RED}✗ No supported CLI platform detected${NC}"
    echo ""
    echo "Supported platforms:"
    echo "  - Claude Code: https://code.claude.com"
    echo "  - OpenAI Codex: https://github.com/openai/openai-codex"
    echo "  - Gemini CLI: (install via npm)"
    exit 1
}

# Check prerequisites
check_prerequisites() {
    echo ""
    echo "Checking prerequisites..."

    # Check Python 3
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}✗ Python 3 not found${NC}"
        echo "Install Python 3.10+ from https://www.python.org/"
        exit 1
    fi

    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo -e "${GREEN}✓ Python $PYTHON_VERSION${NC}"

    # Check Git
    if ! command -v git &> /dev/null; then
        echo -e "${RED}✗ Git not found${NC}"
        echo "Install Git from https://git-scm.com/"
        exit 1
    fi

    GIT_VERSION=$(git --version | cut -d' ' -f3)
    echo -e "${GREEN}✓ Git $GIT_VERSION${NC}"

    # Check for GitHub CLI (optional but helpful)
    if command -v gh &> /dev/null; then
        echo -e "${GREEN}✓ GitHub CLI available${NC}"
    else
        echo -e "${YELLOW}⚠ GitHub CLI not found (optional)${NC}"
        echo "  Install from: https://cli.github.com/"
    fi
}

# Get GitHub credentials
setup_github_auth() {
    echo ""
    echo "GitHub Authentication Setup"
    echo "============================="

    if [ -z "$GITHUB_PERSONAL_ACCESS_TOKEN" ]; then
        echo ""
        echo "You need a GitHub Personal Access Token with these scopes:"
        echo "  - repo (full control)"
        echo "  - read:org"
        echo "  - workflow"
        echo ""
        echo "Create one at: https://github.com/settings/tokens/new"
        echo ""
        read -p "Enter your GitHub Personal Access Token: " -s GITHUB_PAT
        echo ""
        export GITHUB_PERSONAL_ACCESS_TOKEN="$GITHUB_PAT"
    else
        echo -e "${GREEN}✓ GITHUB_PERSONAL_ACCESS_TOKEN already set${NC}"
    fi

    # Save to shell profile for persistence
    if [[ "$SHELL" == *"zsh"* ]]; then
        PROFILE="$HOME/.zshrc"
    else
        PROFILE="$HOME/.bashrc"
    fi

    if ! grep -q "GITHUB_PERSONAL_ACCESS_TOKEN" "$PROFILE" 2>/dev/null; then
        echo "" >> "$PROFILE"
        echo "# Agentic System - GitHub Authentication" >> "$PROFILE"
        echo "export GITHUB_PERSONAL_ACCESS_TOKEN=\"$GITHUB_PERSONAL_ACCESS_TOKEN\"" >> "$PROFILE"
        echo -e "${GREEN}✓ Added to $PROFILE${NC}"
    fi
}

# Get node configuration
setup_node_config() {
    echo ""
    echo "Node Configuration"
    echo "=================="

    # Get node ID
    if [ -z "$NODE_ID" ]; then
        DEFAULT_NODE_ID=$(hostname | tr '[:upper:]' '[:lower:]' | tr ' ' '-')
        read -p "Enter Node ID [$DEFAULT_NODE_ID]: " NODE_ID
        NODE_ID=${NODE_ID:-$DEFAULT_NODE_ID}
    fi

    export NODE_ID
    echo -e "${GREEN}✓ Node ID: $NODE_ID${NC}"

    # Get GitHub repo
    if [ -z "$CLUSTER_REPO" ]; then
        read -p "Enter cluster communication repo [marc-shade/agentic-cluster-comms]: " CLUSTER_REPO
        CLUSTER_REPO=${CLUSTER_REPO:-marc-shade/agentic-cluster-comms}
    fi

    export CLUSTER_REPO
    echo -e "${GREEN}✓ Cluster repo: $CLUSTER_REPO${NC}"

    # Poll interval
    if [ -z "$POLL_INTERVAL" ]; then
        read -p "Enter poll interval in seconds [30]: " POLL_INTERVAL
        POLL_INTERVAL=${POLL_INTERVAL:-30}
    fi

    export POLL_INTERVAL
    echo -e "${GREEN}✓ Poll interval: $POLL_INTERVAL seconds${NC}"
}

# Install Python dependencies
install_python_deps() {
    echo ""
    echo "Installing Python dependencies..."

    if [ -f "requirements.txt" ]; then
        python3 -m pip install --upgrade pip
        python3 -m pip install -r requirements.txt
        echo -e "${GREEN}✓ Python dependencies installed${NC}"
    else
        echo -e "${YELLOW}⚠ No requirements.txt found, skipping${NC}"
    fi
}

# Install MCP servers
install_mcp_servers() {
    echo ""
    echo "Installing MCP servers..."

    if [ -d "mcp-servers" ]; then
        cd mcp-servers

        # Run each installation script
        for install_script in */install.sh; do
            if [ -f "$install_script" ]; then
                echo "Installing $(dirname $install_script)..."
                bash "$install_script"
            fi
        done

        cd ..
        echo -e "${GREEN}✓ MCP servers installed${NC}"
    else
        echo -e "${YELLOW}⚠ No mcp-servers directory found, skipping${NC}"
    fi
}

# Configure MCP for detected platform
configure_mcp() {
    echo ""
    echo "Configuring MCP for $CLI_PLATFORM..."

    TEMPLATE_FILE="config-templates/${CLI_PLATFORM}-config.json"

    if [ -f "$TEMPLATE_FILE" ]; then
        # Copy template to appropriate location
        mkdir -p "$(dirname $CLI_CONFIG)"

        # Replace placeholders in template
        sed "s|{{NODE_ID}}|$NODE_ID|g" "$TEMPLATE_FILE" | \
        sed "s|{{CLUSTER_REPO}}|$CLUSTER_REPO|g" | \
        sed "s|{{POLL_INTERVAL}}|$POLL_INTERVAL|g" | \
        sed "s|{{GITHUB_TOKEN}}|$GITHUB_PERSONAL_ACCESS_TOKEN|g" \
        > "$CLI_CONFIG"

        echo -e "${GREEN}✓ MCP configuration created at $CLI_CONFIG${NC}"
    else
        echo -e "${YELLOW}⚠ No template found for $CLI_PLATFORM${NC}"
        echo "You'll need to configure MCP manually"
    fi
}

# Install daemon
install_daemon() {
    echo ""
    echo "Installing cluster daemon..."

    if [ ! -d "cluster-deployment" ]; then
        echo -e "${RED}✗ cluster-deployment directory not found${NC}"
        exit 1
    fi

    cd cluster-deployment

    # Make scripts executable
    chmod +x *.sh 2>/dev/null || true

    # Create systemd service or launchd plist based on OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS - use launchd
        echo "Creating launchd service..."

        PLIST_FILE="$HOME/Library/LaunchAgents/com.agentic-system.daemon.plist"
        DAEMON_PATH="$(pwd)/github_node_daemon.py"
        LOG_PATH="$HOME/Library/Logs/agentic-system-daemon.log"

        cat > "$PLIST_FILE" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.agentic-system.daemon</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>$DAEMON_PATH</string>
        <string>--node-id</string>
        <string>$NODE_ID</string>
        <string>--repo</string>
        <string>$CLUSTER_REPO</string>
        <string>--poll-interval</string>
        <string>$POLL_INTERVAL</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>GITHUB_PERSONAL_ACCESS_TOKEN</key>
        <string>$GITHUB_PERSONAL_ACCESS_TOKEN</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$LOG_PATH</string>
    <key>StandardErrorPath</key>
    <string>$LOG_PATH</string>
</dict>
</plist>
EOF

        echo -e "${GREEN}✓ Launchd service created${NC}"
        echo ""
        echo "To start the daemon:"
        echo "  launchctl load $PLIST_FILE"
        echo ""
        echo "To stop the daemon:"
        echo "  launchctl unload $PLIST_FILE"

    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux - use systemd
        echo "Creating systemd service..."

        SERVICE_FILE="$HOME/.config/systemd/user/agentic-system-daemon.service"
        DAEMON_PATH="$(pwd)/github_node_daemon.py"

        mkdir -p "$HOME/.config/systemd/user"

        cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Agentic System Cluster Daemon
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 $DAEMON_PATH --node-id $NODE_ID --repo $CLUSTER_REPO --poll-interval $POLL_INTERVAL
Environment="GITHUB_PERSONAL_ACCESS_TOKEN=$GITHUB_PERSONAL_ACCESS_TOKEN"
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
EOF

        echo -e "${GREEN}✓ Systemd service created${NC}"
        echo ""
        echo "To start the daemon:"
        echo "  systemctl --user enable agentic-system-daemon"
        echo "  systemctl --user start agentic-system-daemon"
        echo ""
        echo "To check status:"
        echo "  systemctl --user status agentic-system-daemon"
    else
        echo -e "${YELLOW}⚠ Unsupported OS for auto-daemon setup${NC}"
        echo "You'll need to start the daemon manually with:"
        echo "  cd cluster-deployment"
        echo "  ./start_daemon.sh"
    fi

    cd ..
}

# Main bootstrap flow
main() {
    echo ""

    # Get script directory
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    cd "$SCRIPT_DIR"

    # Run setup steps
    detect_platform
    check_prerequisites
    setup_github_auth
    setup_node_config
    install_python_deps
    install_mcp_servers
    configure_mcp
    install_daemon

    echo ""
    echo "=========================================="
    echo -e "${GREEN}✓ Bootstrap Complete!${NC}"
    echo "=========================================="
    echo ""
    echo "Your node is configured as: $NODE_ID"
    echo "Connected to cluster: $CLUSTER_REPO"
    echo "CLI Platform: $CLI_PLATFORM"
    echo ""
    echo "Next steps:"
    echo "1. Start your daemon (see instructions above)"
    echo "2. Verify connection with health check"
    echo "3. Check cluster documentation in cluster-deployment/"
    echo ""
}

# Run main
main "$@"
