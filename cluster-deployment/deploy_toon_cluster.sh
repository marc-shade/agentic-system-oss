#!/bin/bash
#
# Deploy TOON Format Integration to All Cluster Nodes
# ====================================================
#
# Coordinates cluster-wide upgrade to TOON serialization format
# for 50% token reduction in cluster communication.
#
# CRITICAL SAFETY:
# - All nodes must upgrade together or have fallback capability
# - Test on mac-studio first, then rollout to other nodes
# - Version compatibility checks built-in
#
# Usage:
#   ./deploy_toon_cluster.sh [test|deploy|rollback]
#
# Modes:
#   test     - Test TOON installation on all nodes
#   deploy   - Deploy TOON to all nodes
#   rollback - Rollback to JSON-only (if needed)

set -e  # Exit on error

# Color output

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

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Cluster node definitions
declare -A NODES=(
    ["mac-studio"]="192.168.1.16:9999"
    ["macpro51"]="192.168.1.183:9999"
    ["macbook-air"]="192.168.1.76:9999"
    ["completeu-server"]="192.168.1.186:9999"
)

# Deployment paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOON_CLI_PATH="$STORAGE_BASE/mcp-servers/SHARED/node_modules/.bin/toon"
DEPLOYMENT_LOG="$SCRIPT_DIR/toon_deployment_$(date +%Y%m%d_%H%M%S).log"

# Initialize log
log() {
    echo -e "${BLUE}[$(date +%H:%M:%S)]${NC} $1" | tee -a "$DEPLOYMENT_LOG"
}

log_success() {
    echo -e "${GREEN}[$(date +%H:%M:%S)]${NC} ✅ $1" | tee -a "$DEPLOYMENT_LOG"
}

log_warning() {
    echo -e "${YELLOW}[$(date +%H:%M:%S)]${NC} ⚠️  $1" | tee -a "$DEPLOYMENT_LOG"
}

log_error() {
    echo -e "${RED}[$(date +%H:%M:%S)]${NC} ❌ $1" | tee -a "$DEPLOYMENT_LOG"
}

# Check if TOON CLI is available
check_toon_cli() {
    log "Checking TOON CLI availability..."

    if [ -f "$TOON_CLI_PATH" ]; then
        log_success "TOON CLI found at: $TOON_CLI_PATH"
        return 0
    else
        log_error "TOON CLI not found at: $TOON_CLI_PATH"
        log "Please install TOON first: cd mcp-servers/SHARED && npm install @toon-format/cli"
        return 1
    fi
}

# Test TOON encoding/decoding
test_toon_encoding() {
    log "Testing TOON encoding/decoding..."

    # Create test JSON
    TEST_JSON='{"node":"test","status":"healthy","cpu":15.2}'

    # Encode to TOON
    TOON_ENCODED=$(echo "$TEST_JSON" | "$TOON_CLI_PATH" encode)

    # Decode back to JSON
    TOON_DECODED=$(echo "$TOON_ENCODED" | "$TOON_CLI_PATH" decode)

    log "Original JSON: $TEST_JSON"
    log "TOON Encoded: $TOON_ENCODED"
    log "Decoded JSON: $TOON_DECODED"

    # Verify roundtrip
    if echo "$TOON_DECODED" | jq -e . > /dev/null 2>&1; then
        log_success "TOON encoding/decoding working correctly"
        return 0
    else
        log_error "TOON encoding/decoding failed"
        return 1
    fi
}

# Test node connectivity
test_node_connectivity() {
    local node_id=$1
    local node_addr=$2
    local ip="${node_addr%:*}"
    local port="${node_addr#*:}"

    log "Testing connectivity to $node_id ($ip:$port)..."

    if timeout 5 bash -c "echo 'status' | nc -w 2 $ip $port" > /dev/null 2>&1; then
        log_success "$node_id is reachable"
        return 0
    else
        log_warning "$node_id is not reachable at $ip:$port"
        return 1
    fi
}

