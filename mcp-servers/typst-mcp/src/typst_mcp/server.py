#!/usr/bin/env python3
"""
Typst Document Generation MCP Server
=====================================

Modern typesetting and document generation for the agentic system.

Provides tools for:
- Compiling Typst documents to PDF
- Creating documents from templates
- Converting content to Typst markup
- Managing document projects
- Real-time document preview
- Integration with enhanced-memory for document versioning

MCP Tools:
- typst_compile: Compile .typ file to PDF
- typst_watch: Watch and auto-compile on changes
- typst_from_template: Create document from template
- typst_preview: Generate preview of document
- typst_query: Query document metadata/labels
- typst_convert_markdown: Convert markdown to Typst
- typst_create_project: Create new document project
- list_templates: List available templates
- generate_report: AI-assisted report generation
- generate_paper: AI-assisted research paper generation

Author: Agentic System / Pixel
"""

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
import mcp.types as types

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("typst-mcp")

# Platform-aware path detection
import platform

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    # Check environment variable first
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path("/Volumes/SSDRAID0/agentic-system").exists():
            return Path("/Volumes/SSDRAID0/agentic-system")
        elif Path("/Volumes/FILES/agentic-system").exists():
            return Path("/Volumes/FILES/agentic-system")
    elif system == "Linux":
        if Path("/home/marc/agentic-system").exists():
            return Path("/home/marc/agentic-system")
        elif Path("/mnt/agentic-system").exists():
            return Path("/mnt/agentic-system")
    # Fallback to script location
    return Path(__file__).parent.parent.parent.parent

# Configuration
AGENTIC_PATH = _get_storage_base()
TEMPLATES_DIR = AGENTIC_PATH / "mcp-servers" / "typst-mcp" / "templates"
OUTPUT_DIR = AGENTIC_PATH / "documents" / "typst-output"
PROJECTS_DIR = AGENTIC_PATH / "documents" / "typst-projects"

# Ensure directories exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

# Create MCP server
server = Server("typst-mcp")


