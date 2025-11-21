# Sprite Animation MCP Server

A Model Context Protocol (MCP) server for processing sprite sheets and creating animations. Optimized for game development, pixel art workflows, animation processing, and creating animated avatars for Claude Desktop and Claude Code.

## 🐕 New: Claude Avatar Feature

Transform sprite sheets into interactive animated avatars! Use custom characters (like the included Corgi sprite example) to give Claude a visual personality in your desktop interface.

## Features

- **Parse Sprite Sheets**: Extract frame information from sprite sheet images
- **Create Animations**: Generate animated GIFs from sprite sequences
- **Extract Frames**: Save individual frames as separate PNG files
- **Flip Sprites**: Horizontally or vertically flip sprite sheets
- **Create Sprite Atlas**: Combine multiple sprites into a single atlas
- **Create Avatar Display**: Generate HTML-based animated avatars for Claude
- **Display Avatar**: Show sprite frames as ASCII art in the terminal

## Installation

```bash
cd Documents/Cline/MCP/sprite-animation-mcp
npm install
npm run build
```

## Configuration

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json`):

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

## Tools

### create_avatar_display 🆕
Create an interactive HTML avatar display for Claude Desktop/Code.

```typescript
{
  spriteSheetPath: string,
  outputPath: string,
  config: {
    columns: number,
    rows: number,
    frameSequence?: number[],  // Custom animation sequence
    fps?: number,              // Animation speed (default: 10)
    scale?: number,            // Size multiplier (default: 2)
    position?: "bottom-right" | "bottom-left" | "top-right" | "top-left",
    backgroundColor?: string   // Background color
  }
}
```

### display_avatar 🆕
Display a sprite frame as ASCII art in the terminal.

```typescript
{
  spriteSheetPath: string,
  columns: number,
  rows: number,
  frameIndex: number  // Which frame to display (0-based)
}
```

### parse_sprite_sheet
Parse a sprite sheet and get frame information.

```typescript
{
  imagePath: string,     // Path to sprite sheet
  columns: number,       // Number of columns
  rows: number,         // Number of rows
  frameWidth?: number,  // Optional frame width
  frameHeight?: number  // Optional frame height
}
```

### create_animation
Create an animated GIF from sprite frames.

```typescript
{
  imagePath: string,
  outputPath: string,
  sequence: {
    frames: number[],  // Frame indices to animate
    loop: boolean,     // Should animation loop
    fps: number       // Frames per second
  },
  spriteInfo: {
    columns: number,
    rows: number,
    frameWidth?: number,
    frameHeight?: number
  }
}
```

### extract_frames
Extract individual frames as PNG files.

```typescript
{
  imagePath: string,
  outputDir: string,
  columns: number,
  rows: number,
  framePrefix?: string  // Prefix for output files
}
```

### flip_sprite
Flip a sprite sheet horizontally or vertically.

```typescript
{
  imagePath: string,
  outputPath: string,
  direction: "horizontal" | "vertical"
}
```

### create_sprite_atlas
Combine multiple sprite images into an atlas.

```typescript
{
  inputFiles: string[],  // Array of sprite paths
  outputPath: string,
  columns: number,
  padding?: number      // Space between sprites
}
```

## Example Usage

### Creating a Claude Avatar

```javascript
// Create an animated Corgi avatar for Claude
await create_avatar_display({
  spriteSheetPath: "corgi_sprite.png",
  outputPath: "claude_avatar.html",
  config: {
    columns: 5,
    rows: 4,
    fps: 10,
    scale: 3,
    position: "bottom-right",
    backgroundColor: "rgba(255, 255, 255, 0.9)"
  }
});

// Display a frame in ASCII art
await display_avatar({
  spriteSheetPath: "corgi_sprite.png",
  columns: 5,
  rows: 4,
  frameIndex: 0
});
```

### Creating a Walking Animation

```javascript
// Parse the sprite sheet first
const parseResult = await parse_sprite_sheet({
  imagePath: "corgi_sprites.png",
  columns: 5,
  rows: 4
});

// Create walking animation using frames 0-19
await create_animation({
  imagePath: "corgi_sprites.png",
  outputPath: "corgi_walk.gif",
  sequence: {
    frames: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    loop: true,
    fps: 12
  },
  spriteInfo: {
    columns: 5,
    rows: 4
  }
});
```

### Extracting Individual Frames

```javascript
await extract_frames({
  imagePath: "corgi_sprites.png",
  outputDir: "./corgi_frames",
  columns: 5,
  rows: 4,
  framePrefix: "corgi"
});
```

## Claude Desktop Integration

To use the avatar in Claude Desktop:

1. Generate the avatar HTML using `create_avatar_display`
2. Open the generated HTML file to see your animated avatar
3. The avatar includes interactive controls:
   - Toggle animation on/off
   - Adjust animation speed
   - Trigger random actions
   - Click the avatar for interactions

See the `examples/` directory for:
- `avatar_setup.md` - Complete avatar setup guide
- `claude_desktop_integration.html` - Sample integration template
- Custom animation sequences and configurations

## Development

```bash
# Run in development mode
npm run dev

# Run tests
npm test

# Build
npm run build
```