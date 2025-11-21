#!/bin/bash

# Claude Corgi Avatar Setup Script
# Run this after saving your corgi_sprite.png in the examples folder

echo "🐕 Setting up Claude's Corgi Avatar..."

# Path to the sprite sheet
SPRITE_PATH="/Users/marc/Documents/Cline/MCP/sprite-animation-mcp/examples/corgi_sprite.png"

# Check if sprite exists
if [ ! -f "$SPRITE_PATH" ]; then
    echo "❌ Error: Please save your Corgi sprite sheet as:"
    echo "   $SPRITE_PATH"
    echo ""
    echo "You can save the image from our conversation by:"
    echo "1. Right-click the Corgi sprite image in Claude"
    echo "2. Select 'Save Image As...'"
    echo "3. Save it to the examples folder as 'corgi_sprite.png'"
    exit 1
fi

echo "✅ Found Corgi sprite sheet!"
echo "📦 Building the MCP server..."

cd /Users/marc/Documents/Cline/MCP/sprite-animation-mcp
npm run build

echo "✅ Build complete!"
echo ""
echo "📝 Next steps:"
echo "1. Add this to ~/Library/Application Support/Claude/claude_desktop_config.json:"
echo ""
echo '{'
echo '  "mcpServers": {'
echo '    "sprite-animation": {'
echo '      "command": "node",'
echo '      "args": ["/Users/marc/Documents/Cline/MCP/sprite-animation-mcp/build/index.js"]'
echo '    }'
echo '  }'
echo '}'
echo ""
echo "2. Restart Claude Desktop"
echo "3. Use the create_avatar_display command in Claude"
echo ""
echo "🎉 Setup script complete!"
