#!/bin/bash
# Agent Memory Migration Script - Phase 3
# Migrates agent memory directories from ~/.claude to SSDRAID0

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

HOT_MEMORY="$STORAGE_BASE/agent-memory"
LOG_FILE="$STORAGE_BASE/migration.log"

echo "$(date): Starting agent memory migration to SSDRAID0..." | tee -a "$LOG_FILE"

# Create subdirectories
mkdir -p "$HOT_MEMORY/enhanced_memories"
mkdir -p "$HOT_MEMORY/agent_memories"
mkdir -p "$HOT_MEMORY/conversation_memories"
mkdir -p "$HOT_MEMORY/agentic-evolution"

# Function to migrate directory with backup
migrate_dir() {
    local src="$1"
    local dest="$2"
    local name=$(basename "$src")

    if [ ! -d "$src" ]; then
        echo "$(date): ⚠️  $name not found at $src" | tee -a "$LOG_FILE"
        return 0
    fi

    echo "$(date): Migrating $name..." | tee -a "$LOG_FILE"

    # Copy directory with rsync
    rsync -av "$src/" "$dest/" >> "$LOG_FILE" 2>&1

    # Verify copy by counting files
    src_count=$(find "$src" -type f | wc -l | tr -d ' ')
    dest_count=$(find "$dest" -type f | wc -l | tr -d ' ')

    if [ "$src_count" -eq "$dest_count" ]; then
        src_size=$(du -sh "$src" | cut -f1)
        echo "$(date): ✅ $name migrated and verified ($src_count files, $src_size)" | tee -a "$LOG_FILE"

        # Backup original
        mv "$src" "${src}.backup-$(date +%Y%m%d)"

        # Create symlink
        ln -s "$dest" "$src"
        echo "$(date): ✅ Symlink created for $name" | tee -a "$LOG_FILE"
    else
        echo "$(date): ❌ $name file count mismatch (src: $src_count, dest: $dest_count)" | tee -a "$LOG_FILE"
        rm -rf "$dest"
        return 1
    fi
}

# Migrate enhanced memories (enhanced-memory-mcp database)
echo "$(date): Phase 1: Enhanced Memory MCP..." | tee -a "$LOG_FILE"
migrate_dir "$HOME/.claude/enhanced_memories" "$HOT_MEMORY/enhanced_memories"

# Migrate agent memories
echo "$(date): Phase 2: Agent Memories..." | tee -a "$LOG_FILE"
migrate_dir "$HOME/.claude/agent_memories" "$HOT_MEMORY/agent_memories"

# Migrate conversation memories
echo "$(date): Phase 3: Conversation Memories..." | tee -a "$LOG_FILE"
migrate_dir "$HOME/.claude/conversation_memories" "$HOT_MEMORY/conversation_memories"

# Migrate agentic-evolution data
echo "$(date): Phase 4: Agentic Evolution..." | tee -a "$LOG_FILE"
migrate_dir "$HOME/.claude/agentic-evolution" "$HOT_MEMORY/agentic-evolution"

# Migrate basic memory if exists
if [ -d "$STORAGE_BASE/mcp/.basic-memory" ]; then
    echo "$(date): Phase 5: Basic Memory MCP..." | tee -a "$LOG_FILE"
    mkdir -p "$HOT_MEMORY/basic-memory"
    rsync -av "$STORAGE_BASE/mcp/.basic-memory/" "$HOT_MEMORY/basic-memory/" >> "$LOG_FILE" 2>&1

    # Backup and symlink
    mv "$STORAGE_BASE/mcp/.basic-memory" "$STORAGE_BASE/mcp/.basic-memory.backup-$(date +%Y%m%d)"
    ln -s "$HOT_MEMORY/basic-memory" "$STORAGE_BASE/mcp/.basic-memory"
    echo "$(date): ✅ Basic memory migrated and symlinked" | tee -a "$LOG_FILE"
fi

echo "$(date): ✅ Agent memory migration completed successfully!" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Summary
echo "Migration Summary:" | tee -a "$LOG_FILE"
du -sh "$HOT_MEMORY" | tee -a "$LOG_FILE"
du -sh "$HOT_MEMORY/enhanced_memories" | tee -a "$LOG_FILE"
du -sh "$HOT_MEMORY/agent_memories" | tee -a "$LOG_FILE"
du -sh "$HOT_MEMORY/conversation_memories" | tee -a "$LOG_FILE"
du -sh "$HOT_MEMORY/agentic-evolution" | tee -a "$LOG_FILE"

exit 0
