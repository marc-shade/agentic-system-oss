#!/bin/bash
# System Administration Tools for Claude
# Provides quick access to system management capabilities

# Port Manager CLI
export PM="/Volumes/FILES/code/kutiraai/bin/pm"

# Quick port operations
alias pm-status="$PM status"
alias pm-conflicts="$PM conflicts"
alias pm-cleanup="$PM cleanup"
alias pm-list="$PM list"

# Service management
export KUTIRA_SERVICES="/Volumes/FILES/code/kutiraai/services"
export KUTIRA_BIN="/Volumes/FILES/code/kutiraai/bin"

# Check if Port Manager daemon is running
check_port_manager() {
    if curl -s http://localhost:4102/health >/dev/null 2>&1; then
        echo "✅ Port Manager daemon running"
        return 0
    else
        echo "❌ Port Manager daemon not running"
        echo "Start with: cd $KUTIRA_SERVICES/port-manager-server && node index.js &"
        return 1
    fi
}

# Export functions
export -f check_port_manager
