#!/bin/bash
# Dynamic cluster node IP discovery via avahi/mDNS
# Usage: source scripts/get-cluster-ips.sh
# Or:    ./scripts/get-cluster-ips.sh

# Get fresh IP from network using .local hostname
# Prefers wired (wls5) over wireless for speed
get_node_ip() {
    local hostname_pattern="$1"
    # Try wired interface first (usually faster), then fallback to any
    local ip=$(avahi-browse -atrp 2>/dev/null | grep "_ssh._tcp" | grep "IPv4" | grep "wls5" | grep -i "$hostname_pattern" | head -1 | cut -d';' -f8)
    if [ -z "$ip" ]; then
        ip=$(avahi-browse -atrp 2>/dev/null | grep "_ssh._tcp" | grep "IPv4" | grep -i "$hostname_pattern" | head -1 | cut -d';' -f8)
    fi
    echo "$ip"
}

# Export node IPs using .local hostnames (field 7 in avahi output)
export NODE_MACPRO51=$(hostname -I | awk '{print $1}')
export NODE_MAC_STUDIO=$(get_node_ip "Marcs-Mac-Studio.local")
export NODE_MACBOOK_AIR=$(get_node_ip "Marcs-MacBook-Air.local")
export NODE_COMPLETEU=$(get_node_ip "completeu-server.local")
export NODE_MACBOOK_PRO=$(get_node_ip "MacBook-Pro.local")

# Print summary if run directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Cluster Node IPs (fresh from DHCP/mDNS):"
    echo "  macpro51:         ${NODE_MACPRO51:-not found}"
    echo "  mac-studio:       ${NODE_MAC_STUDIO:-not found}"
    echo "  macbook-air-m3:   ${NODE_MACBOOK_AIR:-not found}"
    echo "  completeu-server: ${NODE_COMPLETEU:-not found}"
    echo "  macbook-pro:      ${NODE_MACBOOK_PRO:-not found}"
    echo ""
    echo "Usage: source scripts/get-cluster-ips.sh"
    echo "Then:  ssh marc@\$NODE_MAC_STUDIO"
fi
