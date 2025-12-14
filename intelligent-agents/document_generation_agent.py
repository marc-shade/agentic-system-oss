#!/usr/bin/env python3
"""
Document Generation Agent
=========================

Intelligent agent for automated document generation using Typst.

Capabilities:
- Generate reports from structured data
- Create papers from research notes
- Convert various formats to Typst
- Manage document projects
- Apply templates and styling
- Integrate with enhanced-memory for versioning

This agent coordinates with:
- typst-mcp: Document compilation
- enhanced-memory-mcp: Document versioning and storage
- research-paper-mcp: Academic paper support

Author: Pixel / Agentic System
"""
import platform

import asyncio
import json
import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("document-generation-agent")

# Paths
AGENTIC_PATH = Path(os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE)))
TEMPLATES_DIR = AGENTIC_PATH / "mcp-servers" / "typst-mcp" / "templates"
OUTPUT_DIR = AGENTIC_PATH / "documents" / "typst-output"
PROJECTS_DIR = AGENTIC_PATH / "documents" / "typst-projects"


@dataclass
class DocumentSpec:
    """Specification for a document to generate."""
    doc_type: str  # report, paper, presentation, letter, invoice
    title: str
    author: str = ""
    sections: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    output_path: Optional[str] = None
    compile_pdf: bool = True
    template: Optional[str] = None


@dataclass
class DocumentResult:
    """Result of document generation."""
    success: bool
    typ_path: Optional[str] = None
    pdf_path: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class DocumentGenerationAgent:
    """
    Intelligent document generation agent.

    Features:
    - Multi-format document generation
    - Template management
    - Content structuring
    - Memory integration for versioning
    - Quality validation
    """

    def __init__(self):
        self.typst_path = self._find_typst()
        self._ensure_directories()

    def _find_typst(self) -> str:
        """Find Typst executable."""
        import shutil
        locations = [
            shutil.which("typst"),
            os.path.expanduser("~/.cargo/bin/typst"),
            "/usr/local/bin/typst",
        ]
        for loc in locations:
            if loc and os.path.exists(loc):
                return loc
        raise FileNotFoundError("Typst not installed")

    def _ensure_directories(self):
        """Ensure output directories exist."""
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

    async def generate_document(self, spec: DocumentSpec) -> DocumentResult:
        """
        Generate a document from specification.

        Args:
            spec: Document specification

        Returns:
            DocumentResult with paths and status
        """
        logger.info(f"Generating {spec.doc_type}: {spec.title}")

        try:
            # Select generation method based on type
            generators = {
                "report": self._generate_report,
                "paper": self._generate_paper,
                "presentation": self._generate_presentation,
                "letter": self._generate_letter,
                "invoice": self._generate_invoice,
                "minimal": self._generate_minimal,
            }

            generator = generators.get(spec.doc_type, self._generate_minimal)
            typst_content = await generator(spec)

            # Determine output path
            if spec.output_path:
                output_path = Path(spec.output_path).expanduser()
            else:
                safe_title = self._safe_filename(spec.title)
                output_path = OUTPUT_DIR / f"{safe_title}.typ"

            # Ensure parent directory
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write Typst file
            output_path.write_text(typst_content)
            logger.info(f"Created: {output_path}")

            result = DocumentResult(
                success=True,
                typ_path=str(output_path),
                metadata={
                    "title": spec.title,
                    "type": spec.doc_type,
                    "created": datetime.now().isoformat(),
                    "sections": len(spec.sections)
                }
            )

            # Compile to PDF if requested
            if spec.compile_pdf:
                pdf_result = await self._compile_pdf(output_path)
                if pdf_result:
                    result.pdf_path = str(pdf_result)
                else:
                    logger.warning("PDF compilation failed")

            return result

        except Exception as e:
            logger.error(f"Document generation failed: {e}", exc_info=True)
            return DocumentResult(success=False, error=str(e))

    async def _generate_report(self, spec: DocumentSpec) -> str:
        """Generate a report document."""
        content = f'''#set document(title: "{spec.title}", author: "{spec.author}")
#set page(
  paper: "us-letter",
  margin: (top: 1in, bottom: 1in, left: 1.25in, right: 1in),
  header: context {{
    if counter(page).get().first() > 1 [
      #set text(size: 9pt, fill: gray)
      {spec.title}
      #h(1fr)
      #counter(page).display()
    ]
  }}
)
#set text(font: "New Computer Modern", size: 11pt)
#set heading(numbering: "1.1")
#set par(justify: true)

// Title Page
#align(center + horizon)[
  #text(size: 28pt, weight: "bold")[{spec.title}]

  #v(2em)

  #text(size: 14pt)[{spec.author}]

  #v(1em)

  #text(size: 12pt, fill: gray)[{datetime.now().strftime('%B %d, %Y')}]
]

#pagebreak()

// Table of Contents
#outline(title: "Contents", indent: auto)

#pagebreak()

'''
        # Add sections
        for section in spec.sections:
            heading = section.get("heading", "Section")
            section_content = section.get("content", "")
            level = section.get("level", 1)
            heading_marks = "=" * level

            content += f"\n{heading_marks} {heading}\n\n{section_content}\n"

        return content

    async def _generate_paper(self, spec: DocumentSpec) -> str:
        """Generate an academic paper."""
        authors = spec.metadata.get("authors", [spec.author])
        abstract = spec.metadata.get("abstract", "")
        affiliation = spec.metadata.get("affiliation", "")

        authors_list = ", ".join(f'"{a}"' for a in authors)
        authors_display = ", ".join(authors)

        content = f'''#set document(title: "{spec.title}", author: ({authors_list}))
#set page(paper: "us-letter", margin: 1in)
#set text(font: "New Computer Modern", size: 10pt)
#set heading(numbering: "1.1")
#set par(justify: true, first-line-indent: 1em)
#set math.equation(numbering: "(1)")

// Title block
#align(center)[
  #text(size: 16pt, weight: "bold")[{spec.title}]

  #v(1em)

  #text(size: 11pt)[{authors_display}]

  #{f'#v(0.3em)#text(size: 9pt, style: "italic")[{affiliation}]' if affiliation else ''}

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
        for section in spec.sections:
            heading = section.get("heading", "Section")
            section_content = section.get("content", "")
            content += f"\n= {heading}\n\n{section_content}\n"

        # Add bibliography if provided
        bibliography = spec.metadata.get("bibliography", [])
        if bibliography:
            content += "\n= References\n\n"
            for i, ref in enumerate(bibliography, 1):
                content += f"[{i}] {ref}\n\n"

        return content

    async def _generate_presentation(self, spec: DocumentSpec) -> str:
        """Generate a presentation using Polylux."""
        content = f'''#import "@preview/polylux:0.3.1": *

