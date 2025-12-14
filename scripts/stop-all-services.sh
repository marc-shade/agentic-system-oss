#!/bin/bash
# Graceful shutdown of all agentic services
# Run this before system shutdown/reboot

echo "🛑 Stopping all agentic services..."

# Stop n8n gracefully
echo "Stopping n8n..."
pkill -TERM -f "n8n" 2>/dev/null && sleep 2

# Stop AutoKitteh
echo "Stopping AutoKitteh..."
pkill -TERM -f "ak up" 2>/dev/null && sleep 2

# Stop Temporal (let it persist state)
echo "Stopping Temporal..."
pkill -TERM -f "temporal server" 2>/dev/null && sleep 2

# Stop Qdrant (let it flush)
echo "Stopping Qdrant..."
pkill -TERM -f "qdrant" 2>/dev/null && sleep 3

# Stop Chatterbox TTS
echo "Stopping Chatterbox TTS..."
pkill -TERM -f "chatterbox" 2>/dev/null
pkill -TERM -f "uvicorn.*8004" 2>/dev/null
sleep 1

# Verify all stopped
echo ""
echo "Checking service status..."
for service in n8n qdrant temporal "ak up" chatterbox; do
    if pgrep -f "$service" > /dev/null 2>&1; then
        echo "⚠️  $service still running"
    else
        echo "✅ $service stopped"
    fi
done

echo ""
echo "✅ All services stopped. Safe to reboot."
