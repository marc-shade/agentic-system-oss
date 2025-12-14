#!/bin/bash
# Setup script for Intelligent AI Agent Framework

set -e  # Exit on error


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

echo "=========================================="
echo "Intelligent AI Agent Framework Setup"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version || { echo "❌ Python 3 not found"; exit 1; }
echo "✅ Python 3 found"
echo ""

# Check for API keys
echo "Checking API keys..."
API_KEYS_OK=true

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "⚠️  ANTHROPIC_API_KEY not set"
    API_KEYS_OK=false
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OPENAI_API_KEY not set"
    API_KEYS_OK=false
fi

if [ -z "$GOOGLE_API_KEY" ]; then
    echo "⚠️  GOOGLE_API_KEY not set"
    API_KEYS_OK=false
fi

if [ "$API_KEYS_OK" = false ]; then
    echo ""
    echo "To set API keys:"
    echo "  export ANTHROPIC_API_KEY='your_key_here'"
    echo "  export OPENAI_API_KEY='your_key_here'"
    echo "  export GOOGLE_API_KEY='your_key_here'"
    echo ""
    echo "Add to ~/.zshrc or ~/.bashrc for persistence"
    echo ""
fi

# Install dependencies
echo "Installing dependencies..."
pip3 install -r requirements.txt || { echo "❌ Failed to install dependencies"; exit 1; }
echo "✅ Dependencies installed"
echo ""

# Create necessary directories
echo "Creating directories..."
mkdir -p /tmp/agent-logs
mkdir -p $STORAGE_BASE/config
echo "✅ Directories created"
echo ""

# Verify evolution config exists
EVOLUTION_CONFIG="$STORAGE_BASE/config/evolution_phases.json"
if [ -f "$EVOLUTION_CONFIG" ]; then
    echo "✅ Evolution phases config found"
else
    echo "⚠️  Evolution phases config not found at $EVOLUTION_CONFIG"
fi
echo ""

# Check for Arduino (optional)
echo "Checking for Arduino..."
ARDUINO_FOUND=false
for port in /dev/tty.usbmodem*; do
    if [ -e "$port" ]; then
        echo "✅ Arduino found at $port"
        ARDUINO_FOUND=true
        ARDUINO_PORT="$port"
        break
    fi
done

if [ "$ARDUINO_FOUND" = false ]; then
    echo "⚠️  No Arduino detected (optional for SystemHealthGuardian)"
fi
echo ""

# Summary
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Available Agents:"
echo "  1. SystemHealthGuardian (replaces arduino_system_monitor_daemon.py)"
echo "  2. CodeEvolutionProtector (evolution-aware protection)"
echo ""

if [ "$ARDUINO_FOUND" = true ]; then
    echo "To run SystemHealthGuardian:"
    echo "  python3 specialized/system_health_guardian.py $ARDUINO_PORT"
    echo ""
fi

echo "To run CodeEvolutionProtector:"
echo "  python3 specialized/code_evolution_protector.py"
echo ""

echo "See README.md for full documentation"
echo ""

if [ "$API_KEYS_OK" = false ]; then
    echo "⚠️  Remember to set API keys before running agents"
fi

echo ""
echo "🤖 Ready to run intelligent agents!"
