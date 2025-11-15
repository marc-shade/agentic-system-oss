#!/bin/bash
# Agentic System - Local Network Bootstrap
# Transfer this single file to a new node and run it to bootstrap the entire system
#
# Usage:
#   1. Copy this file to the new node: scp bootstrap-local.sh user@newnode:~/
#   2. Run on new node: bash bootstrap-local.sh
#   3. Follow voice-guided setup
#
# This script can:
#   - Clone from GitHub (if you have credentials)
#   - Clone from a local node on the network (no internet needed)
#   - Download as zip and extract

set -e

# OS-specific TTS function (works out of the box)
speak() {
    local message="$1"

    case "$(uname -s)" in
        Darwin)
            say "$message"
            ;;
        Linux)
            if command -v spd-say &> /dev/null; then
                spd-say "$message"
            elif command -v espeak &> /dev/null; then
                espeak "$message"
            elif command -v festival &> /dev/null; then
                echo "$message" | festival --tts
            else
                echo "🔊 $message"
            fi
            ;;
        MINGW*|MSYS*|CYGWIN*)
            powershell -Command "Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('$message')"
            ;;
        *)
            echo "🔊 $message"
            ;;
    esac
}

echo "🤖 Agentic System - Local Network Bootstrap"
echo "==========================================="
echo ""

speak "Welcome! I'm going to help you set up this node to join the agentic cluster. Let me first check your system prerequisites."

# === Check Prerequisites ===
echo "📋 Checking Prerequisites..."
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    speak "Python 3 is not installed. Please install Python 3.10 or newer first."
    echo "❌ Python 3 not found"
    echo ""
    echo "Install Python 3:"
    echo "  macOS: brew install python@3.11"
    echo "  Ubuntu/Debian: sudo apt install python3.11"
    echo "  Fedora: sudo dnf install python3.11"
    echo ""
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]; }; then
    speak "Python version $PYTHON_VERSION is too old. Please install Python 3.10 or newer."
    echo "❌ Python $PYTHON_VERSION (need 3.10+)"
    exit 1
fi

echo "✓ Python $PYTHON_VERSION"

# Check Git
if ! command -v git &> /dev/null; then
    speak "Git is not installed. Please install Git first."
    echo "❌ Git not found"
    echo ""
    echo "Install Git:"
    echo "  macOS: brew install git"
    echo "  Ubuntu/Debian: sudo apt install git"
    echo "  Fedora: sudo dnf install git"
    echo ""
    exit 1
fi

echo "✓ Git $(git --version | awk '{print $3}')"
echo ""

speak "Prerequisites check complete! Python and Git are installed. Now let's get the agentic system code."

# === Choose Installation Method ===
echo "📦 How would you like to get the agentic system code?"
echo ""
echo "  1) Clone from GitHub (requires internet + GitHub credentials)"
echo "  2) Clone from local node on the network (no internet needed)"
echo "  3) Download as zip from GitHub (requires internet, no credentials)"
echo ""

read -p "Enter choice (1-3): " INSTALL_METHOD

case "$INSTALL_METHOD" in
    1)
        # GitHub clone
        speak "I'll clone the repository from GitHub. You'll need your GitHub credentials."

        echo ""
        echo "GitHub Repository: https://github.com/marc-shade/agentic-system"
        echo ""

        REPO_DIR="$HOME/agentic-system"

        if [ -d "$REPO_DIR" ]; then
            speak "The agentic system directory already exists. I'll use the existing installation."
            echo "✓ Using existing installation at $REPO_DIR"
        else
            speak "Cloning from GitHub now. You may be prompted for credentials."

            if git clone https://github.com/marc-shade/agentic-system.git "$REPO_DIR"; then
                echo "✓ Repository cloned to $REPO_DIR"
                speak "Repository cloned successfully!"
            else
                speak "Failed to clone from GitHub. Please check your internet connection and credentials."
                echo "❌ Git clone failed"
                exit 1
            fi
        fi
        ;;

    2)
        # Local network clone
        speak "I'll clone from a local node on your network. You'll need the IP address or hostname of an existing node."

        echo ""
        read -p "Enter the IP or hostname of the source node: " SOURCE_NODE
        read -p "Enter the username on that node: " SOURCE_USER

        REPO_DIR="$HOME/agentic-system"
        SOURCE_PATH="/tmp/agentic-system-clean"  # Default location on source node

        speak "I'm going to clone from $SOURCE_NODE using git protocol or direct copy."

        # Try git clone over SSH first
        if git clone "ssh://${SOURCE_USER}@${SOURCE_NODE}${SOURCE_PATH}" "$REPO_DIR" 2>/dev/null; then
            echo "✓ Repository cloned via git+ssh"
            speak "Repository cloned successfully from local node!"
        else
            # Fallback to rsync/scp
            speak "Git clone didn't work. Trying direct copy with rsync."

            if command -v rsync &> /dev/null; then
                if rsync -avz --exclude='.git' "${SOURCE_USER}@${SOURCE_NODE}:${SOURCE_PATH}/" "$REPO_DIR/"; then
                    echo "✓ Files copied via rsync"
                    cd "$REPO_DIR"
                    git init
                    git remote add origin https://github.com/marc-shade/agentic-system.git
                    speak "Files copied successfully from local node!"
                else
                    speak "Failed to copy files. Please check the source node address and your SSH access."
                    echo "❌ rsync failed"
                    exit 1
                fi
            else
                speak "rsync is not available. Please install rsync or choose a different installation method."
                echo "❌ rsync not found"
                exit 1
            fi
        fi
        ;;

    3)
        # Download zip
        speak "I'll download the repository as a zip file from GitHub."

        REPO_DIR="$HOME/agentic-system"
        ZIP_URL="https://github.com/marc-shade/agentic-system/archive/refs/heads/master.zip"

        if command -v curl &> /dev/null; then
            if curl -L "$ZIP_URL" -o /tmp/agentic-system.zip; then
                unzip -q /tmp/agentic-system.zip -d /tmp/
                mv /tmp/agentic-system-master "$REPO_DIR"
                rm /tmp/agentic-system.zip
                echo "✓ Repository downloaded and extracted"
                speak "Repository downloaded successfully!"
            else
                speak "Failed to download from GitHub. Please check your internet connection."
                echo "❌ Download failed"
                exit 1
            fi
        else
            speak "curl is not installed. Please install curl or choose a different installation method."
            echo "❌ curl not found"
            exit 1
        fi
        ;;

    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

# === Run Full Onboarding ===
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Starting Full Onboarding Process"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

speak "The agentic system is now available on this node. I'm going to start the full onboarding process. This will install all required components and configure everything automatically."

cd "$REPO_DIR"

if [ -f "onboard-with-claude.sh" ]; then
    chmod +x onboard-with-claude.sh
    exec ./onboard-with-claude.sh
else
    speak "The onboarding script is missing from the repository. Please check the installation."
    echo "❌ onboard-with-claude.sh not found in $REPO_DIR"
    exit 1
fi
