# MCP Builder Skill

Guide for creating high-quality MCP (Model Context Protocol) servers that enable LLMs to interact with external services through well-designed tools.

## When to Use

Invoke this skill when:
- Building a new MCP server
- Debugging MCP server issues
- Designing tool schemas
- Integrating external APIs

## MCP Server Structure

```
my-mcp-server/
├── src/
│   └── my_server/
│       ├── __init__.py
│       ├── server.py      # Main MCP server
│       └── tools.py       # Tool implementations
├── pyproject.toml
└── README.md
```

## Basic Server Pattern (Python)

```python
#!/usr/bin/env python3
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

server = Server("my-server")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="my_tool",
            description="What this tool does",
            inputSchema={
                "type": "object",
                "properties": {
                    "param": {
                        "type": "string",
                        "description": "Parameter description"
                    }
                },
                "required": ["param"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "my_tool":
        result = do_something(arguments.get("param"))
        return [types.TextContent(type="text", text=result)]
    raise ValueError(f"Unknown tool: {name}")

async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## Tool Design Best Practices

1. **Clear Names**: Use verb_noun format (search_files, create_entity)
2. **Descriptive Schemas**: Include descriptions for all parameters
3. **Sensible Defaults**: Provide defaults where appropriate
4. **Error Handling**: Return helpful error messages
5. **JSON Output**: Return structured JSON for complex results

## Configuration Pattern

Use environment variables for configuration:

```python
import os

API_KEY = os.environ.get("MY_API_KEY", "")
DATA_DIR = os.environ.get("MY_DATA_DIR", "~/.my-server")
```

## Testing

```bash
# Test standalone
python3 server.py

# With Claude Code
# Add to ~/.claude.json and restart Claude Code
```

## Common Issues

1. **Import errors**: Check all dependencies installed
2. **Schema validation**: Ensure inputSchema matches JSON Schema spec
3. **Async issues**: All tool handlers must be async
4. **Stdio conflicts**: Don't print to stdout (use stderr for logging)
