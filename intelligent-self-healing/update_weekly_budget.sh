#!/bin/bash
# Quick updater for weekly token budget
# Usage: update_weekly_budget.sh <percentage>
# Example: update_weekly_budget.sh 41

if [ -z "$1" ]; then
    echo "Usage: $0 <percentage>"
    echo "Example: $0 41"
    echo ""
    echo "Run '/usage' in Claude Code to get your current percentage"
    exit 1
fi

PERCENTAGE=$1
BUDGET_FILE="$HOME/.claude/weekly_budget.json"

# Calculate tokens (assumes 200k weekly limit)
WEEKLY_LIMIT=200000
CURRENT_TOKENS=$((WEEKLY_LIMIT * PERCENTAGE / 100))
TODAY=$(date +%Y-%m-%d)

# Update the JSON file
cat > "$BUDGET_FILE" <<EOF
{
  "current_tokens": $CURRENT_TOKENS,
  "weekly_limit": $WEEKLY_LIMIT,
  "percentage": $PERCENTAGE,
  "last_updated": "$TODAY",
  "note": "Run '/usage' in Claude Code and update this file with the percentage shown"
}
EOF

echo "✓ Updated weekly budget to $PERCENTAGE% ($CURRENT_TOKENS / $WEEKLY_LIMIT tokens)"
echo ""
echo "Statusline preview:"
/home/marc/.claude/agentic-statusline.sh
