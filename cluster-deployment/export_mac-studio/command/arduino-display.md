# arduino-display

Display a message on the Arduino LCD (16x2 character display).

Use the Arduino Surface MCP tool to write text:

```
mcp__arduino-surface__surface_display(row, col, text)
```

Parameters:
- `row`: Row number (0 or 1)
- `col`: Column number (0-15)
- `text`: Text to display (max 16 characters per row)

Example:
- Display on top row: `mcp__arduino-surface__surface_display(0, 0, "Hello Marc!")`
- Display on bottom row: `mcp__arduino-surface__surface_display(1, 0, "Status: OK")`

To clear the display first:
```
mcp__arduino-surface__surface_display_clear()
```

This is useful for showing system status, agent activities, or user notifications on the physical interface.