#set page(paper: "presentation-16-9")
#set text(font: "New Computer Modern Sans", size: 20pt)

// Title slide
#polylux-slide[
  #align(center + horizon)[
    #text(size: 40pt, weight: "bold")[{spec.title}]

    #v(1em)

    #text(size: 24pt)[{spec.author}]

    #v(0.5em)

    #text(size: 18pt, fill: gray)[{datetime.now().strftime('%B %d, %Y')}]
  ]
]

'''
        # Add content slides
        for section in spec.sections:
            heading = section.get("heading", "Slide")
            section_content = section.get("content", "")

            # Convert content to bullet points if needed
            if "\n" in section_content:
                bullets = "\n".join(f"  - {line.strip()}"
                                  for line in section_content.split("\n")
                                  if line.strip())
                section_content = bullets

            content += f'''
#polylux-slide[
  = {heading}

{section_content}
]
'''

        # Closing slide
        content += '''
#polylux-slide[
  #align(center + horizon)[
    #text(size: 32pt, weight: "bold")[Thank You]

    #v(1em)

    #text(size: 20pt)[Questions?]
  ]
]
'''
        return content

    async def _generate_letter(self, spec: DocumentSpec) -> str:
        """Generate a formal letter."""
        recipient = spec.metadata.get("recipient", "Recipient")
        recipient_address = spec.metadata.get("recipient_address", "")
        sender_address = spec.metadata.get("sender_address", "")
        body = spec.sections[0].get("content", "") if spec.sections else ""

        content = f'''#set page(paper: "us-letter", margin: 1in)
