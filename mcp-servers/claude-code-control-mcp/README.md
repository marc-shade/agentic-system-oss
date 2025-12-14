# Claude Code Control MCP Server

Programmatic task execution using Claude AI for autonomous coding workflows.

## Overview

The Claude Code Control MCP enables programmatic code task execution through the Model Context Protocol. It provides a bridge for AI agents and workflows to execute coding tasks using Claude Sonnet 4.5, with comprehensive file tracking, command execution, and status monitoring.

## Features

- **Programmatic Task Execution**: Execute natural language coding tasks autonomously
- **File Operations**: Read, write, edit, and track file changes
- **Code Search**: Grep-like search across codebases
- **Command Execution**: Run shell commands with output capture
- **Change Tracking**: Monitor all file modifications during execution
- **Status Monitoring**: Real-time execution status and history

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  MCP Client (Claude Code)               │
└────────────────────┬────────────────────────────────────┘
                     │ MCP Protocol
┌────────────────────▼────────────────────────────────────┐
│         Claude Code Control MCP Server                  │
│  ┌──────────────┐  ┌───────────────┐  ┌─────────────┐ │
│  │   Server     │  │   Executor    │  │   Tracker   │ │
│  │   (MCP)      │  │  (Claude AI)  │  │   (Files)   │ │
│  └──────────────┘  └───────────────┘  └─────────────┘ │
└────────────────────┬────────────────────────────────────┘
                     │ Anthropic API
┌────────────────────▼────────────────────────────────────┐
│         Claude Sonnet 4.5 (Anthropic API)              │
└─────────────────────────────────────────────────────────┘
```

## Installation

1. **Install dependencies**:
```bash
cd /mnt/agentic-system/mcp-servers/claude-code-control-mcp
pip3 install -r requirements.txt
```

2. **Set API key**:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

3. **Register with Claude Code**:

Add to `~/.claude.json`:
```json
{
  "mcpServers": {
    "claude-code-control": {
      "command": "python3",
      "args": [
        "/mnt/agentic-system/mcp-servers/claude-code-control-mcp/server.py"
      ],
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-..."
      },
      "disabled": false
    }
  }
}
```

4. **Restart Claude Code**:
```bash
# Exit current session and restart
```

## MCP Tools

### execute_code_task

Execute a coding task using Claude AI with autonomous tool use.

**Input**:
```json
{
  "task_description": "Add error handling to the API endpoint in server.py",
  "working_directory": "/mnt/agentic-system/api",
  "context_files": ["server.py", "tests/test_api.py"],
  "max_iterations": 20
}
```

**Output**:
```json
{
  "success": true,
  "task_description": "Add error handling...",
  "working_directory": "/mnt/agentic-system/api",
  "iterations": 8,
  "tool_uses": [
    {
      "tool": "read_file",
      "input": {"path": "server.py"},
      "result": "File content..."
    }
  ],
  "file_changes": {
    "total_changes": 2,
    "files_modified": ["server.py"],
    "files_created": [],
    "files_deleted": []
  },
  "duration_seconds": 12.5,
  "final_message": "Successfully added error handling..."
}
```

### read_codebase

Read and analyze multiple files using glob patterns.

**Input**:
```json
{
  "patterns": ["*.py", "src/**/*.ts"],
  "working_directory": "/mnt/agentic-system",
  "max_files": 50
}
```

**Output**:
```json
{
  "files_read": 12,
  "files": [
    {
      "path": "server.py",
      "size": 2048,
      "content": "#!/usr/bin/env python3..."
    }
  ]
}
```

### search_code

Search for code patterns across the codebase.

**Input**:
```json
{
  "query": "async def.*execute",
  "working_directory": "/mnt/agentic-system",
  "file_pattern": "*.py",
  "case_sensitive": true,
  "max_results": 100
}
```

**Output**:
```json
{
  "query": "async def.*execute",
  "total_matches": 5,
  "matches": [
    "executor.py:42:async def execute_task(...)",
    "server.py:156:async def execute_command(...)"
  ]
}
```

### modify_files

Modify multiple files with batch operations.

**Input**:
```json
{
  "changes": [
    {
      "path": "config.py",
      "action": "write",
      "content": "DEBUG = True\n"
    },
    {
      "path": "server.py",
      "action": "edit",
      "old_content": "port = 8080",
      "new_content": "port = 9000"
    }
  ],
  "working_directory": "/mnt/agentic-system"
}
```

**Output**:
```json
{
  "modifications": [
    {"path": "config.py", "status": "written"},
    {"path": "server.py", "status": "edited"}
  ],
  "file_changes": {
    "total_changes": 2,
    "files_created": ["config.py"],
    "files_modified": ["server.py"]
  }
}
```

### run_commands

Execute shell commands with output capture.

**Input**:
```json
{
  "commands": [
    "python3 -m pytest tests/",
    "black --check *.py"
  ],
  "working_directory": "/mnt/agentic-system",
  "timeout": 30
}
```

**Output**:
```json
{
  "command_results": [
    {
      "command": "python3 -m pytest tests/",
      "exit_code": 0,
      "stdout": "===== 5 passed in 2.5s =====",
      "stderr": ""
    },
    {
      "command": "black --check *.py",
      "exit_code": 0,
      "stdout": "All done! ✨",
      "stderr": ""
    }
  ]
}
```

### get_execution_status

Get status of current or recent execution.

**Input**:
```json
{
  "include_history": true
}
```

**Output**:
```json
{
  "current_execution": {
    "task_description": "Add error handling...",
    "success": true,
    "iterations": 8
  },
  "executor_initialized": true,
  "execution_history": [...]
}
```

## Usage Examples

### Example 1: Automated Code Refactoring

```python
# Using from Python with anthropic client
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=4096,
    tools=[...],  # MCP tools from claude-code-control
    messages=[{
        "role": "user",
        "content": "Refactor the authentication module to use async/await"
    }]
)
```

### Example 2: Autonomous Bug Fixing

```bash
# Using from Claude Code
claude --prompt "Fix the memory leak in server.py using the claude-code-control MCP"
```

### Example 3: Integration Testing

```python
# Using from workflow automation
from anthropic import Anthropic

