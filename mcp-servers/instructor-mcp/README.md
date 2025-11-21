# Instructor MCP Server

Structured output extraction using Pydantic validation and Anthropic Claude.

## Features

- **Structured Extraction**: Extract data into predefined or custom Pydantic models
- **Automatic Validation**: Built-in retry logic with exponential backoff
- **Complex Schemas**: Support for nested objects, enums, and lists
- **Memory Integration**: Direct output format for enhanced-memory-mcp
- **Code Analysis**: Structured code analysis for agentic coding

## Installation

```bash
cd /Volumes/SSDRAID0/agentic-system/mcp-servers/instructor-mcp
pip install -r requirements.txt
```

## Configuration

Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "instructor-mcp": {
      "command": "python",
      "args": ["/Volumes/SSDRAID0/agentic-system/mcp-servers/instructor-mcp/server.py"],
      "env": {
        "ANTHROPIC_API_KEY": "your-api-key"
      }
    }
  }
}
```

## Tools

### extract_structured
Extract data using predefined models or custom schemas.

```python
# Using predefined model
mcp__instructor-mcp__extract_structured({
    "content": "John works at Acme Corp as a senior engineer",
    "model_name": "entity"
})

# Using custom schema
mcp__instructor-mcp__extract_structured({
    "content": "The product costs $99.99",
    "custom_schema": {
        "properties": {
            "product_name": {"type": "string"},
            "price": {"type": "number"}
        },
        "required": ["price"]
    }
})
```

### extract_entities
Extract named entities and relationships.

```python
mcp__instructor-mcp__extract_entities({
    "content": "Alice and Bob work together at StartupXYZ",
    "include_relations": true
})
```

### extract_tasks
Extract actionable tasks from text.

```python
mcp__instructor-mcp__extract_tasks({
    "content": "Meeting notes: John to review PR by Friday. Alice will deploy v2.0.",
    "context": "Sprint planning meeting"
})
```

### extract_for_memory
Format extraction for enhanced-memory-mcp storage.

```python
mcp__instructor-mcp__extract_for_memory({
    "content": "Claude is an AI assistant made by Anthropic",
    "source": "documentation"
})
# Returns entries ready for create_entities()
```

### validate_schema
Validate data against a model without extraction.

```python
mcp__instructor-mcp__validate_schema({
    "data": {"name": "Test", "entity_type": "concept"},
    "model_name": "entity"
})
```

### analyze_code
Structured code analysis.

```python
mcp__instructor-mcp__analyze_code({
    "code": "def factorial(n): return 1 if n <= 1 else n * factorial(n-1)",
    "language": "python"
})
```

## Available Models

- `entity` - Named entity with type and confidence
- `relation` - Relationship between entities
- `knowledge_graph` - Complete entity-relation graph
- `task` - Actionable task with priority/deadline
- `action_item` - Meeting action item
- `meeting_notes` - Full meeting notes structure
- `code_analysis` - Code analysis results
- `memory_entry` - enhanced-memory-mcp compatible entry

## Integration Example

```python
# Extract and store in memory
result = mcp__instructor-mcp__extract_for_memory({
    "content": document_text,
    "source": "user_document.pdf"
})

# Store in enhanced-memory-mcp
mcp__enhanced-memory-mcp__create_entities(result["entries"])
```
