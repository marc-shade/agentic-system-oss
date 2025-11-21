#!/bin/bash

# Manual Dashboard Testing Script
# Tests dashboards 6-10 by checking URLs and API endpoints

BASE_URL="http://localhost:3101"
API_URL="http://localhost:3002"

echo "========================================"
echo "KutiraAI Dashboard Testing (6-10)"
echo "========================================"
echo ""
echo "Testing Date: $(date)"
echo "Frontend URL: $BASE_URL"
echo "Backend URL: $API_URL"
echo ""

# Test function
test_dashboard() {
    local dashboard_num=$1
    local dashboard_name=$2
    local dashboard_url=$3
    local api_endpoints=$4

    echo "========================================"
    echo "Dashboard #$dashboard_num: $dashboard_name"
    echo "========================================"
    echo "URL: $BASE_URL$dashboard_url"
    echo ""

    # Test frontend URL
    echo "Testing frontend page..."
    http_code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$dashboard_url")

    if [ "$http_code" = "200" ]; then
        echo "✅ Frontend loads (HTTP $http_code)"
    else
        echo "❌ Frontend error (HTTP $http_code)"
    fi

    # Test API endpoints
    if [ -n "$api_endpoints" ]; then
        echo ""
        echo "Testing API endpoints:"
        IFS=',' read -ra ENDPOINTS <<< "$api_endpoints"
        for endpoint in "${ENDPOINTS[@]}"; do
            endpoint=$(echo "$endpoint" | xargs) # trim whitespace
            api_url="$API_URL$endpoint"

            response=$(curl -s -w "\n%{http_code}" "$api_url")
            http_code=$(echo "$response" | tail -n1)
            body=$(echo "$response" | head -n -1)

            if [ "$http_code" = "200" ]; then
                # Check if response has data
                if echo "$body" | grep -q '"success".*true'; then
                    echo "   ✅ $endpoint - OK (has data)"
                elif echo "$body" | grep -q '"data"'; then
                    echo "   ✅ $endpoint - OK"
                else
                    echo "   ⚠️  $endpoint - OK but no data"
                fi
            else
                error_msg=$(echo "$body" | head -c 100)
                echo "   ❌ $endpoint - ERROR (HTTP $http_code)"
                echo "      Error: $error_msg"
            fi
        done
    fi

    echo ""
}

# Dashboard 6: Custom Agents
test_dashboard 6 \
    "Custom Agents Dashboard" \
    "/custom-agents" \
    "/api/agents,/api/agent-templates"

# Dashboard 7: Usage Analytics
test_dashboard 7 \
    "Usage Analytics Dashboard" \
    "/usage-analytics" \
    "/api/usage/stats"

# Dashboard 8: Telemetry Monitoring
test_dashboard 8 \
    "Telemetry Monitoring Dashboard" \
    "/telemetry-monitoring" \
    "/api/telemetry/stats,/api/telemetry/sessions,/api/telemetry/model-performance,/api/telemetry/tool-summary"

# Dashboard 9: Overnight Automation
test_dashboard 9 \
    "Overnight Automation Dashboard" \
    "/overnight-automation" \
    "/api/overnight/status"

# Dashboard 10: Workflow Automation
test_dashboard 10 \
    "Workflow Automation Dashboard" \
    "/agentic/workflow" \
    "/api/workflows"

echo "========================================"
echo "Test Complete"
echo "========================================"
