#!/bin/bash
# Database Migration Script - Phase 2
# Migrates SQLite databases from FILES to SSDRAID0 for performance

set -e

HOT_DB="/mnt/agentic-system/databases"
COLD_DB="/Volumes/FILES/agentic-system"
LOG_FILE="/mnt/agentic-system/migration.log"

echo "$(date): Starting database migration to SSDRAID0..." | tee -a "$LOG_FILE"

# Create subdirectories
mkdir -p "$HOT_DB/mcp"
mkdir -p "$HOT_DB/sensory"
mkdir -p "$HOT_DB/claude"
mkdir -p "$HOT_DB/claude/agentic-evolution"
mkdir -p "$HOT_DB/claude/brainsim"

# Function to migrate a database with integrity check
migrate_db() {
    local src="$1"
    local dest="$2"
    local name=$(basename "$src")

    echo "$(date): Migrating $name..." | tee -a "$LOG_FILE"

    # Copy database
    cp "$src" "$dest"

    # Verify integrity
    if sqlite3 "$dest/$name" "PRAGMA integrity_check;" | grep -q "ok"; then
        echo "$(date): ✅ $name migrated and verified" | tee -a "$LOG_FILE"

        # Backup original
        mv "$src" "${src}.backup-$(date +%Y%m%d)"

        # Create symlink
        ln -s "$dest/$name" "$src"
        echo "$(date): ✅ Symlink created for $name" | tee -a "$LOG_FILE"
    else
        echo "$(date): ❌ $name failed integrity check" | tee -a "$LOG_FILE"
        rm "$dest/$name"
        return 1
    fi
}

# Migrate high-priority MCP databases
echo "$(date): Phase 1: High-priority MCP databases..." | tee -a "$LOG_FILE"

if [ -f "$COLD_DB/mcp/comprehensive_monitoring.db" ]; then
    migrate_db "$COLD_DB/mcp/comprehensive_monitoring.db" "$HOT_DB/mcp"
fi

if [ -f "$COLD_DB/mcp/audit_intelligence.db" ]; then
    migrate_db "$COLD_DB/mcp/audit_intelligence.db" "$HOT_DB/mcp"
fi

if [ -f "$COLD_DB/mcp/events.db" ]; then
    migrate_db "$COLD_DB/mcp/events.db" "$HOT_DB/mcp"
fi

if [ -f "$COLD_DB/mcp/monitoring.db" ]; then
    migrate_db "$COLD_DB/mcp/monitoring.db" "$HOT_DB/mcp"
fi

if [ -f "$COLD_DB/mcp/cross_node_salon.db" ]; then
    migrate_db "$COLD_DB/mcp/cross_node_salon.db" "$HOT_DB/mcp"
fi

# Migrate sensory database
echo "$(date): Phase 2: Sensory database..." | tee -a "$LOG_FILE"

if [ -f "$COLD_DB/data/sensory/sensory_memory.db" ]; then
    migrate_db "$COLD_DB/data/sensory/sensory_memory.db" "$HOT_DB/sensory"
fi

# Migrate ~/.claude databases
echo "$(date): Phase 3: Claude system databases..." | tee -a "$LOG_FILE"

for db in ~/.claude/*.db; do
    if [ -f "$db" ]; then
        migrate_db "$db" "$HOT_DB/claude"
    fi
done

for db in ~/.claude/agentic-evolution/*.db; do
    if [ -f "$db" ]; then
        migrate_db "$db" "$HOT_DB/claude/agentic-evolution"
    fi
done

if [ -f ~/.claude/brainsim/brainsim_knowledge.db ]; then
    migrate_db ~/.claude/brainsim/brainsim_knowledge.db "$HOT_DB/claude/brainsim"
fi

echo "$(date): ✅ Database migration completed successfully!" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Summary
echo "Migration Summary:" | tee -a "$LOG_FILE"
du -sh "$HOT_DB" | tee -a "$LOG_FILE"
du -sh "$HOT_DB/mcp" | tee -a "$LOG_FILE"
du -sh "$HOT_DB/sensory" | tee -a "$LOG_FILE"
du -sh "$HOT_DB/claude" | tee -a "$LOG_FILE"

exit 0
