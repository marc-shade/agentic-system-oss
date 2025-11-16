#!/bin/bash
# Platform-agnostic storage path detection
# Auto-detects macOS vs Linux and sets appropriate base path
# Can be overridden with AGENTIC_ROOT environment variable

# Check if user has set custom path
if [ -n "$AGENTIC_ROOT" ]; then
    echo "$AGENTIC_ROOT"
    exit 0
fi

# Auto-detect based on platform
case "$(uname -s)" in
    Darwin)
        # macOS - use SSDRAID0
        if [ -d "/Volumes/SSDRAID0/agentic-system" ]; then
            echo "/Volumes/SSDRAID0/agentic-system"
        elif [ -d "/Volumes/FILES/agentic-system" ]; then
            # Fallback to FILES if SSDRAID0 not mounted
            echo "/Volumes/FILES/agentic-system"
        else
            echo "ERROR: No agentic-system found on macOS volumes" >&2
            exit 1
        fi
        ;;
    Linux)
        # Linux - use home directory
        if [ -d "/home/marc/agentic-system" ]; then
            echo "/home/marc/agentic-system"
        elif [ -d "/home/$USER/agentic-system" ]; then
            echo "/home/$USER/agentic-system"
        else
            echo "ERROR: No agentic-system found in Linux home" >&2
            exit 1
        fi
        ;;
    *)
        echo "ERROR: Unsupported platform: $(uname -s)" >&2
        exit 1
        ;;
esac
