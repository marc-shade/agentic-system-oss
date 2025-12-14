#!/bin/bash
# Session management hook
echo "[HOOK] Session: Managing swarm coordination state..."
npx claude-flow@alpha hooks session-end --export-metrics true --generate-summary true
