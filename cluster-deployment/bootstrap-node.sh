#!/bin/bash
###############################################################################
# Agentic Cluster Node Bootstrap Script
#
# Automated onboarding for new cluster nodes
# Works on Linux and macOS
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/marc-shade/agentic-system/main/cluster-deployment/bootstrap-node.sh | bash -s -- <node-id>
#
# Or manually:
#   ./bootstrap-node.sh <node-id>
#
# Example:
#   ./bootstrap-node.sh scott-remote
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
GITHUB_REPO="marc-shade/agentic-cluster-comms"
MAIN_REPO="marc-shade/agentic-system"
INSTALL_DIR="$HOME/agentic-system"

###############################################################################
# Helper Functions
###############################################################################

print_header() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

print_step() {
    echo -e "\n${BLUE}▶${NC} $1"
}

check_command() {
    if command -v "$1" &> /dev/null; then
        print_success "$1 is installed"
        return 0
    else
        print_error "$1 is not installed"
        return 1
    fi
}

###############################################################################
# Main Script
###############################################################################

print_header "Agentic Cluster Node Bootstrap"

# Check if node ID was provided
if [ -z "$1" ]; then
    print_error "Node ID is required"
    echo ""
    echo "Usage: $0 <node-id>"
    echo ""
    echo "Examples:"
    echo "  $0 scott-remote"
    echo "  $0 developer-laptop"
    echo "  $0 build-server"
    exit 1
fi

NODE_ID="$1"
print_info "Node ID: $NODE_ID"

# Detect platform
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PLATFORM="linux"
    print_info "Platform: Linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macos"
    print_info "Platform: macOS"
else
    print_error "Unsupported platform: $OSTYPE"
    exit 1
fi

###############################################################################
# Step 1: Check Prerequisites
###############################################################################

print_step "Checking prerequisites..."

MISSING_DEPS=0

if ! check_command "git"; then
    print_error "Git is required. Install it first:"
    if [ "$PLATFORM" = "linux" ]; then
        echo "  sudo apt-get install git    # Debian/Ubuntu"
        echo "  sudo dnf install git        # Fedora/RHEL"
    else
        echo "  brew install git            # macOS with Homebrew"
    fi
    MISSING_DEPS=1
fi

if ! check_command "python3"; then
    print_error "Python 3 is required. Install it first."
    MISSING_DEPS=1
fi

if ! check_command "pip3"; then
    print_error "pip3 is required. Install it first."
    MISSING_DEPS=1
fi

if [ $MISSING_DEPS -eq 1 ]; then
    print_error "Please install missing dependencies and try again."
    exit 1
fi

###############################################################################
# Step 2: Install Python Dependencies
###############################################################################

print_step "Installing Python dependencies..."

if python3 -c "import psutil" 2>/dev/null; then
    print_success "psutil already installed"
else
    print_info "Installing psutil..."
    pip3 install --user psutil
    print_success "psutil installed"
fi

###############################################################################
# Step 3: Create Directory Structure
###############################################################################

print_step "Creating directory structure..."

mkdir -p "$INSTALL_DIR"/{cluster-deployment,logs,databases/cluster/{nodes/$NODE_ID,shared}}
print_success "Directories created at $INSTALL_DIR"

###############################################################################
# Step 4: Download GitMQ Scripts
###############################################################################

print_step "Downloading GitMQ scripts..."

cd "$INSTALL_DIR/cluster-deployment"

# Download daemon
if [ ! -f github_node_daemon.py ]; then
    print_info "Downloading github_node_daemon.py..."
    curl -fsSL "https://raw.githubusercontent.com/$MAIN_REPO/main/cluster-deployment/github_node_daemon.py" \
        -o github_node_daemon.py
    chmod +x github_node_daemon.py
    print_success "Downloaded github_node_daemon.py"
else
    print_success "github_node_daemon.py already exists"
fi

# Download task submitter
if [ ! -f submit_cluster_task.py ]; then
    print_info "Downloading submit_cluster_task.py..."
    curl -fsSL "https://raw.githubusercontent.com/$MAIN_REPO/main/cluster-deployment/submit_cluster_task.py" \
        -o submit_cluster_task.py
    chmod +x submit_cluster_task.py
    print_success "Downloaded submit_cluster_task.py"
else
    print_success "submit_cluster_task.py already exists"
fi

