#!/bin/bash
# Python Environment Verification and Fix Script
# Ensures all services use Homebrew Python 3.13+, never system Python 3.9

set -e


# Platform-aware storage detection
detect_storage_base() {
    if [ -n "$AGENTIC_SYSTEM_PATH" ] && [ -d "$AGENTIC_SYSTEM_PATH" ]; then
        echo "$AGENTIC_SYSTEM_PATH"
        return
    fi
    case "$(uname -s)" in
        Darwin)
            if [ -d "/Volumes/SSDRAID0/agentic-system" ]; then
                echo "/Volumes/SSDRAID0/agentic-system"
            elif [ -d "/Volumes/FILES/agentic-system" ]; then
                echo "/Volumes/FILES/agentic-system"
            fi
            ;;
        Linux)
            if [ -d "/home/marc/agentic-system" ]; then
                echo "/home/marc/agentic-system"
            elif [ -d "/mnt/agentic-system" ]; then
                echo "/mnt/agentic-system"
            fi
            ;;
    esac
}

STORAGE_BASE=$(detect_storage_base)

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

HOMEBREW_PYTHON="/opt/homebrew/bin/python3"
REQUIRED_VERSION="3.11"
SYSTEM_PYTHON="/usr/bin/python3"

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║     PYTHON ENVIRONMENT VERIFICATION & FIX                        ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Check Homebrew Python exists and version
if [ ! -f "$HOMEBREW_PYTHON" ]; then
    echo -e "${RED}❌ ERROR: Homebrew Python not found at $HOMEBREW_PYTHON${NC}"
    echo "Install with: brew install python@3.13"
    exit 1
fi

HOMEBREW_VERSION=$($HOMEBREW_PYTHON --version | awk '{print $2}')
echo -e "${GREEN}✅ Homebrew Python:${NC} $HOMEBREW_VERSION ($HOMEBREW_PYTHON)"

# Check system Python (should NOT be used)
if [ -f "$SYSTEM_PYTHON" ]; then
    SYSTEM_VERSION=$($SYSTEM_PYTHON --version | awk '{print $2}')
    echo -e "${YELLOW}⚠️  System Python:${NC} $SYSTEM_VERSION ($SYSTEM_PYTHON) - NOT USED"
else
    echo -e "${GREEN}✅ System Python:${NC} Not present"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 RUNNING PYTHON PROCESSES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check running Python processes
PYTHON_PROCS=$(ps aux | grep -E "[p]ython" | grep -v "grep")

if [ -z "$PYTHON_PROCS" ]; then
    echo -e "${YELLOW}⚠️  No Python processes currently running${NC}"
else
    echo "$PYTHON_PROCS" | while read line; do
        PID=$(echo "$line" | awk '{print $2}')
        BINARY=$(echo "$line" | awk '{print $11}')
        SCRIPT=$(echo "$line" | awk '{print $12}' | xargs basename 2>/dev/null || echo "N/A")

        if [[ "$BINARY" == *"homebrew"* ]] || [[ "$BINARY" == *"3.13"* ]] || [[ "$BINARY" == *"3.12"* ]] || [[ "$BINARY" == *"3.11"* ]]; then
            echo -e "${GREEN}✅ PID $PID:${NC} $SCRIPT (Homebrew Python)"
        elif [[ "$BINARY" == "/usr/bin/python3" ]]; then
            echo -e "${RED}❌ PID $PID:${NC} $SCRIPT (SYSTEM PYTHON - BAD!)"
        else
            echo -e "${YELLOW}⚠️  PID $PID:${NC} $SCRIPT ($BINARY)"
        fi
    done
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 CHECKING SERVICE CONFIGURATIONS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

check_script() {
    local script="$1"
    local name="$2"

    if [ ! -f "$script" ]; then
        echo -e "${YELLOW}⚠️  $name:${NC} Not found"
        return
    fi

    if grep -q "export PATH=\"/opt/homebrew/bin" "$script" 2>/dev/null; then
        echo -e "${GREEN}✅ $name:${NC} Homebrew Python in PATH"
    else
        echo -e "${RED}❌ $name:${NC} Missing Homebrew PATH priority"
        echo "   Fix: Add 'export PATH=\"/opt/homebrew/bin:\$PATH\"' to top of script"
    fi
}

