#!/bin/bash

# Qdrant startup script for launchd
# This ensures Qdrant starts with correct environment and configuration

export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/Users/marc/.local/bin:$PATH"

exec /Users/marc/.local/bin/qdrant \
  --config-path /mnt/agentic-system/config/qdrant-config.yaml \
  >> /mnt/agentic-system/logs/qdrant-stdout.log \
  2>> /mnt/agentic-system/logs/qdrant-stderr.log
