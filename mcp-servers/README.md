# MCP Servers

This directory contains MCP (Model Context Protocol) servers for the agentic system.

## Installation

Each MCP server has an `install.sh` script that handles its setup:

```bash
cd enhanced-memory-mcp
./install.sh
```

Or use the main bootstrap script which installs all servers automatically:

```bash
cd /path/to/agentic-system
./bootstrap.sh
```

## Available Servers

### enhanced-memory-mcp
Provides 4-tier memory architecture with compression, versioning, and RAG capabilities.

**Features**:
- Working memory (volatile, short-term)
- Episodic memory (experiences and events)
- Semantic memory (timeless knowledge)
- Procedural memory (skills and procedures)
- Git-like versioning with branches and commits
- Compression and consolidation
- Multi-query RAG with re-ranking

**Port**: 8101

### agent-runtime-mcp
Persistent task and goal management that survives across sessions.

**Features**:
- Goal creation and decomposition
- Task queue management
- Dependency tracking
- Session persistence
- Priority-based scheduling

**Port**: 8102

## Manual Installation

If the install scripts don't work on your platform:

1. **Copy the full MCP server from the source node**:
   ```bash
   scp -r source-node:/path/to/mcp-servers/enhanced-memory-mcp ./mcp-servers/
   ```

2. **Install Python dependencies**:
   ```bash
   cd mcp-servers/enhanced-memory-mcp
   pip3 install -r requirements.txt
   ```

3. **Test the server**:
   ```bash
   python3 server.py
   ```

4. **Add to your CLI configuration** (see config-templates/)

## Configuration

MCP servers are configured in your CLI's configuration file:
- **Claude Code**: `~/.claude.json`
- **OpenAI Code**: `~/.openai.json`
- **Gemini CLI**: `~/.gemini.json`

The bootstrap script handles this automatically using templates from `config-templates/`.
