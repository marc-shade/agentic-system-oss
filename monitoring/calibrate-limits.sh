#!/bin/bash
# Calibrate Prometheus metrics limits to match /usage command
#
# Usage: Run this after checking /usage in Claude Code
#   /usage
#   Current session: 65,432 / 200,000 tokens (33%)
#   Current week: $4.25 / $25.00 (17%)
#
# Then run: ./calibrate-limits.sh

echo "=== Claude Code Usage Calibration ==="
echo ""
echo "First, run /usage in Claude Code to get the actual values."
echo ""
echo "Current Prometheus metrics:"
python3 ~/agentic-system/intelligent-self-healing/prometheus_metrics.py | python3 -c "
import json, sys
data = json.load(sys.stdin)
session = data.get('session', {})
weekly = data.get('weekly', {})

print(f\"Session: {session.get('current', 0):,} / {session.get('limit', 0):,} tokens ({session.get('percentage', 0)}%)\")
if weekly.get('is_cost'):
    print(f\"Weekly: \${weekly.get('current', 0):.2f} / \${weekly.get('limit', 0):.2f} ({weekly.get('percentage', 0)}%)\")
else:
    print(f\"Weekly: {weekly.get('current', 0):,} tokens ({weekly.get('percentage', 0)}%)\")
"

echo ""
echo "To update limits, edit:"
echo "  ~/agentic-system/intelligent-self-healing/prometheus_metrics.py"
echo ""
echo "Change these lines:"
echo "  Line 49:  limit = 200000  # Session token limit"  
echo "  Line 77:  weekly_cost_limit = 10.0  # Weekly cost limit in USD"
