#!/bin/bash
#
# Install Arduino Display Agent as Auto-Start Service
# Run this on the Mac Studio (orchestrator) where the Arduino is connected
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARDUINO_DIR="$(dirname "$SCRIPT_DIR")"
PLIST_SOURCE="$ARDUINO_DIR/com.agentic.arduino-display-agent.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.agentic.arduino-display-agent.plist"

echo "========================================"
echo "Arduino Display Agent Service Installer"
echo "========================================"
echo ""

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ This script must be run on macOS (Mac Studio)"
    echo "   The Arduino is connected to macOS nodes only."
    exit 1
fi

# Check Arduino connection
echo "🔍 Checking for Arduino device..."
ARDUINO_PORT=$(ls /dev/tty.usbmodem* 2>/dev/null | head -1)
if [ -z "$ARDUINO_PORT" ]; then
    echo "⚠️  Warning: No Arduino detected at /dev/tty.usbmodem*"
    echo "   Make sure the Arduino is connected via USB."
    echo "   Continuing anyway - service will wait for connection..."
else
    echo "✅ Found Arduino at: $ARDUINO_PORT"
fi

# Create logs directory
echo ""
echo "📁 Creating logs directory..."
mkdir -p "$ARDUINO_DIR/logs"
echo "✅ Logs directory ready: $ARDUINO_DIR/logs"

# Create LaunchAgents directory if needed
echo ""
echo "📁 Checking LaunchAgents directory..."
mkdir -p "$HOME/Library/LaunchAgents"
echo "✅ LaunchAgents directory ready"

# Stop existing service if running
echo ""
echo "🛑 Stopping existing service (if any)..."
launchctl unload "$PLIST_DEST" 2>/dev/null || true
echo "✅ Cleared any existing service"

# Copy plist to LaunchAgents
echo ""
echo "📋 Installing launchd plist..."
cp "$PLIST_SOURCE" "$PLIST_DEST"
echo "✅ Plist installed to: $PLIST_DEST"

# Update ANTHROPIC_API_KEY in plist if set
if [ -n "$ANTHROPIC_API_KEY" ]; then
    echo ""
    echo "🔑 Setting ANTHROPIC_API_KEY in plist..."
    # Use sed to replace the placeholder
    sed -i '' "s|\${ANTHROPIC_API_KEY}|$ANTHROPIC_API_KEY|g" "$PLIST_DEST"
    echo "✅ API key configured"
else
    echo ""
    echo "⚠️  Warning: ANTHROPIC_API_KEY not set"
    echo "   The intelligent agent features will be limited."
    echo "   Set it with: export ANTHROPIC_API_KEY=sk-ant-..."
fi

# Load the service
echo ""
echo "🚀 Starting Arduino Display Agent service..."
launchctl load "$PLIST_DEST"
sleep 2

# Check if running
if launchctl list | grep -q "com.agentic.arduino-display-agent"; then
    echo "✅ Service started successfully!"
else
    echo "❌ Service failed to start. Check logs:"
    echo "   tail -f $ARDUINO_DIR/logs/display-agent.log"
    exit 1
fi

echo ""
echo "========================================"
echo "Installation Complete!"
echo "========================================"
echo ""
echo "Service Status Commands:"
echo "  Check status:  launchctl list | grep arduino"
echo "  View logs:     tail -f $ARDUINO_DIR/logs/display-agent.log"
echo "  Stop service:  launchctl unload $PLIST_DEST"
echo "  Start service: launchctl load $PLIST_DEST"
echo ""
echo "The Arduino display agent will:"
echo "  • Start automatically on boot"
echo "  • Restart automatically if it crashes"
echo "  • Display system status on the Arduino LCD"
echo "  • Control LEDs based on system health"
echo "  • Provide AI-powered status analysis (with API key)"
echo ""
