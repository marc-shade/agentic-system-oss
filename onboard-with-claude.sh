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

# === CRITICAL: Check for Environmental Awareness First ===
AWARENESS_FILE="$HOME/.claude/environmental-awareness.json"

if [ ! -f "$AWARENESS_FILE" ]; then
    echo "⚠️  ENVIRONMENTAL AWARENESS REQUIRED"
    echo ""
    speak "Welcome! Before I can begin onboarding, I need to understand your current environment. Please complete the environmental awareness check first."
    echo ""
    echo "You must complete environmental awareness before onboarding."
    echo "This ensures I don't break anything you already have running."
    echo ""
    echo "Please see: 00-START-HERE.md for instructions"
    echo ""
    echo "Quick start:"
    echo "  1. Read 00-START-HERE.md (it explains everything)"
    echo "  2. Create environmental awareness script"
    echo "  3. Run: python3 ~/.claude/hooks/environmental-awareness.py"
    echo "  4. Re-run this onboarding script"
    echo ""
    exit 1
fi

speak "Great! I found your environmental awareness data. Let me review what you already have so I can integrate intelligently without breaking anything."

echo "✅ Environmental awareness found: $AWARENESS_FILE"
echo ""
echo "📊 Analyzing your current environment..."
echo ""

# Load and display awareness summary
if command -v jq &> /dev/null; then
    RUNNING_SERVICES=$(cat "$AWARENESS_FILE" | jq -r '.services | to_entries[] | select(.value.running == true) | .key' | wc -l | tr -d ' ')
    TOTAL_SERVICES=$(cat "$AWARENESS_FILE" | jq '.services | length')
    MCP_USER=$(cat "$AWARENESS_FILE" | jq -r '.mcp_config.user_level.count // 0')
    MCP_PROJECT=$(cat "$AWARENESS_FILE" | jq -r '.mcp_config.project_level.count // 0')
    DB_COUNT=$(cat "$AWARENESS_FILE" | jq '.databases | length')

    echo "Current Environment:"
    echo "  Services Running: $RUNNING_SERVICES/$TOTAL_SERVICES"
    echo "  MCP Servers: User=$MCP_USER, Project=$MCP_PROJECT"
    echo "  Databases Found: $DB_COUNT"
    echo ""
fi

cat <<'EOF'
📋 INTELLIGENT ONBOARDING OVERVIEW

I will autonomously:
1. ✅ Preserve all your existing services and data
2. ✅ Install ONLY missing components
3. ✅ Merge MCP configurations (not replace)
4. ✅ Create backups before any changes
5. ✅ Set up authentication (with your help for credentials)
6. ✅ Integrate cluster daemon with existing setup
7. ✅ Verify everything works without breaking existing functionality

Principles:
- I will NOT stop or restart your existing services
- I will NOT delete or modify your existing databases
- I will NOT replace your existing configurations
- I WILL merge new capabilities with what you have
- I WILL create backups before any changes

Let's begin intelligent integration!
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

# === STEP 0: Create Backups ===
echo "🎯 STEP 0: Creating Backups"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

speak "Before making any changes, I'm creating backups of your current configuration."

BACKUP_DIR="$HOME/.claude/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup Claude configurations
[ -f "$HOME/.claude.json" ] && cp "$HOME/.claude.json" "$BACKUP_DIR/claude.json.backup"
[ -f "$HOME/.mcp.json" ] && cp "$HOME/.mcp.json" "$BACKUP_DIR/mcp.json.backup"
[ -f "$HOME/.claude/CLAUDE.md" ] && cp "$HOME/.claude/CLAUDE.md" "$BACKUP_DIR/CLAUDE.md.backup"

# Backup directories
for dir in hooks skills agents commands; do
    [ -d "$HOME/.claude/$dir" ] && cp -r "$HOME/.claude/$dir" "$BACKUP_DIR/${dir}.backup"
done

echo "✅ Backups created in: $BACKUP_DIR"
echo ""

# === STEP 1: Prerequisites Check ===
echo "🎯 STEP 1: Prerequisites and Current State Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

speak "I'm checking your current system state to understand what you have and what's missing."

