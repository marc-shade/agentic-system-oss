#!/bin/bash
# Claude Code Cluster Wrapper
# Wraps bash commands to automatically use cluster when beneficial

# Source cluster offload functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# Check if command should be offloaded
should_offload() {
    local cmd="$1"

    # Offload these patterns
    if [[ "$cmd" =~ (make|cargo|npm|pytest|jest|build|test|compile) ]]; then
        return 0
    fi

    # Don't offload simple commands
    if [[ "$cmd" =~ ^(ls|cat|echo|pwd|cd) ]]; then
        return 1
    fi

    return 1
}

# Main logic
COMMAND="$@"

if should_offload "$COMMAND"; then
    # Offload to cluster
    python3 "$SCRIPT_DIR/cluster_offload.py" "$COMMAND"
else
    # Execute locally
    eval "$COMMAND"
fi
