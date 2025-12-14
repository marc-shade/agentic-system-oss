# PDF Operations

Create and merge PDF documents from various sources using superpdf-server MCP.

## PDF Generation

**From Markdown:**
- Convert markdown content to formatted PDFs
- Support for headers, lists, code blocks
- Custom CSS styling
- Table of contents generation

**From HTML:**
- Convert HTML to PDF with full CSS support
- Preserve formatting and layout
- Custom margins and page sizes
- Headers and footers

**From Images:**
- Combine multiple images into single PDF
- Automatic sizing and alignment
- Sequential page layout
- Image quality optimization

**Usage:**
```
Create PDF from this markdown content with headers
Convert this HTML to PDF with custom CSS styling
Combine these images into a PDF document
```

**MCP Tools:**
- `mcp__superpdf-server__generate_pdf_from_markdown`
- `mcp__superpdf-server__generate_pdf_from_html`
- `mcp__superpdf-server__generate_pdf_from_images`

**Options:**
- Headers/footers with custom content
- Table of contents with links
- Custom margins (top, bottom, left, right)
- CSS styling for appearance
- Page numbering

## PDF Merging

**Combine Multiple PDFs:**
- Merge any number of PDF files
- Preserves original formatting
- Maintains bookmarks and links
- Sequential page numbering
- Optional custom output path

**Usage:**
```
Merge report1.pdf, report2.pdf, and appendix.pdf into final-report.pdf
Combine all PDFs in folder into single document
```

**MCP Tool:** `mcp__superpdf-server__merge_pdfs`

**Features:**
- Format preservation across all source files
- Bookmark retention and organization
- Automatic page numbering
- Custom output file naming

## Example Workflows

**Documentation Generation:**
```
1. Generate PDF from markdown README
2. Create PDF from HTML API docs
3. Merge into complete documentation.pdf
```

**Report Assembly:**
```
1. Convert analysis results (markdown) to PDF
2. Convert charts (HTML) to PDF
3. Add appendix images to PDF
4. Merge all sections into final report
```

## Token Cost: ~50 tokens
Replaces 2 PDF commands (34 lines, ~136 tokens) = **86 token savings**
