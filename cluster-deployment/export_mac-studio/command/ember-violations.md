# Ember Violations Report

Show violations detected by Ember (production-only policy enforcement).

## Command
```bash
if [ -f ~/.claude/ember_violations.jsonl ]; then
    echo "=== Ember Violation History ==="
    echo ""
    tail -20 ~/.claude/ember_violations.jsonl | while read line; do
        echo "$line" | jq -r '"\(.observations[1]) - \(.observations[4])"'
    done
else
    echo "No violations detected yet. Ember is keeping Phoenix honest!"
fi
```

Display recent violations caught by Ember's production-only policy enforcement.