# Download cluster memory manager
if [ ! -f cluster_memory.py ]; then
    print_info "Downloading cluster_memory.py..."
    curl -fsSL "https://raw.githubusercontent.com/$MAIN_REPO/main/cluster-deployment/cluster_memory.py" \
        -o cluster_memory.py
    print_success "Downloaded cluster_memory.py"
else
    print_success "cluster_memory.py already exists"
fi

###############################################################################
# Step 5: Configure Node
###############################################################################

print_step "Configuring node..."

NODE_CONFIG="$HOME/.claude/node-config.json"
mkdir -p "$HOME/.claude"

if [ ! -f "$NODE_CONFIG" ]; then
    cat > "$NODE_CONFIG" << EOF
{
  "node_id": "$NODE_ID",
  "node_role": "remote",
  "capabilities": [
    "execute",
    "build",
    "test"
  ],
  "storage": {
    "agentic_base": "$INSTALL_DIR",
    "databases": "$INSTALL_DIR/databases",
    "logs": "$INSTALL_DIR/logs"
  },
  "memory": {
    "local_db": "$INSTALL_DIR/databases/mcp/enhanced_memories.db",
    "personal_db": "$INSTALL_DIR/databases/cluster/nodes/$NODE_ID/personal_memories.db",
    "shared_db": "$INSTALL_DIR/databases/cluster/shared_memories.db"
  }
}
EOF
    print_success "Node configuration created: $NODE_CONFIG"
else
    print_info "Node configuration already exists: $NODE_CONFIG"
fi

###############################################################################
# Step 6: Configure Git Credentials
###############################################################################

print_step "Configuring Git credentials..."

# Check if GitHub is already configured
if git config --global credential.helper &>/dev/null; then
    print_success "Git credential helper already configured"
else
    print_info "Configuring git credential helper..."
    git config --global credential.helper store
    print_success "Git credential helper configured"
fi

print_info "You will need a GitHub Personal Access Token (PAT) with 'repo' scope"
print_info "Create one at: https://github.com/settings/tokens"

###############################################################################
# Step 7: Test GitHub Access
###############################################################################

print_step "Testing GitHub access..."

if [ -d "$INSTALL_DIR/agentic-cluster-comms/.git" ]; then
    print_success "Repository already cloned"
    cd "$INSTALL_DIR/agentic-cluster-comms"

    print_info "Fetching latest changes..."
    if git fetch --all 2>&1 | grep -q "denied\|Authentication"; then
        print_error "GitHub authentication failed"
        print_info "Please ensure you have access to the repository and valid credentials"
        print_info "When prompted, use your GitHub username and PAT (not password)"
    else
        print_success "GitHub authentication working"
    fi
else
    print_info "Repository not yet cloned - daemon will clone it on first run"
fi

###############################################################################
# Step 8: Create Startup Scripts
###############################################################################

print_step "Creating startup scripts..."

# Create daemon start script
cat > "$INSTALL_DIR/cluster-deployment/start-daemon.sh" << 'EOFSTART'
#!/bin/bash
# Start GitMQ daemon for this node

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NODE_CONFIG="$HOME/.claude/node-config.json"

if [ ! -f "$NODE_CONFIG" ]; then
    echo "Error: Node configuration not found at $NODE_CONFIG"
    exit 1
fi

NODE_ID=$(jq -r '.node_id' "$NODE_CONFIG")
REPO="marc-shade/agentic-cluster-comms"

echo "Starting GitMQ daemon for node: $NODE_ID"
echo "Repository: $REPO"
echo ""

exec python3 "$SCRIPT_DIR/github_node_daemon.py" \
    --node-id "$NODE_ID" \
    --repo "$REPO" \
    --poll-interval 30
EOFSTART

chmod +x "$INSTALL_DIR/cluster-deployment/start-daemon.sh"
print_success "Created start-daemon.sh"

# Create helper script for task submission
cat > "$INSTALL_DIR/cluster-deployment/send-task.sh" << 'EOFSEND'
#!/bin/bash
# Helper script for sending tasks

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $0 <target-node-id> <task-type> [additional-args]"
    echo ""
    echo "Examples:"
    echo "  $0 scott-remote health_check"
    echo "  $0 macpro51 code_execution --command 'uname -a'"
    echo "  $0 macpro51 build --project my-app"
    echo ""
    echo "Check results:"
    echo "  $0 scott-remote --check-results"
    echo ""
    echo "Check heartbeat:"
    echo "  $0 scott-remote --check-heartbeat"
    exit 0
