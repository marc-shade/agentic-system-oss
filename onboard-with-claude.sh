#!/bin/bash
# Agentic System Onboarding - Claude Code Orchestrated
# This script is designed to be run BY Claude Code to orchestrate complete system setup

set -e

REPO_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# OS-specific TTS function
speak() {
    local message="$1"

    # Detect OS and use appropriate TTS
    case "$(uname -s)" in
        Darwin)
            # macOS - use say command
            say "$message"
            ;;
        Linux)
            # Linux - try multiple TTS engines in order of preference
            if command -v spd-say &> /dev/null; then
                spd-say "$message"
            elif command -v espeak &> /dev/null; then
                espeak "$message"
            elif command -v festival &> /dev/null; then
                echo "$message" | festival --tts
            else
                echo "TTS: $message" # Fallback to text output
            fi
            ;;
        MINGW*|MSYS*|CYGWIN*)
            # Windows - use PowerShell
            powershell -Command "Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('$message')"
            ;;
        *)
            echo "TTS: $message" # Unknown OS - fallback to text
            ;;
    esac
}

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
echo "1. Use OS-specific TTS (speak function works out of the box):"
echo ""
echo "   speak \"I'm going to set up your system to join the agentic cluster. First, let me check what prerequisites you have installed.\""
echo ""
echo "2. Run: ./check-platforms.sh"
echo ""
echo "3. Parse the JSON output at: /tmp/platform-status.json"
echo ""
echo "4. Based on what's missing, announce:"
echo ""
echo "   speak \"I found 2 of 4 AI platforms installed. Now I'm going to install the missing infrastructure components automatically.\""
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎯 STEP 2: Component Installation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Claude Code should now:"
echo ""
echo "1. Announce:"
echo ""
echo "   speak \"I'm going to install the core infrastructure. This may take a few minutes. I'll install Qdrant, Temporal, and AutoKitteh.\""
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
echo "3. After installation completes:"
echo ""
echo "   speak \"Installation complete! Now I need your help setting up authentication for GitHub and the AI platforms.\""
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
echo "Claude Code uses OS-specific 'speak' function to guide the human through each step."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎯 STEP 4: Python Dependencies"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Claude Code should now:"
echo ""
echo "1. Announce:"
echo ""
echo "   speak \"Installing Python dependencies for MCP servers\""
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
echo "1. Announce:"
echo ""
echo "   speak \"Configuring MCP servers across all AI platforms\""
echo ""
echo "2. Run: ./configure-all-mcps.sh"
echo ""
echo "3. Confirm:"
echo ""
echo "   speak \"MCP configuration complete. All your AI platforms can now access shared memory and cluster communication.\""
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎯 STEP 6: Start Cluster Daemon"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Claude Code should now:"
echo ""
echo "1. Announce:"
echo ""
echo "   speak \"Starting the cluster daemon for inter-node communication\""
echo ""
echo "2. Run: cd cluster-deployment && ./start_daemon.sh"
echo ""
echo "3. Confirm:"
echo ""
echo "   speak \"Cluster daemon is running. Your node can now communicate with other nodes via GitHub.\""
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎯 STEP 7: Final Verification"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Claude Code should now:"
echo ""
echo "1. Announce:"
echo ""
echo "   speak \"Running final verification checks\""
echo ""
echo "2. Run verification:"
echo ""
echo "   ./verify-onboarding.sh"
echo ""
echo "3. Celebrate:"
echo ""
echo "   speak \"Congratulations! Your node is fully onboarded and ready to join the agentic cluster. You can now collaborate with other nodes and run autonomous workflows.\""
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📖 For detailed instructions, see: claude-onboarding-guide.md"
echo ""
