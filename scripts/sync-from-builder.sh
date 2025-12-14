#!/bin/bash
# Sync configuration and scripts from builder node
# Usage: ./sync-from-builder.sh


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

BUILDER_HOST="macpro51.local"
BUILDER_PATH="$STORAGE_BASE"
LOCAL_PATH="${CLUSTER_STORAGE_BASE:-$(dirname $(dirname $0))}"

echo "Syncing from $BUILDER_HOST to $LOCAL_PATH..."

# Sync config directory
rsync -avz --delete \
    "marc@$BUILDER_HOST:$BUILDER_PATH/config/" \
    "$LOCAL_PATH/config/"

# Sync scripts directory
rsync -avz --delete \
    "marc@$BUILDER_HOST:$BUILDER_PATH/scripts/" \
    "$LOCAL_PATH/scripts/"

# Sync cluster deployment
rsync -avz --delete \
    "marc@$BUILDER_HOST:$BUILDER_PATH/cluster-deployment/" \
    "$LOCAL_PATH/cluster-deployment/"

echo "Sync complete!"