client = Anthropic()

# Execute task
result = await mcp_execute_tool(
    "execute_code_task",
    {
        "task_description": "Add integration tests for the API endpoints",
        "working_directory": "/mnt/agentic-system/api",
        "context_files": ["server.py", "models.py"]
    }
)

print(f"Tests created: {result['file_changes']['files_created']}")
```

## Integration Points

### Temporal Workflows

```python
@workflow.defn
class CodeTaskWorkflow:
    @workflow.run
    async def run(self, task_description: str) -> dict:
        # Execute code task via MCP
        result = await workflow.execute_activity(
            execute_via_mcp,
            args=[task_description],
            start_to_close_timeout=timedelta(minutes=5)
        )
        return result
```

### n8n Workflows

Use HTTP Request node to call MCP server:
```javascript
{
  "method": "POST",
  "url": "http://localhost:PORT/execute",
  "body": {
    "tool": "execute_code_task",
    "arguments": {
      "task_description": "{{$json.task}}"
    }
  }
}
```

### Intelligent Agents

```python
from intelligent_agents.sdk_agents import ClaudeAgent

agent = ClaudeAgent()

# Agent uses MCP tools automatically
result = agent.execute(
    "Refactor authentication to use OAuth2",
    mcp_tools=["claude-code-control"]
)
```

## File Tracking

The MCP server tracks all file changes during execution:

- **Created files**: New files written
- **Modified files**: Existing files changed
- **Deleted files**: Files removed
- **Read files**: Files accessed for reading

Changes include:
- File hashes (SHA256)
- Size changes
- Timestamps
- Line change statistics (when available)

## Error Handling

The server handles errors gracefully:

- **Tool execution errors**: Returned with error details
- **File operation errors**: Logged and returned to caller
- **Command execution errors**: Exit codes and stderr captured
- **API errors**: Anthropic API errors propagated with context

## Security Considerations

1. **API Key Management**: Store `ANTHROPIC_API_KEY` securely
2. **File Access**: Limited to specified working directories
3. **Command Execution**: Shell commands run with user permissions
4. **Input Validation**: All inputs validated before execution
5. **Output Sanitization**: Sensitive data filtered from outputs

## Performance

- **Typical task execution**: 5-30 seconds
- **File operations**: < 1 second per file
- **Code search**: < 5 seconds for large codebases
- **Memory usage**: ~50-100MB during execution

## Troubleshooting

### Server won't start

```bash
# Check API key
echo $ANTHROPIC_API_KEY

# Test server directly
python3 server.py

# Check logs
tail -f ~/.claude/logs/mcp-servers.log
```

### Tool execution fails

```bash
# Verify dependencies
pip3 list | grep anthropic
pip3 list | grep mcp

# Test executor
python3 test_executor.py
```

### File tracking issues

```bash
# Check permissions
ls -la /mnt/agentic-system/

# Verify working directory
pwd
```

## Development

### Running Tests

```bash
cd /mnt/agentic-system/mcp-servers/claude-code-control-mcp
python3 test_server.py
```

### Adding New Tools

1. Add tool definition to `list_tools()`
2. Implement handler in `call_tool()`
3. Update documentation
4. Add tests

### Debugging

Enable debug logging:
```python
logging.basicConfig(level=logging.DEBUG)
```

## Roadmap

- [ ] Batch task execution
- [ ] Task queuing and scheduling
- [ ] Integration with enhanced-memory MCP
- [ ] Code analysis tools (complexity, coverage)
- [ ] Git integration (commit, push, PR creation)
- [ ] Multi-file refactoring support
- [ ] Streaming execution updates
- [ ] Web UI for monitoring

## Contributing

Contributions welcome! Areas for improvement:

1. Additional tool implementations
2. Performance optimizations
3. Enhanced error handling
4. Documentation improvements
5. Test coverage

## License

Part of the agentic-system project. See main LICENSE file.

## Support

For issues and questions:
- Check logs: `~/.claude/logs/`
- Review MCP documentation: https://modelcontextprotocol.io
- Anthropic API docs: https://docs.anthropic.com

## Related Documentation

- [MCP Protocol Specification](https://modelcontextprotocol.io)
- [Anthropic API Documentation](https://docs.anthropic.com)
- [Enhanced Memory MCP](../enhanced-memory-mcp/README.md)
- [Agent Runtime MCP](../agent-runtime-mcp/README.md)
