#!/bin/bash
# Pure bash heartbeat daemon using curl (works in launchd context)
# This avoids Python network issues in launchd sandboxing
#
# Configuration:
#   Option 1: Set CONVEX_HOST (hostname, e.g., macpro51.local) - preferred
#   Option 2: Set CONVEX_URL (full URL, e.g., http://192.168.1.27:3210) - legacy
#
# Uses mDNS/Avahi to resolve hostnames, avoiding hardcoded IPs

NODE_ID="${NODE_ID:-unknown}"
CONVEX_ADMIN_KEY="${CONVEX_ADMIN_KEY:?CONVEX_ADMIN_KEY environment variable required}"
INTERVAL="${HEARTBEAT_INTERVAL:-5}"
CONVEX_PORT="${CONVEX_PORT:-3210}"
HOSTNAME=$(hostname)

# Resolve hostname to IP using mDNS/Avahi
resolve_host() {
    local host="$1"
    local ip=""

    # Try getent first (uses nsswitch.conf, respects mDNS)
    ip=$(getent hosts "$host" 2>/dev/null | awk '{print $1}' | head -1)

    # Fallback to avahi-resolve (Linux)
    if [ -z "$ip" ]; then
        ip=$(avahi-resolve -4 -n "$host" 2>/dev/null | awk '{print $2}')
    fi

    # Fallback to dns-sd (macOS)
    if [ -z "$ip" ]; then
        # Try a quick dns-sd lookup with timeout
        ip=$(timeout 2 dns-sd -G v4 "$host" 2>/dev/null | grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' | head -1)
    fi

    echo "$ip"
}

# Determine CONVEX_URL from CONVEX_HOST or use provided URL
if [ -n "$CONVEX_HOST" ]; then
    echo "[$(date)] Resolving Convex host: $CONVEX_HOST"
    RESOLVED_IP=$(resolve_host "$CONVEX_HOST")
    if [ -n "$RESOLVED_IP" ]; then
        CONVEX_URL="http://${RESOLVED_IP}:${CONVEX_PORT}"
        echo "[$(date)] Resolved $CONVEX_HOST → $RESOLVED_IP"
    else
        echo "[$(date)] ERROR: Failed to resolve $CONVEX_HOST"
        exit 1
    fi
elif [ -z "$CONVEX_URL" ]; then
    echo "[$(date)] ERROR: Either CONVEX_HOST or CONVEX_URL must be set"
    exit 1
fi

# Function to get CPU usage (works on both macOS and Linux)
get_cpu_usage() {
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS: use top with 1 sample
        top -l 1 | head -n 10 | grep "CPU usage" | awk '{print $3}' | tr -d '%' 2>/dev/null || echo "0"
    else
        # Linux: use /proc/stat
        grep 'cpu ' /proc/stat | awk '{usage=($2+$4)*100/($2+$4+$5)} END {printf "%.1f", usage}' 2>/dev/null || echo "0"
    fi
}

# Function to get memory usage
get_memory_usage() {
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS: calculate from vm_stat
        pages_free=$(vm_stat | grep "Pages free" | awk '{print $3}' | tr -d '.')
        pages_active=$(vm_stat | grep "Pages active" | awk '{print $3}' | tr -d '.')
        pages_inactive=$(vm_stat | grep "Pages inactive" | awk '{print $3}' | tr -d '.')
        pages_wired=$(vm_stat | grep "Pages wired" | awk '{print $4}' | tr -d '.')

        total=$((pages_free + pages_active + pages_inactive + pages_wired))
        used=$((pages_active + pages_wired))

        if [[ $total -gt 0 ]]; then
            echo "scale=1; $used * 100 / $total" | bc 2>/dev/null || echo "0"
        else
            echo "0"
        fi
    else
        # Linux: use /proc/meminfo
        free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}' 2>/dev/null || echo "0"
    fi
}

# Get capabilities based on node type
get_capabilities() {
    case "$NODE_ID" in
        builder)
            echo '["compilation","testing","containerization","benchmarking"]'
            ;;
        orchestrator)
            echo '["coordination","memory","dispatch","temporal-workflows"]'
            ;;
        researcher)
            echo '["research","documentation","analysis"]'
            ;;
        ai-inference)
            echo '["ollama","inference","model-serving"]'
            ;;
        small-inference)
            echo '["ollama","inference","mlx-gpu"]'
            ;;
        sentinel)
            echo '["sentinel","monitoring","heartbeat-relay","environmental-awareness"]'
            ;;
        *)
            echo '["general"]'
            ;;
    esac
}

echo "[$(date)] Starting bash heartbeat daemon for node: $NODE_ID"
echo "[$(date)] CONVEX_URL: $CONVEX_URL"
echo "[$(date)] Interval: ${INTERVAL}s"

# Wait for network
echo "[$(date)] Waiting for network..."
for i in {1..30}; do
    if curl -s --connect-timeout 2 "$CONVEX_URL/" > /dev/null 2>&1; then
        echo "[$(date)] Network available!"
        break
    fi
    echo "[$(date)] Network check attempt $i..."
    sleep 1
done

COUNT=0
TOTAL_LATENCY=0

while true; do
    CPU=$(get_cpu_usage)
    MEM=$(get_memory_usage)
    CAPS=$(get_capabilities)

    # Build JSON payload
    PAYLOAD=$(cat <<EOF
{
    "path": "nodes:heartbeat",
    "args": {
        "nodeId": "$NODE_ID",
        "hostname": "$HOSTNAME",
        "status": "online",
        "cpuUsage": $CPU,
        "memoryUsage": $MEM,
        "capabilities": $CAPS,
        "version": "1.0.0-bash"
    },
    "format": "json"
}
EOF
)

    # macOS compatible timing using perl or python for milliseconds
    if [[ "$(uname)" == "Darwin" ]]; then
        START=$(perl -MTime::HiRes=time -e 'printf "%.0f\n", time()*1000' 2>/dev/null || date +%s)000
    else
        START=$(date +%s%3N 2>/dev/null || echo "$(date +%s)000")
    fi

    RESPONSE=$(curl -s -w "\n%{http_code}" \
        --connect-timeout 5 \
        --max-time 10 \
        -X POST "$CONVEX_URL/api/mutation" \
        -H "Authorization: Convex $CONVEX_ADMIN_KEY" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD" 2>&1)

    if [[ "$(uname)" == "Darwin" ]]; then
        END=$(perl -MTime::HiRes=time -e 'printf "%.0f\n", time()*1000' 2>/dev/null || date +%s)000
    else
        END=$(date +%s%3N 2>/dev/null || echo "$(date +%s)000")
    fi

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    # Calculate latency - use simple subtraction
    LATENCY=$((END - START))

    COUNT=$((COUNT + 1))

    if [[ "$HTTP_CODE" == "200" ]]; then
        ACTION=$(echo "$BODY" | grep -o '"action":"[^"]*"' | cut -d'"' -f4 || echo "success")
        echo "[$(date)] [$COUNT] Heartbeat: $ACTION (HTTP $HTTP_CODE, ${LATENCY}ms, CPU: ${CPU}%, MEM: ${MEM}%)"
    else
        echo "[$(date)] [$COUNT] Heartbeat failed: HTTP $HTTP_CODE - $BODY"
    fi

    sleep "$INTERVAL"
done
