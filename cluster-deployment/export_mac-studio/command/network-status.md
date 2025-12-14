---
description: Check current status of all distributed nodes
---

# 🌐 Network Awareness Check

Displaying current status of all nodes in the distributed Mac cluster:

!python3 /Users/marc/Documents/Cline/MCP/check_network_state.py

## Quick Node Check:
!python3 -c "
from pathlib import Path
import sys
sys.path.append('/Users/marc/Documents/Cline/MCP')
from network_awareness_scanner import NetworkAwarenessScanner
scanner = NetworkAwarenessScanner()
print('\\n🔍 Live node status:')
for ip, info in scanner.known_nodes.items():
    status = '✅' if scanner.ping_host(ip) else '❌'
    print(f'{status} {info[\"name\"]:<15} ({ip:<15}) - {info[\"role\"]}')
"

## Environmental Awareness Active ✅
The network monitoring system maintains real-time awareness of:
- Node availability and response times
- Running services on each node
- Performance metrics (CPU, memory, disk)
- MCP server status on each node
- Network topology and connectivity