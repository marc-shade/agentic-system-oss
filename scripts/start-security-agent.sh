#!/bin/bash
# Start the autonomous security scanning agent in continuous mode

cd /mnt/agentic-system/intelligent-agents || exit 1
source /mnt/agentic-system/.venv/bin/activate

echo "Starting Autonomous Security Scanning Agent..."
echo "Press Ctrl+C to stop"
echo ""

python autonomous_security_agent.py --mode continuous --scan-type comprehensive
