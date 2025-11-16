#!/bin/bash
# Check Arduino Status Daemon

PID_FILE="/tmp/arduino_daemon.pid"
LOG_FILE="/tmp/arduino_daemon.log"

echo "Arduino Status Daemon"
echo "===================="

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        PID_SOURCE="(pid file)"
    else
        echo "Status: ✗ NOT RUNNING (stale PID: $PID)"
        rm "$PID_FILE"
        PID=""
    fi
fi

if [ -z "${PID:-}" ]; then
    PID=$(pgrep -f arduino_enhanced_daemon.py | head -n 1)
    if [ -n "$PID" ]; then
        PID_SOURCE="(pgrep fallback)"
    fi
fi

if [ -n "$PID" ]; then
    echo "Status: ✓ RUNNING $PID_SOURCE"
    echo "PID: $PID"
    echo "Uptime: $(ps -o etime= -p $PID | tr -d ' ')"
    echo ""
    echo "Recent logs (last 10 lines):"
    echo "----------------------------"
    if [ -f "$LOG_FILE" ]; then
        tail -10 "$LOG_FILE"
    else
        echo "No log file found"
    fi
else
    echo "Status: ✗ NOT RUNNING"
    exit 1
fi

echo ""
echo "Ember Web API"
echo "-------------"

API_PID_FILE="/tmp/ember_api.pid"
API_LOG_FILE="/tmp/ember_api.log"

if [ ! -f "$API_PID_FILE" ]; then
    echo "Status: ✗ NOT RUNNING"
else
    API_PID=$(cat "$API_PID_FILE")
    if ps -p "$API_PID" > /dev/null 2>&1; then
        echo "Status: ✓ RUNNING"
        echo "PID: $API_PID"
        if [ -f "$API_LOG_FILE" ]; then
            echo ""
            echo "Recent logs (last 10 lines):"
            echo "----------------------------"
            tail -10 "$API_LOG_FILE"
        fi
    else
        echo "Status: ✗ NOT RUNNING (stale PID: $API_PID)"
        rm "$API_PID_FILE"
    fi
fi
