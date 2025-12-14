#!/bin/bash
# Wazuh Agent Installation for macOS
# Run this script locally on each Mac node

WAZUH_MANAGER="192.168.1.183"  # macpro51.local (Wazuh Server)
WAZUH_VERSION="4.14.1"

echo "=========================================="
echo "Wazuh Agent Installation for macOS"
echo "Manager: ${WAZUH_MANAGER}"
echo "Version: ${WAZUH_VERSION}"
echo "=========================================="

# Detect architecture
ARCH=$(uname -m)
if [ "$ARCH" == "arm64" ]; then
    AGENT_PKG="wazuh-agent-${WAZUH_VERSION}-1.arm64.pkg"
else
    AGENT_PKG="wazuh-agent-${WAZUH_VERSION}-1.intel64.pkg"
fi
AGENT_URL="https://packages.wazuh.com/4.x/macos/${AGENT_PKG}"

echo "Detected architecture: ${ARCH}"
echo "Package: ${AGENT_PKG}"
echo ""

# Download
echo "=== Downloading Wazuh agent ==="
cd /tmp
curl -sO "${AGENT_URL}"
if [ ! -f "${AGENT_PKG}" ]; then
    echo "ERROR: Download failed"
    exit 1
fi
echo "Downloaded successfully"

# Install
echo ""
echo "=== Installing Wazuh agent (requires sudo) ==="
sudo installer -pkg "${AGENT_PKG}" -target /
if [ $? -ne 0 ]; then
    echo "ERROR: Installation failed"
    exit 1
fi

# Configure - register with manager
echo ""
echo "=== Registering agent with manager ==="
sudo /Library/Ossec/bin/agent-auth -m "${WAZUH_MANAGER}"
if [ $? -ne 0 ]; then
    echo "ERROR: Agent registration failed"
    echo "Make sure port 1515 is open on the Wazuh server"
    exit 1
fi

# Start agent
echo ""
echo "=== Starting Wazuh agent ==="
sudo /Library/Ossec/bin/wazuh-control start

# Verify
echo ""
echo "=== Agent Status ==="
sudo /Library/Ossec/bin/wazuh-control status

# Cleanup
rm -f "/tmp/${AGENT_PKG}"

echo ""
echo "=========================================="
echo "Wazuh agent installed successfully!"
echo "Check the Wazuh dashboard to see this agent"
echo "Dashboard: https://macpro51.local"
echo "=========================================="
