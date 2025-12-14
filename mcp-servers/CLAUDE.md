# MCP Servers - Context

**Location:** `/mnt/agentic-system/mcp-servers/`
**Purpose:** Model Context Protocol server implementations

## Active Servers

| Server | Port/Socket | Purpose |
|--------|-------------|---------|
| `enhanced-memory-mcp` | Unix socket | Versioned memory, RAG, 4-tier memory |
| `agent-runtime-mcp` | Unix socket | Goals, tasks, persistent queues |
| `SAFLA` | Unix socket | Self-aware framework (1.75M+ ops/sec) |
| `ember-mcp` | Unix socket | Quality conscience, violation checking |
| `voice-mode` | Unix socket | Speech I/O |
| `research-paper-mcp` | Unix socket | arXiv, Semantic Scholar |
| `security-scanner-mcp` | Unix socket | Nuclei vulnerability scanning |
| `node-chat-mcp` | Unix socket | Inter-node communication |

## Server Structure

Each server follows:
```
server-name/
├── src/
│   └── server_name/
│       ├── __init__.py
│       ├── server.py      # Main MCP server
│       └── tools.py       # Tool implementations
├── pyproject.toml
└── README.md
```

## Creating a New Server

1. **Setup:**
```bash
mkdir my-mcp && cd my-mcp
# Use existing server as template
```

2. **Server Pattern:**
```python
from mcp.server import Server
from mcp.server.stdio import stdio_server

server = Server("my-server")

@server.tool()
async def my_tool(param: str) -> str:
    """Tool description."""
    return result

async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write)
```

3. **Install:**
```bash
pip install -e .
```

4. **Configure:**
Add to `~/.claude.json` mcpServers section

## Key Servers Detail

### enhanced-memory-mcp
- 4-tier memory: working, episodic, semantic, procedural
- Version control for memories
- Hybrid search (BM25 + vector)
- Uses Qdrant backend

### SAFLA
- Extreme optimization (1.75M+ ops/sec)
- Embedding generation
- Memory operations

### ember-mcp
- Quality conscience keeper
- Violation checking
- Learning from corrections

## Testing

```bash
cd /mnt/agentic-system/mcp-servers/[server]
source .venv/bin/activate  # Server-specific venv
python -m pytest tests/
```

## Configuration

All servers configured in `~/.claude.json`:
```json
{
  "mcpServers": {
    "server-name": {
      "command": "uv",
      "args": ["run", "--directory", "/path", "server-name"]
    }
  }
}
```
