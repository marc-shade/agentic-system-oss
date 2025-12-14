#!/bin/bash
# Master Boot Orchestrator for Autonomous Agentic System
# Manages startup sequence with proper dependencies and timing

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

LOG_FILE="$STORAGE_BASE/logs/boot-orchestrator.log"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

check_service() {
    local service_name="$1"
    local check_command="$2"

    if eval "$check_command" > /dev/null 2>&1; then
        log "✅ $service_name is running"
        return 0
    else
        log "❌ $service_name is NOT running"
        return 1
    fi
}

wait_for_service() {
    local service_name="$1"
    local check_command="$2"
    local max_wait="${3:-60}"
    local wait_count=0

    log "⏳ Waiting for $service_name..."

    while [ $wait_count -lt $max_wait ]; do
        if eval "$check_command" > /dev/null 2>&1; then
            log "✅ $service_name is ready"
            return 0
        fi

        sleep 1
        wait_count=$((wait_count + 1))
    done

    log "❌ $service_name failed to start within ${max_wait}s"
    return 1
}

start_service() {
    local service_name="$1"
    local start_script="$2"
    local check_command="$3"

    log "🚀 Starting $service_name..."

    if eval "$check_command" > /dev/null 2>&1; then
        log "⚠️  $service_name already running"
        return 0
    fi

    if [ -f "$start_script" ]; then
        "$start_script" >> "$LOG_FILE" 2>&1 &
        sleep 3
        if wait_for_service "$service_name" "$check_command" 30; then
            return 0
        else
            return 1
        fi
    else
        log "❌ Start script not found: $start_script"
        return 1
    fi
}

log "═══════════════════════════════════════════════════════════"
log "🚀 AUTONOMOUS AGENTIC SYSTEM - BOOT ORCHESTRATION"
log "═══════════════════════════════════════════════════════════"

# Phase 1: Foundation Services (no dependencies)
log ""
log "📍 PHASE 1: Foundation Services"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Qdrant Vector Database
start_service "Qdrant" \
    "$SCRIPT_DIR/qdrant-monitor.sh" \
    "curl -sf http://localhost:6333/healthz"

log ""
log "⏱️  Waiting 5 seconds before Phase 2..."
sleep 5

# Phase 2: Core Infrastructure (independent services)
log ""
log "📍 PHASE 2: Core Infrastructure"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Start Temporal, n8n, and AutoKitteh in parallel
start_service "Temporal Server" \
    "$SCRIPT_DIR/temporal-monitor.sh" \
    "lsof -i:7233" &
TEMPORAL_PID=$!

start_service "n8n" \
    "$SCRIPT_DIR/n8n-monitor.sh" \
    "curl -sf http://localhost:5678" &
N8N_PID=$!

start_service "AutoKitteh" \
    "$SCRIPT_DIR/autokitteh-monitor.sh" \
    "curl -sf http://localhost:9980/health" &
AUTOKITTEH_PID=$!

# Wait for parallel starts to complete
wait $TEMPORAL_PID
wait $N8N_PID
wait $AUTOKITTEH_PID

log ""
log "⏱️  Waiting 10 seconds for services to stabilize..."
sleep 10

# Phase 3: Dependent Services (need Temporal)
log ""
log "📍 PHASE 3: Workflow Workers"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Temporal Workers (need Temporal server)
if check_service "Temporal Server" "lsof -i:7233"; then
    log "🚀 Starting Temporal Workers..."
    "$SCRIPT_DIR/start-temporal-workers.sh" >> "$LOG_FILE" 2>&1 &
    sleep 10
    log "✅ Temporal Workers started"
else
    log "⚠️  Skipping Temporal Workers (Temporal Server not ready)"
fi

log ""
log "⏱️  Waiting 5 seconds for workers to register..."
sleep 5

# Phase 4: Status Summary
log ""
log "📍 FINAL STATUS"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

check_service "Qdrant" "curl -sf http://localhost:6333/healthz"
check_service "Temporal Server" "lsof -i:7233"
check_service "n8n" "curl -sf http://localhost:5678"
check_service "AutoKitteh" "curl -sf http://localhost:9980/health"

# Count running workers
WORKER_COUNT=$(ps aux | grep -E "(agi_learning|ai_agent_monitoring|youtube_processing|cross_system|overnight_automation)" | grep python | grep -v grep | wc -l | tr -d ' ')
log "Temporal Workers: $WORKER_COUNT active"

log ""
log "═══════════════════════════════════════════════════════════"
log "✅ BOOT ORCHESTRATION COMPLETE"
log "═══════════════════════════════════════════════════════════"
log ""
log "📊 System Status Dashboard: $STORAGE_BASE/claude-status.sh"
log "📋 Logs: tail -f $LOG_FILE"
log ""
