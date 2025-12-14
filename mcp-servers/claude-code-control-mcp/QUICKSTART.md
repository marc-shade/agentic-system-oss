# Claude Code Control MCP - Quick Start Guide

Get up and running with the Claude Code Control MCP server in 5 minutes.

## Prerequisites

- Python 3.9+
- Anthropic API key
- Claude Code installed

## 1. Installation

```bash
cd /mnt/agentic-system/mcp-servers/claude-code-control-mcp

# Install dependencies
pip3 install -r requirements.txt
```

## 2. Configuration

### Set API Key

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Or add to your shell profile:

```bash
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.bashrc
source ~/.bashrc
```

### Enable MCP Server

Edit `~/.claude.json` and update the `claude-code-control` section:

```json
{
  "mcpServers": {
    "claude-code-control": {
      "command": "python3",
      "args": ["/mnt/agentic-system/mcp-servers/claude-code-control-mcp/server.py"],
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-..."
      },
      "disabled": false
    }
  }
}
```

**Important**: Replace `"sk-ant-..."` with your actual API key, or use environment variable expansion if your version supports it.

## 3. Verification

### Test the components

```bash
# Test file tracker
python3 -c "from file_tracker import FileTracker; print('✓ File tracker OK')"

# Test executor (requires API key)
python3 -c "from executor import TaskExecutor; print('✓ Executor OK')"

# Run full test suite (optional)
python3 test_server.py
```

### Start Claude Code

```bash
# Restart Claude Code to load the new MCP server
# (Exit current session and start again)
claude
```

## 4. First Task

Try executing a simple task:

```
Use the claude-code-control MCP to create a Python script that prints "Hello from MCP!"
```

Claude Code will:
1. Call the `execute_code_task` tool
2. Use Claude AI to autonomously write the script
3. Track file changes
4. Return execution results

## Example Workflows

### Example 1: Create and Test Code

```
Use claude-code-control to:
1. Create a Python function that calculates fibonacci numbers
2. Add unit tests for the function
3. Run the tests to verify they pass
```

### Example 2: Refactor Existing Code

```
Use claude-code-control to refactor the authentication module:
- Convert sync functions to async
- Add type hints
- Improve error handling
```

### Example 3: Automated Code Review

```
Use claude-code-control to:
1. Read all Python files in src/
2. Search for TODO comments
3. Create a summary report
```

## Available Tools

Once enabled, you have access to these MCP tools:

1. **execute_code_task** - Execute autonomous coding tasks
2. **read_codebase** - Read multiple files with glob patterns
3. **search_code** - Search codebase with regex
4. **modify_files** - Batch file modifications
5. **run_commands** - Execute shell commands
6. **get_execution_status** - Monitor task execution

## Troubleshooting

### MCP Server Not Loading

```bash
# Check Claude Code logs
tail -f ~/.claude/logs/claude-code.log

# Check MCP server logs
tail -f ~/.claude/logs/mcp-servers.log

# Verify configuration
cat ~/.claude.json | jq '.mcpServers."claude-code-control"'
```

### API Key Issues

```bash
# Verify key is set
echo $ANTHROPIC_API_KEY

# Test API key directly
python3 -c "
from anthropic import Anthropic
client = Anthropic()
print('✓ API key valid')
"
```

### Permission Errors

```bash
# Make scripts executable
chmod +x /mnt/agentic-system/mcp-servers/claude-code-control-mcp/*.py

# Check file permissions
ls -la /mnt/agentic-system/mcp-servers/claude-code-control-mcp/
```

## Next Steps

1. **Explore the README**: Full documentation in `README.md`
2. **Run tests**: Execute `python3 test_server.py`
3. **Try examples**: See `examples/` directory (coming soon)
4. **Integration**: Connect with Temporal workflows or n8n

## Best Practices

1. **Start simple**: Begin with basic tasks before complex refactoring
2. **Provide context**: Include relevant files in `context_files` parameter
3. **Set limits**: Use `max_iterations` to prevent runaway execution
4. **Monitor changes**: Always review file changes before committing
5. **Test first**: Run tests after code modifications

## Performance Tips

- **Limit iterations**: Set `max_iterations` to 10-15 for most tasks
- **Provide context**: Pre-read relevant files to reduce API calls
- **Use patterns**: Leverage glob patterns for batch operations
- **Batch commands**: Group related commands together

## Security Notes

- Store API keys securely (environment variables or keychain)
- Review all file changes before committing
- Limit working directory to project scope
- Monitor command executions in production

## Getting Help

- Check logs: `~/.claude/logs/`
- Review MCP docs: https://modelcontextprotocol.io
- Anthropic API: https://docs.anthropic.com
- File an issue: Create issue in repository

## Quick Reference

### Execute a task
```python
{
  "tool": "execute_code_task",
  "arguments": {
    "task_description": "Your task here",
    "working_directory": "/path/to/project",
    "max_iterations": 15
  }
}
```

### Read files
```python
{
  "tool": "read_codebase",
  "arguments": {
    "patterns": ["*.py", "tests/**/*.py"],
    "max_files": 50
  }
}
```

### Search code
```python
{
  "tool": "search_code",
  "arguments": {
    "query": "async def.*execute",
    "file_pattern": "*.py"
  }
}
```

---

**Ready to start?** Just say to Claude Code:

```
Use the claude-code-control MCP to create a simple web server in Python
```

And watch the magic happen! ✨
