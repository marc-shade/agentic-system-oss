#!/bin/bash
# Quick deployment script for Mac nodes
# Run this on mac-studio or macbook-air

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}GitMQ Node Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Detect node name from hostname
NODE_ID=$(hostname | cut -d. -f1)
echo -e "${GREEN}✓${NC} Detected node ID: ${YELLOW}$NODE_ID${NC}"

# Confirm
read -p "Is this correct? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    read -p "Enter node ID (mac-studio, macbook-air, etc.): " NODE_ID
fi

echo ""
echo -e "${BLUE}Starting deployment for: ${YELLOW}$NODE_ID${NC}"
echo ""

# Step 1: Check prerequisites
echo -e "${BLUE}[1/6]${NC} Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗${NC} python3 not found. Please install Python 3.8+"
    exit 1
fi
echo -e "${GREEN}✓${NC} Python 3: $(python3 --version)"

if ! command -v git &> /dev/null; then
    echo -e "${RED}✗${NC} git not found. Please install git"
    exit 1
fi
echo -e "${GREEN}✓${NC} Git: $(git --version | head -1)"

# Step 2: Install dependencies
echo ""
echo -e "${BLUE}[2/6]${NC} Installing Python dependencies..."

pip3 install --quiet psutil GitPython 2>&1 | grep -v "already satisfied" || true
echo -e "${GREEN}✓${NC} Dependencies installed"

# Step 3: Set up directory structure
echo ""
echo -e "${BLUE}[3/6]${NC} Creating directory structure..."

AGENTIC_BASE="$HOME/agentic-system"
mkdir -p "$AGENTIC_BASE"/{cluster-deployment,logs,databases/cluster}

echo -e "${GREEN}✓${NC} Directories created at $AGENTIC_BASE"

# Step 4: Clone or update repository
echo ""
echo -e "${BLUE}[4/6]${NC} Setting up GitHub repository..."

REPO_PATH="$AGENTIC_BASE/agentic-cluster-comms"

if [ -d "$REPO_PATH" ]; then
    echo "Repository already exists, updating..."
    cd "$REPO_PATH"
    git fetch --all
else
    echo "Cloning repository..."
    cd "$AGENTIC_BASE"
    git clone https://github.com/marc-shade/agentic-cluster-comms.git
    cd "$REPO_PATH"
fi

echo -e "${GREEN}✓${NC} Repository ready at $REPO_PATH"

# Step 5: Download daemon scripts
echo ""
echo -e "${BLUE}[5/6]${NC} Downloading daemon scripts..."

cd "$AGENTIC_BASE/cluster-deployment"

# Download main daemon
curl -fsSL https://raw.githubusercontent.com/marc-shade/agentic-system/main/cluster-deployment/github_node_daemon.py -o github_node_daemon.py
chmod +x github_node_daemon.py

# Download task submitter
curl -fsSL https://raw.githubusercontent.com/marc-shade/agentic-system/main/cluster-deployment/submit_cluster_task.py -o submit_cluster_task.py
chmod +x submit_cluster_task.py

echo -e "${GREEN}✓${NC} Scripts downloaded"

# Step 6: Create helper scripts
echo ""
echo -e "${BLUE}[6/6]${NC} Creating helper scripts..."

# Create start-daemon.sh
cat > start-daemon.sh << 'EOF'
#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOG_DIR="$HOME/agentic-system/logs"

NODE_ID=$(hostname | cut -d. -f1)

echo "Starting GitMQ daemon for $NODE_ID..."
nohup python3 "$SCRIPT_DIR/github_node_daemon.py" \
    --node-id "$NODE_ID" \
    --repo marc-shade/agentic-cluster-comms \
    --poll-interval 30 \
    > "$LOG_DIR/github-daemon.log" 2>&1 &

DAEMON_PID=$!
echo "Daemon started with PID: $DAEMON_PID"
echo "Logs: $LOG_DIR/github-daemon.log"
echo ""
echo "To check status:"
echo "  tail -f $LOG_DIR/github-daemon.log"
echo ""
echo "To check heartbeat:"
echo "  ./send-task.sh $NODE_ID --check-heartbeat"
EOF
chmod +x start-daemon.sh

# Create send-task.sh
cat > send-task.sh << 'EOF'
#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
python3 "$SCRIPT_DIR/submit_cluster_task.py" "$@"
EOF
chmod +x send-task.sh

# Create stop-daemon.sh
cat > stop-daemon.sh << 'EOF'
#!/bin/bash
echo "Stopping GitMQ daemon..."
pkill -f github_node_daemon.py
echo "Daemon stopped"
EOF
chmod +x stop-daemon.sh

echo -e "${GREEN}✓${NC} Helper scripts created"

# Summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo ""
echo -e "1. Start the daemon:"
echo -e "   ${BLUE}cd $AGENTIC_BASE/cluster-deployment${NC}"
echo -e "   ${BLUE}./start-daemon.sh${NC}"
echo ""
echo -e "2. Verify it's running:"
echo -e "   ${BLUE}ps aux | grep github_node_daemon${NC}"
echo ""
echo -e "3. Check heartbeat:"
echo -e "   ${BLUE}./send-task.sh $NODE_ID --check-heartbeat${NC}"
echo ""
echo -e "4. View logs:"
echo -e "   ${BLUE}tail -f ~/agentic-system/logs/github-daemon.log${NC}"
echo ""
echo -e "${GREEN}Ready to join the cluster!${NC}"
echo ""
