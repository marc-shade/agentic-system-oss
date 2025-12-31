#!/bin/bash

# Qdrant startup script for launchd
# This ensures Qdrant starts with correct environment and configuration


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

export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"

# Detect qdrant binary location
detect_qdrant_binary() {
    # Check common locations
    for bin_path in \
        "$HOME/.local/bin/qdrant" \
        "/usr/local/bin/qdrant" \
        "/usr/bin/qdrant" \
        "$STORAGE_BASE/bin/qdrant"; do
        if [ -x "$bin_path" ]; then
            echo "$bin_path"
            return
        fi
    done
    # Fallback to PATH
    command -v qdrant 2>/dev/null
}

QDRANT_BIN=$(detect_qdrant_binary)
if [ -z "$QDRANT_BIN" ]; then
    echo "ERROR: qdrant binary not found" >&2
    exit 1
fi

# Ensure directories exist
mkdir -p "${STORAGE_BASE}/logs"
mkdir -p "${STORAGE_BASE}/databases/qdrant"

# Start qdrant (storage path is set in config file)
exec "$QDRANT_BIN" \
  --config-path "${STORAGE_BASE}/config/qdrant-config.yaml" \
  >> "${STORAGE_BASE}/logs/qdrant-stdout.log" \
  2>> "${STORAGE_BASE}/logs/qdrant-stderr.log"
