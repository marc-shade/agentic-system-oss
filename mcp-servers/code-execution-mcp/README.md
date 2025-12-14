# Code Execution MCP

Implements the patterns from Anthropic's ["Code Execution with MCP"](https://www.anthropic.com/engineering/code-execution-with-mcp) article for efficient AI agent operations.

## Core Insight

Instead of loading thousands of tool definitions upfront and passing intermediate results through model context, agents write code that:
1. Discovers tools on-demand (progressive disclosure)
2. Processes data in a sandbox (not in context)
3. Returns only summarized/filtered results

**Result**: Up to 98.7% token reduction compared to direct tool invocation.

## Features

### 1. Sandboxed Code Execution
- Resource limits (30s timeout, 500MB memory)
- Restricted builtins (safe subset)
- Safe modules (json, re, math, datetime, etc.)
- Workspace file utilities

### 2. Progressive Tool Discovery
- Search tools by query without loading definitions
- Get summaries first, full definitions on-demand
- Organized by category (security, memory, cluster, etc.)

### 3. PII Tokenization
- Auto-detect sensitive data (emails, phones, SSNs, etc.)
- Replace with tokens before data reaches model
- Restore when needed for tool calls

### 4. Skills Persistence
- Save reusable code snippets
- Build compound capabilities over time
- Share across sessions

## Tools

| Tool | Description |
|------|-------------|
| `execute_code` | Run Python in secure sandbox |
| `search_tools` | Progressive tool discovery |
| `get_tool_definition` | Load full tool details |
| `save_skill` | Persist reusable code |
| `load_skill` | Load saved skill |
| `list_skills` | List all skills |
| `sanitize_pii` | Tokenize PII in text |
| `restore_pii` | Restore tokenized PII |
| `write_workspace_file` | Persist data to workspace |
| `read_workspace_file` | Read from workspace |
| `list_workspace_files` | List workspace contents |
| `get_execution_stats` | Environment statistics |

## Usage Examples

### Efficient Data Processing
```python
# Instead of returning 10,000 rows to context:
code = '''
data = json.loads(read_file("large_dataset.json"))
filtered = [d for d in data if d['status'] == 'active']
result = {
    'total': len(data),
    'active': len(filtered),
    'sample': filtered[:5]
}
'''
execute_code(code)
# Returns only summary, not full dataset
```

### Progressive Tool Discovery
```python
# Find security tools (minimal tokens)
search_tools("vulnerability", category="security", detail_level="summary")

# Load full definition only when needed
get_tool_definition("web_vuln_scanner", category="security")
```

### Privacy-Preserving Operations
```python
# Sanitize before processing
sanitize_pii("Contact john@example.com at 555-123-4567")
# Returns: "Contact [EMAIL_abc123] at [PHONE_def456]"

# Restore when needed
restore_pii("[EMAIL_abc123]")
# Returns: "john@example.com"
```

### Building Skills
```python
# Save a reusable skill
save_skill(
    name="filter_high_risk",
    code="def filter_high_risk(vulns): return [v for v in vulns if v['severity'] in ['high', 'critical']]",
    description="Filter vulnerabilities to high/critical only"
)

# Use in future code execution
code = '''
skill = load_skill("filter_high_risk")
exec(skill)
vulns = json.loads(read_file("scan_results.json"))
result = filter_high_risk(vulns)
'''
```

## Installation

```bash
cd /mnt/agentic-system/mcp-servers/code-execution-mcp
pip install -e .
```

## Configuration

Add to `~/.claude.json`:
```json
{
  "mcpServers": {
    "code-execution": {
      "command": "/mnt/agentic-system/.venv/bin/python3",
      "args": ["/mnt/agentic-system/mcp-servers/code-execution-mcp/src/code_execution_mcp/server.py"],
      "disabled": false
    }
  }
}
```

## Architecture

```
code-execution-mcp/
├── workspace/           # Sandboxed file storage
├── skills/              # Persistent skill definitions
├── tools_registry/      # Tool definitions for discovery
│   ├── security/        # Security tools
│   └── memory/          # Memory tools
└── src/
    └── code_execution_mcp/
        └── server.py    # Main MCP server
```

## Security Notes

- Code runs with restricted builtins (no `open`, `exec`, `eval` on arbitrary input)
- File access limited to workspace directory
- Resource limits prevent runaway execution
- No network access from sandbox

## References

- [Anthropic: Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)
- [Cloudflare: Code Mode Research](https://blog.cloudflare.com/)
