#!/bin/bash
# Qdrant Status for Autonomous System Monitoring
# Integrates with system monitoring dashboard

# Colors for output

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

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 Qdrant Vector Database Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo

# Check if Qdrant is running
if ! curl -sf http://localhost:6333/healthz > /dev/null 2>&1; then
    echo -e "${RED}❌ Qdrant is NOT running${NC}"
    echo "   To start: $STORAGE_BASE/scripts/qdrant-monitor.sh start"
    exit 1
fi

echo -e "${GREEN}✅ Qdrant is running${NC}"
echo

# Get server info
VERSION=$(curl -s http://localhost:6333/ | jq -r '.version' 2>/dev/null || echo "unknown")
echo "📊 Server Information"
echo "   Version: $VERSION"

# Get port info
PID=$(lsof -t -i:6333 2>/dev/null)
echo "   PID: ${PID:-unknown}"
echo "   HTTP Port: 6333"
echo "   gRPC Port: 6334"
echo

# Get collections info
COLLECTIONS=$(curl -s http://localhost:6333/collections | jq -r '.result.collections | length' 2>/dev/null || echo "0")
echo "📦 Collections"
echo "   Total: $COLLECTIONS"

# List each collection with point count
if [ "$COLLECTIONS" -gt 0 ]; then
    curl -s http://localhost:6333/collections | jq -r '.result.collections[] | "   - \(.name): \(.points_count // 0) points"' 2>/dev/null || echo "   Unable to fetch collection details"
fi
echo

# Storage stats
DB_PATH="$STORAGE_BASE/databases/qdrant"
DB_SIZE=$(du -sh "$DB_PATH" 2>/dev/null | cut -f1 || echo "unknown")
echo "💾 Storage"
echo "   Database path: $DB_PATH"
echo "   Size: $DB_SIZE"
echo

# Log stats
LOG_DIR="$STORAGE_BASE/logs"
STDOUT_LOG="$LOG_DIR/qdrant-stdout.log"
STDERR_LOG="$LOG_DIR/qdrant-stderr.log"

if [ -f "$STDERR_LOG" ]; then
    STDERR_SIZE=$(wc -l < "$STDERR_LOG" 2>/dev/null || echo "0")
    STDERR_RECENT=$(tail -1 "$STDERR_LOG" 2>/dev/null || echo "No recent errors")

    echo "📋 Recent Activity"
    if [ "$STDERR_SIZE" -gt 10 ]; then
        echo -e "   ${YELLOW}⚠️  $STDERR_SIZE lines in error log${NC}"
        echo "   Last error: $STDERR_RECENT"
    else
        echo -e "   ${GREEN}✅ No significant errors${NC}"
    fi
fi
echo

# Integration status
echo "🔗 SAFLA Integration"
echo "   Neural Memory Fabric: $([ -f "$DB_PATH/collection/enhanced_memory/storage.sqlite" ] && echo "✅ Active" || echo "⚠️  Not initialized")"
echo "   Memory collections: $COLLECTIONS"
echo

# Web UI
echo "🌐 Web Interface"
echo "   Dashboard: http://localhost:6333/dashboard"
echo "   API: http://localhost:6333/"
echo

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
