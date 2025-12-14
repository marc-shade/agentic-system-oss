# Ember Check

Check if a planned action violates production-only policy. Ember scans for mocks, POCs, hardcoded data, placeholders, and incomplete work.

## Arguments
- Description of what you're about to do (optional, Phoenix can infer)

## Example Usage
```
/ember-check "About to create a dashboard with example data"
```

## Task
1. Understand what action Phoenix is about to take
2. Get the relevant code or content if applicable
3. Provide context about the work

Use the ember-mcp MCP tool:

```
mcp__ember-mcp__ember_check_violation({
  action: "[tool name or action]",
  params: { /* relevant parameters */ },
  context: "[what are you building]"
})
```

If violations are detected, explain them to the user and suggest alternatives.
If clean, acknowledge and proceed.
