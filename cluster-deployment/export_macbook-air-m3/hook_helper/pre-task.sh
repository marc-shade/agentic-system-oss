#!/bin/bash
# Pre-task coordination hook
echo "[HOOK] Pre-task: Loading context and coordinating with swarm..."
npx claude-flow@alpha hooks pre-task --description "$1" --auto-spawn-agents false
npx claude-flow@alpha hooks session-restore --session-id "swarm-$$" --load-memory true
