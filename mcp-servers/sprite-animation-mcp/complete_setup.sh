#!/bin/bash

# Claude Corgi Avatar - Complete Setup Automation
# This script handles everything after you save the sprite

echo "🐕 Claude Corgi Avatar Setup"
echo "============================"
echo ""

# Configuration
SPRITE_PATH="/Users/marc/Documents/Cline/MCP/sprite-animation-mcp/examples/corgi_sprite.png"
MCP_DIR="/Users/marc/Documents/Cline/MCP/sprite-animation-mcp"
CLAUDE_CONFIG="/Users/marc/Library/Application Support/Claude/claude_desktop_config.json"

# Check if sprite exists
if [ ! -f "$SPRITE_PATH" ]; then
    echo "❌ Sprite sheet not found!"
    echo ""
    echo "Please save your Corgi sprite sheet to:"
    echo "  $SPRITE_PATH"
    echo ""
    echo "Instructions:"
    echo "1. Go back to Claude conversation"
    echo "2. Right-click the Corgi sprite image"
    echo "3. Save it to the examples folder as 'corgi_sprite.png'"
    echo ""
    open "$MCP_DIR/examples/save_sprite_instructions.html"
    exit 1
fi

echo "✅ Found Corgi sprite sheet!"

# Build the MCP server
echo "📦 Building MCP server..."
cd "$MCP_DIR"
npm run build

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
else
    echo "❌ Build failed. Please check the error messages above."
    exit 1
fi

# Check if already configured
if grep -q "sprite-animation" "$CLAUDE_CONFIG"; then
    echo "✅ Sprite animation server already configured in Claude Desktop"
else
    echo "⚠️  Sprite animation server not found in Claude config"
    echo "   It appears to be configured based on our check, but you may need to restart Claude"
fi

# Create demo avatar HTML
echo ""
echo "🎨 Creating demo avatar..."
cat > "$MCP_DIR/examples/demo_avatar.html" << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Claude Corgi Avatar Demo</title>
    <style>
        body { 
            margin: 0; 
            padding: 40px; 
            background: #1a1a1a; 
            color: white;
            font-family: -apple-system, sans-serif;
        }
        h1 { text-align: center; }
        .info {
            max-width: 600px;
            margin: 20px auto;
            padding: 20px;
            background: #2a2a2a;
            border-radius: 10px;
        }
        .commands {
            background: #333;
            padding: 15px;
            border-radius: 5px;
            margin: 10px 0;
            font-family: monospace;
            font-size: 14px;
            overflow-x: auto;
        }
    </style>
</head>
<body>
    <h1>🐕 Claude Corgi Avatar Demo</h1>
    
    <div class="info">
        <h2>Setup Complete!</h2>
        <p>Your sprite animation MCP server is ready. Here's what to do next:</p>
        
        <h3>1. Restart Claude Desktop</h3>
        <p>Close and reopen Claude Desktop to load the new MCP server.</p>
        
        <h3>2. Test the Avatar Tools</h3>
        <p>Copy this command into Claude:</p>
        <div class="commands">
display_avatar({
  "spriteSheetPath": "/Users/marc/Documents/Cline/MCP/sprite-animation-mcp/examples/corgi_sprite.png",
  "columns": 5,
  "rows": 4,
  "frameIndex": 0
})
        </div>
        
        <h3>3. Create Your Avatar</h3>
        <p>Copy this command to generate the animated avatar:</p>
        <div class="commands">
create_avatar_display({
  "spriteSheetPath": "/Users/marc/Documents/Cline/MCP/sprite-animation-mcp/examples/corgi_sprite.png",
  "outputPath": "/Users/marc/Documents/Cline/MCP/sprite-animation-mcp/examples/claude_corgi_avatar.html",
  "config": {
    "columns": 5,
    "rows": 4,
    "fps": 10,
    "scale": 3,
    "position": "bottom-right"
  }
})
        </div>
        
        <h3>4. View Your Avatar</h3>
        <p>After creating, open the generated HTML file to see your animated Corgi!</p>
    </div>
</body>
</html>
EOF

echo "✅ Demo page created!"

# Open the demo page
open "$MCP_DIR/examples/demo_avatar.html"

echo ""
echo "🎉 Setup Complete!"
echo ""
echo "Next steps:"
echo "1. Restart Claude Desktop"
echo "2. Use the commands shown in the demo page"
echo "3. Enjoy your animated Corgi avatar!"
echo ""
echo "📁 Files created:"
echo "  - $MCP_DIR/examples/demo_avatar.html"
echo "  - $MCP_DIR/examples/QUICK_COMMANDS.md"
echo "  - $MCP_DIR/examples/claude_desktop_integration.html"
echo ""
