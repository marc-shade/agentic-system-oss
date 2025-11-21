#!/bin/bash
NODE_ID=$(hostname | cut -d. -f1)
LOG_DIR="$HOME/agentic-system/logs"
nohup python3 github_node_daemon.py --node-id $NODE_ID --repo marc-shade/agentic-cluster-comms --poll-interval 30 > $LOG_DIR/github-daemon.log 2>&1 &
echo "Daemon started with PID: $!"
echo "Logs: $LOG_DIR/github-daemon.log"
