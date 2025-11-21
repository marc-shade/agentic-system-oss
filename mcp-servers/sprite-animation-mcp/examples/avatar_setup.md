# Claude Avatar Configuration
# Using the Corgi Sprite as Claude's Visual Avatar

This directory contains examples for using the sprite-animation-mcp server to create
animated avatars for Claude Desktop and Claude Code.

## Corgi Avatar Setup

The Corgi sprite sheet you provided has the following specifications:
- Grid: 5 columns × 4 rows (20 frames total)
- Animation: Walking/running cycle
- Special frames: Last row shows turning/different poses

## Quick Start

1. Save your Corgi sprite sheet as `corgi_sprite.png` in this directory

2. Generate the avatar display HTML:
```bash
# Using the MCP tool in Claude
create_avatar_display({
  "spriteSheetPath": "/Users/marc/Documents/Cline/MCP/sprite-animation-mcp/examples/corgi_sprite.png",
  "outputPath": "/Users/marc/Documents/Cline/MCP/sprite-animation-mcp/examples/claude_avatar.html",
  "config": {
    "columns": 5,
    "rows": 4,
    "fps": 10,
    "scale": 3,
    "position": "bottom-right",
    "backgroundColor": "rgba(255, 255, 255, 0.9)"
  }
})
```

3. Open the generated HTML file in your browser to see the animated avatar

## Custom Animation Sequences

You can create different animations using specific frame sequences:

### Walking Animation (frames 0-14)
```json
{
  "frameSequence": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
}
```

### Idle Animation (frames 0-4 repeated)
```json
{
  "frameSequence": [0, 1, 2, 3, 4, 3, 2, 1]
}
```

### Turn Animation (using last row)
```json
{
  "frameSequence": [15, 16, 17, 18, 19, 18, 17, 16]
}
```

## Integration with Claude Desktop

To use this as Claude's avatar in your interface:

1. Generate the avatar HTML with your preferred settings
2. Embed the HTML in an iframe or webview component
3. The avatar includes interactive controls for:
   - Pausing/resuming animation
   - Adjusting animation speed
   - Triggering random actions

## ASCII Art Display

You can also display individual frames as ASCII art in the terminal:

```bash
display_avatar({
  "spriteSheetPath": "/path/to/corgi_sprite.png",
  "columns": 5,
  "rows": 4,
  "frameIndex": 0
})
```

This is useful for terminal-based interfaces or debugging.
