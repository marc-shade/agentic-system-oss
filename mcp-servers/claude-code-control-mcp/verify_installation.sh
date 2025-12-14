#!/bin/bash
# Verification script for Claude Code Control MCP installation

echo "=============================================="
echo "Claude Code Control MCP - Installation Check"
echo "=============================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo -n "Checking Python version... "
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 9 ]; then
    echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION"
else
    echo -e "${RED}✗${NC} Python $PYTHON_VERSION (need 3.9+)"
    exit 1
fi

# Check required packages
echo -n "Checking anthropic package... "
if python3 -c "import anthropic" 2>/dev/null; then
    VERSION=$(python3 -c "import anthropic; print(anthropic.__version__)" 2>/dev/null)
    echo -e "${GREEN}✓${NC} anthropic $VERSION"
else
    echo -e "${RED}✗${NC} Not installed"
    echo "  Install with: pip3 install anthropic"
    exit 1
fi

echo -n "Checking mcp package... "
if python3 -c "import mcp" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} mcp installed"
else
    echo -e "${RED}✗${NC} Not installed"
    echo "  Install with: pip3 install mcp"
    exit 1
fi

echo -n "Checking pathspec package... "
if python3 -c "import pathspec" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} pathspec installed"
else
    echo -e "${YELLOW}⚠${NC} Not installed (optional)"
fi

# Check API key
echo ""
echo -n "Checking ANTHROPIC_API_KEY... "
if [ -n "$ANTHROPIC_API_KEY" ]; then
    if [[ $ANTHROPIC_API_KEY == sk-ant-* ]]; then
        echo -e "${GREEN}✓${NC} Set (${ANTHROPIC_API_KEY:0:15}...)"
    else
        echo -e "${YELLOW}⚠${NC} Set but doesn't match expected format"
    fi
else
    echo -e "${YELLOW}⚠${NC} Not set"
    echo "  Set with: export ANTHROPIC_API_KEY='sk-ant-...'"
fi

# Check files
echo ""
echo "Checking required files..."

FILES=(
    "server.py"
    "executor.py"
    "file_tracker.py"
    "requirements.txt"
    "README.md"
    "QUICKSTART.md"
    "test_server.py"
    "example_usage.py"
)

for file in "${FILES[@]}"; do
    echo -n "  $file... "
    if [ -f "$file" ]; then
        if [ -x "$file" ] || [[ $file == *.md ]] || [[ $file == *.txt ]]; then
            echo -e "${GREEN}✓${NC}"
        else
            echo -e "${YELLOW}⚠${NC} Not executable"
        fi
    else
        echo -e "${RED}✗${NC} Missing"
        exit 1
    fi
done

# Check MCP configuration
echo ""
echo -n "Checking MCP configuration... "
if [ -f ~/.claude.json ]; then
    if grep -q "claude-code-control" ~/.claude.json; then
        echo -e "${GREEN}✓${NC} Registered in ~/.claude.json"

        # Check if disabled
        DISABLED=$(cat ~/.claude.json | jq -r '.mcpServers."claude-code-control".disabled' 2>/dev/null)
        if [ "$DISABLED" == "true" ]; then
            echo -e "  ${YELLOW}⚠${NC} Server is disabled"
            echo "  Enable by setting 'disabled': false and adding your API key"
        else
            echo -e "  ${GREEN}✓${NC} Server is enabled"
        fi
    else
        echo -e "${YELLOW}⚠${NC} Not registered"
        echo "  Add configuration to ~/.claude.json (see README.md)"
    fi
else
    echo -e "${RED}✗${NC} ~/.claude.json not found"
fi

# Test imports
echo ""
echo "Testing component imports..."

echo -n "  file_tracker... "
if python3 -c "from file_tracker import FileTracker; FileTracker('/tmp')" 2>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    exit 1
fi

echo -n "  executor... "
if [ -n "$ANTHROPIC_API_KEY" ]; then
    if python3 -c "from executor import TaskExecutor; TaskExecutor()" 2>/dev/null; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠${NC} Skipped (no API key)"
fi

# Summary
echo ""
echo "=============================================="
echo "Summary"
echo "=============================================="

WARNINGS=0
ERRORS=0

if [ "$PYTHON_MAJOR" -lt 3 ] || [ "$PYTHON_MINOR" -lt 9 ]; then
    ERRORS=$((ERRORS + 1))
fi

if ! python3 -c "import anthropic" 2>/dev/null; then
    ERRORS=$((ERRORS + 1))
fi

if ! python3 -c "import mcp" 2>/dev/null; then
    ERRORS=$((ERRORS + 1))
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
    WARNINGS=$((WARNINGS + 1))
fi

if [ ! -f ~/.claude.json ] || ! grep -q "claude-code-control" ~/.claude.json; then
    WARNINGS=$((WARNINGS + 1))
fi

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ Installation complete and ready!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Set ANTHROPIC_API_KEY in ~/.claude.json"
    echo "  2. Set 'disabled': false in MCP configuration"
    echo "  3. Restart Claude Code"
    echo "  4. Try: python3 example_usage.py"
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ Installation complete with warnings${NC}"
    echo "  $WARNINGS warning(s) found"
    echo ""
    echo "Review warnings above and configure as needed"
else
    echo -e "${RED}✗ Installation incomplete${NC}"
    echo "  $ERRORS error(s) found"
    echo "  $WARNINGS warning(s) found"
    echo ""
    echo "Fix errors above before continuing"
    exit 1
fi

echo ""
echo "Documentation:"
echo "  Quick start: cat QUICKSTART.md"
echo "  Full docs:   cat README.md"
echo "  Design doc:  cat ../../../docs/CLAUDE_CODE_CONTROL_MCP_DESIGN.md"
echo ""
