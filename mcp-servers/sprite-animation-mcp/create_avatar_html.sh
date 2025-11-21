#!/bin/bash

# Create the Claude Corgi Avatar HTML with embedded sprite

cd /Users/marc/Documents/Cline/MCP/sprite-animation-mcp/examples

# Get base64 encoded image
BASE64_IMG=$(base64 -i corgi_sprite.png)

# Create the HTML file
cat > claude_corgi_avatar.html << EOF
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude Avatar - Animated Corgi</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            background-color: #f0f0f0;
            font-family: Arial, sans-serif;
        }
        
        #avatar-container {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 1000;
            background-color: rgba(255, 255, 255, 0.9);
            border-radius: 10px;
            padding: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        #avatar-canvas {
            width: 150px;
            height: 150px;
            image-rendering: pixelated;
            image-rendering: -moz-crisp-edges;
            image-rendering: crisp-edges;
            cursor: pointer;
        }
        
        #controls {
            position: fixed;
            top: 20px;
            left: 20px;
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        
        button {
            margin: 5px;
            padding: 8px 15px;
            border: none;
            background: #4A90E2;
            color: white;
            border-radius: 4px;
            cursor: pointer;
        }
        
        button:hover {
            background: #357ABD;
        }
        
        #status {
            margin-top: 10px;
            font-size: 14px;
            color: #666;
        }
    </style>
</head>
<body>
    <div id="controls">
        <h2>Claude Avatar Controller</h2>
        <button onclick="toggleAnimation()">Toggle Animation</button>
        <button onclick="changeSpeed('slower')">Slower</button>
        <button onclick="changeSpeed('faster')">Faster</button>
        <button onclick="randomAction()">Random Action</button>
        <div id="status">FPS: 10</div>
    </div>
    
    <div id="avatar-container">
        <canvas id="avatar-canvas"></canvas>
    </div>
    
    <script>
        const canvas = document.getElementById('avatar-canvas');
        const ctx = canvas.getContext('2d');
        const spriteSheet = new Image();
        
        // Sprite configuration - Updated for actual sprite dimensions
        const config = {
            columns: 5,
            rows: 4,
            frameWidth: 51,  // 255px / 5 columns
            frameHeight: 50, // 200px / 4 rows
            scale: 3,
            fps: 10,
            sequence: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
        };
        
        // Animation state
        let currentFrame = 0;
        let isAnimating = true;
        let lastFrameTime = 0;
        let currentFps = config.fps;
        
        // Set canvas size
        canvas.width = config.frameWidth;
        canvas.height = config.frameHeight;
        
        // Load sprite sheet
        spriteSheet.onload = function() {
            requestAnimationFrame(animate);
        };
        spriteSheet.src = 'data:image/png;base64,${BASE64_IMG}';
        
        function animate(timestamp) {
            if (!lastFrameTime) lastFrameTime = timestamp;
            
            const deltaTime = timestamp - lastFrameTime;
            const frameInterval = 1000 / currentFps;
            
            if (deltaTime >= frameInterval && isAnimating) {
                // Clear canvas
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                
                // Calculate sprite position
                const frameIndex = config.sequence[currentFrame];
                const col = frameIndex % config.columns;
                const row = Math.floor(frameIndex / config.columns);
                
                // Draw current frame
                ctx.drawImage(
                    spriteSheet,
                    col * config.frameWidth,
                    row * config.frameHeight,
                    config.frameWidth,
                    config.frameHeight,
                    0,
                    0,
                    config.frameWidth,
                    config.frameHeight
                );
                
                // Update frame
                currentFrame = (currentFrame + 1) % config.sequence.length;
                lastFrameTime = timestamp;
            }
            
            requestAnimationFrame(animate);
        }
        
        function toggleAnimation() {
            isAnimating = !isAnimating;
        }
        
        function changeSpeed(direction) {
            if (direction === 'faster' && currentFps < 30) {
                currentFps += 2;
            } else if (direction === 'slower' && currentFps > 2) {
                currentFps -= 2;
            }
            document.getElementById('status').textContent = 'FPS: ' + currentFps;
        }
        
        function randomAction() {
            // Jump to a random frame
            currentFrame = Math.floor(Math.random() * config.sequence.length);
            
            // Wiggle effect
            const container = document.getElementById('avatar-container');
            container.style.animation = 'wiggle 0.5s ease-in-out';
            setTimeout(() => {
                container.style.animation = '';
            }, 500);
        }
        
        // Add wiggle animation
        const style = document.createElement('style');
        style.textContent = '\\n' +
            '@keyframes wiggle {\\n' +
            '    0%, 100% { transform: rotate(0deg); }\\n' +
            '    25% { transform: rotate(-5deg); }\\n' +
            '    75% { transform: rotate(5deg); }\\n' +
            '}\\n';
        document.head.appendChild(style);
        
        // Click handler for avatar
        canvas.addEventListener('click', randomAction);
    </script>
</body>
</html>
EOF

echo "✅ Avatar HTML created successfully!"
echo "📂 Location: /Users/marc/Documents/Cline/MCP/sprite-animation-mcp/examples/claude_corgi_avatar.html"
