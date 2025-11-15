#!/bin/bash
# Install Ollama - Local LLM Server

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "📦 Installing Ollama..."
echo "======================="
echo ""

# Check if already installed
if command -v ollama &> /dev/null; then
    echo -e "${YELLOW}⚠ Ollama already installed${NC}"
    ollama --version
    exit 0
fi

# Detect OS
OS=$(uname -s)

case "$OS" in
    Darwin)
        echo "Detected macOS"
        if command -v brew &> /dev/null; then
            echo "Installing via Homebrew..."
            brew install ollama
        else
            echo "Homebrew not found. Installing via official script..."
            curl -fsSL https://ollama.ai/install.sh | sh
        fi
        ;;
    Linux)
        echo "Detected Linux"
        echo "Installing via official script..."
        curl -fsSL https://ollama.ai/install.sh | sh
        ;;
    *)
        echo -e "${RED}✗ Unsupported OS: $OS${NC}"
        echo "Please install Ollama manually from https://ollama.ai/download"
        exit 1
        ;;
esac

# Verify installation
if command -v ollama &> /dev/null; then
    echo ""
    echo -e "${GREEN}✓ Ollama installed successfully${NC}"
    ollama --version

    # Start Ollama service in background
    echo ""
    echo "Starting Ollama service..."
    nohup ollama serve > /tmp/ollama.log 2>&1 &
    sleep 2

    # Pull default model
    echo ""
    echo "Pulling default model (llama2)..."
    ollama pull llama2

    echo -e "${GREEN}✓ Ollama ready${NC}"
else
    echo -e "${RED}✗ Installation failed${NC}"
    exit 1
fi
