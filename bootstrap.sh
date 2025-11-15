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

# Check all required platforms
check_all_platforms() {
    echo "Checking for all required CLI platforms..."
    echo ""

    PLATFORMS_FOUND=0
    PLATFORMS_MISSING=()

    # Check Claude Code (primary orchestrator)
    if command -v claude-code &> /dev/null; then
        echo -e "${GREEN}✓ Claude Code detected${NC}"
        export HAS_CLAUDE_CODE=true
        PLATFORMS_FOUND=$((PLATFORMS_FOUND + 1))
    else
        echo -e "${RED}✗ Claude Code not found${NC}"
        export HAS_CLAUDE_CODE=false
        PLATFORMS_MISSING+=("Claude Code")
    fi

    # Check Ollama
    if command -v ollama &> /dev/null; then
        echo -e "${GREEN}✓ Ollama detected${NC}"
        export HAS_OLLAMA=true
        PLATFORMS_FOUND=$((PLATFORMS_FOUND + 1))
    else
        echo -e "${YELLOW}⚠ Ollama not found${NC}"
        export HAS_OLLAMA=false
        PLATFORMS_MISSING+=("Ollama")
    fi

    # Check OpenAI Codex
    if command -v codex &> /dev/null; then
        echo -e "${GREEN}✓ OpenAI Codex detected${NC}"
        export HAS_CODEX=true
        PLATFORMS_FOUND=$((PLATFORMS_FOUND + 1))
    else
        echo -e "${YELLOW}⚠ OpenAI Codex not found${NC}"
        export HAS_CODEX=false
        PLATFORMS_MISSING+=("OpenAI Codex")
    fi

    # Check Gemini CLI
    if command -v gemini &> /dev/null; then
        echo -e "${GREEN}✓ Gemini CLI detected${NC}"
        export HAS_GEMINI=true
        PLATFORMS_FOUND=$((PLATFORMS_FOUND + 1))
    else
        echo -e "${YELLOW}⚠ Gemini CLI not found${NC}"
        export HAS_GEMINI=false
        PLATFORMS_MISSING+=("Gemini CLI")
    fi

    echo ""
    echo "Platforms found: $PLATFORMS_FOUND/4"

    if [ "$HAS_CLAUDE_CODE" = false ]; then
        echo ""
        echo -e "${RED}✗ Claude Code is required as the primary orchestrator${NC}"
        echo "Install from: https://code.claude.com"
        exit 1
    fi

    if [ ${#PLATFORMS_MISSING[@]} -gt 0 ]; then
        echo ""
        echo -e "${YELLOW}⚠ Missing platforms detected${NC}"
        echo "The following platforms are recommended but not required:"
        for platform in "${PLATFORMS_MISSING[@]}"; do
            echo "  - $platform"
        done
        echo ""
        echo "Installation instructions:"
        echo "  - Ollama: https://ollama.ai/download"
        echo "  - OpenAI Codex: https://github.com/openai/openai-codex"
        echo "  - Gemini CLI: npm install -g @google/generative-ai-cli"
        echo ""
        read -p "Continue with partial setup? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
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

# Setup authentication for all platforms
setup_all_auth() {
    echo ""
    echo "Multi-Platform Authentication Setup"
    echo "====================================="

    # Determine shell profile
    if [[ "$SHELL" == *"zsh"* ]]; then
        PROFILE="$HOME/.zshrc"
    else
        PROFILE="$HOME/.bashrc"
    fi

    # 1. GitHub Authentication (required for cluster communication)
    echo ""
    echo "1. GitHub Authentication"
    echo "------------------------"
    if [ -z "$GITHUB_PERSONAL_ACCESS_TOKEN" ]; then
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

        if ! grep -q "GITHUB_PERSONAL_ACCESS_TOKEN" "$PROFILE" 2>/dev/null; then
            echo "" >> "$PROFILE"
            echo "# Agentic System - GitHub Authentication" >> "$PROFILE"
            echo "export GITHUB_PERSONAL_ACCESS_TOKEN=\"$GITHUB_PERSONAL_ACCESS_TOKEN\"" >> "$PROFILE"
        fi
        echo -e "${GREEN}✓ GitHub authentication configured${NC}"
    else
        echo -e "${GREEN}✓ GITHUB_PERSONAL_ACCESS_TOKEN already set${NC}"
    fi

    # 2. Ollama Authentication (optional, runs locally without auth by default)
    if [ "$HAS_OLLAMA" = true ]; then
        echo ""
        echo "2. Ollama Configuration"
        echo "-----------------------"
        echo -e "${GREEN}✓ Ollama runs locally without authentication${NC}"
        echo "  Host: ${OLLAMA_HOST:-http://localhost:11434}"

        # Optionally set OLLAMA_HOST if user wants to change it
        if [ -z "$OLLAMA_HOST" ]; then
            export OLLAMA_HOST="http://localhost:11434"
            if ! grep -q "OLLAMA_HOST" "$PROFILE" 2>/dev/null; then
                echo "export OLLAMA_HOST=\"http://localhost:11434\"" >> "$PROFILE"
            fi
        fi
    fi

    # 3. OpenAI Codex Authentication
    if [ "$HAS_CODEX" = true ]; then
        echo ""
        echo "3. OpenAI Codex Authentication"
        echo "-------------------------------"

        # Check if already authenticated
        if codex login status &> /dev/null; then
            echo -e "${GREEN}✓ OpenAI Codex already authenticated${NC}"
        else
            echo "Choose authentication method:"
            echo "  1) ChatGPT OAuth (recommended - auto-configured)"
            echo "  2) API Key (manual setup)"
            read -p "Select method (1-2): " -n 1 -r CODEX_AUTH_METHOD
            echo ""

            if [[ $CODEX_AUTH_METHOD == "1" ]]; then
                echo "Opening browser for ChatGPT OAuth..."
                codex login
                echo -e "${GREEN}✓ OpenAI Codex authenticated via OAuth${NC}"
            else
                echo ""
                echo "Get your API key from: https://platform.openai.com/api-keys"
                read -p "Enter your OpenAI API key: " -s OPENAI_KEY
                echo ""
                export OPENAI_API_KEY="$OPENAI_KEY"
                codex login --api-key "$OPENAI_KEY"

                if ! grep -q "OPENAI_API_KEY" "$PROFILE" 2>/dev/null; then
                    echo "export OPENAI_API_KEY=\"$OPENAI_API_KEY\"" >> "$PROFILE"
                fi
                echo -e "${GREEN}✓ OpenAI Codex authenticated via API key${NC}"
            fi
        fi
    fi

    # 4. Gemini CLI Authentication
    if [ "$HAS_GEMINI" = true ]; then
        echo ""
        echo "4. Gemini CLI Authentication"
        echo "-----------------------------"

        echo "Choose authentication method:"
        echo "  1) Google Cloud ADC (recommended for Google Cloud users)"
        echo "  2) API Key (simpler, for direct Gemini API access)"
        read -p "Select method (1-2): " -n 1 -r GEMINI_AUTH_METHOD
        echo ""

        if [[ $GEMINI_AUTH_METHOD == "1" ]]; then
            echo "Setting up Application Default Credentials..."

            if command -v gcloud &> /dev/null; then
                gcloud auth application-default login

                read -p "Enter your Google Cloud Project ID: " GCP_PROJECT
                read -p "Enter your Google Cloud Location [us-central1]: " GCP_LOCATION
                GCP_LOCATION=${GCP_LOCATION:-us-central1}

                export GOOGLE_CLOUD_PROJECT="$GCP_PROJECT"
                export GOOGLE_CLOUD_LOCATION="$GCP_LOCATION"

                if ! grep -q "GOOGLE_CLOUD_PROJECT" "$PROFILE" 2>/dev/null; then
                    echo "export GOOGLE_CLOUD_PROJECT=\"$GCP_PROJECT\"" >> "$PROFILE"
                    echo "export GOOGLE_CLOUD_LOCATION=\"$GCP_LOCATION\"" >> "$PROFILE"
                fi
                echo -e "${GREEN}✓ Gemini CLI authenticated via ADC${NC}"
            else
                echo -e "${YELLOW}⚠ gcloud CLI not found. Install from: https://cloud.google.com/sdk/docs/install${NC}"
                echo "Falling back to API key method..."
                GEMINI_AUTH_METHOD="2"
            fi
        fi

        if [[ $GEMINI_AUTH_METHOD == "2" ]]; then
            echo ""
            echo "Get your API key from: https://aistudio.google.com/app/apikey"
            read -p "Enter your Gemini API key: " -s GEMINI_KEY
            echo ""
            export GEMINI_API_KEY="$GEMINI_KEY"

            # Create .gemini/.env file for persistent config
            mkdir -p "$HOME/.gemini"
            echo "GEMINI_API_KEY=$GEMINI_KEY" > "$HOME/.gemini/.env"

            if ! grep -q "GEMINI_API_KEY" "$PROFILE" 2>/dev/null; then
                echo "export GEMINI_API_KEY=\"$GEMINI_API_KEY\"" >> "$PROFILE"
            fi
            echo -e "${GREEN}✓ Gemini CLI authenticated via API key${NC}"
        fi
    fi

    echo ""
    echo -e "${GREEN}✓ All authentication configured${NC}"
    echo "Environment variables saved to: $PROFILE"
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
