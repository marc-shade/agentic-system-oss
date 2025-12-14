#!/bin/bash
#
# Local Incremental Backup Script
# Backs up critical AGI system data to /mnt/backup-local
# Uses btrfs snapshots for space-efficient incremental backups
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

BACKUP_ROOT="/mnt/backup-local"
SOURCE="$STORAGE_BASE"
DATE=$(date +%Y-%m-%d-%H%M)
SNAPSHOT_DIR="$BACKUP_ROOT/snapshots"
CURRENT_DIR="$BACKUP_ROOT/current"
LOG_FILE="/var/log/backup-local.log"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Check if backup drive is mounted
if ! mountpoint -q "$BACKUP_ROOT"; then
    log "ERROR: $BACKUP_ROOT is not mounted!"
    exit 1
fi

log "=== Starting local backup ==="

# Create snapshot of current state before syncing new data
if [ -d "$CURRENT_DIR" ]; then
    log "Creating read-only snapshot: $SNAPSHOT_DIR/$DATE"
    sudo btrfs subvolume snapshot -r "$CURRENT_DIR" "$SNAPSHOT_DIR/$DATE"
else
    log "First backup - creating current subvolume"
    sudo btrfs subvolume create "$CURRENT_DIR"
fi

# Sync critical data from md0 to current backup
log "Syncing critical data..."

# Create directory structure
mkdir -p "$CURRENT_DIR"/{databases,intelligent-agents,mcp-servers,configs}

# Backup databases
if [ -d "$SOURCE/databases" ]; then
    log "  - Backing up databases..."
    rsync -a --delete \
        --exclude '*.tmp' \
        --exclude '*.lock' \
        "$SOURCE/databases/" "$CURRENT_DIR/databases/"
fi

# Backup intelligent agents
if [ -d "$SOURCE/intelligent-agents" ]; then
    log "  - Backing up intelligent agents..."
    rsync -a --delete \
        --exclude '__pycache__' \
        --exclude '*.pyc' \
        --exclude '.pytest_cache' \
        "$SOURCE/intelligent-agents/" "$CURRENT_DIR/intelligent-agents/"
fi

# Backup MCP servers
if [ -d "$SOURCE/mcp-servers" ]; then
    log "  - Backing up MCP servers..."
    rsync -a --delete \
        --exclude 'node_modules' \
        --exclude '__pycache__' \
        --exclude 'dist' \
        --exclude '.venv' \
        --exclude 'build' \
        "$SOURCE/mcp-servers/" "$CURRENT_DIR/mcp-servers/"
fi

# Backup critical config files
log "  - Backing up config files..."
[ -f "$SOURCE/agi_config.json" ] && cp "$SOURCE/agi_config.json" "$CURRENT_DIR/configs/"
[ -d "$SOURCE/.git" ] && rsync -a "$SOURCE/.git/" "$CURRENT_DIR/configs/git/"
[ -d "$SOURCE/scripts" ] && rsync -a --delete "$SOURCE/scripts/" "$CURRENT_DIR/configs/scripts/"

# Backup user configs
if [ -d "/home/marc/.claude" ]; then
    log "  - Backing up Claude Code configs..."
    rsync -a --delete /home/marc/.claude/ "$CURRENT_DIR/configs/claude/"
fi

# Delete snapshots older than 30 days
log "Cleaning old snapshots (keeping last 30 days)..."
find "$SNAPSHOT_DIR" -maxdepth 1 -type d -mtime +30 | while read -r old_snapshot; do
    if [ "$old_snapshot" != "$SNAPSHOT_DIR" ]; then
        log "  - Deleting old snapshot: $(basename "$old_snapshot")"
        sudo btrfs subvolume delete "$old_snapshot" || true
    fi
done

# Report backup statistics
BACKUP_SIZE=$(du -sh "$CURRENT_DIR" | cut -f1)
SNAPSHOT_COUNT=$(find "$SNAPSHOT_DIR" -maxdepth 1 -type d | wc -l)
DISK_USAGE=$(df -h "$BACKUP_ROOT" | tail -1 | awk '{print $5}')

log "=== Backup completed successfully ==="
log "Backup size: $BACKUP_SIZE"
log "Total snapshots: $((SNAPSHOT_COUNT - 1))"
log "Disk usage: $DISK_USAGE"
log "Latest snapshot: $SNAPSHOT_DIR/$DATE"

exit 0
