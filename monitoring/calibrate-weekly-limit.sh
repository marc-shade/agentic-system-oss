#!/bin/bash
# One-time calibration: Set your weekly token limit based on /usage

echo "=== Weekly Token Limit Calibration ==="
echo ""
echo "Step 1: Run /usage in Claude Code"
echo "Step 2: Look at 'Current week (all models)'"
echo ""
echo "Example:"
echo "  Current week (all models)"
echo "  ███████████████████████████  54% used"
echo "  Resets Nov 19, 4pm (America/New_York)"
echo ""

# Ask for the percentage
read -p "Enter the % used (just the number, e.g. 54): " PCT_USED

if [ -z "$PCT_USED" ]; then
    echo "Error: No percentage entered"
    exit 1
fi

# Get current Prometheus 7-day token count
TOKENS=$(curl -s 'http://localhost:9090/api/v1/query?query=sum(increase(claude_code_token_usage_total%7Btype%3D~%22input%7Coutput%22%7D%5B7d%5D))' 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(int(float(d['data']['result'][0]['value'][1])))" 2>/dev/null)

if [ -z "$TOKENS" ] || [ "$TOKENS" -eq 0 ]; then
    echo "Error: Could not get token count from Prometheus"
    exit 1
fi

# Calculate actual limit
LIMIT=$(python3 -c "print(int($TOKENS / ($PCT_USED / 100)))")

echo ""
echo "Calculation:"
echo "  Tokens used (last 7 days): $TOKENS"
echo "  Percentage from /usage: $PCT_USED%"
echo "  Calculated weekly limit: $LIMIT tokens"
echo ""

# Update prometheus_metrics.py
sed -i "s/weekly_limit = [0-9]*/weekly_limit = $LIMIT/" ~/agentic-system/intelligent-self-healing/prometheus_metrics.py

echo "✅ Updated weekly limit to $LIMIT tokens"
echo ""
echo "Your statusline will now show accurate weekly % based on your plan!"
echo "Re-run this script if your plan changes."
