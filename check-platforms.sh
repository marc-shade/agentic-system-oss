#!/bin/bash
# Platform Detection - Used by Claude Code during onboarding

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🔍 Checking Platform Installation Status"
echo "========================================="
echo ""

PLATFORMS_FOUND=0
PLATFORMS_MISSING=()
PLATFORMS_STATUS=()

# Check Claude Code
if command -v claude-code &> /dev/null; then
    echo -e "${GREEN}✓ Claude Code installed${NC}"
    PLATFORMS_STATUS+=("claude-code:installed")
    PLATFORMS_FOUND=$((PLATFORMS_FOUND + 1))
else
    echo -e "${RED}✗ Claude Code NOT installed${NC}"
    echo "   Install from: https://code.claude.com"
    PLATFORMS_STATUS+=("claude-code:missing")
    PLATFORMS_MISSING+=("Claude Code")
fi

# Check Ollama
if command -v ollama &> /dev/null; then
    echo -e "${GREEN}✓ Ollama installed${NC}"
    OLLAMA_VERSION=$(ollama --version 2>/dev/null || echo "unknown")
    echo "   Version: $OLLAMA_VERSION"
    PLATFORMS_STATUS+=("ollama:installed")
    PLATFORMS_FOUND=$((PLATFORMS_FOUND + 1))
else
    echo -e "${YELLOW}⚠ Ollama NOT installed${NC}"
    echo "   Install from: https://ollama.ai/download"
    PLATFORMS_STATUS+=("ollama:missing")
    PLATFORMS_MISSING+=("Ollama")
fi

# Check OpenAI Codex
if command -v codex &> /dev/null; then
    echo -e "${GREEN}✓ OpenAI Codex installed${NC}"
    CODEX_VERSION=$(codex --version 2>/dev/null || echo "unknown")
    echo "   Version: $CODEX_VERSION"

    # Check auth status
    if codex login status &> /dev/null; then
        echo -e "   ${GREEN}✓ Authenticated${NC}"
        PLATFORMS_STATUS+=("codex:installed:authenticated")
    else
        echo -e "   ${YELLOW}⚠ Not authenticated${NC}"
        PLATFORMS_STATUS+=("codex:installed:not-authenticated")
    fi
    PLATFORMS_FOUND=$((PLATFORMS_FOUND + 1))
else
    echo -e "${YELLOW}⚠ OpenAI Codex NOT installed${NC}"
    echo "   Follow OpenAI's installation guide"
    PLATFORMS_STATUS+=("codex:missing")
    PLATFORMS_MISSING+=("OpenAI Codex")
fi

# Check Gemini CLI
if command -v gemini &> /dev/null; then
    echo -e "${GREEN}✓ Gemini CLI installed${NC}"
    GEMINI_VERSION=$(gemini --version 2>/dev/null || echo "unknown")
    echo "   Version: $GEMINI_VERSION"

    # Check for API key
    if [ -n "$GEMINI_API_KEY" ] || [ -f "$HOME/.gemini/.env" ]; then
        echo -e "   ${GREEN}✓ API key configured${NC}"
        PLATFORMS_STATUS+=("gemini:installed:authenticated")
    else
        echo -e "   ${YELLOW}⚠ API key not configured${NC}"
        PLATFORMS_STATUS+=("gemini:installed:not-authenticated")
    fi
    PLATFORMS_FOUND=$((PLATFORMS_FOUND + 1))
else
    echo -e "${YELLOW}⚠ Gemini CLI NOT installed${NC}"
    echo "   Install: npm install -g @google/generative-ai-cli"
    PLATFORMS_STATUS+=("gemini:missing")
    PLATFORMS_MISSING+=("Gemini CLI")
fi

echo ""
echo "─────────────────────────────────────────"
echo -e "Platforms installed: ${GREEN}$PLATFORMS_FOUND/4${NC}"

if [ ${#PLATFORMS_MISSING[@]} -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}Missing platforms:${NC}"
    for platform in "${PLATFORMS_MISSING[@]}"; do
        echo "  - $platform"
    done
fi

# Output JSON for Claude Code to parse
cat > /tmp/platform-status.json <<EOF
{
  "total_found": $PLATFORMS_FOUND,
  "platforms": {
$(IFS=$'\n'; echo "${PLATFORMS_STATUS[*]}" | awk '{print "    \"" $0 "\": true,"}' | sed '$ s/,$//')
  },
  "missing": [
$(if [ ${#PLATFORMS_MISSING[@]} -gt 0 ]; then
    printf '    "%s"' "${PLATFORMS_MISSING[0]}"
    for platform in "${PLATFORMS_MISSING[@]:1}"; do
        printf ',\n    "%s"' "$platform"
    done
    echo ""
fi)
  ]
}
EOF

echo ""
echo "📊 Status saved to: /tmp/platform-status.json"

# Exit with status based on platforms found
if [ $PLATFORMS_FOUND -eq 4 ]; then
    echo ""
    echo -e "${GREEN}✓ All platforms installed!${NC}"
    exit 0
elif [ $PLATFORMS_FOUND -ge 1 ]; then
    echo ""
    echo -e "${YELLOW}⚠ Partial installation${NC}"
    exit 1
else
    echo ""
    echo -e "${RED}✗ No platforms found${NC}"
    exit 2
fi
