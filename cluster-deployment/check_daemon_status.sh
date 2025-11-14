#!/bin/bash
# Quick daemon status checker

echo "=== GitHub Node Daemon Status ==="
echo ""

# Check if PID file exists
if [ -f /tmp/github-daemon-mac-studio.pid ]; then
    PID=$(cat /tmp/github-daemon-mac-studio.pid)

    # Check if process is running
    if ps -p $PID > /dev/null 2>&1; then
        echo "✓ Daemon running (PID: $PID)"

        # Show process details
        ps -p $PID -o pid,ppid,user,%cpu,%mem,start,command

        # Check repo status
        if [ -d /tmp/agentic-cluster-comms/repo ]; then
            echo ""
            echo "=== Repository Status ==="
            cd /tmp/agentic-cluster-comms/repo
            echo "Current branch: $(git branch --show-current)"
            echo "Last pull: $(git log -1 --format='%ar')"

            # Count tasks on each branch
            echo ""
            echo "=== Task Queue Status ==="
            for branch in $(git branch -r | grep 'tasks/' | sed 's/.*\///'); do
                git checkout $branch 2>/dev/null
                count=$(git log --oneline | wc -l | tr -d ' ')
                echo "  $branch: $count commits"
            done

            git checkout tasks/mac-studio 2>/dev/null
        fi

        # Show recent log output
        if [ -f /tmp/github-daemon-mac-studio.log ]; then
            echo ""
            echo "=== Recent Log Output (last 10 lines) ==="
            tail -10 /tmp/github-daemon-mac-studio.log
        fi

    else
        echo "✗ Daemon not running (stale PID: $PID)"
    fi
else
    echo "✗ No PID file found"
fi

echo ""
echo "=== Quick Actions ==="
echo "  Start:   cd /Volumes/SSDRAID0/agentic-system/cluster-deployment && ./start_daemon.sh"
echo "  Stop:    kill \$(cat /tmp/github-daemon-mac-studio.pid)"
echo "  Restart: kill \$(cat /tmp/github-daemon-mac-studio.pid) && ./start_daemon.sh"
echo "  Logs:    tail -f /tmp/github-daemon-mac-studio.log"
