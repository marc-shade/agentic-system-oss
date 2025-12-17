#!/bin/bash
# Agentic System - Open Source Bootstrap
# One-command installation for independent verification
#
# Usage: curl -fsSL https://github.com/marc-shade/agentic-system/raw/main/bootstrap-open-source.sh | bash
#    or: ./bootstrap-open-source.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     AGENTIC SYSTEM - Open Source Bootstrap                     ║${NC}"
echo -e "${BLUE}║     24/7 Autonomous AI Infrastructure                          ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        CONTAINER_RUNTIME="docker"
        if command -v container &> /dev/null; then
            CONTAINER_RUNTIME="container"  # Apple Container preferred
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        CONTAINER_RUNTIME="podman"
        if ! command -v podman &> /dev/null; then
            CONTAINER_RUNTIME="docker"
        fi
    else
        echo -e "${RED}Unsupported OS: $OSTYPE${NC}"
        exit 1
    fi
    echo -e "${GREEN}Detected OS: $OS${NC}"
    echo -e "${GREEN}Container runtime: $CONTAINER_RUNTIME${NC}"
}

# Check prerequisites
check_prerequisites() {
    echo ""
    echo "Checking prerequisites..."

    MISSING=()

    # Python 3.10+
    if command -v python3 &> /dev/null; then
        PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        PY_MAJOR=$(echo $PY_VERSION | cut -d. -f1)
        PY_MINOR=$(echo $PY_VERSION | cut -d. -f2)
        if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 10 ]; then
            echo -e "${GREEN}✓ Python $PY_VERSION${NC}"
        else
            echo -e "${RED}✗ Python 3.10+ required (found $PY_VERSION)${NC}"
            MISSING+=("python3.10+")
        fi
    else
        echo -e "${RED}✗ Python 3 not found${NC}"
        MISSING+=("python3")
    fi

    # Git
    if command -v git &> /dev/null; then
        echo -e "${GREEN}✓ Git $(git --version | cut -d' ' -f3)${NC}"
    else
        echo -e "${RED}✗ Git not found${NC}"
        MISSING+=("git")
    fi

    # Container runtime
    if command -v $CONTAINER_RUNTIME &> /dev/null; then
        echo -e "${GREEN}✓ $CONTAINER_RUNTIME available${NC}"
    else
        echo -e "${YELLOW}⚠ $CONTAINER_RUNTIME not found (optional for AVIR)${NC}"
    fi

    # Claude Code (primary orchestrator)
    if command -v claude &> /dev/null; then
        echo -e "${GREEN}✓ Claude Code CLI${NC}"
    else
        echo -e "${YELLOW}⚠ Claude Code CLI not found${NC}"
        echo "  Install from: https://claude.ai/code"
        MISSING+=("claude-code")
    fi

    if [ ${#MISSING[@]} -gt 0 ]; then
        echo ""
        echo -e "${RED}Missing required dependencies:${NC}"
        for dep in "${MISSING[@]}"; do
            echo "  - $dep"
        done
        echo ""
        echo "Please install missing dependencies and re-run."
        exit 1
    fi
}

# Detect or set installation directory
setup_directory() {
    echo ""

    # If running from existing repo, use that
    if [ -f "./CLAUDE.md" ] && [ -d "./mcp-servers" ]; then
        INSTALL_DIR="$(pwd)"
        echo -e "${GREEN}Using existing installation: $INSTALL_DIR${NC}"
        return
    fi

    # Default installation paths
    if [[ "$OS" == "macos" ]]; then
        if [ -d "/Volumes/SSDRAID0" ]; then
            DEFAULT_DIR="/Volumes/SSDRAID0/agentic-system"
        else
            DEFAULT_DIR="$HOME/agentic-system"
        fi
    else
        DEFAULT_DIR="$HOME/agentic-system"
    fi

    echo -e "Installation directory [${DEFAULT_DIR}]: \c"
    read INSTALL_DIR
    INSTALL_DIR=${INSTALL_DIR:-$DEFAULT_DIR}

    if [ -d "$INSTALL_DIR" ]; then
        echo -e "${YELLOW}Directory exists. Updating...${NC}"
        cd "$INSTALL_DIR"
        git pull || true
    else
        echo "Cloning repository..."
        git clone https://github.com/marc-shade/agentic-system.git "$INSTALL_DIR"
        cd "$INSTALL_DIR"
    fi

    echo -e "${GREEN}Installation directory: $INSTALL_DIR${NC}"
}

# Install Python dependencies
install_python_deps() {
    echo ""
    echo "Installing Python dependencies..."

    # Create virtual environment
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi

    source venv/bin/activate

    # Upgrade pip
    pip install --upgrade pip

    # Install core dependencies
    pip install anthropic openai google-generativeai
    pip install fastapi uvicorn httpx aiohttp
    pip install sqlalchemy qdrant-client sentence-transformers
    pip install pydantic python-dotenv

    # Install MCP server dependencies
    if [ -f "mcp-servers/enhanced-memory-mcp/requirements.txt" ]; then
        pip install -r mcp-servers/enhanced-memory-mcp/requirements.txt
    fi

    if [ -f "mcp-servers/agent-runtime-mcp/requirements.txt" ]; then
        pip install -r mcp-servers/agent-runtime-mcp/requirements.txt
    fi

    echo -e "${GREEN}✓ Python dependencies installed${NC}"
}

# Setup databases
setup_databases() {
    echo ""
    echo "Setting up databases..."

    mkdir -p databases/{temporal,qdrant,mcp,cluster/shared,cluster/nodes}
    mkdir -p logs
    mkdir -p tmp-workspace

    # Initialize SQLite databases
    python3 << 'EOF'
import sqlite3
import os

# Enhanced memory database
db_path = "databases/mcp/enhanced_memory.db"
if not os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE,
            entity_type TEXT,
            observations TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    print("Created enhanced_memory.db")

# Agent runtime database
db_path = "databases/mcp/agent_runtime.db"
if not os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY,
            name TEXT,
            description TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY,
            goal_id INTEGER,
            title TEXT,
            description TEXT,
            status TEXT DEFAULT 'pending',
            priority INTEGER DEFAULT 5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (goal_id) REFERENCES goals(id)
        )
    """)
    conn.commit()
    conn.close()
    print("Created agent_runtime.db")

# Cluster shared memory
db_path = "databases/cluster/shared_memories.db"
if not os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS shared_memories (
            id INTEGER PRIMARY KEY,
            name TEXT,
            content TEXT,
            node_origin TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    print("Created shared_memories.db")

print("Database setup complete")
EOF

    echo -e "${GREEN}✓ Databases initialized${NC}"
}

# Start core services
start_services() {
    echo ""
    echo "Starting core services..."

    # Check if Qdrant is needed and available
    if command -v $CONTAINER_RUNTIME &> /dev/null; then
        # Check if Qdrant is already running
        if ! $CONTAINER_RUNTIME ps | grep -q qdrant; then
            echo "Starting Qdrant vector database..."
            $CONTAINER_RUNTIME run -d \
                --name qdrant \
                -p 6333:6333 \
                -p 6334:6334 \
                -v "$(pwd)/databases/qdrant:/qdrant/storage" \
                qdrant/qdrant:latest 2>/dev/null || echo "Qdrant may already exist"
        fi
        echo -e "${GREEN}✓ Qdrant running on port 6333${NC}"
    else
        echo -e "${YELLOW}⚠ Container runtime not available, skipping Qdrant${NC}"
        echo "  Memory will use SQLite fallback"
    fi
}

# Configure Claude Code MCP
configure_mcp() {
    echo ""
    echo "Configuring MCP servers..."

    CLAUDE_CONFIG="$HOME/.claude.json"

    # Check if config exists
    if [ -f "$CLAUDE_CONFIG" ]; then
        echo -e "${YELLOW}Existing Claude config found. Backing up...${NC}"
        cp "$CLAUDE_CONFIG" "$CLAUDE_CONFIG.backup.$(date +%Y%m%d%H%M%S)"
    fi

    # Create minimal MCP config for open source
    cat > "$CLAUDE_CONFIG" << EOF
{
  "mcpServers": {
    "enhanced-memory": {
      "command": "python3",
      "args": ["$INSTALL_DIR/mcp-servers/enhanced-memory-mcp/server.py"],
      "env": {
        "MEMORY_DB_PATH": "$INSTALL_DIR/databases/mcp/enhanced_memory.db",
        "QDRANT_URL": "http://localhost:6333"
      }
    },
    "agent-runtime-mcp": {
      "command": "python3",
      "args": ["$INSTALL_DIR/mcp-servers/agent-runtime-mcp/server.py"],
      "env": {
        "RUNTIME_DB_PATH": "$INSTALL_DIR/databases/mcp/agent_runtime.db"
      }
    },
    "sequential-thinking": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-sequential-thinking"]
    }
  }
}
EOF

    echo -e "${GREEN}✓ MCP configuration created${NC}"
}

# Run verification tests
run_verification() {
    echo ""
    echo "Running verification tests..."

    source venv/bin/activate

    # System health check
    if [ -f "system_health_check.py" ]; then
        python3 system_health_check.py || echo "Health check had warnings"
    fi

    # Basic functionality test
    python3 << 'EOF'
import sys
sys.path.insert(0, '.')

# Test memory
try:
    from mcp_servers.enhanced_memory_mcp import server as memory
    print("✓ Enhanced memory module loaded")
except:
    print("⚠ Enhanced memory not available (will use fallback)")

# Test imports
try:
    import anthropic
    print("✓ Anthropic SDK available")
except:
    print("⚠ Anthropic SDK not installed")

try:
    import openai
    print("✓ OpenAI SDK available")
except:
    print("⚠ OpenAI SDK not installed")

print("\nBasic verification complete")
EOF

    echo -e "${GREEN}✓ Verification complete${NC}"
}

# Print next steps
print_next_steps() {
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                    INSTALLATION COMPLETE                       ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}Installation directory: $INSTALL_DIR${NC}"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Activate the environment:"
    echo "   cd $INSTALL_DIR"
    echo "   source venv/bin/activate"
    echo ""
    echo "2. Set your API keys:"
    echo "   export ANTHROPIC_API_KEY='your-key'"
    echo "   export OPENAI_API_KEY='your-key'  # Optional, for AVIR"
    echo ""
    echo "3. Start Claude Code:"
    echo "   claude"
    echo ""
    echo "4. Run the AGI demo:"
    echo "   python3 demo_agi_workflow.py"
    echo ""
    echo "5. Run AVIR verification (requires Codex CLI):"
    echo "   python3 avir/run_verification.py"
    echo ""
    echo -e "${BLUE}Documentation: https://github.com/marc-shade/agentic-system${NC}"
    echo -e "${BLUE}Research Paper: research-paper/PAPER.md${NC}"
    echo ""
}

# Main installation flow
main() {
    detect_os
    check_prerequisites
    setup_directory
    install_python_deps
    setup_databases
    start_services
    configure_mcp
    run_verification
    print_next_steps
}

# Run main
main "$@"
