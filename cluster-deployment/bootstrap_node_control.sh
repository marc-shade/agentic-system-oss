#!/bin/bash
#
# Bootstrap Node Control System
# Sets up telnet-style command listener on cluster nodes
#
# Usage: ./bootstrap_node_control.sh [node_id] [port]
# Example: ./bootstrap_node_control.sh macpro51 9999
#

set -e

# Configuration
NODE_ID="${1:-$(hostname -s)}"
PORT="${2:-9999}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Node Control System Bootstrap${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo "Node ID: ${NODE_ID}"
echo "Port: ${PORT}"
echo ""

# Step 1: Make script executable
echo -e "${YELLOW}Step 1: Making command listener executable...${NC}"
chmod +x "${SCRIPT_DIR}/node_command_listener.py"
echo "✅ Done"
echo ""

# Step 2: Test Python availability
echo -e "${YELLOW}Step 2: Checking Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}ERROR: Python3 not found${NC}"
    exit 1
fi
echo "✅ Python3 found: $(python3 --version)"
echo ""

# Step 3: Check if port is available
echo -e "${YELLOW}Step 3: Checking port ${PORT}...${NC}"
if lsof -i :${PORT} &> /dev/null || ss -tuln | grep -q ":${PORT} "; then
    echo -e "${RED}WARNING: Port ${PORT} is already in use${NC}"
    echo "Kill existing process or choose a different port"
    if command -v lsof &> /dev/null; then
        echo "Current process:"
        lsof -i :${PORT}
    fi
else
    echo "✅ Port ${PORT} is available"
fi
echo ""

# Step 4: Create systemd service (if systemd available)
echo -e "${YELLOW}Step 4: Setting up systemd service...${NC}"
if command -v systemctl &> /dev/null; then
    SERVICE_FILE="/etc/systemd/system/node-command-listener.service"

    echo "Creating systemd service at ${SERVICE_FILE}"
    sudo tee "${SERVICE_FILE}" > /dev/null << EOF
[Unit]
Description=Node Command Listener for ${NODE_ID}
After=network.target

[Service]
Type=simple
User=${USER}
WorkingDirectory=${SCRIPT_DIR}
ExecStart=/usr/bin/python3 ${SCRIPT_DIR}/node_command_listener.py ${NODE_ID} ${PORT}
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    echo "✅ Service file created"
    echo ""
    echo "To enable and start the service:"
    echo "  sudo systemctl daemon-reload"
    echo "  sudo systemctl enable node-command-listener"
    echo "  sudo systemctl start node-command-listener"
    echo "  sudo systemctl status node-command-listener"
else
    echo "⚠️  systemd not available, skipping service creation"
fi
echo ""

# Step 5: Quick start option
echo -e "${YELLOW}Step 5: Starting listener (foreground mode)...${NC}"
echo "Press Ctrl+C to stop, or use background/systemd mode"
echo ""
echo "Starting in 3 seconds..."
sleep 3

# Start listener
python3 "${SCRIPT_DIR}/node_command_listener.py" "${NODE_ID}" "${PORT}"