# Check platforms
./check-platforms.sh

# Show what we found from environmental awareness
if command -v jq &> /dev/null && [ -f "$AWARENESS_FILE" ]; then
    PLATFORMS=$(cat "$AWARENESS_FILE" | jq -r '.ai_platforms')
    echo "AI Platforms Detected:"
    echo "$PLATFORMS" | jq -r 'to_entries[] | "  \(.key): \(if .value then "✅ Installed" else "❌ Not installed" end)"'
    echo ""

    INSTALLED_COUNT=$(echo "$PLATFORMS" | jq '[.[] | select(. == true)] | length')
    speak "I found $INSTALLED_COUNT of 4 AI platforms installed."
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎯 STEP 2: Intelligent Component Installation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

speak "Now I'll determine which components need to be installed. I'll skip anything you already have running."

# Check which services are already running
INSTALL_NEEDED=false

if command -v jq &> /dev/null && [ -f "$AWARENESS_FILE" ]; then
    echo "Checking running services..."
    echo ""

    # Function to check if service is running
    check_service() {
        local service_name=$1
        local running=$(cat "$AWARENESS_FILE" | jq -r ".services.\"$service_name\".running")
        echo "$running"
    }

    # Ollama
    if [ "$(check_service 'Ollama')" = "true" ]; then
        echo "✅ Ollama: Already running (will reuse)"
    else
        echo "📥 Ollama: Will install"
        INSTALL_NEEDED=true
    fi

    # Qdrant
    if [ "$(check_service 'Qdrant')" = "true" ]; then
        echo "✅ Qdrant: Already running (will reuse)"
    else
        echo "📥 Qdrant: Will install"
        INSTALL_NEEDED=true
    fi

    # Temporal
    if [ "$(check_service 'Temporal gRPC')" = "true" ]; then
        echo "✅ Temporal: Already running (will reuse)"
    else
        echo "📥 Temporal: Will install"
        INSTALL_NEEDED=true
    fi

    # AutoKitteh
    if [ "$(check_service 'AutoKitteh')" = "true" ]; then
        echo "✅ AutoKitteh: Already running (will reuse)"
    else
        echo "📥 AutoKitteh: Will install"
        INSTALL_NEEDED=true
    fi

    echo ""
fi

if [ "$INSTALL_NEEDED" = "true" ]; then
    speak "I found some missing components. I'm going to install them now. This may take a few minutes."

    echo "Running master installer with intelligent detection..."
    cd install-scripts && ./install-all.sh standard
    cd ..

    speak "Installation of missing components complete!"
else
    speak "Great news! All required components are already running. I don't need to install anything."
    echo "✅ All required services detected - skipping installation"
fi

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
echo "🎯 STEP 5: Intelligent MCP Configuration Merge"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

speak "Now I'll configure MCP servers. I'll merge with your existing configuration, not replace it."

# Check if we have existing MCP configuration
HAS_EXISTING_MCP=false
if [ -f "$HOME/.claude.json" ]; then
    if command -v jq &> /dev/null; then
        EXISTING_COUNT=$(cat "$HOME/.claude.json" | jq '.mcpServers | length' 2>/dev/null || echo "0")
        if [ "$EXISTING_COUNT" -gt 0 ]; then
            HAS_EXISTING_MCP=true
            echo "Found existing MCP configuration with $EXISTING_COUNT servers"
            speak "I found your existing MCP servers. I'll add the cluster MCP servers without removing yours."
        fi
    fi
fi

if [ "$HAS_EXISTING_MCP" = "true" ]; then
    echo "Using intelligent merge..."
    # Create merge script if it doesn't exist
    if [ -f "./scripts/merge-mcp-config.py" ]; then
        python3 ./scripts/merge-mcp-config.py
    else
        echo "⚠️  Merge script not found - using standard configuration"
        ./configure-all-mcps.sh
    fi
else
    echo "No existing MCP configuration - creating fresh setup"
    ./configure-all-mcps.sh
fi

speak "MCP configuration complete. All your AI platforms can now access shared memory and cluster communication, alongside any existing MCP servers you had."

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