fi

exec python3 "$SCRIPT_DIR/submit_cluster_task.py" \
    --to "$@"
EOFSEND

chmod +x "$INSTALL_DIR/cluster-deployment/send-task.sh"
print_success "Created send-task.sh helper"

###############################################################################
# Step 9: Create Systemd Service (Linux Only)
###############################################################################

if [ "$PLATFORM" = "linux" ]; then
    print_step "Creating systemd service..."

    SERVICE_FILE="$HOME/.config/systemd/user/github-node-daemon.service"
    mkdir -p "$HOME/.config/systemd/user"

    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=GitHub Node Daemon - GitMQ for $NODE_ID
After=network.target

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR/cluster-deployment
ExecStart=/usr/bin/python3 $INSTALL_DIR/cluster-deployment/github_node_daemon.py --node-id $NODE_ID --repo $GITHUB_REPO --poll-interval 30
Restart=always
RestartSec=10
StandardOutput=append:$INSTALL_DIR/logs/github-daemon.log
StandardError=append:$INSTALL_DIR/logs/github-daemon-error.log

[Install]
WantedBy=default.target
EOF

    print_success "Created systemd service: $SERVICE_FILE"
    print_info "Enable with: systemctl --user enable github-node-daemon.service"
    print_info "Start with: systemctl --user start github-node-daemon.service"
fi

###############################################################################
# Step 10: Create LaunchAgent (macOS Only)
###############################################################################

if [ "$PLATFORM" = "macos" ]; then
    print_step "Creating LaunchAgent..."

    PLIST_FILE="$HOME/Library/LaunchAgents/com.agentic.github-daemon.plist"
    mkdir -p "$HOME/Library/LaunchAgents"

    cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.agentic.github-daemon</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>$INSTALL_DIR/cluster-deployment/github_node_daemon.py</string>
        <string>--node-id</string>
        <string>$NODE_ID</string>
        <string>--repo</string>
        <string>$GITHUB_REPO</string>
        <string>--poll-interval</string>
        <string>30</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$INSTALL_DIR/logs/github-daemon.log</string>
    <key>StandardErrorPath</key>
    <string>$INSTALL_DIR/logs/github-daemon-error.log</string>
</dict>
</plist>
EOF

    print_success "Created LaunchAgent: $PLIST_FILE"
    print_info "Load with: launchctl load ~/Library/LaunchAgents/com.agentic.github-daemon.plist"
fi

###############################################################################
# Step 11: Summary and Next Steps
###############################################################################

print_header "Bootstrap Complete!"

echo -e "${GREEN}✓ Node successfully configured!${NC}\n"

print_info "Node ID: $NODE_ID"
print_info "Install directory: $INSTALL_DIR"
print_info "Configuration: $NODE_CONFIG"

echo ""
print_header "Next Steps"

echo "1. Test the daemon:"
echo "   cd $INSTALL_DIR/cluster-deployment"
echo "   ./start-daemon.sh"
echo ""

echo "2. Send a test task to another node:"
echo "   ./send-task.sh macpro51 health_check"
echo ""

echo "3. Check results:"
echo "   ./send-task.sh macpro51 --check-results"
echo ""

echo "4. Run as background service:"
if [ "$PLATFORM" = "linux" ]; then
    echo "   systemctl --user enable github-node-daemon.service"
    echo "   systemctl --user start github-node-daemon.service"
    echo "   systemctl --user status github-node-daemon.service"
else
    echo "   launchctl load ~/Library/LaunchAgents/com.agentic.github-daemon.plist"
    echo "   launchctl list | grep github-daemon"
fi
echo ""

print_header "Important Notes"

echo "• You will need GitHub credentials on first run"
echo "  - Username: Your GitHub username"
echo "  - Password: Personal Access Token (PAT) with 'repo' scope"
echo "  - Create PAT at: https://github.com/settings/tokens"
echo ""

echo "• The daemon will:"
echo "  - Clone the cluster communication repository"
echo "  - Post initial heartbeat to GitHub"
echo "  - Poll for tasks every 30 seconds"
echo "  - Execute tasks and post results"
echo ""

echo "• Logs are stored in:"
echo "  $INSTALL_DIR/logs/github-daemon.log"
echo ""

print_success "Node $NODE_ID is ready to join the cluster!"

exit 0
