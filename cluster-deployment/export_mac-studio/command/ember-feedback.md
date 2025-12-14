# Ember Feedback

Get Ember's assessment of recent work. Ember provides behavioral feedback, quality insights, and patterns noticed.

## Arguments
- Timeframe: "last_action", "session", or "recent" (optional, defaults to "session")

## Example Usage
```
/ember-feedback session
```

## Task
Use the ember-mcp MCP tool to get feedback:

```
mcp__ember-mcp__ember_get_feedback({
  timeframe: "session"
})
```

Display Ember's feedback, including:
- Quality assessment
- Patterns noticed
- Suggestions for improvement
- Recent statistics

Present this information clearly to the user.
