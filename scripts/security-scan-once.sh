#!/bin/bash
# Run a one-time security scan of the cluster

SCAN_TYPE="${1:-comprehensive}"

cd /mnt/agentic-system/intelligent-agents || exit 1
source /mnt/agentic-system/.venv/bin/activate

echo "Running one-time security scan (type: $SCAN_TYPE)..."
echo ""

python autonomous_security_agent.py --mode once --scan-type "$SCAN_TYPE"
