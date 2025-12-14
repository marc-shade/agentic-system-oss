# Ember Chat

Have a free-form conversation with Ember, your flame-themed AI conscience keeper.

## Arguments
- Message to Ember (required)

## Example Usage
```
/ember-chat "What do you think about using agent spawning for this task?"
```

## Task
Use the ember-mcp MCP tool to chat with Ember:

```
mcp__ember-mcp__ember_chat({
  message: "[user's message]"
})
```

Display Ember's response to the user.
