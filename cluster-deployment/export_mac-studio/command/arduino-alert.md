# arduino-alert

Trigger a physical alert pattern on the Arduino Surface (LED + sound).

Use the Arduino Surface MCP tool to play an alert:

```
mcp__arduino-surface__surface_alert(type)
```

Available alert types:
- `"success"` - Green LED + ascending beeps (confirmation)
- `"warning"` - Yellow LED + mid-tone beep (caution)
- `"error"` - Red LED + descending beeps (problem)
- `"info"` - Blue LED + single beep (notification)

Example:
- Task completed: `mcp__arduino-surface__surface_alert("success")`
- Warning detected: `mcp__arduino-surface__surface_alert("warning")`
- Error occurred: `mcp__arduino-surface__surface_alert("error")`

This provides physical feedback for important agent events and system status changes.