def get_typst_path() -> str:
    """Get Typst executable path."""
    # Check common locations
    locations = [
        shutil.which("typst"),
        os.path.expanduser("~/.cargo/bin/typst"),
        "/usr/local/bin/typst",
        "/usr/bin/typst"
    ]
    for loc in locations:
        if loc and os.path.exists(loc):
            return loc
    raise FileNotFoundError("Typst not found. Install with: cargo install typst-cli")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available Typst document tools."""
    return [
        types.Tool(
            name="typst_compile",
            description="Compile a Typst (.typ) file to PDF. Returns path to generated PDF.",
            inputSchema={
                "type": "object",
                "properties": {
                    "input_path": {
                        "type": "string",
                        "description": "Path to .typ file to compile"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Optional output PDF path. Defaults to same name as input."
                    },
                    "root": {
                        "type": "string",
                        "description": "Optional root directory for relative imports"
                    }
                },
                "required": ["input_path"]
            }
        ),
        types.Tool(
            name="typst_watch",
            description="Watch a Typst file and recompile on changes. Returns process ID for monitoring.",
            inputSchema={
                "type": "object",
                "properties": {
                    "input_path": {
                        "type": "string",
                        "description": "Path to .typ file to watch"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Optional output PDF path"
                    }
                },
                "required": ["input_path"]
            }
        ),
        types.Tool(
            name="typst_from_template",
            description="Create a new document from a template. Available templates: report, paper, presentation, letter, invoice, minimal.",
            inputSchema={
                "type": "object",
                "properties": {
                    "template": {
                        "type": "string",
                        "description": "Template name (report, paper, presentation, letter, invoice, minimal)",
                        "enum": ["report", "paper", "presentation", "letter", "invoice", "minimal"]
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Path for the new document"
                    },
                    "variables": {
                        "type": "object",
                        "description": "Template variables (title, author, date, etc.)"
                    }
                },
                "required": ["template", "output_path"]
            }
        ),
        types.Tool(
            name="typst_preview",
            description="Generate a PNG preview of the first page(s) of a document.",
            inputSchema={
                "type": "object",
                "properties": {
                    "input_path": {
                        "type": "string",
                        "description": "Path to .typ file"
                    },
                    "pages": {
                        "type": "integer",
                        "description": "Number of pages to preview (default: 1)",
                        "default": 1
                    },
                    "dpi": {
                        "type": "integer",
                        "description": "DPI for preview images (default: 144)",
                        "default": 144
                    }
                },
                "required": ["input_path"]
            }
        ),
        types.Tool(
            name="typst_query",
            description="Query document for metadata, labels, or structured data.",
            inputSchema={
                "type": "object",
                "properties": {
                    "input_path": {
                        "type": "string",
                        "description": "Path to .typ file"
                    },
                    "selector": {
                        "type": "string",
                        "description": "Typst selector (e.g., '<heading>', '<figure>', 'label')"
                    }
                },
                "required": ["input_path", "selector"]
            }
        ),
        types.Tool(
            name="typst_convert_markdown",
            description="Convert Markdown content to Typst markup.",
            inputSchema={
                "type": "object",
                "properties": {
                    "markdown": {
                        "type": "string",
                        "description": "Markdown content to convert"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Optional path to save converted file"
                    }
                },
                "required": ["markdown"]
            }
        ),
        types.Tool(
            name="typst_create_project",
            description="Create a new Typst document project with proper structure.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Project name"
                    },
                    "template": {
                        "type": "string",
                        "description": "Base template (report, paper, presentation)",
                        "default": "report"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Project metadata (title, author, description)"
                    }
                },
                "required": ["name"]
            }
        ),
        types.Tool(
            name="list_templates",
            description="List all available Typst templates with descriptions.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="generate_report",
            description="Generate a structured report document with AI assistance. Provide content sections and it will create a professional Typst document.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Report title"
                    },
                    "author": {
                        "type": "string",
                        "description": "Author name"
                    },
                    "sections": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "heading": {"type": "string"},
                                "content": {"type": "string"}
                            }
                        },
                        "description": "Report sections with headings and content"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Output path for the document"
                    },
                    "compile_pdf": {
                        "type": "boolean",
                        "description": "Also compile to PDF (default: true)",
                        "default": True
                    }
                },
                "required": ["title", "sections"]
            }
        ),
        types.Tool(
            name="generate_paper",
            description="Generate a research paper document structure. Supports academic paper conventions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Paper title"
                    },
                    "authors": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of authors"
                    },
                    "abstract": {
                        "type": "string",
                        "description": "Paper abstract"
                    },
                    "sections": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "heading": {"type": "string"},
                                "content": {"type": "string"}
                            }
                        },
                        "description": "Paper sections"
                    },
                    "bibliography": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Bibliography entries in BibTeX or hayagriva format"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Output path"
                    }
                },
                "required": ["title", "authors", "abstract"]
            }
        ),
        types.Tool(
            name="typst_fonts",
            description="List available fonts or check if specific fonts are installed.",
            inputSchema={
                "type": "object",
                "properties": {
                    "search": {
                        "type": "string",
                        "description": "Optional font name to search for"
                    }
                }
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests."""
    args = arguments or {}

    if name == "typst_compile":
        return await typst_compile(args)
    elif name == "typst_watch":
        return await typst_watch(args)
    elif name == "typst_from_template":
        return await typst_from_template(args)
    elif name == "typst_preview":
        return await typst_preview(args)
    elif name == "typst_query":
        return await typst_query(args)
    elif name == "typst_convert_markdown":
        return await typst_convert_markdown(args)
    elif name == "typst_create_project":
        return await typst_create_project(args)
    elif name == "list_templates":
        return await list_templates(args)
    elif name == "generate_report":
        return await generate_report(args)
    elif name == "generate_paper":
        return await generate_paper(args)
    elif name == "typst_fonts":
        return await typst_fonts(args)
    else:
        raise ValueError(f"Unknown tool: {name}")


