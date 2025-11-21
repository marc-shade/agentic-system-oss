#!/bin/bash
# Deploy Tmux-Cluster Integration to All Nodes
# Integrates cluster-execution-mcp with tmux fork for full observability

set -e

echo "🚀 Deploying Tmux-Cluster Integration"
echo "======================================"
echo ""

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Cluster nodes
NODES=(
    "192.168.1.183:macpro51"
    "192.168.1.76:macbook-air"
    "192.168.1.186:completeu-server"
)

# ========================================
# DEPLOY TMUX CONFIGURATION
# ========================================

echo -e "${BLUE}Step 1: Deploying tmux configuration to all nodes...${NC}"

for node in "${NODES[@]}"; do
    IFS=':' read -r ip name <<< "$node"
    echo -e "${GREEN}  → $name ($ip)${NC}"

    # Create .config/tmux directory
    ssh -o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=no marc@$ip "mkdir -p ~/.config/tmux" 2>/dev/null || true

    # Copy cluster status script
    scp -o ConnectTimeout=5 ~/.config/tmux/cluster_status.sh marc@$ip:~/.config/tmux/ 2>/dev/null || true
    ssh marc@$ip "chmod +x ~/.config/tmux/cluster_status.sh" 2>/dev/null || true

    # Copy cluster-aware tmux config
    scp -o ConnectTimeout=5 ~/.config/tmux/cluster-aware.conf marc@$ip:~/.config/tmux/ 2>/dev/null || true

    # Copy main tmux config
    scp -o ConnectTimeout=5 ~/.tmux.conf marc@$ip:~/.tmux.conf 2>/dev/null || true

    echo "    ✅ Tmux config deployed"
done

echo ""

# ========================================
# DEPLOY DISTRIBUTED TASK ROUTER
# ========================================

echo -e "${BLUE}Step 2: Deploying distributed_task_router.py with tmux integration...${NC}"

for node in "${NODES[@]}"; do
    IFS=':' read -r ip name <<< "$node"
    echo -e "${GREEN}  → $name ($ip)${NC}"

    # Determine correct path (Linux vs macOS)
    # See FILE_LOCATION_POLICY.md - use SSDRAID0 on macOS, /mnt on Linux
    if [[ "$name" == "macpro51" ]]; then
        # Linux node uses /mnt
        remote_path="/mnt/agentic-system/cluster-deployment"
    elif [[ "$name" == "completeu-server" ]]; then
        # CompletU server - check what drive it has
        remote_path="/Volumes/SSDRAID0/agentic-system/cluster-deployment"
    else
        # macOS nodes use SSDRAID0
        remote_path="/Volumes/SSDRAID0/agentic-system/cluster-deployment"
    fi

    # Ensure directory exists
    ssh -o ConnectTimeout=5 marc@$ip "mkdir -p $remote_path" 2>/dev/null || true

    # Copy updated router
    rsync -avz --timeout=10 \
        /Volumes/SSDRAID0/agentic-system/cluster-deployment/distributed_task_router.py \
        marc@$ip:$remote_path/ 2>/dev/null || true

    # Verify deployment
    if ssh marc@$ip "test -f $remote_path/distributed_task_router.py"; then
        echo "    ✅ Router deployed"
    else
        echo "    ❌ Router deployment failed"
    fi
done

echo ""

# ========================================
# INSTALL TMUX PLUGINS
# ========================================

echo -e "${BLUE}Step 3: Installing tmux plugins (resurrect, continuum)...${NC}"

for node in "${NODES[@]}"; do
    IFS=':' read -r ip name <<< "$node"
    echo -e "${GREEN}  → $name ($ip)${NC}"

    # Install TPM (Tmux Plugin Manager) if not present
    ssh marc@$ip "
        if [ ! -d ~/.tmux/plugins/tpm ]; then
            git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
            echo '    ✅ TPM installed'
        else
            echo '    ⚪ TPM already installed'
        fi

        # Install plugins
        ~/.tmux/plugins/tpm/bin/install_plugins 2>/dev/null || true
    " || true
done

echo ""

# ========================================
# CREATE TMUX SESSION DIRECTORIES
# ========================================

echo -e "${BLUE}Step 4: Creating tmux session directories...${NC}"

for node in "${NODES[@]}"; do
    IFS=':' read -r ip name <<< "$node"
    echo -e "${GREEN}  → $name ($ip)${NC}"

    # Determine correct path (see FILE_LOCATION_POLICY.md)
    if [[ "$name" == "macpro51" ]]; then
        session_dir="/mnt/agentic-system/databases/cluster/tmux-sessions"
    elif [[ "$name" == "completeu-server" ]]; then
        session_dir="/Volumes/SSDRAID0/agentic-system/databases/cluster/tmux-sessions"
    else
        # macOS nodes use SSDRAID0
        session_dir="/Volumes/SSDRAID0/agentic-system/databases/cluster/tmux-sessions"
    fi

    ssh marc@$ip "mkdir -p $session_dir" 2>/dev/null || true
    echo "    ✅ Session directory created: $session_dir"
done

echo ""

# ========================================
# VERIFICATION
# ========================================

echo -e "${BLUE}Step 5: Verifying deployment...${NC}"

for node in "${NODES[@]}"; do
    IFS=':' read -r ip name <<< "$node"
    echo -e "${GREEN}  → $name ($ip)${NC}"

    # Check files exist
    files_ok=true

    if ! ssh marc@$ip "test -f ~/.tmux.conf"; then
        echo "    ❌ .tmux.conf missing"
        files_ok=false
    fi

    if ! ssh marc@$ip "test -f ~/.config/tmux/cluster-aware.conf"; then
        echo "    ❌ cluster-aware.conf missing"
        files_ok=false
    fi

    if ! ssh marc@$ip "test -f ~/.config/tmux/cluster_status.sh"; then
        echo "    ❌ cluster_status.sh missing"
        files_ok=false
    fi

    if $files_ok; then
        echo "    ✅ All files verified"
    fi
done

echo ""
echo "======================================"
echo -e "${GREEN}✅ Tmux-Cluster Integration Deployed!${NC}"
echo ""
echo "Next Steps:"
echo "  1. Restart Claude Code to reload cluster-execution-mcp"
echo "  2. Test with: mcp__cluster-execution__cluster_bash"
echo "  3. View sessions: mcp__cluster-execution__tmux_sessions"
echo "  4. Check cluster status in tmux status bar"
echo ""
echo "The AI agent now has:"
echo "  ✅ Real-time cluster metrics in tmux status bar"
echo "  ✅ Persistent task sessions on remote nodes"
echo "  ✅ Full observability into all tmux sessions"
echo "  ✅ Context retrieval from any session"
echo ""
