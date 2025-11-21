#!/bin/bash

cd "$(dirname "$0")"

# Function to restart the MCP configuration
restart_mcp() {
  echo "Restarting MCP configuration..."
  killall "Windsurf MCP" &>/dev/null
  sleep 2
  open -a "Windsurf MCP"
  echo "MCP restarted"
}

# Make the server files executable
chmod +x src/core/notification_manager_server.py
chmod +x src/core/configuration_manager_server.py

# Verify the MCP configuration
echo "Verifying MCP configuration..."
MCP_CONFIG="$HOME/.codeium/windsurf/mcp_config.json"

if [ -f "$MCP_CONFIG" ]; then
  echo "MCP config found at: $MCP_CONFIG"
  
  # Display the notification and configuration sections
  echo ""
  echo "Notification Manager config:"
  grep -A 10 '"notification"' "$MCP_CONFIG"
  
  echo ""
  echo "Configuration Manager config:"
  grep -A 15 '"configuration"' "$MCP_CONFIG"
  
  # Prompt to restart MCP
  echo ""
  echo "To apply changes, you need to restart the Windsurf MCP application."
  echo "Would you like to restart MCP now? (y/n)"
  read -r answer
  if [ "$answer" = "y" ]; then
    restart_mcp
  else
    echo "Please restart MCP manually to apply changes."
  fi
else
  echo "MCP config not found at: $MCP_CONFIG"
  echo "Please ensure the MCP application is installed and has been run at least once."
fi

echo ""
echo "Setup complete. The notification_manager_server.py and configuration_manager_server.py files are ready."
