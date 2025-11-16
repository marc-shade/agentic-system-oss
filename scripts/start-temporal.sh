#!/bin/bash
# Temporal Server Startup Script for Autonomous System
# Runs Temporal with hot tier storage for performance

export PATH="/home/marc/.temporalio/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

# Database on primary storage
DB_FILE="/home/marc/agentic-system/databases/temporal/temporal.db"
UI_PORT=8233
GRPC_PORT=7233
METRICS_PORT=57271

# Namespace for autonomous workflows
NAMESPACE="default"

# Ensure directories exist
mkdir -p "$(dirname "$DB_FILE")"
mkdir -p "/home/marc/agentic-system/logs"

# Start Temporal server
exec temporal server start-dev \
  --db-filename "$DB_FILE" \
  --ui-port "$UI_PORT" \
  --port "$GRPC_PORT" \
  --metrics-port "$METRICS_PORT" \
  --namespace "$NAMESPACE" \
  --log-level info \
  >> /home/marc/agentic-system/logs/temporal-stdout.log \
  2>> /home/marc/agentic-system/logs/temporal-stderr.log
