#!/bin/bash
# Deploy Cluster Self-X System to All Nodes
# Automated deployment script for distributed autonomous self-improvement

set -e  # Exit on error

echo "=========================================="
echo "Cluster Self-X System Deployment"
echo "=========================================="

# Configuration
NODES=(
    "192.168.1.176:mac-studio:macOS"
    "192.168.1.76:macbook-air:macOS"
)

LINUX_NODE="192.168.1.154"  # macpro51 (this node)

DEPLOYMENT_FILES=(
    "performance_optimizer.py"
    "auto_task_interceptor.py"
    "node_discovery.py"
    "autonomous_self_improvement_agent.py"
    "ollama_persistent_agent.py"
    "cluster_self_x_daemon.py"
    "distributed_task_router.py"
    "cluster_offload.py"
)

SERVICE_FILES=(
    "cluster-self-x.service"
    "com.agentic.cluster-self-x.plist"
)

# Deploy to macOS nodes
for node_config in "${NODES[@]}"; do
    IFS=':' read -r ip name os <<< "$node_config"

    echo ""
    echo "Deploying to $name ($ip)..."

    # Copy deployment files
    for file in "${DEPLOYMENT_FILES[@]}"; do
        echo "  Copying $file..."
        scp -q "$file" "marc@$ip:~/agentic-system/cluster-deployment/"
    done

    # Copy service file for macOS
    echo "  Copying launchd plist..."
    scp -q "com.agentic.cluster-self-x.plist" "marc@$ip:~/"

    # Make scripts executable
    echo "  Setting permissions..."
    ssh "marc@$ip" "cd ~/agentic-system/cluster-deployment && chmod +x *.py"

    # Install launchd service
    echo "  Installing launchd service..."
    ssh "marc@$ip" "mv ~/com.agentic.cluster-self-x.plist ~/Library/LaunchAgents/ && \
                     mkdir -p ~/agentic-system/logs"

    echo "  ✓ $name deployment complete"
done

# Deploy to local Linux node (macpro51)
echo ""
echo "Deploying to macpro51 (local Linux node)..."

# Make scripts executable
chmod +x *.py

# Install systemd service
echo "  Installing systemd service..."
mkdir -p ~/.config/systemd/user
cp cluster-self-x.service ~/.config/systemd/user/
systemctl --user daemon-reload

echo "  ✓ macpro51 deployment complete"

echo ""
echo "=========================================="
echo "Deployment Summary"
echo "=========================================="
echo "Deployed to nodes:"
echo "  - macpro51 (Linux)"
for node_config in "${NODES[@]}"; do
    IFS=':' read -r ip name os <<< "$node_config"
    echo "  - $name (macOS)"
done

echo ""
echo "Next steps:"
echo "1. Start services on all nodes:"
echo "   - macpro51: systemctl --user start cluster-self-x.service"
echo "   - Mac nodes: launchctl load ~/Library/LaunchAgents/com.agentic.cluster-self-x.plist"
echo ""
echo "2. Check status:"
echo "   - macpro51: systemctl --user status cluster-self-x.service"
echo "   - Mac nodes: tail -f ~/agentic-system/logs/cluster-self-x.log"
echo ""
echo "3. Monitor operations:"
echo "   - python3 cluster_self_x_daemon.py --stats"
echo ""
echo "=========================================="
echo "Deployment complete!"
echo "=========================================="