#set text(font: "New Computer Modern", size: 11pt)

#align(right)[
  {sender_address}

  {datetime.now().strftime('%B %d, %Y')}
]

#v(2em)

{recipient}\\
{recipient_address}

#v(1em)

Dear {recipient},

#v(0.5em)

{body}

#v(1em)

Sincerely,

#v(2em)

{spec.author}
'''
        return content

    async def _generate_invoice(self, spec: DocumentSpec) -> str:
        """Generate an invoice."""
        client = spec.metadata.get("client", "Client Name")
        client_address = spec.metadata.get("client_address", "")
        company = spec.metadata.get("company", spec.author)
        company_address = spec.metadata.get("company_address", "")
        invoice_number = spec.metadata.get("invoice_number", "001")
        items = spec.metadata.get("items", [])

        # Calculate totals
        subtotal = sum(item.get("amount", 0) for item in items)
        tax_rate = spec.metadata.get("tax_rate", 0)
        tax = subtotal * tax_rate
        total = subtotal + tax

        content = f'''#set page(paper: "us-letter", margin: 0.75in)
#set text(font: "New Computer Modern Sans", size: 10pt)

#grid(
  columns: (1fr, 1fr),
  [
    #text(size: 24pt, weight: "bold")[INVOICE]

    #v(0.5em)

    *Invoice #:* {invoice_number}\\
    *Date:* {datetime.now().strftime('%B %d, %Y')}\\
    *Due Date:* {spec.metadata.get('due_date', 'Upon Receipt')}
  ],
  align(right)[
    *{company}*\\
    {company_address}
  ]
)

#v(2em)

#line(length: 100%, stroke: 0.5pt)

#v(1em)

*Bill To:*\\
{client}\\
{client_address}

#v(2em)

#table(
  columns: (auto, 1fr, auto, auto),
  inset: 8pt,
  align: (left, left, right, right),
  stroke: none,

  [*#*], [*Description*], [*Qty*], [*Amount*],
  table.hline(),
'''

        for i, item in enumerate(items, 1):
            desc = item.get("description", "Item")
            qty = item.get("qty", 1)
            amount = item.get("amount", 0)
            content += f"  [{i}], [{desc}], [{qty}], [\\${amount:.2f}],\n"

        content += f'''
  table.hline(),
  [], [], [*Subtotal*], [\\${subtotal:.2f}],
  [], [], [*Tax ({tax_rate*100:.0f}%)*], [\\${tax:.2f}],
  table.hline(stroke: 2pt),
  [], [], [*Total*], [*\\${total:.2f}*],
)

#v(2em)

*Payment Terms:* {spec.metadata.get('payment_terms', 'Net 30')}

*Notes:* {spec.metadata.get('notes', '')}
'''
        return content

    async def _generate_minimal(self, spec: DocumentSpec) -> str:
        """Generate a minimal document."""
        content = f'''#set page(paper: "us-letter", margin: 1in)
#set text(size: 11pt)

= {spec.title}

