# Outlines MCP Server

Constrained generation MCP server using [Outlines](https://github.com/outlines-dev/outlines) for guaranteed schema-compliant outputs with local Ollama models.

## Features

- **Schema-constrained generation**: Output guaranteed to match JSON schema
- **Choice constraints**: Force output to be one of specified options
- **Regex patterns**: Output matching regex patterns (email, phone, URL, etc.)
- **Grammar-based generation**: Context-free grammar compliance
- **Code generation**: Syntactically valid code output
- **Ollama integration**: Full local model support

## Installation

```bash
cd /Volumes/SSDRAID0/agentic-system/mcp-servers/outlines-mcp
pip install -r requirements.txt
```

Ensure Ollama is running:
```bash
ollama serve
ollama pull mistral  # or your preferred model
```

## MCP Tools

### `generate_constrained`
Generate output constrained to a JSON schema.

```python
result = generate_constrained(
    prompt="Create a user profile",
    schema={"type": "object", "properties": {"name": {"type": "string"}, "age": {"type": "integer"}}},
    model="mistral"
)
```

### `generate_choice`
Force output to be one of specific choices.

```python
result = generate_choice(
    prompt="Is this code secure?",
    choices=["secure", "vulnerable", "needs_review"],
    model="mistral"
)
```

### `generate_regex`
Generate output matching a regex pattern.

```python
result = generate_regex(
    prompt="Generate a valid email",
    pattern=r"[a-z]+@[a-z]+\.[a-z]{2,4}",
    model="mistral"
)
```

### `generate_json`
Generate valid JSON with optional built-in schema.

```python
# With built-in schema
result = generate_json(
    prompt="Analyze this code and suggest improvements",
    schema_name="code_review",
    model="mistral"
)

# With custom schema
result = generate_json(
    prompt="Extract meeting details",
    custom_schema={"type": "object", "properties": {...}},
    model="mistral"
)
```

### `generate_code`
Generate syntactically valid code.

```python
result = generate_code(
    prompt="Create a function to calculate fibonacci",
    language="python",
    model="mistral"
)
```

### `generate_grammar`
Generate output conforming to a grammar.

```python
result = generate_grammar(
    prompt="Generate an arithmetic expression",
    grammar=GRAMMARS["arithmetic"],
    model="mistral"
)
```

### `generate_with_pattern`
Use named patterns for common formats.

```python
result = generate_with_pattern(
    prompt="Generate a valid phone number",
    pattern_name="phone",  # email, url, date_iso, uuid, etc.
    model="mistral"
)
```

### Utility Tools

- `list_available_patterns`: Show all regex patterns
- `list_available_grammars`: Show all grammars
- `list_available_schemas`: Show all built-in schemas
- `check_ollama_status`: Verify Ollama and list models

## Built-in Schemas

### Code Schemas
- `function_signature`: Function with parameters and return type
- `class_definition`: Class with attributes and methods
- `code_block`: Code with language and imports
- `code_review`: Issues, suggestions, quality score

### Data Schemas
- `extracted_data`: Entities, keywords, sentiment
- `contact_info`: Name, email, phone, company
- `structured_document`: Title, sections, metadata
- `data_validation`: Validation results

### Agent Schemas
- `agent_decision`: Action type, reasoning, tool calls
- `task_decomposition`: Subtasks with dependencies
- `agent_response`: Answer with sources and confidence
- `execution_plan`: Steps with success criteria

## Configuration

Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "outlines-mcp": {
      "command": "python",
      "args": ["/Volumes/SSDRAID0/agentic-system/mcp-servers/outlines-mcp/server.py"],
      "env": {
        "OLLAMA_HOST": "http://localhost:11434"
      }
    }
  }
}
```

## Architecture

```
outlines-mcp/
├── server.py              # FastMCP server with all tools
├── generators.py          # Constrained generation utilities
├── ollama_integration.py  # Local model client
├── schemas/
│   ├── code_schemas.py    # Code generation schemas
│   ├── data_schemas.py    # Data extraction schemas
│   └── agent_schemas.py   # Agent decision schemas
├── requirements.txt
└── README.md
```

## Usage Examples

### Structured Agent Decision
```python
result = generate_json(
    prompt="User asks: 'Deploy the latest version to production'. What should I do?",
    schema_name="agent_decision",
    model="mistral"
)
# Returns: {"action": "execute", "confidence": 0.85, "reasoning": "...", "tool_calls": [...]}
```

### Code Review
```python
result = generate_json(
    prompt="Review this code: def foo(x): return x+1",
    schema_name="code_review",
    model="mistral"
)
# Returns: {"has_issues": true, "issues": [...], "suggestions": [...], "quality_score": 7}
```

### Constrained Classification
```python
result = generate_choice(
    prompt="Classify this support ticket priority: 'Server is down!'",
    choices=["low", "medium", "high", "critical"],
    model="mistral"
)
# Returns: "critical"
```
