# Claude Code Control MCP - Quick Reference

## Installation

```bash
cd /mnt/agentic-system/mcp-servers/claude-code-control-mcp
pip3 install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."
./verify_installation.sh
```

## Configuration

Edit `~/.claude.json`:
```json
{
  "mcpServers": {
    "claude-code-control": {
      "disabled": false,
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-..."
      }
    }
  }
}
```

## MCP Tools

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| **execute_code_task** | Autonomous coding | task_description, working_directory |
| **read_codebase** | Read multiple files | patterns, max_files |
| **search_code** | Search codebase | query, file_pattern |
| **modify_files** | Batch modifications | changes (array) |
| **run_commands** | Execute commands | commands (array) |
| **get_execution_status** | Check status | include_history |

## Usage Examples

### Execute Task
```
Use claude-code-control to create a Python REST API with authentication
```

### Read Code
```python
{
  "tool": "read_codebase",
  "arguments": {
    "patterns": ["*.py", "tests/**/*.py"]
  }
}
```

### Search
```python
{
  "tool": "search_code",
  "arguments": {
    "query": "async def.*execute",
    "file_pattern": "*.py"
  }
}
```

### Modify Files
```python
{
  "tool": "modify_files",
  "arguments": {
    "changes": [
      {
        "path": "config.py",
        "action": "write",
        "content": "DEBUG = True\n"
      }
    ]
  }
}
```

### Run Commands
```python
{
  "tool": "run_commands",
  "arguments": {
    "commands": ["python3 -m pytest tests/"]
  }
}
```

## Common Tasks

### Create Script
```
Use claude-code-control to create a script that processes CSV files
```

### Refactor Code
```
Use claude-code-control to refactor auth.py to use async/await
```

### Add Tests
```
Use claude-code-control to add unit tests for the calculator module
```

### Fix Bugs
```
Use claude-code-control to fix the memory leak in server.py
```

## File Structure

```
claude-code-control-mcp/
├── server.py           # MCP server
├── executor.py         # Task executor
├── file_tracker.py     # Change tracker
├── requirements.txt    # Dependencies
├── README.md           # Full docs
├── QUICKSTART.md       # Setup guide
├── test_server.py      # Tests
├── example_usage.py    # Examples
└── verify_installation.sh  # Checker
```

## Troubleshooting

### Server Not Loading
```bash
tail -f ~/.claude/logs/mcp-servers.log
cat ~/.claude.json | jq '.mcpServers."claude-code-control"'
```

### API Key Issues
```bash
echo $ANTHROPIC_API_KEY
python3 -c "from anthropic import Anthropic; Anthropic()"
```

### Import Errors
```bash
pip3 install -r requirements.txt
python3 -c "from file_tracker import FileTracker"
```

### Verification
```bash
./verify_installation.sh
python3 test_server.py
```

## Performance

| Metric | Value |
|--------|-------|
| Initialization | < 1s |
| Simple task | 10-20s |
| Complex task | 30-60s |
| File operation | < 100ms |
| Memory usage | 50-100MB |

## Limits

| Parameter | Default | Max |
|-----------|---------|-----|
| max_iterations | 20 | Configurable |
| max_files | 50 | Configurable |
| max_results | 100 | Configurable |
| timeout | 30s | Configurable |
| file_size | 10KB | For context |

## Integration

### Temporal
```python
await workflow.execute_activity(
    execute_code_task,
    args=[task_description]
)
```

### n8n
```javascript
{
  method: "POST",
  body: {
    tool: "execute_code_task",
    arguments: { task_description: "..." }
  }
}
```

### Python
```python
from executor import TaskExecutor
executor = TaskExecutor(api_key)
result = await executor.execute_task("...")
```

## Documentation

| File | Purpose |
|------|---------|
| QUICKSTART.md | 5-minute setup |
| README.md | Complete reference |
| IMPLEMENTATION_SUMMARY.md | Implementation details |
| DESIGN.md | Architecture |

## Key Commands

```bash
# Install
pip3 install -r requirements.txt

# Verify
./verify_installation.sh

# Test
python3 test_server.py

# Examples
python3 example_usage.py

# Logs
tail -f ~/.claude/logs/mcp-servers.log
```

## Support

- Docs: `cat README.md`
- Quick Start: `cat QUICKSTART.md`
- Examples: `python3 example_usage.py`
- MCP Protocol: https://modelcontextprotocol.io
- Anthropic API: https://docs.anthropic.com

---

**Ready to start?** Set your API key, enable the server, and restart Claude Code!
