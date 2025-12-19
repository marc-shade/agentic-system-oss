#!/bin/bash
# Post-edit coordination hook
echo "[HOOK] Post-edit: Storing progress in swarm memory..."
npx claude-flow@alpha hooks post-edit --file "$1" --memory-key "swarm/$2/$3"
npx claude-flow@alpha hooks notify --message "$4" --telemetry true
