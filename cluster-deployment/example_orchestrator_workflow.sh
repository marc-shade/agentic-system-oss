#!/bin/bash
# Example: Orchestrator delegates build task to Builder node
# Demonstrates cross-machine persistent context

echo "🎯 Example: Orchestrator → Builder Task Delegation"
echo "=================================================="
echo ""

# 1. Create persistent session on Builder
echo "1️⃣  Creating persistent build session on Builder node..."
./orchestrator_delegate_task.sh create example-build

echo ""
echo "2️⃣  Cloning repository in Builder session..."
./orchestrator_delegate_task.sh execute example-build "cd /tmp && git clone https://github.com/toon-format/toon toon-example 2>/dev/null || cd toon-example && git pull"

echo ""
echo "3️⃣  Installing dependencies..."
./orchestrator_delegate_task.sh execute example-build "cd /tmp/toon-example && npm install"

echo ""
echo "4️⃣  Running build..."
./orchestrator_delegate_task.sh execute example-build "cd /tmp/toon-example && export PATH=~/.npm-global/bin:\$PATH && pnpm run build"

echo ""
echo "5️⃣  Capturing build results..."
sleep 3
ssh marc@192.168.1.183 "tmux capture-pane -t example-build -p -S -50" | tail -30

echo ""
echo "=================================================="
echo "✅ Build completed on Builder node!"
echo ""
echo "📊 Session persists across disconnections - try:"
echo "   ./orchestrator_delegate_task.sh attach example-build"
echo ""
echo "🔄 Session state saved to:"
echo "   /mnt/agentic-system/databases/cluster/tmux-sessions/"
echo ""
echo "🎯 Context retained - can continue work later!"
