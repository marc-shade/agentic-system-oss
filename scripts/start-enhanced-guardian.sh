#!/bin/bash
# Start Enhanced System Health Guardian with Chain of Verification

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
AGENT_DIR="$BASE_DIR/intelligent-agents/enhanced_agents"
LOG_DIR="$BASE_DIR/logs"
ARDUINO_PORT="/dev/tty.usbmodem8344401"

# Create logs directory if needed
mkdir -p "$LOG_DIR"

echo "🔥 Starting Enhanced System Health Guardian with Verification..."

# Start enhanced guardian in background
nohup python3 "$AGENT_DIR/guardian_with_verification.py" "$ARDUINO_PORT" \
    > "$LOG_DIR/enhanced_guardian_stdout.log" 2>&1 &

GUARDIAN_PID=$!
echo "✅ Enhanced Guardian started (PID: $GUARDIAN_PID)"
echo "📝 Logs: $LOG_DIR/enhanced_guardian_stdout.log"
echo "🔍 Verification: ENABLED"
echo ""
echo "To check status: ps aux | grep guardian_with_verification"
echo "To view logs: tail -f $LOG_DIR/enhanced_guardian_stdout.log"
