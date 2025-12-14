#!/bin/bash
#
# Cluster Memory Rsync - Bidirectional sync with orchestrator
# Uses rsync over SSH for reliable cluster database synchronization
#

set -e


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

ORCHESTRATOR="marc@192.168.1.16"
ORCHESTRATOR_PATH="$STORAGE_BASE/databases/cluster"
LOCAL_PATH="$STORAGE_BASE/databases/cluster"
LOG_FILE="$HOME/.claude/cluster-memory-sync.log"
LOCK_FILE="/tmp/cluster-memory-sync.lock"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Prevent concurrent runs
if [ -f "$LOCK_FILE" ]; then
    PID=$(cat "$LOCK_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        log "Another sync is running (PID $PID), exiting"
        exit 0
    fi
fi
echo $$ > "$LOCK_FILE"
trap "rm -f $LOCK_FILE" EXIT

log "=== Starting cluster memory sync ==="

# Check orchestrator connectivity
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "$ORCHESTRATOR" "echo 'connected'" >/dev/null 2>&1; then
    log "ERROR: Cannot connect to orchestrator"
    exit 1
fi

# PULL: Get latest from orchestrator (orchestrator is source of truth for shared memories)
log "PULL: Syncing from orchestrator..."
rsync -az --delete \
    --exclude='*.backup*' \
    --exclude='tmux-sessions' \
    --exclude='nodes/macpro51' \
    "$ORCHESTRATOR:$ORCHESTRATOR_PATH/" \
    "$LOCAL_PATH/" 2>&1 | tee -a "$LOG_FILE"

# PUSH: Send our local node-specific data back to orchestrator
log "PUSH: Sending local node data to orchestrator..."

# Ensure our node directory exists on orchestrator
ssh "$ORCHESTRATOR" "mkdir -p $ORCHESTRATOR_PATH/nodes/macpro51"

# Sync our node-specific memories
if [ -d "$LOCAL_PATH/nodes/macpro51" ]; then
    rsync -az \
        "$LOCAL_PATH/nodes/macpro51/" \
        "$ORCHESTRATOR:$ORCHESTRATOR_PATH/nodes/macpro51/" 2>&1 | tee -a "$LOG_FILE"
fi

# Push shared_memories.db changes (merge strategy: our entries get pushed)
log "PUSH: Syncing shared_memories.db..."
rsync -az \
    "$LOCAL_PATH/shared_memories.db" \
    "$ORCHESTRATOR:$ORCHESTRATOR_PATH/shared_memories.db" 2>&1 | tee -a "$LOG_FILE"

# Sync any local enhanced memories to shared pool (selective push)
# Only push high-value memories based on access count or explicit sharing flag
LOCAL_ENHANCED_DB="$HOME/.claude/enhanced_memories/memory.db"
if [ -f "$LOCAL_ENHANCED_DB" ]; then
    log "Checking for high-value memories to share..."
    # Use the Python sync script for intelligent syncing
    python3 $STORAGE_BASE/scripts/cluster-memory-sync.py push 2>&1 | tee -a "$LOG_FILE" || true
fi

log "=== Sync complete ==="

# Report sync status
SHARED_COUNT=$(sqlite3 "$LOCAL_PATH/shared_memories.db" "SELECT COUNT(*) FROM entities;" 2>/dev/null || echo "0")
NODE_CHAT_COUNT=$(sqlite3 "$LOCAL_PATH/node_chat.db" "SELECT COUNT(*) FROM messages;" 2>/dev/null || echo "0")
log "Stats: shared_memories=$SHARED_COUNT entities, node_chat=$NODE_CHAT_COUNT messages"
