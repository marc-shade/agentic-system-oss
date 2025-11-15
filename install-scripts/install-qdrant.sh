#!/bin/bash
# Install Qdrant - Vector Database

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "📦 Installing Qdrant..."
echo "======================="
echo ""

# Check if Qdrant is running
if curl -s http://localhost:6333 > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠ Qdrant already running${NC}"
    exit 0
fi

# Detect OS
OS=$(uname -s)

echo "Checking installation method..."
echo ""

# Try Docker first (preferred)
if command -v docker &> /dev/null; then
    echo "Docker found - installing Qdrant via Docker..."

    # Check if container already exists
    if docker ps -a | grep -q qdrant; then
        echo "Qdrant container exists, starting..."
        docker start qdrant || docker rm qdrant
    fi

    # Run Qdrant container
    docker run -d \
        --name qdrant \
        -p 6333:6333 \
        -p 6334:6334 \
        -v "$(pwd)/databases/qdrant:/qdrant/storage" \
        qdrant/qdrant:latest

    sleep 3

elif [ "$OS" = "Darwin" ] && command -v brew &> /dev/null; then
    echo "macOS with Homebrew - installing Qdrant via brew..."
    brew install qdrant

    # Start Qdrant service
    brew services start qdrant

    sleep 3

else
    echo -e "${YELLOW}⚠ Neither Docker nor Homebrew available${NC}"
    echo ""
    echo "Please install Qdrant manually:"
    echo "  1. Install Docker: https://docs.docker.com/get-docker/"
    echo "  2. Run: docker run -d -p 6333:6333 qdrant/qdrant"
    echo ""
    echo "OR download binary from: https://qdrant.tech/documentation/quick-start/"
    exit 1
fi

# Verify Qdrant is running
echo ""
echo "Verifying Qdrant..."
sleep 2

if curl -s http://localhost:6333 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Qdrant installed and running${NC}"
    echo "  Access at: http://localhost:6333"
    echo "  Dashboard: http://localhost:6333/dashboard"
else
    echo -e "${RED}✗ Qdrant installation failed${NC}"
    exit 1
fi
