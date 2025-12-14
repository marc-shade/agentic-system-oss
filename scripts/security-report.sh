#!/bin/bash
# Generate security vulnerability report

cd /mnt/agentic-system/intelligent-agents || exit 1
source /mnt/agentic-system/.venv/bin/activate

python autonomous_security_agent.py --report | jq '.'