async def typst_compile(args: Dict) -> List[types.TextContent]:
    """Compile Typst file to PDF."""
    input_path = Path(args["input_path"]).expanduser()
    output_path = args.get("output_path")
    root = args.get("root")

    logger.info(f"Compiling: {input_path}")

    try:
        typst = get_typst_path()

        if not input_path.exists():
            return [types.TextContent(
                type="text",
                text=json.dumps({"success": False, "error": f"File not found: {input_path}"})
            )]

        # Build command
        cmd = [typst, "compile"]

        if root:
            cmd.extend(["--root", str(root)])

        cmd.append(str(input_path))

        if output_path:
            cmd.append(str(Path(output_path).expanduser()))
            final_output = Path(output_path).expanduser()
        else:
            final_output = input_path.with_suffix(".pdf")

        # Run compilation
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "input": str(input_path),
                    "output": str(final_output),
                    "size_bytes": final_output.stat().st_size if final_output.exists() else 0
                }, indent=2)
            )]
        else:
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": stderr.decode(),
                    "stdout": stdout.decode()
                }, indent=2)
            )]

    except Exception as e:
        logger.error(f"Compilation failed: {e}", exc_info=True)
        return [types.TextContent(
            type="text",
            text=json.dumps({"success": False, "error": str(e)})
        )]


async def typst_watch(args: Dict) -> List[types.TextContent]:
    """Watch and auto-compile Typst file."""
    input_path = Path(args["input_path"]).expanduser()
    output_path = args.get("output_path")

    logger.info(f"Starting watch: {input_path}")

    try:
        typst = get_typst_path()

        cmd = [typst, "watch", str(input_path)]
        if output_path:
            cmd.append(str(Path(output_path).expanduser()))

        # Start background process
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "success": True,
                "message": f"Watch started for {input_path}",
                "pid": process.pid,
                "note": "Process running in background. Kill with: kill {pid}"
            }, indent=2)
        )]

    except Exception as e:
        logger.error(f"Watch failed: {e}", exc_info=True)
        return [types.TextContent(
            type="text",
            text=json.dumps({"success": False, "error": str(e)})
        )]


async def typst_from_template(args: Dict) -> List[types.TextContent]:
    """Create document from template."""
    template_name = args["template"]
    output_path = Path(args["output_path"]).expanduser()
    variables = args.get("variables", {})

    logger.info(f"Creating from template: {template_name}")

    try:
        # Get template content
        template_content = get_template(template_name)

        # Replace variables
        for key, value in variables.items():
            template_content = template_content.replace(f"{{{{ {key} }}}}", str(value))
            template_content = template_content.replace(f"{{{{{key}}}}}", str(value))

        # Set defaults for common variables
        defaults = {
            "title": "Untitled Document",
            "author": "Author",
            "date": datetime.now().strftime("%Y-%m-%d")
        }

        for key, value in defaults.items():
            template_content = template_content.replace(f"{{{{ {key} }}}}", str(value))
            template_content = template_content.replace(f"{{{{{key}}}}}", str(value))

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        output_path.write_text(template_content)

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "success": True,
                "template": template_name,
                "output": str(output_path),
                "variables_applied": list(variables.keys())
            }, indent=2)
        )]

    except Exception as e:
        logger.error(f"Template creation failed: {e}", exc_info=True)
        return [types.TextContent(
            type="text",
            text=json.dumps({"success": False, "error": str(e)})
        )]


async def typst_preview(args: Dict) -> List[types.TextContent]:
    """Generate PNG preview of document."""
    input_path = Path(args["input_path"]).expanduser()
    pages = args.get("pages", 1)
    dpi = args.get("dpi", 144)

    logger.info(f"Generating preview: {input_path}")

    try:
        typst = get_typst_path()

        # Create temp directory for PNGs
        with tempfile.TemporaryDirectory() as tmpdir:
            output_pattern = Path(tmpdir) / "page-{n}.png"

            cmd = [
                typst, "compile",
                "--format", "png",
                "--ppi", str(dpi),
                str(input_path),
                str(output_pattern)
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                return [types.TextContent(
                    type="text",
                    text=json.dumps({"success": False, "error": stderr.decode()})
                )]

            # Move generated PNGs to output directory
            preview_dir = OUTPUT_DIR / "previews"
            preview_dir.mkdir(exist_ok=True)

            preview_paths = []
            for i in range(1, pages + 1):
                src = Path(tmpdir) / f"page-{i}.png"
                if src.exists():
                    dest = preview_dir / f"{input_path.stem}-page-{i}.png"
                    shutil.copy(src, dest)
                    preview_paths.append(str(dest))

            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "previews": preview_paths,
                    "pages_generated": len(preview_paths)
                }, indent=2)
            )]

    except Exception as e:
        logger.error(f"Preview generation failed: {e}", exc_info=True)
        return [types.TextContent(
            type="text",
            text=json.dumps({"success": False, "error": str(e)})
        )]