# Check startup scripts
check_script "$STORAGE_BASE/scripts/start-temporal-workers.sh" "Temporal Workers"
check_script "$STORAGE_BASE/scripts/start-autokitteh.sh" "AutoKitteh"
check_script "$STORAGE_BASE/arduino-surface/scripts/start_agentic_stack.sh" "Arduino Surface"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 LAUNCHD SERVICE CONFIGURATIONS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

check_plist() {
    local plist="$1"
    local name="$2"

    if [ ! -f "$plist" ]; then
        echo -e "${YELLOW}⚠️  $name:${NC} Plist not found"
        return
    fi

    if grep -q "/opt/homebrew/bin" "$plist" 2>/dev/null; then
        echo -e "${GREEN}✅ $name:${NC} Homebrew PATH configured"
    else
        echo -e "${RED}❌ $name:${NC} Missing Homebrew PATH in launchd"
        echo "   Fix: Update PATH in $plist"
    fi
}

# Check launchd plists
check_plist "$HOME/Library/LaunchAgents/com.temporal.workers.plist" "Temporal Workers"
check_plist "$HOME/Library/LaunchAgents/com.autokitteh.server.plist" "AutoKitteh"
check_plist "$HOME/Library/LaunchAgents/com.arduino.surface.plist" "Arduino Surface"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 MCP SERVER PYTHON CHECK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check MCP server directories
MCP_DIR="$STORAGE_BASE/mcp-servers"
if [ -d "$MCP_DIR" ]; then
    for server in "$MCP_DIR"/*; do
        if [ -d "$server" ]; then
            SERVER_NAME=$(basename "$server")

            # Check for venv
            if [ -d "$server/venv" ] || [ -d "$server/.venv" ]; then
                VENV_PATH=$([ -d "$server/venv" ] && echo "$server/venv" || echo "$server/.venv")
                VENV_PYTHON="$VENV_PATH/bin/python"

                if [ -f "$VENV_PYTHON" ]; then
                    VENV_VERSION=$($VENV_PYTHON --version 2>&1 | awk '{print $2}')
                    VENV_BASE=$($VENV_PYTHON -c "import sys; print(sys.base_prefix)" 2>/dev/null)

                    if [[ "$VENV_BASE" == *"homebrew"* ]]; then
                        echo -e "${GREEN}✅ $SERVER_NAME:${NC} venv with Homebrew Python $VENV_VERSION"
                    else
                        echo -e "${RED}❌ $SERVER_NAME:${NC} venv with system Python $VENV_VERSION"
                        echo "   Fix: rm -rf $VENV_PATH && /opt/homebrew/bin/python3 -m venv $VENV_PATH"
                    fi
                fi
            else
                echo -e "${YELLOW}⚠️  $SERVER_NAME:${NC} No venv (uses system python3)"
            fi
        fi
    done
else
    echo -e "${YELLOW}⚠️  MCP servers directory not found${NC}"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💡 RECOMMENDATIONS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
echo "1. ALWAYS use Homebrew Python:"
echo "   which python3  # Should be /opt/homebrew/bin/python3"
echo ""
echo "2. For new virtual environments:"
echo "   /opt/homebrew/bin/python3 -m venv venv"
echo ""
echo "3. For scripts, set PATH first:"
echo "   export PATH=\"/opt/homebrew/bin:\$PATH\""
echo ""
echo "4. Never use system Python:"
echo "   /usr/bin/python3  # AVOID - Python 3.9.6 is too old"
echo ""
echo "5. Check documentation:"
echo "   $STORAGE_BASE/PYTHON_ENVIRONMENT_SUMMARY.md"
echo ""

echo "═══════════════════════════════════════════════════════════════════"
echo "Verification complete. Review any ❌ or ⚠️  items above."
echo "═══════════════════════════════════════════════════════════════════"
