#!/bin/bash
# Cluster Node Configuration
# Source this file to set cluster environment variables
# Usage: source $STORAGE_BASE/config/cluster-env.sh
# Updated: 2025-12-30 - Fixed stale IPs (orchestrator .16, researcher .76)

# Builder Node (macpro51 - Linux x86_64)
export CLUSTER_BUILDER_HOST="macpro51.local"
export CLUSTER_BUILDER_IP="192.168.1.27"

# Orchestrator Node (mac-studio - macOS ARM64)
export CLUSTER_ORCHESTRATOR_HOST="mac-studio.local"
export CLUSTER_ORCHESTRATOR_IP="192.168.1.16"

# Researcher Node (macbook-air - macOS ARM64)
export CLUSTER_RESEARCHER_HOST="macbook-air.local"
export CLUSTER_RESEARCHER_IP="192.168.1.76"

# Inference Node (completeu-server - macOS ARM64)
export CLUSTER_INFERENCE_HOST="completeu-server.local"
export CLUSTER_INFERENCE_IP="192.168.1.186"

# Small Inference Node (macmini - macOS ARM64)
export CLUSTER_SMALL_INFERENCE_HOST="macmini.local"
export CLUSTER_SMALL_INFERENCE_IP="192.168.1.2"

# Sentinel Node (bpi-sentinel - Linux ARM64)
export CLUSTER_SENTINEL_HOST="bpi-sentinel.local"
export CLUSTER_SENTINEL_IP="192.168.1.234"

# SSH Configuration
export CLUSTER_SSH_USER="marc"
export CLUSTER_SSH_TIMEOUT="5"
export CLUSTER_SSH_CONNECT_TIMEOUT="2"
export CLUSTER_SSH_RETRIES="2"

# Load thresholds
export CLUSTER_CPU_THRESHOLD="40"
export CLUSTER_LOAD_THRESHOLD="4"
export CLUSTER_MEMORY_THRESHOLD="80"

# Command timeout
export CLUSTER_CMD_TIMEOUT="300"
export CLUSTER_STATUS_TIMEOUT="5"

# Current node info
export CLUSTER_NODE_ROLE="${CLUSTER_NODE_ROLE:-unknown}"
export CLUSTER_STORAGE_BASE="${CLUSTER_STORAGE_BASE:-}"

# Agentic system path
export AGENTIC_SYSTEM_PATH="${CLUSTER_STORAGE_BASE:-/Volumes/SSDRAID0/agentic-system}"

echo "Cluster environment loaded for node: $CLUSTER_NODE_ROLE"
