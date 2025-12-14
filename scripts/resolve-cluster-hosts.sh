#!/bin/bash
# Resolve cluster hostnames via mDNS/Avahi
# Usage: source resolve-cluster-hosts.sh
# Or: ./resolve-cluster-hosts.sh <hostname.local>

# Helper function to resolve hostname to IP
resolve_host() {
    local hostname="$1"
    local ip=""

    # Try getent first (uses nsswitch.conf, respects mDNS)
    ip=$(getent hosts "$hostname" 2>/dev/null | awk '{print $1}' | head -1)

    # Fallback to avahi-resolve
    if [ -z "$ip" ]; then
        ip=$(avahi-resolve -4 -n "$hostname" 2>/dev/null | awk '{print $2}')
    fi

    # Fallback to dig with mdns
    if [ -z "$ip" ]; then
        ip=$(dig +short "$hostname" @224.0.0.251 -p 5353 2>/dev/null | head -1)
    fi

    echo "$ip"
}

# If called with argument, resolve and exit
if [ -n "$1" ]; then
    resolve_host "$1"
    exit 0
fi

# Export resolved IPs for sourcing
export BUILDER_HOST="macpro51.local"
export ORCHESTRATOR_HOST="Marcs-Mac-Studio.local"
export RESEARCHER_HOST="Marcs-MacBook-Air.local"
export AI_INFERENCE_HOST="completeu-server.local"
export SMALL_INFERENCE_HOST="macmini.local"
export SENTINEL_HOST="bpi-sentinel.local"

# Resolve IPs on demand (only if needed)
get_builder_ip() { resolve_host "$BUILDER_HOST"; }
get_orchestrator_ip() { resolve_host "$ORCHESTRATOR_HOST"; }
get_researcher_ip() { resolve_host "$RESEARCHER_HOST"; }
get_ai_inference_ip() { resolve_host "$AI_INFERENCE_HOST"; }
get_small_inference_ip() { resolve_host "$SMALL_INFERENCE_HOST"; }
get_sentinel_ip() { resolve_host "$SENTINEL_HOST"; }

# Convex backend - always resolve via mDNS
get_convex_url() {
    local ip=$(get_builder_ip)
    echo "http://${ip}:3210"
}

# Print all resolved hosts if run directly
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    echo "=== Cluster Host Resolution ==="
    echo "Builder:        $BUILDER_HOST → $(get_builder_ip)"
    echo "Orchestrator:   $ORCHESTRATOR_HOST → $(get_orchestrator_ip)"
    echo "Researcher:     $RESEARCHER_HOST → $(get_researcher_ip)"
    echo "AI Inference:   $AI_INFERENCE_HOST → $(get_ai_inference_ip)"
    echo "Small Inference: $SMALL_INFERENCE_HOST → $(get_small_inference_ip)"
    echo "Sentinel:       $SENTINEL_HOST → $(get_sentinel_ip)"
    echo ""
    echo "Convex URL: $(get_convex_url)"
fi