async def typst_query(args: Dict) -> List[types.TextContent]:
    """Query document for metadata."""
    input_path = Path(args["input_path"]).expanduser()
    selector = args["selector"]

    logger.info(f"Querying: {input_path} for {selector}")

    try:
        typst = get_typst_path()

        cmd = [typst, "query", str(input_path), selector, "--format", "json"]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            try:
                results = json.loads(stdout.decode())
            except json.JSONDecodeError:
                results = stdout.decode()

            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "selector": selector,
                    "results": results
                }, indent=2)
            )]
        else:
            return [types.TextContent(
                type="text",
                text=json.dumps({"success": False, "error": stderr.decode()})
            )]

    except Exception as e:
        logger.error(f"Query failed: {e}", exc_info=True)
        return [types.TextContent(
            type="text",
            text=json.dumps({"success": False, "error": str(e)})
        )]


async def typst_convert_markdown(args: Dict) -> List[types.TextContent]:
    """Convert Markdown to Typst markup."""
    markdown = args["markdown"]
    output_path = args.get("output_path")

    logger.info("Converting Markdown to Typst")

    try:
        # Basic Markdown to Typst conversion
        typst_content = markdown

        # Headers
        typst_content = re.sub(r'^# (.+)$', r'= \1', typst_content, flags=re.MULTILINE)
        typst_content = re.sub(r'^## (.+)$', r'== \1', typst_content, flags=re.MULTILINE)
        typst_content = re.sub(r'^### (.+)$', r'=== \1', typst_content, flags=re.MULTILINE)
        typst_content = re.sub(r'^#### (.+)$', r'==== \1', typst_content, flags=re.MULTILINE)

        # Bold and italic
        typst_content = re.sub(r'\*\*\*(.+?)\*\*\*', r'_*\1*_', typst_content)
        typst_content = re.sub(r'\*\*(.+?)\*\*', r'*\1*', typst_content)
        typst_content = re.sub(r'\*(.+?)\*', r'_\1_', typst_content)
        typst_content = re.sub(r'_(.+?)_', r'_\1_', typst_content)

        # Links
        typst_content = re.sub(r'\[(.+?)\]\((.+?)\)', r'#link("\2")[\1]', typst_content)

        # Inline code
        typst_content = re.sub(r'`(.+?)`', r'`\1`', typst_content)

        # Code blocks
        typst_content = re.sub(
            r'```(\w*)\n(.*?)```',
            r'```\1\n\2```',
            typst_content,
            flags=re.DOTALL
        )

        # Lists
        typst_content = re.sub(r'^- (.+)$', r'- \1', typst_content, flags=re.MULTILINE)
        typst_content = re.sub(r'^\d+\. (.+)$', r'+ \1', typst_content, flags=re.MULTILINE)

        # Blockquotes
        typst_content = re.sub(r'^> (.+)$', r'#quote[\1]', typst_content, flags=re.MULTILINE)

        if output_path:
            output = Path(output_path).expanduser()
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(typst_content)

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "success": True,
                "typst_content": typst_content,
                "output_path": str(output_path) if output_path else None
            }, indent=2)
        )]

    except Exception as e:
        logger.error(f"Conversion failed: {e}", exc_info=True)
        return [types.TextContent(
            type="text",
            text=json.dumps({"success": False, "error": str(e)})
        )]


