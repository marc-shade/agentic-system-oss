#!/bin/bash
# Setup script for agi-extended plugin
# Starts Docker services and initializes vector memory

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}AGI-Extended Plugin Setup${NC}"
echo "=========================="

PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="$HOME/.claude/agi"

echo -e "\n${YELLOW}Configuration:${NC}"
echo "  Plugin: $PLUGIN_DIR"
echo "  Data: $DATA_DIR"

# Check Docker
echo -e "\n${YELLOW}Checking Docker...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker not found. Please install Docker.${NC}"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}Error: Docker daemon not running.${NC}"
    exit 1
fi
echo -e "${GREEN}Docker OK${NC}"

# Check docker-compose
echo -e "\n${YELLOW}Checking docker-compose...${NC}"
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    echo -e "${RED}Error: docker-compose not found.${NC}"
    exit 1
fi
echo -e "${GREEN}Using: $COMPOSE_CMD${NC}"

# Create directories
echo -e "\n${YELLOW}Creating directories...${NC}"
mkdir -p "$DATA_DIR/databases"
mkdir -p "$DATA_DIR/research-papers"
mkdir -p "$DATA_DIR/video-transcripts"

# Start Docker services
echo -e "\n${YELLOW}Starting Docker services...${NC}"
cd "$PLUGIN_DIR/docker"
$COMPOSE_CMD up -d

# Wait for Qdrant
echo -e "\n${YELLOW}Waiting for Qdrant to be ready...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:6333/health > /dev/null 2>&1; then
        echo -e "${GREEN}Qdrant is ready!${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}Timeout waiting for Qdrant${NC}"
        exit 1
    fi
    sleep 1
    echo -n "."
done

# Initialize Qdrant collections
echo -e "\n${YELLOW}Initializing Qdrant collections...${NC}"
python3 "$PLUGIN_DIR/scripts/init-qdrant.py"

# Install Python dependencies
echo -e "\n${YELLOW}Installing Python dependencies...${NC}"
pip3 install --quiet qdrant-client sentence-transformers whisper edge-tts yt-dlp 2>/dev/null || true

# Verify MCP servers
echo -e "\n${YELLOW}Verifying MCP servers...${NC}"

for server in enhanced-memory research-paper video-transcript voice-mode; do
    if [ -f "$PLUGIN_DIR/mcp/$server/server.py" ]; then
        echo -e "${GREEN}  $server: OK${NC}"
    else
        echo -e "${RED}  $server: MISSING${NC}"
    fi
done

echo -e "\n${GREEN}Setup complete!${NC}"
echo ""
echo "Docker services running:"
$COMPOSE_CMD ps
echo ""
echo "Next steps:"
echo "  1. Restart Claude Code to load MCP servers"
echo "  2. Run /agi-research to start learning"
echo "  3. Run /agi-improve to enhance capabilities"
echo ""
echo "To stop services: $PLUGIN_DIR/scripts/stop-services.sh"