'''
        for section in spec.sections:
            heading = section.get("heading")
            section_content = section.get("content", "")

            if heading:
                content += f"\n== {heading}\n\n"
            content += f"{section_content}\n"

        return content

    async def _compile_pdf(self, typ_path: Path) -> Optional[Path]:
        """Compile Typst file to PDF."""
        try:
            pdf_path = typ_path.with_suffix(".pdf")

            process = await asyncio.create_subprocess_exec(
                self.typst_path, "compile",
                str(typ_path), str(pdf_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                logger.info(f"Compiled: {pdf_path}")
                return pdf_path
            else:
                logger.error(f"Compilation error: {stderr.decode()}")
                return None

        except Exception as e:
            logger.error(f"Compilation failed: {e}")
            return None

    def _safe_filename(self, title: str) -> str:
        """Convert title to safe filename."""
        safe = re.sub(r'[^\w\s-]', '', title).strip()
        safe = re.sub(r'[\s]+', '-', safe)
        return safe[:50]

    async def convert_markdown_to_typst(self, markdown: str) -> str:
        """Convert Markdown content to Typst markup."""
        typst = markdown

        # Headers
        typst = re.sub(r'^# (.+)$', r'= \1', typst, flags=re.MULTILINE)
        typst = re.sub(r'^## (.+)$', r'== \1', typst, flags=re.MULTILINE)
        typst = re.sub(r'^### (.+)$', r'=== \1', typst, flags=re.MULTILINE)
        typst = re.sub(r'^#### (.+)$', r'==== \1', typst, flags=re.MULTILINE)

        # Bold and italic
        typst = re.sub(r'\*\*\*(.+?)\*\*\*', r'_*\1*_', typst)
        typst = re.sub(r'\*\*(.+?)\*\*', r'*\1*', typst)
        typst = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'_\1_', typst)

        # Links
        typst = re.sub(r'\[(.+?)\]\((.+?)\)', r'#link("\2")[\1]', typst)

        # Code blocks
        typst = re.sub(
            r'```(\w*)\n(.*?)```',
            lambda m: f'```{m.group(1)}\n{m.group(2)}```',
            typst,
            flags=re.DOTALL
        )

        # Inline code
        typst = re.sub(r'`([^`]+)`', r'`\1`', typst)

        # Lists
        typst = re.sub(r'^- (.+)$', r'- \1', typst, flags=re.MULTILINE)
        typst = re.sub(r'^\d+\. (.+)$', r'+ \1', typst, flags=re.MULTILINE)

        # Blockquotes
        typst = re.sub(r'^> (.+)$', r'#quote[\1]', typst, flags=re.MULTILINE)

        return typst

    async def generate_from_data(
        self,
        data: Dict[str, Any],
        template: str = "report"
    ) -> DocumentResult:
        """
        Generate document from structured data.

        Args:
            data: Dictionary with document data
            template: Template to use

        Returns:
            DocumentResult
        """
        spec = DocumentSpec(
            doc_type=template,
            title=data.get("title", "Untitled"),
            author=data.get("author", ""),
            sections=[
                {"heading": k, "content": str(v)}
                for k, v in data.get("sections", {}).items()
            ],
            metadata=data.get("metadata", {}),
            output_path=data.get("output_path"),
            compile_pdf=data.get("compile_pdf", True)
        )

        return await self.generate_document(spec)


# Standalone functions for direct use

async def generate_report(
    title: str,
    sections: List[Dict[str, str]],
    author: str = "",
    output_path: Optional[str] = None
) -> DocumentResult:
    """Quick report generation."""
    agent = DocumentGenerationAgent()
    spec = DocumentSpec(
        doc_type="report",
        title=title,
        author=author,
        sections=sections,
        output_path=output_path
    )
    return await agent.generate_document(spec)


async def generate_paper(
    title: str,
    authors: List[str],
    abstract: str,
    sections: List[Dict[str, str]],
    output_path: Optional[str] = None
) -> DocumentResult:
    """Quick paper generation."""
    agent = DocumentGenerationAgent()
    spec = DocumentSpec(
        doc_type="paper",
        title=title,
        author=authors[0] if authors else "",
        sections=sections,
        metadata={
            "authors": authors,
            "abstract": abstract
        },
        output_path=output_path
    )
    return await agent.generate_document(spec)


# CLI interface
if __name__ == "__main__":
    import argparse

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    elif system == "Linux":
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()


    parser = argparse.ArgumentParser(description="Document Generation Agent")
    parser.add_argument("--type", choices=["report", "paper", "presentation", "letter", "invoice", "minimal"],
                       default="report", help="Document type")
    parser.add_argument("--title", required=True, help="Document title")
    parser.add_argument("--author", default="", help="Author name")
    parser.add_argument("--output", help="Output path")
    parser.add_argument("--no-pdf", action="store_true", help="Skip PDF compilation")

    args = parser.parse_args()

    agent = DocumentGenerationAgent()
    spec = DocumentSpec(
        doc_type=args.type,
        title=args.title,
        author=args.author,
        sections=[{"heading": "Introduction", "content": "Content here."}],
        output_path=args.output,
        compile_pdf=not args.no_pdf
    )

    result = asyncio.run(agent.generate_document(spec))

    if result.success:
        print(f"Created: {result.typ_path}")
        if result.pdf_path:
            print(f"PDF: {result.pdf_path}")
    else:
        print(f"Error: {result.error}")