async def typst_create_project(args: Dict) -> List[types.TextContent]:
    """Create a new Typst project."""
    name = args["name"]
    template = args.get("template", "report")
    metadata = args.get("metadata", {})

    logger.info(f"Creating project: {name}")

    try:
        # Create project directory
        project_dir = PROJECTS_DIR / name
        project_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (project_dir / "src").mkdir(exist_ok=True)
        (project_dir / "assets").mkdir(exist_ok=True)
        (project_dir / "bibliography").mkdir(exist_ok=True)
        (project_dir / "output").mkdir(exist_ok=True)

        # Create main.typ from template
        template_content = get_template(template)

        # Apply metadata
        for key, value in metadata.items():
            template_content = template_content.replace(f"{{{{ {key} }}}}", str(value))

        (project_dir / "src" / "main.typ").write_text(template_content)

        # Create project config
        config = {
            "name": name,
            "template": template,
            "created": datetime.now().isoformat(),
            "metadata": metadata,
            "entry_point": "src/main.typ"
        }
        (project_dir / "typst-project.json").write_text(json.dumps(config, indent=2))

        # Create README
        readme = f"""# {name}

Typst document project created on {datetime.now().strftime('%Y-%m-%d')}.

## Structure

- `src/` - Typst source files
- `assets/` - Images and other assets
- `bibliography/` - Bibliography files (.bib, .yml)
- `output/` - Compiled PDFs

## Build

```bash
typst compile src/main.typ output/{name}.pdf
```

## Watch

```bash
typst watch src/main.typ output/{name}.pdf
```
"""
        (project_dir / "README.md").write_text(readme)

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "success": True,
                "project_path": str(project_dir),
                "main_file": str(project_dir / "src" / "main.typ"),
                "structure": {
                    "src": "Source files",
                    "assets": "Images and resources",
                    "bibliography": "Bibliography files",
                    "output": "Compiled documents"
                }
            }, indent=2)
        )]

    except Exception as e:
        logger.error(f"Project creation failed: {e}", exc_info=True)
        return [types.TextContent(
            type="text",
            text=json.dumps({"success": False, "error": str(e)})
        )]


async def list_templates(args: Dict) -> List[types.TextContent]:
    """List available templates."""
    templates = {
        "minimal": {
            "description": "Minimal document with basic setup",
            "use_case": "Quick notes, simple documents"
        },
        "report": {
            "description": "Professional report with sections, TOC, and styling",
            "use_case": "Business reports, technical documentation"
        },
        "paper": {
            "description": "Academic paper with abstract, citations, and figures",
            "use_case": "Research papers, academic submissions"
        },
        "presentation": {
            "description": "Slide deck with speaker notes",
            "use_case": "Presentations, talks"
        },
        "letter": {
            "description": "Formal letter format",
            "use_case": "Business correspondence"
        },
        "invoice": {
            "description": "Invoice with line items and totals",
            "use_case": "Billing, invoicing"
        }
    }

    return [types.TextContent(
        type="text",
        text=json.dumps({
            "success": True,
            "templates": templates,
            "templates_dir": str(TEMPLATES_DIR)
        }, indent=2)
    )]


async def generate_report(args: Dict) -> List[types.TextContent]:
    """Generate a report document."""
    title = args["title"]
    author = args.get("author", "")
    sections = args.get("sections", [])
    output_path = args.get("output_path")
    compile_pdf = args.get("compile_pdf", True)

    logger.info(f"Generating report: {title}")

    try:
        # Build Typst content
        content = f'''#set document(title: "{title}", author: "{author}")
#set page(paper: "us-letter", margin: 1in)
#set text(font: "New Computer Modern", size: 11pt)
#set heading(numbering: "1.1")
#set par(justify: true)

#align(center)[
  #text(size: 24pt, weight: "bold")[{title}]

  #v(0.5em)

  #text(size: 12pt)[{author}]

  #v(0.5em)

  #text(size: 10pt, fill: gray)[{datetime.now().strftime('%B %d, %Y')}]
]

#v(2em)

#outline(title: "Contents", indent: auto)

#pagebreak()

'''

        for section in sections:
            heading = section.get("heading", "Section")
            section_content = section.get("content", "")
            content += f"\n= {heading}\n\n{section_content}\n"

        # Save file
        if output_path:
            output = Path(output_path).expanduser()
        else:
            safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '-')
            output = OUTPUT_DIR / f"{safe_title}.typ"

        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content)

        result = {
            "success": True,
            "typ_file": str(output),
            "title": title,
            "sections_count": len(sections)
        }

        # Compile if requested
        if compile_pdf:
            compile_result = await typst_compile({"input_path": str(output)})
            compile_data = json.loads(compile_result[0].text)
            if compile_data.get("success"):
                result["pdf_file"] = compile_data.get("output")

        return [types.TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]

    except Exception as e:
        logger.error(f"Report generation failed: {e}", exc_info=True)
        return [types.TextContent(
            type="text",
            text=json.dumps({"success": False, "error": str(e)})
        )]


