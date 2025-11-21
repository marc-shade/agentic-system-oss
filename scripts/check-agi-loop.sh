#!/bin/bash
# Quick status check for autonomous AGI loop

echo "=== Autonomous AGI Loop Status ==="
echo ""

# Check if process is running
if ps aux | grep -q "[a]utonomous_recursive_agi_loop.py"; then
    PID=$(ps aux | grep "[a]utonomous_recursive_agi_loop.py" | awk '{print $2}')
    MEM=$(ps aux | grep "[a]utonomous_recursive_agi_loop.py" | awk '{print $6}')
    CPU=$(ps aux | grep "[a]utonomous_recursive_agi_loop.py" | awk '{print $3}')
    echo "✅ RUNNING"
    echo "   PID: $PID"
    echo "   CPU: ${CPU}%"
    echo "   Memory: ${MEM}KB"
else
    echo "❌ NOT RUNNING"
    exit 1
fi

echo ""
echo "=== Recent Activity ==="
tail -10 /mnt/agentic-system/logs/agi_loop.log

echo ""
echo "=== Cycle Count ==="
grep -c "CYCLE #" /mnt/agentic-system/logs/agi_loop.log

echo ""
echo "=== Recent Improvements ==="
ls -lt /mnt/agentic-system/implementations/*.json 2>/dev/null | head -3 | awk '{print $9}'
