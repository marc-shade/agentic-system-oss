#!/bin/bash
# Threat Intel Sync Daemon Installer
# Usage: ./install-daemon.sh [install|uninstall|start|stop|status|logs]

set -e

PLIST_NAME="com.phoenix.threat-intel-sync"
PLIST_SOURCE="$(dirname "$0")/${PLIST_NAME}.plist"
PLIST_DEST="${HOME}/Library/LaunchAgents/${PLIST_NAME}.plist"
LOG_DIR="${HOME}/.local/share/threat-intel/logs"

case "${1:-install}" in
    install)
        echo "Installing Threat Intel Sync Daemon..."

        # Create log directory
        mkdir -p "$LOG_DIR"

        # Copy plist to LaunchAgents
        cp "$PLIST_SOURCE" "$PLIST_DEST"

        # Load the daemon
        launchctl load "$PLIST_DEST"

        echo "Daemon installed and started"
        echo "Logs: $LOG_DIR/threat-intel-sync.log"
        ;;

    uninstall)
        echo "Uninstalling Threat Intel Sync Daemon..."

        # Unload if running
        launchctl unload "$PLIST_DEST" 2>/dev/null || true

        # Remove plist
        rm -f "$PLIST_DEST"

        echo "Daemon uninstalled"
        ;;

    start)
        echo "Starting Threat Intel Sync Daemon..."
        launchctl start "$PLIST_NAME"
        echo "Started"
        ;;

    stop)
        echo "Stopping Threat Intel Sync Daemon..."
        launchctl stop "$PLIST_NAME"
        echo "Stopped"
        ;;

    restart)
        echo "Restarting Threat Intel Sync Daemon..."
        launchctl stop "$PLIST_NAME" 2>/dev/null || true
        sleep 2
        launchctl start "$PLIST_NAME"
        echo "Restarted"
        ;;

    status)
        echo "Threat Intel Sync Daemon Status:"
        echo "================================="
        if launchctl list | grep -q "$PLIST_NAME"; then
            echo "Status: Running"
            launchctl list "$PLIST_NAME" 2>/dev/null || echo "  (checking...)"
        else
            echo "Status: Not loaded"
        fi
        echo ""
        echo "Recent log entries:"
        tail -10 "$LOG_DIR/threat-intel-sync.log" 2>/dev/null || echo "  No logs yet"
        ;;

    logs)
        echo "Following Threat Intel Sync logs (Ctrl+C to exit)..."
        tail -f "$LOG_DIR/threat-intel-sync.log"
        ;;

    sync-now)
        echo "Triggering immediate sync..."
        cd "$(dirname "$0")"
        python3 sync_scheduler.py --once
        ;;

    *)
        echo "Usage: $0 {install|uninstall|start|stop|restart|status|logs|sync-now}"
        exit 1
        ;;
esac