async def generate_paper(args: Dict) -> List[types.TextContent]:
    """Generate an academic paper."""
    title = args["title"]
    authors = args.get("authors", [])
    abstract = args.get("abstract", "")
    sections = args.get("sections", [])
    bibliography = args.get("bibliography", [])
    output_path = args.get("output_path")

    logger.info(f"Generating paper: {title}")

    try:
        # Format authors
        authors_str = ", ".join(authors) if authors else "Author"

        content = f'''#set document(title: "{title}", author: ({", ".join(f'"{a}"' for a in authors)}))
#set page(paper: "us-letter", margin: 1in)
#set text(font: "New Computer Modern", size: 10pt)
#set heading(numbering: "1.1")
#set par(justify: true, first-line-indent: 1em)
#set math.equation(numbering: "(1)")

// Title block
#align(center)[
  #text(size: 16pt, weight: "bold")[{title}]

  #v(1em)

  #text(size: 11pt)[{authors_str}]

  #v(1em)
]

// Abstract
#align(center)[
  #box(width: 85%)[
    #set text(size: 9pt)
    #par(justify: true)[
      *Abstract.* {abstract}
    ]
  ]
]

#v(2em)

'''

        # Add sections
        for section in sections:
            heading = section.get("heading", "Section")
            section_content = section.get("content", "")
            content += f"\n= {heading}\n\n{section_content}\n"

        # Add bibliography section if entries provided
        if bibliography:
            content += "\n= References\n\n"
            for i, entry in enumerate(bibliography, 1):
                content += f"[{i}] {entry}\n\n"

        # Save
        if output_path:
            output = Path(output_path).expanduser()
        else:
            safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '-')[:50]
            output = OUTPUT_DIR / f"{safe_title}-paper.typ"

        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content)

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "success": True,
                "typ_file": str(output),
                "title": title,
                "authors": authors,
                "sections_count": len(sections)
            }, indent=2)
        )]

    except Exception as e:
        logger.error(f"Paper generation failed: {e}", exc_info=True)
        return [types.TextContent(
            type="text",
            text=json.dumps({"success": False, "error": str(e)})
        )]


async def typst_fonts(args: Dict) -> List[types.TextContent]:
    """List available fonts."""
    search = args.get("search")

    try:
        typst = get_typst_path()

        cmd = [typst, "fonts"]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        fonts = stdout.decode().strip().split('\n')

        if search:
            fonts = [f for f in fonts if search.lower() in f.lower()]

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "success": True,
                "fonts": fonts,
                "count": len(fonts),
                "search_filter": search
            }, indent=2)
        )]

    except Exception as e:
        logger.error(f"Font listing failed: {e}", exc_info=True)
        return [types.TextContent(
            type="text",
            text=json.dumps({"success": False, "error": str(e)})
        )]


