#!/bin/bash
# Session Start Hook - Complete Environmental Snapshot for Phoenix

SNAPSHOT="/tmp/phoenix_session_start.json"
LOG_FILE="/tmp/phoenix_session_start.log"

echo "=== Phoenix Session Start $(date) ===" > "$LOG_FILE"

# Generate comprehensive environment snapshot
python3 ~/.claude/hooks/env_check.py json > "$SNAPSHOT" 2>>"$LOG_FILE"

if [ $? -eq 0 ]; then
    echo "✅ Environment snapshot generated: $SNAPSHOT" >> "$LOG_FILE"
    
    # Print summary for immediate awareness
    echo "" >> "$LOG_FILE"
    python3 ~/.claude/hooks/env_check.py >> "$LOG_FILE"
    
    # Run verification
    echo "" >> "$LOG_FILE"
    echo "=== System Verification ===" >> "$LOG_FILE"
    python3 ~/.claude/hooks/system_control.py verify >> "$LOG_FILE" 2>&1
    
    # Auto-heal if needed
    echo "" >> "$LOG_FILE"
    echo "=== Auto-Heal Check ===" >> "$LOG_FILE"
    python3 ~/.claude/hooks/system_control.py heal >> "$LOG_FILE" 2>&1

    # Intelligent StatusLine Protection - AI-powered watchdog
    echo "" >> "$LOG_FILE"
    echo "=== Intelligent StatusLine Protection (AI-Powered) ===" >> "$LOG_FILE"
    python3 /Volumes/SSDRAID0/agentic-system/intelligent-self-healing/intelligent_statusline_watchdog.py >> "$LOG_FILE" 2>&1

    # Environmental Awareness - Full system state for Sonnet 4.5
    echo "" >> "$LOG_FILE"
    echo "=== Environmental Awareness ===" >> "$LOG_FILE"
    python3 ~/.claude/hooks/environmental-awareness.py >> "$LOG_FILE" 2>&1

    echo "✅ Phoenix session initialized successfully" >> "$LOG_FILE"
else
    echo "❌ Failed to generate environment snapshot" >> "$LOG_FILE"
fi

# Make log available to Phoenix
cat "$LOG_FILE"
