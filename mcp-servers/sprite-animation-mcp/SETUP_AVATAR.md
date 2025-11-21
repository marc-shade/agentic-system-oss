# Setting Up Claude's Corgi Avatar

This guide will help you set up the sprite animation MCP server to display your Corgi sprite as Claude's animated avatar.

## Quick Setup

1. **Save your Corgi sprite sheet**
   - Save your sprite sheet image as: `/Users/marc/Documents/Cline/MCP/sprite-animation-mcp/examples/corgi_sprite.png`

2. **Configure Claude Desktop**
   - Edit your Claude Desktop config file:
   ```
   ~/Library/Application Support/Claude/claude_desktop_config.json
   ```
   
   - Add the sprite animation server:
   ```json
   {
     "mcpServers": {
       "sprite-animation": {
         "command": "node",
         "args": ["/Users/marc/Documents/Cline/MCP/sprite-animation-mcp/build/index.js"]
       }
     }
   }
   ```

3. **Restart Claude Desktop** to load the MCP server

## Using the Avatar Tools

Once the server is configured, you can use these commands in Claude:

### Create the Avatar Display
```javascript
create_avatar_display({
  "spriteSheetPath": "/Users/marc/Documents/Cline/MCP/sprite-animation-mcp/examples/corgi_sprite.png",
  "outputPath": "/Users/marc/Documents/Cline/MCP/sprite-animation-mcp/examples/claude_corgi_avatar.html",
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

### View ASCII Art Version
```javascript
display_avatar({
  "spriteSheetPath": "/Users/marc/Documents/Cline/MCP/sprite-animation-mcp/examples/corgi_sprite.png",
  "columns": 5,
  "rows": 4,
  "frameIndex": 0
})
```

### Create a Walking Animation GIF
```javascript
create_animation({
  "imagePath": "/Users/marc/Documents/Cline/MCP/sprite-animation-mcp/examples/corgi_sprite.png",
  "outputPath": "/Users/marc/Documents/Cline/MCP/sprite-animation-mcp/examples/corgi_walk.gif",
  "sequence": {
    "frames": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
    "loop": true,
    "fps": 12
  },
  "spriteInfo": {
    "columns": 5,
    "rows": 4
  }
})
```

## Integration Ideas

1. **Embed in your web projects** - Use the generated HTML as an iframe or component
2. **Create custom animations** - Mix frames for idle, walking, or action sequences
3. **Multiple avatars** - Create different moods or characters
4. **Interactive features** - The avatar responds to clicks and can be controlled

## Troubleshooting

- If the MCP server doesn't load, check the console logs in Claude Desktop
- Make sure the sprite sheet path is correct
- Verify the build completed successfully with `npm run build`

Enjoy your animated Corgi companion in Claude!