def get_template(name: str) -> str:
    """Get template content by name."""
    templates = {
        "minimal": '''// Minimal Typst Document
#set page(paper: "us-letter", margin: 1in)
#set text(size: 11pt)

= {{ title }}

{{ content }}
''',
        "report": '''// Professional Report Template
#set document(title: "{{ title }}", author: "{{ author }}")
#set page(
  paper: "us-letter",
  margin: (top: 1in, bottom: 1in, left: 1.25in, right: 1in),
  header: context {
    if counter(page).get().first() > 1 [
      #set text(size: 9pt, fill: gray)
      {{ title }}
      #h(1fr)
      #counter(page).display()
    ]
  }
)
#set text(font: "New Computer Modern", size: 11pt)
#set heading(numbering: "1.1")
#set par(justify: true)

// Title Page
#align(center + horizon)[
  #text(size: 28pt, weight: "bold")[{{ title }}]

  #v(2em)

  #text(size: 14pt)[{{ author }}]

  #v(1em)

  #text(size: 12pt, fill: gray)[{{ date }}]
]

#pagebreak()

// Table of Contents
#outline(title: "Table of Contents", indent: auto)

#pagebreak()

// Content starts here
= Introduction

Your introduction here.

= Background

Background information.

= Methodology

Methodology description.

= Results

Results and findings.

= Conclusion

Conclusions and future work.
''',
        "paper": '''// Academic Paper Template
#set document(title: "{{ title }}", author: ("{{ author }}",))
#set page(paper: "us-letter", margin: 1in)
#set text(font: "New Computer Modern", size: 10pt)
#set heading(numbering: "1.1")
#set par(justify: true, first-line-indent: 1em)
#set math.equation(numbering: "(1)")

// Paper title
#align(center)[
  #text(size: 14pt, weight: "bold")[{{ title }}]
  #v(1em)
  #text(size: 11pt)[{{ author }}]
  #v(0.5em)
  #text(size: 9pt, style: "italic")[{{ affiliation }}]
  #v(1em)
]

// Abstract
#align(center)[
  #box(width: 85%)[
    #set text(size: 9pt)
    *Abstract* --- {{ abstract }}
  ]
]

#v(1.5em)

= Introduction

Introduction text.

= Related Work

Related work discussion.

= Methodology

Methods description.

= Experiments

Experimental setup and results.

= Conclusion

Concluding remarks.

// Bibliography
#bibliography("refs.bib", style: "ieee")
''',
        "presentation": '''// Presentation Template (using polylux)
#import "@preview/polylux:0.3.1": *

#set page(paper: "presentation-16-9")
#set text(font: "New Computer Modern Sans", size: 20pt)

#polylux-slide[
  #align(center + horizon)[
    #text(size: 40pt, weight: "bold")[{{ title }}]

    #v(1em)

    #text(size: 24pt)[{{ author }}]

    #text(size: 18pt, fill: gray)[{{ date }}]
  ]
]

#polylux-slide[
  = Outline

  - Introduction
  - Main Points
  - Conclusion
]

#polylux-slide[
  = Introduction

  Your introduction content here.
]

#polylux-slide[
  = Thank You

  Questions?
]
''',
        "letter": '''// Formal Letter Template
#set page(paper: "us-letter", margin: 1in)
#set text(font: "New Computer Modern", size: 11pt)

#align(right)[
  {{ sender_address }}

  {{ date }}
]

#v(2em)

{{ recipient_name }}\\
{{ recipient_address }}

#v(1em)

Dear {{ recipient_name }},

#v(0.5em)

{{ body }}

#v(1em)

Sincerely,

#v(2em)

{{ sender_name }}
''',
        "invoice": '''// Invoice Template
#set page(paper: "us-letter", margin: 0.75in)
#set text(font: "New Computer Modern Sans", size: 10pt)

#grid(
  columns: (1fr, 1fr),
  [
    #text(size: 24pt, weight: "bold")[INVOICE]

    #v(0.5em)

    *Invoice #:* {{ invoice_number }}\\
    *Date:* {{ date }}\\
    *Due Date:* {{ due_date }}
  ],
  align(right)[
    *{{ company_name }}*\\
    {{ company_address }}\\
    {{ company_email }}
  ]
)

#v(2em)

#line(length: 100%, stroke: 0.5pt)

#v(1em)

*Bill To:*\\
{{ client_name }}\\
{{ client_address }}

#v(2em)

#table(
  columns: (auto, 1fr, auto, auto),
  inset: 8pt,
  align: (left, left, right, right),
  stroke: none,

  [*#*], [*Description*], [*Qty*], [*Amount*],
  table.hline(),

  [1], [Item description], [1], [\\$100.00],
  [2], [Another item], [2], [\\$200.00],

  table.hline(),
  [], [], [*Subtotal*], [\\$300.00],
  [], [], [*Tax (10%)*], [\\$30.00],
  table.hline(stroke: 2pt),
  [], [], [*Total*], [*\\$330.00*],
)

#v(2em)

*Payment Terms:* Net 30

*Notes:* {{ notes }}
'''
    }

    return templates.get(name, templates["minimal"])


async def main():
    """Run the MCP server."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info("Typst Document MCP Server starting...")
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="typst-mcp",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
