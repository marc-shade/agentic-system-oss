#!/bin/bash
# n8n Startup Script for Autonomous System
# Runs n8n with optimized configuration on hot tier

export PATH="/Users/marc/.nvm/versions/node/v24.3.0/bin:$PATH"
export N8N_USER_FOLDER="/mnt/agentic-system/n8n-data"
export N8N_PORT=5678
export N8N_HOST="0.0.0.0"
export N8N_PROTOCOL="http"
export N8N_LOG_LEVEL="info"
export N8N_LOG_OUTPUT="file"
export N8N_LOG_FILE_LOCATION="/mnt/agentic-system/logs/n8n-output.log"

# Database on hot tier for performance
export DB_TYPE="sqlite"
export DB_SQLITE_DATABASE="/mnt/agentic-system/n8n-data/database.sqlite"

# Disable telemetry
export N8N_DIAGNOSTICS_ENABLED=false
export N8N_VERSION_NOTIFICATIONS_ENABLED=false

# Performance optimizations
export N8N_PAYLOAD_SIZE_MAX=16
export EXECUTIONS_DATA_SAVE_ON_SUCCESS="all"
export EXECUTIONS_DATA_SAVE_ON_ERROR="all"
export EXECUTIONS_DATA_MAX_AGE=336  # 14 days

# Start n8n
exec n8n \
  >> /mnt/agentic-system/logs/n8n-stdout.log \
  2>> /mnt/agentic-system/logs/n8n-stderr.log