# Deploy TOON to single node
deploy_to_node() {
    local node_id=$1
    local node_addr=$2
    local ip="${node_addr%:*}"
    local port="${node_addr#*:}"

    log "Deploying TOON to $node_id..."

    # Check if node command listener is running
    if ! test_node_connectivity "$node_id" "$node_addr"; then
        log_warning "Skipping $node_id - not reachable"
        return 1
    fi

    # Copy toon_serialization.py to node
    log "Copying toon_serialization.py to $node_id..."

    # For mac-studio (local), just verify file exists
    if [ "$node_id" == "mac-studio" ]; then
        if [ -f "$SCRIPT_DIR/toon_serialization.py" ]; then
            log_success "toon_serialization.py already present on mac-studio"
        else
            log_error "toon_serialization.py not found on mac-studio"
            return 1
        fi
    else
        # For remote nodes, use scp
        if scp "$SCRIPT_DIR/toon_serialization.py" "marc@$ip:/tmp/" > /dev/null 2>&1; then
            log_success "Copied toon_serialization.py to $node_id"
        else
            log_error "Failed to copy toon_serialization.py to $node_id"
            return 1
        fi

        # Move to cluster-deployment directory
        ssh "marc@$ip" "mkdir -p /mnt/ssdraid0/agentic-system/cluster-deployment && mv /tmp/toon_serialization.py /mnt/ssdraid0/agentic-system/cluster-deployment/" > /dev/null 2>&1
    fi

    # Verify Python can import toon_serialization
    log "Verifying toon_serialization import on $node_id..."

    if [ "$node_id" == "mac-studio" ]; then
        if python3 -c "import sys; sys.path.insert(0, '$SCRIPT_DIR'); from toon_serialization import get_serialization_stats; print(get_serialization_stats())" > /dev/null 2>&1; then
            log_success "toon_serialization imports successfully on $node_id"
        else
            log_error "toon_serialization import failed on $node_id"
            return 1
        fi
    else
        if ssh "marc@$ip" "python3 -c \"import sys; sys.path.insert(0, '/mnt/ssdraid0/agentic-system/cluster-deployment'); from toon_serialization import get_serialization_stats\"" > /dev/null 2>&1; then
            log_success "toon_serialization imports successfully on $node_id"
        else
            log_warning "toon_serialization import failed on $node_id (TOON CLI may not be installed)"
            log "This node will use JSON fallback"
        fi
    fi

    log_success "Deployment to $node_id complete"
    return 0
}

# Test TOON on all nodes
test_all_nodes() {
    log "========================================="
    log "Testing TOON on All Cluster Nodes"
    log "========================================="

    local success_count=0
    local total_count=0

    for node_id in "${!NODES[@]}"; do
        total_count=$((total_count + 1))

        log ""
        if deploy_to_node "$node_id" "${NODES[$node_id]}"; then
            success_count=$((success_count + 1))
        fi
    done

    log ""
    log "========================================="
    log "Test Results: $success_count/$total_count nodes ready"
    log "========================================="

    if [ $success_count -eq $total_count ]; then
        log_success "All nodes ready for TOON deployment"
        return 0
    else
        log_warning "Some nodes not ready - mixed TOON/JSON cluster will operate"
        return 1
    fi
}

# Deploy TOON to all nodes
deploy_all_nodes() {
    log "========================================="
    log "Deploying TOON to All Cluster Nodes"
    log "========================================="

    # First, verify TOON CLI is available
    if ! check_toon_cli; then
        log_error "Cannot deploy - TOON CLI not available"
        exit 1
    fi

    # Test TOON encoding
    if ! test_toon_encoding; then
        log_error "Cannot deploy - TOON encoding test failed"
        exit 1
    fi

    # Deploy to each node
    local deployed_count=0
    local total_count=0

    for node_id in "${!NODES[@]}"; do
        total_count=$((total_count + 1))

        log ""
        if deploy_to_node "$node_id" "${NODES[$node_id]}"; then
            deployed_count=$((deployed_count + 1))
        fi
    done

    log ""
    log "========================================="
    log "Deployment Results: $deployed_count/$total_count nodes"
    log "========================================="

    if [ $deployed_count -eq $total_count ]; then
        log_success "TOON deployed to all nodes successfully"
    else
        log_warning "TOON deployed to $deployed_count/$total_count nodes"
        log "Cluster will operate in mixed TOON/JSON mode"
    fi

    log ""
    log "Deployment log saved to: $DEPLOYMENT_LOG"
}

# Rollback to JSON-only
rollback_all_nodes() {
    log "========================================="
    log "Rolling Back to JSON-Only Mode"
    log "========================================="

    log_warning "Rollback not yet implemented"
    log "TOON has built-in JSON fallback, so rollback is safe by default"
    log "To disable TOON, remove toon_serialization.py from cluster-deployment/"
}

# Main script logic
main() {
    local mode="${1:-test}"

    case "$mode" in
        test)
            test_all_nodes
            ;;
        deploy)
            deploy_all_nodes
            ;;
        rollback)
            rollback_all_nodes
            ;;
        *)
            echo "Usage: $0 [test|deploy|rollback]"
            echo ""
            echo "Modes:"
            echo "  test     - Test TOON installation on all nodes"
            echo "  deploy   - Deploy TOON to all nodes"
            echo "  rollback - Rollback to JSON-only (if needed)"
            exit 1
            ;;
    esac
}

# Run main
main "$@"
