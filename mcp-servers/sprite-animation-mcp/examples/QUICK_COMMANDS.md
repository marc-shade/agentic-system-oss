# 🐕 Claude Corgi Avatar - Quick Commands

Copy and paste these commands into Claude after setting up the MCP server:

## 1. Create Animated Avatar Display
```
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

## 2. Create Walking Animation GIF
```
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

## 3. Display ASCII Art Frame
```
display_avatar({
  "spriteSheetPath": "/Users/marc/Documents/Cline/MCP/sprite-animation-mcp/examples/corgi_sprite.png",
  "columns": 5,
  "rows": 4,
  "frameIndex": 0
})
```

## 4. Extract All Frames
```
extract_frames({
  "imagePath": "/Users/marc/Documents/Cline/MCP/sprite-animation-mcp/examples/corgi_sprite.png",
  "outputDir": "/Users/marc/Documents/Cline/MCP/sprite-animation-mcp/examples/corgi_frames",
  "columns": 5,
  "rows": 4,
  "framePrefix": "corgi"
})
```

## 5. Create Idle Animation
```
create_animation({
  "imagePath": "/Users/marc/Documents/Cline/MCP/sprite-animation-mcp/examples/corgi_sprite.png",
  "outputPath": "/Users/marc/Documents/Cline/MCP/sprite-animation-mcp/examples/corgi_idle.gif",
  "sequence": {
    "frames": [0, 1, 2, 3, 4, 3, 2, 1],
    "loop": true,
    "fps": 8
  },
  "spriteInfo": {
    "columns": 5,
    "rows": 4
  }
})
```

## 6. Create Turn Animation
```
create_animation({
  "imagePath": "/Users/marc/Documents/Cline/MCP/sprite-animation-mcp/examples/corgi_sprite.png",
  "outputPath": "/Users/marc/Documents/Cline/MCP/sprite-animation-mcp/examples/corgi_turn.gif",
  "sequence": {
    "frames": [15, 16, 17, 18, 19],
    "loop": false,
    "fps": 10
  },
  "spriteInfo": {
    "columns": 5,
    "rows": 4
  }
})
```
