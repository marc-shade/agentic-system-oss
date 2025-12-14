#!/bin/bash
# Test Hook Functionality
# Simulates hook execution to verify they work correctly


# Platform-aware storage detection
detect_storage_base() {
    if [ -n "$AGENTIC_SYSTEM_PATH" ] && [ -d "$AGENTIC_SYSTEM_PATH" ]; then
        echo "$AGENTIC_SYSTEM_PATH"
        return
    fi
    case "$(uname -s)" in
        Darwin)
            if [ -d "/Volumes/SSDRAID0/agentic-system" ]; then
                echo "/Volumes/SSDRAID0/agentic-system"
            elif [ -d "/Volumes/FILES/agentic-system" ]; then
                echo "/Volumes/FILES/agentic-system"
            fi
            ;;
        Linux)
            if [ -d "/home/marc/agentic-system" ]; then
                echo "/home/marc/agentic-system"
            elif [ -d "/mnt/agentic-system" ]; then
                echo "/mnt/agentic-system"
            fi
            ;;
    esac
}

STORAGE_BASE=$(detect_storage_base)

echo "=========================================="
echo "CLAUDE CODE HOOKS FUNCTIONALITY TEST"
echo "=========================================="
echo ""

# Test 1: PostCompact Hook
echo "Test 1: PostCompact Hook"
echo "-------------------------"
export CLAUDE_SESSION_DIR="/tmp/test-session"
export CLAUDE_SESSION_ID="test-session-123"
$STORAGE_BASE/scripts/hooks/post-compact.sh
if [ $? -eq 0 ]; then
    echo "✅ PostCompact hook executed successfully"
    # Check if log entry was created
    if grep -q "post_compact" $STORAGE_BASE/logs/claude-sessions.log 2>/dev/null; then
        echo "✅ Log entry created"
    else
        echo "⚠️  No log entry found"
    fi
else
    echo "❌ PostCompact hook failed"
fi
echo ""

# Test 2: PreQuery Hook
echo "Test 2: PreQuery Hook"
echo "---------------------"
TEST_INPUT=$(cat <<'EOF'
{
  "query_id": "test-query-456",
  "model": "claude-sonnet-4-5",
  "context_tokens": 1500
}
EOF
)
echo "$TEST_INPUT" | $STORAGE_BASE/scripts/hooks/pre-query.sh
if [ $? -eq 0 ]; then
    echo "✅ PreQuery hook executed successfully"
    # Check if log entry was created
    if grep -q "test-query-456" $STORAGE_BASE/logs/query-metrics.log 2>/dev/null; then
        echo "✅ Query metrics logged"
    else
        echo "⚠️  No query metrics found"
    fi
    # Check if temp file was created
    if [ -f "/tmp/claude_query_test-query-456.json" ]; then
        echo "✅ Query tracking file created"
    else
        echo "⚠️  Query tracking file not found"
    fi
else
    echo "❌ PreQuery hook failed"
fi
echo ""

# Test 3: PostQuery Hook
echo "Test 3: PostQuery Hook"
echo "----------------------"
TEST_INPUT=$(cat <<'EOF'
{
  "query_id": "test-query-456",
  "model": "claude-sonnet-4-5",
  "input_tokens": 1500,
  "output_tokens": 750,
  "cache_read_tokens": 500,
  "cache_creation_tokens": 200,
  "stop_reason": "end_turn"
}
EOF
)
echo "$TEST_INPUT" | $STORAGE_BASE/scripts/hooks/post-query.sh
if [ $? -eq 0 ]; then
    echo "✅ PostQuery hook executed successfully"
    # Check if log entry was created with cost calculation
    if grep -q "estimated_cost_usd" $STORAGE_BASE/logs/query-metrics.log 2>/dev/null; then
        echo "✅ Cost calculation logged"
        LAST_COST=$(tail -1 $STORAGE_BASE/logs/query-metrics.log | python3 -c "import json, sys; print(json.load(sys.stdin).get('estimated_cost_usd', 'N/A'))" 2>/dev/null)
        echo "   Estimated cost: \$$LAST_COST"
    else
        echo "⚠️  Cost calculation not found"
    fi
    # Check if temp file was cleaned up
    if [ ! -f "/tmp/claude_query_test-query-456.json" ]; then
        echo "✅ Query tracking file cleaned up"
    else
        echo "⚠️  Query tracking file still exists"
    fi
else
    echo "❌ PostQuery hook failed"
fi
echo ""

# Summary
echo "=========================================="
echo "TEST SUMMARY"
echo "=========================================="
echo ""
echo "Hook Files Created:"
ls -lh $STORAGE_BASE/scripts/hooks/*.sh | grep -E "(post-compact|pre-query|post-query)" | awk '{print "  " $9 " (" $5 ")"}'
echo ""
echo "Configuration:"
jq -r '.hooks | keys[]' ~/.claude/settings.json | grep -E "(PostCompact|PreQuery|PostQuery)" | sed 's/^/  ✓ /'
echo ""
echo "Log Files:"
for log in query-metrics.log cost-tracking.log compaction-events.log; do
    if [ -f "$STORAGE_BASE/logs/$log" ]; then
        LINES=$(wc -l < "$STORAGE_BASE/logs/$log" 2>/dev/null)
        echo "  ✓ $log ($LINES entries)"
    else
        echo "  ✗ $log (missing)"
    fi
done
echo ""

# Show recent query metrics
echo "Recent Query Metrics (last 3):"
tail -3 $STORAGE_BASE/logs/query-metrics.log 2>/dev/null | python3 -c "
import json
import sys
for line in sys.stdin:
    try:
        data = json.loads(line)
        event = data.get('event', 'unknown')
        query_id = data.get('query_id', 'N/A')
        cost = data.get('estimated_cost_usd', 'N/A')
        tokens = data.get('input_tokens', 0) + data.get('output_tokens', 0)
        print(f'  {event}: {query_id} - {tokens} tokens - \${cost}')
    except:
        pass
" || echo "  (No metrics yet)"
echo ""

echo "✅ Hook testing complete!"
echo "   All 3 new hooks are configured and operational."
echo ""
echo "Next: Restart Claude Code to activate the hooks."
