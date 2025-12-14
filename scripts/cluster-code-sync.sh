#!/bin/bash
#
# Cluster Code Sync Script
# Syncs agentic system code from macpro51 (Builder) to local node
#
# Usage: ./cluster-code-sync.sh [--dry-run] [--full] [--watch]
#
# This script:
# 1. Mounts SMB share from macpro51 if not mounted
# 2. Syncs .claude/, mcp-servers/, scripts/ with path translation
# 3. Preserves node-specific configs (personas, paths)
#

set -e

# Configuration

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

BUILDER_IP="192.168.1.27"
BUILDER_SHARE="agentic-system"
BUILDER_USER="marc"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[SYNC]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Detect local storage path
detect_local_storage() {
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS
        if [[ -d "$STORAGE_BASE" ]]; then
            echo "$STORAGE_BASE"
        elif [[ -d "$HOME/agentic-system" ]]; then
            echo "$HOME/agentic-system"
        else
            echo "$STORAGE_BASE"
        fi
    else
        # Linux
        if [[ -d "$STORAGE_BASE" ]]; then
            echo "$STORAGE_BASE"
        else
            echo "$HOME/agentic-system"
        fi
    fi
}

# Detect mount point for SMB share
detect_mount_point() {
    if [[ "$(uname)" == "Darwin" ]]; then
        echo "/Volumes/macpro51-agentic"
    else
        echo "/mnt/macpro51-agentic"
    fi
}

LOCAL_STORAGE=$(detect_local_storage)
MOUNT_POINT=$(detect_mount_point)

# Parse arguments
DRY_RUN=""
FULL_SYNC=false
WATCH_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run) DRY_RUN="--dry-run"; shift ;;
        --full) FULL_SYNC=true; shift ;;
        --watch) WATCH_MODE=true; shift ;;
        *) shift ;;
    esac
done

# Check if we're on the builder node itself
HOSTNAME=$(hostname -s 2>/dev/null || hostname)
if [[ "$HOSTNAME" == "macpro51" ]]; then
    log "Running on Builder node - nothing to sync from self"
    exit 0
fi

log "================================================"
log "  Cluster Code Sync from macpro51 (Builder)"
log "================================================"
log "Local storage: $LOCAL_STORAGE"
log "Mount point: $MOUNT_POINT"
[[ -n "$DRY_RUN" ]] && warn "DRY RUN MODE - no changes will be made"

# Mount SMB share if not already mounted
mount_share() {
    if mount | grep -q "$MOUNT_POINT"; then
        success "SMB share already mounted at $MOUNT_POINT"
        return 0
    fi

    log "Mounting SMB share from $BUILDER_IP..."
    mkdir -p "$MOUNT_POINT"

    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS mount
        mount -t smbfs "//${BUILDER_USER}@${BUILDER_IP}/${BUILDER_SHARE}" "$MOUNT_POINT" 2>/dev/null || {
            error "Failed to mount. Try manually: Finder → Cmd+K → smb://${BUILDER_USER}@${BUILDER_IP}/${BUILDER_SHARE}"
            return 1
        }
    else
        # Linux mount (requires cifs-utils)
        sudo mount -t cifs "//${BUILDER_IP}/${BUILDER_SHARE}" "$MOUNT_POINT" \
            -o username=${BUILDER_USER},uid=$(id -u),gid=$(id -g) 2>/dev/null || {
            error "Failed to mount. Install cifs-utils: sudo dnf install cifs-utils"
            return 1
        }
    fi

    success "Mounted SMB share at $MOUNT_POINT"
}

# Sync .claude directory (agents, commands, skills, hooks)
sync_claude_config() {
    log "Syncing Claude config (.claude/)..."

    # Ensure local .claude exists
    mkdir -p "$LOCAL_STORAGE/.claude"

    # Directories to sync
    local CLAUDE_DIRS="agents commands skills helpers"

    for dir in $CLAUDE_DIRS; do
        if [[ -d "$MOUNT_POINT/.claude/$dir" ]]; then
            log "  Syncing .claude/$dir/"
            rsync -av $DRY_RUN --delete \
                --exclude='*.pyc' \
                --exclude='__pycache__' \
                --exclude='.DS_Store' \
                "$MOUNT_POINT/.claude/$dir/" \
                "$LOCAL_STORAGE/.claude/$dir/"
        fi
    done

    # Sync hooks but preserve local customizations
    if [[ -d "$MOUNT_POINT/.claude/hooks" ]]; then
        log "  Syncing .claude/hooks/ (preserving local mods)"
        rsync -av $DRY_RUN \
            --exclude='*.pyc' \
            --exclude='__pycache__' \
            --exclude='.DS_Store' \
            --exclude='*.local.*' \
            "$MOUNT_POINT/.claude/hooks/" \
            "$LOCAL_STORAGE/.claude/hooks/"
    fi

    # Sync statusline script
    if [[ -f "$MOUNT_POINT/.claude/statusline-command.sh" ]]; then
        log "  Syncing statusline-command.sh"
        rsync -av $DRY_RUN \
            "$MOUNT_POINT/.claude/statusline-command.sh" \
            "$LOCAL_STORAGE/.claude/"
    fi

    success "Claude config synced"
}

