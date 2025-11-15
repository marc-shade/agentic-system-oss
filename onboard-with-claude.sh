#!/bin/bash
# Agentic System Onboarding - Claude Code Orchestrated
# This script is designed to be run BY Claude Code to orchestrate complete system setup

set -e

REPO_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "🤖 Agentic System Onboarding"
echo "Orchestrated by Claude Code"
echo "============================="
echo ""

cat <<'EOF'
📋 ONBOARDING OVERVIEW

Claude Code will autonomously:
1. Check current system state
2. Install missing components (Ollama, Temporal, AutoKitteh, Qdrant, etc.)
3. Configure MCP servers across all platforms
4. Set up authentication (with human help for OAuth/API keys)
5. Start cluster daemon
6. Verify everything is working

Human interaction required for:
- Providing GitHub Personal Access Token
- OpenAI Codex authentication (OAuth or API key)
- Gemini CLI authentication (Google Cloud or API key)

Let's begin!
EOF

echo ""

# Create tracking file
ONBOARD_STATUS="$HOME/.agentic-system-onboarding-status.json"

cat > "$ONBOARD_STATUS" <<EOF
{
  "status": "in_progress",
  "started_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "repo_dir": "$REPO_DIR",
  "steps": {
    "prerequisites": "pending",
    "component_installation": "pending",
    "github_auth": "pending",
    "ollama_setup": "pending",
    "codex_auth": "pending",
    "gemini_auth": "pending",
    "python_deps": "pending",
    "mcp_config": "pending",
    "daemon_setup": "pending",
    "verification": "pending"
  }
}
EOF

echo "📝 Status tracking: $ONBOARD_STATUS"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ===== CLAUDE CODE ORCHESTRATION BEGINS =====
echo "🎯 STEP 1: Prerequisites Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Claude Code should now:"
echo ""
echo "1. Use voice-mode MCP to say:"
echo "   'I'm going to set up your system to join the agentic cluster."
echo "    First, let me check what prerequisites you have installed.'"
echo ""
echo "2. Run: ./check-platforms.sh"
echo ""
echo "3. Parse the JSON output at: /tmp/platform-status.json"
echo ""
echo "4. Based on what's missing, use voice-mode to say:"
echo "   'I found [X] of 4 AI platforms installed. Now I'm going to"
echo "    install the missing infrastructure components automatically.'"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎯 STEP 2: Component Installation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Claude Code should now:"
echo ""
echo "1. Use voice-mode to say:"
echo "   'I'm going to install the core infrastructure. This may take"
echo "    a few minutes. I'll install Qdrant, Temporal, and AutoKitteh.'"
echo ""
echo "2. Run the master installer:"
echo "   cd install-scripts && ./install-all.sh standard"
echo ""
echo "   This will automatically install:"
echo "   - Ollama (if missing)"
echo "   - Qdrant (vector database)"
echo "   - Temporal (workflow engine)"
echo "   - AutoKitteh (event-driven workflows)"
echo ""
echo "3. After installation completes, say:"
echo "   'Installation complete! Now I need your help setting up"
echo "    authentication for GitHub and the AI platforms.'"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎯 STEP 3: Authentication Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Claude Code should now run the authentication flow:"
echo "   ./bootstrap.sh"
echo ""
echo "This will interactively prompt for:"
echo "- GitHub Personal Access Token"
echo "- OpenAI Codex authentication (OAuth or API key)"
echo "- Gemini CLI authentication (ADC or API key)"
echo ""
echo "Claude Code can use voice-mode to guide the human through each step."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎯 STEP 4: Python Dependencies"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Claude Code should now:"
echo ""
echo "1. Say: 'Installing Python dependencies for MCP servers...'"
echo ""
echo "2. Run: pip3 install -r requirements.txt"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎯 STEP 5: MCP Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Claude Code should now:"
echo ""
echo "1. Say: 'Configuring MCP servers across all AI platforms...'"
echo ""
echo "2. Run: ./configure-all-mcps.sh"
echo ""
echo "3. Say: 'MCP configuration complete. All your AI platforms can"
echo "        now access shared memory and cluster communication.'"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎯 STEP 6: Start Cluster Daemon"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Claude Code should now:"
echo ""
echo "1. Say: 'Starting the cluster daemon for inter-node communication...'"
echo ""
echo "2. Run: cd cluster-deployment && ./start_daemon.sh"
echo ""
echo "3. Say: 'Cluster daemon is running. Your node can now communicate"
echo "        with other nodes via GitHub.'"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎯 STEP 7: Final Verification"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Claude Code should now:"
echo ""
echo "1. Say: 'Running final verification checks...'"
echo ""
echo "2. If verify-onboarding.sh exists, run it"
echo "   Otherwise, manually verify:"
echo "   - All platforms installed: ./check-platforms.sh"
echo "   - Services running: Check ports 6333, 7233, 8101, 8102, 9980"
echo "   - Daemon running: cat cluster-deployment/daemon.pid"
echo ""
echo "3. Say: 'Congratulations! Your node is fully onboarded and ready"
echo "        to join the agentic cluster. You can now collaborate with"
echo "        other nodes and run autonomous workflows.'"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📖 For detailed instructions, see: claude-onboarding-guide.md"
echo ""
