# Typst Document Generation MCP Server

Modern typesetting and document generation for the agentic system.

## Overview

This MCP server provides tools for creating, compiling, and managing Typst documents. Typst is a modern markup-based typesetting system that offers the power of LaTeX with much simpler syntax.

## Features

- **Document Compilation**: Compile `.typ` files to PDF
- **Template System**: Pre-built templates for reports, papers, presentations, letters, and invoices
- **AI-Assisted Generation**: Generate structured documents from specifications
- **Markdown Conversion**: Convert Markdown to Typst markup
- **Project Management**: Create and manage document projects
- **Live Preview**: Watch mode for automatic recompilation

## Installation

### Prerequisites

1. **Typst CLI** (automatically detected if installed):
   ```bash
   cargo install typst-cli
   ```

2. **Python 3.10+**

### Install MCP Server

```bash
cd /mnt/agentic-system/mcp-servers/typst-mcp
pip install -e .
```

### Configure Claude Code

Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "typst-mcp": {
      "command": "python",
      "args": ["-m", "typst_mcp.server"],
      "env": {
        "AGENTIC_SYSTEM_PATH": "/mnt/agentic-system"
      }
    }
  }
}
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `typst_compile` | Compile .typ file to PDF |
| `typst_watch` | Watch and auto-compile on changes |
| `typst_from_template` | Create document from template |
| `typst_preview` | Generate PNG preview |
| `typst_query` | Query document metadata |
| `typst_convert_markdown` | Convert Markdown to Typst |
| `typst_create_project` | Create new document project |
| `list_templates` | List available templates |
| `generate_report` | AI-assisted report generation |
| `generate_paper` | Academic paper generation |
| `typst_fonts` | List available fonts |

## Templates

### Available Templates

- **minimal**: Quick notes, simple documents
- **report**: Professional business reports
- **paper**: Academic research papers
- **presentation**: Slide decks (requires Polylux)
- **letter**: Formal correspondence
- **invoice**: Billing documents

### Template Location

Templates are stored in:
```
/mnt/agentic-system/mcp-servers/typst-mcp/templates/
├── reports/
│   └── technical-report.typ
├── papers/
│   └── research-paper.typ
├── presentations/
│   └── slides.typ
├── letters/
│   └── formal-letter.typ
└── invoices/
    └── invoice.typ
```

## Usage Examples

### Generate a Report

```python
# Using the MCP tool
result = await mcp__typst_mcp__generate_report(
    title="Q4 2025 Analysis",
    author="Marc",
    sections=[
        {"heading": "Executive Summary", "content": "Key findings..."},
        {"heading": "Analysis", "content": "Detailed analysis..."},
        {"heading": "Recommendations", "content": "Next steps..."}
    ],
    compile_pdf=True
)
```

### Create from Template

```python
result = await mcp__typst_mcp__typst_from_template(
    template="paper",
    output_path="~/Documents/my-paper.typ",
    variables={
        "title": "Novel Approach to AGI",
        "author": "Marc",
        "abstract": "This paper presents..."
    }
)
```

### Compile Document

```bash
# CLI
typst compile document.typ

# MCP tool
result = await mcp__typst_mcp__typst_compile(
    input_path="document.typ",
    output_path="document.pdf"
)
```

## Integration

### With Enhanced Memory

Documents can be tracked in enhanced-memory for versioning:

```python
await mcp__enhanced_memory__create_entities([{
    "name": f"document_{doc_id}",
    "entityType": "typst_document",
    "observations": [
        f"Title: {title}",
        f"Path: {output_path}",
        f"Created: {timestamp}"
    ]
}])
```

### With Agent Runtime

Queue document generation tasks:

```python
await mcp__agent_runtime__create_task(
    title="Generate Monthly Report",
    description="Create monthly performance report",
    priority=7
)
```

## Output Directories

- **Compiled PDFs**: `/mnt/agentic-system/documents/typst-output/`
- **Projects**: `/mnt/agentic-system/documents/typst-projects/`
- **Previews**: `/mnt/agentic-system/documents/typst-output/previews/`

## Slash Commands

After Claude Code restart:

- `/typst/new` - Create new document
- `/typst/compile` - Compile document
- `/typst/report` - Generate report
- `/typst/paper` - Generate research paper

## Skill

The `typst-documents` skill provides comprehensive documentation:
`/home/marc/.claude/skills/typst-documents/SKILL.md`

## License

MIT License - Part of the Agentic System