# Sync MCP servers
sync_mcp_servers() {
    log "Syncing MCP servers..."

    mkdir -p "$LOCAL_STORAGE/mcp-servers"

    # List of MCP servers to sync
    local MCP_SERVERS=$(ls -d "$MOUNT_POINT/mcp-servers"/*/ 2>/dev/null | xargs -n1 basename)

    for server in $MCP_SERVERS; do
        if [[ -d "$MOUNT_POINT/mcp-servers/$server" ]]; then
            log "  Syncing mcp-servers/$server/"
            rsync -av $DRY_RUN \
                --exclude='*.pyc' \
                --exclude='__pycache__' \
                --exclude='.DS_Store' \
                --exclude='*.db' \
                --exclude='*.sqlite' \
                --exclude='.venv' \
                --exclude='node_modules' \
                --exclude='*.log' \
                --exclude='.archive' \
                "$MOUNT_POINT/mcp-servers/$server/" \
                "$LOCAL_STORAGE/mcp-servers/$server/"
        fi
    done

    success "MCP servers synced"
}

# Sync scripts directory
sync_scripts() {
    log "Syncing scripts..."

    mkdir -p "$LOCAL_STORAGE/scripts"

    rsync -av $DRY_RUN \
        --exclude='*.pyc' \
        --exclude='__pycache__' \
        --exclude='.DS_Store' \
        --exclude='*.log' \
        --exclude='ramdisk*' \
        "$MOUNT_POINT/scripts/" \
        "$LOCAL_STORAGE/scripts/"

    success "Scripts synced"
}

# Sync cluster-deployment
sync_cluster_deployment() {
    log "Syncing cluster-deployment..."

    mkdir -p "$LOCAL_STORAGE/cluster-deployment"

    rsync -av $DRY_RUN \
        --exclude='*.pyc' \
        --exclude='__pycache__' \
        --exclude='.DS_Store' \
        --exclude='*.log' \
        --exclude='*.db' \
        --exclude='.claude-flow' \
        "$MOUNT_POINT/cluster-deployment/" \
        "$LOCAL_STORAGE/cluster-deployment/"

    success "Cluster deployment synced"
}

# Sync intelligent-agents
sync_intelligent_agents() {
    log "Syncing intelligent-agents..."

    mkdir -p "$LOCAL_STORAGE/intelligent-agents"

    rsync -av $DRY_RUN \
        --exclude='*.pyc' \
        --exclude='__pycache__' \
        --exclude='.DS_Store' \
        --exclude='*.log' \
        --exclude='data/' \
        "$MOUNT_POINT/intelligent-agents/" \
        "$LOCAL_STORAGE/intelligent-agents/"

    success "Intelligent agents synced"
}

# Update ~/.claude.json with correct local paths
update_claude_json() {
    log "Note: ~/.claude.json may need manual path updates"
    log "  Builder paths: $STORAGE_BASE/..."
    log "  Your paths: $LOCAL_STORAGE/..."

    if [[ -f "$HOME/.claude.json" ]]; then
        # Check if paths need updating
        if grep -q "$STORAGE_BASE" "$HOME/.claude.json"; then
            warn "~/.claude.json contains /mnt/agentic-system paths"
            warn "These should be updated to: $LOCAL_STORAGE"

            if [[ -z "$DRY_RUN" ]]; then
                # Create backup
                cp "$HOME/.claude.json" "$HOME/.claude.json.bak"

                # Replace paths (careful with sed on macOS)
                if [[ "$(uname)" == "Darwin" ]]; then
                    sed -i '' "s|/mnt/agentic-system|$LOCAL_STORAGE|g" "$HOME/.claude.json"
                else
                    sed -i "s|/mnt/agentic-system|$LOCAL_STORAGE|g" "$HOME/.claude.json"
                fi
                success "Updated paths in ~/.claude.json (backup at ~/.claude.json.bak)"
            fi
        fi
    fi
}

# Main sync function
do_sync() {
    mount_share || exit 1

    echo ""
    sync_claude_config
    echo ""
    sync_mcp_servers
    echo ""
    sync_scripts
    echo ""
    sync_cluster_deployment
    echo ""
    sync_intelligent_agents
    echo ""
    update_claude_json

    echo ""
    log "================================================"
    success "Sync complete!"
    log "================================================"
    log ""
    log "Next steps:"
    log "  1. Restart Claude Code to pick up changes"
    log "  2. Verify MCP servers load correctly"
    log "  3. Test slash commands and agents"
    log ""
    log "To auto-sync on changes, run: $0 --watch"
}

# Watch mode - sync when builder changes
watch_mode() {
    log "Starting watch mode - will sync on changes from Builder"
    log "Press Ctrl+C to stop"

    mount_share || exit 1

    while true; do
        # Check for changes (using a simple timestamp approach)
        REMOTE_STAMP=$(stat -c %Y "$MOUNT_POINT/.claude" 2>/dev/null || stat -f %m "$MOUNT_POINT/.claude" 2>/dev/null)
        LOCAL_STAMP=$(stat -c %Y "$LOCAL_STORAGE/.claude" 2>/dev/null || stat -f %m "$LOCAL_STORAGE/.claude" 2>/dev/null)

        if [[ "$REMOTE_STAMP" -gt "$LOCAL_STAMP" ]]; then
            log "Changes detected on Builder - syncing..."
            do_sync
        fi

        sleep 60
    done
}

# Run
if $WATCH_MODE; then
    watch_mode
else
    do_sync
fi
