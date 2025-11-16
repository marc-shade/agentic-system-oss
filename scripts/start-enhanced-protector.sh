#!/bin/bash
# Start Enhanced Code Evolution Protector with Chain of Verification

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
AGENT_DIR="$BASE_DIR/intelligent-agents/enhanced_agents"
LOG_DIR="$BASE_DIR/logs"
EVOLUTION_CONFIG="$BASE_DIR/config/evolution_phases.json"

# Create logs directory if needed
mkdir -p "$LOG_DIR"

echo "🔥 Starting Enhanced Code Evolution Protector with Verification..."

# Start enhanced protector in background
nohup python3 "$AGENT_DIR/protector_with_verification.py" \
    > "$LOG_DIR/enhanced_protector_stdout.log" 2>&1 &

PROTECTOR_PID=$!
echo "✅ Enhanced Protector started (PID: $PROTECTOR_PID)"
echo "📝 Logs: $LOG_DIR/enhanced_protector_stdout.log"
echo "🔍 Verification: ENABLED"
echo "📚 Edge Learning: ENABLED"
echo ""
echo "To check status: ps aux | grep protector_with_verification"
echo "To view logs: tail -f $LOG_DIR/enhanced_protector_stdout.log"
