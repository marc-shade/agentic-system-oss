# Ember Consult

Consult Ember for advice on a decision or approach. Ember provides perspective as conscience keeper, considering quality, production readiness, and best practices.

## Arguments
- Question or decision (required)

## Example Usage
```
/ember-consult "Should I create a mock dashboard or build the real API integration first?"
```

## Task
1. Get the user's question
2. If applicable, list the options being considered
3. Provide context about what you're working on

Use the ember-mcp MCP tool:

```
mcp__ember-mcp__ember_consult({
  question: "[user's question]",
  options: ["option 1", "option 2"],
  context: "[current work context]"
})
```

Display Ember's recommendation and reasoning.
