#!/bin/bash
# Update weekly_budget.json from /usage command output
# 
# Usage:
#   1. Run /usage in Claude Code
#   2. Run this script and paste the weekly percentage when prompted

BUDGET_FILE="$HOME/.claude/weekly_budget.json"

echo "=== Update Weekly Budget from /usage ===" 
echo ""
echo "First, run /usage in Claude Code"
echo ""
read -p "Enter weekly percentage (just the number, e.g., 54): " PERCENTAGE

# Calculate tokens from percentage (assuming 200k limit)
LIMIT=200000
TOKENS=$((PERCENTAGE * LIMIT / 100))

# Update the file
cat > "$BUDGET_FILE" << JSON
{
  "current_tokens": $TOKENS,
  "weekly_limit": $LIMIT,
  "percentage": $PERCENTAGE,
  "last_updated": "$(date +%Y-%m-%d)",
  "note": "Updated from /usage command"
}
JSON

echo ""
echo "✅ Updated $BUDGET_FILE"
echo "   Weekly: $TOKENS / $LIMIT tokens ($PERCENTAGE%)"
echo ""
echo "Your statusline will now show the correct weekly percentage!"
