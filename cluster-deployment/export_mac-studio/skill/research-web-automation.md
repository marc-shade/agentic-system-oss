# Research & Web Automation

Comprehensive research workflows with multi-agent orchestration, browser automation, and web data extraction.

## Parallel Research Workflows

**Kenny's Parallel Agent Pattern** - Spawn specialized agents simultaneously:

**Agent Selection:**
- `research-coordinator` - Multi-source research with citations
- `web-analyst` - Browser automation, analytics extraction
- `documentation-researcher` - Official docs and implementation guides
- `compounding-engineering:best-practices-researcher` - Framework best practices
- `compounding-engineering:framework-docs-researcher` - Framework documentation

**Execution Pattern:**
```python
# Spawn multiple agents in parallel
[
  Task("research-coordinator", "Research AI tools"),
  Task("web-analyst", "Extract YouTube analytics"),
  Task("documentation-researcher", "Create implementation guide")
]

# Voice narration
mcp__voice-mode__converse(
    "I've spawned three specialized agents working in parallel...",
    wait_for_response=False
)
```

**Voice Narration:**
- Start: "Starting parallel research. Spawning [N] specialized agents..."
- During: "Research coordinator searching sources, web analyst navigating..."
- Complete: "All agents completed. Synthesizing findings..."

**Output Standards:**
- Save reports as markdown with citations
- Include sources and references
- Structured formats (tables, sections)
- Production-ready only

## Web Search

**Standard Search:**
- Use `WebSearch` tool for current information
- Domain filtering (include/exclude sites)
- Results auto-fetched and analyzed
- Up-to-date beyond training cutoff

**Brave Search (Privacy-Focused):**
- Search types: general, news, academic, code
- Options: count (max 20), freshness, country, language, safe-search
- Features: No tracking, independent index, AI summarization, unbiased
- MCP tools: `mcp__brave-search__search`, `search_news`, `search_images`, `get_summary`

Examples:
```
"Latest AI developments" --type=news --freshness=day
"Machine learning healthcare" --type=academic
"FastAPI authentication" --type=code
```

## Web Content Fetching

**Fetch Formats:**
- Markdown: `mcp__fetch__fetch_markdown` - Clean, readable
- HTML: `mcp__fetch__fetch_html` - Full HTML
- Text: `mcp__fetch__fetch_txt` - Plain text
- JSON: `mcp__fetch__fetch_json` - API endpoints

**Use Cases:**
- Research and analysis
- Content extraction
- API data retrieval

## Browser Automation

**Core Actions:**

**Screenshot:**
```
Capture webpage --full-page --format=png
```

**Extract Data:**
```
Extract structured data --selector=".article-title" --limit=10
Extract product prices --selector=".price" --attribute="text"
Extract table data --selector="table" --format=csv
```

**Automate Interactions:**
```
Automate login-flow --url="https://app.com" --script="login.js"
Form fill --data='{"name": "John", "email": "john@example.com"}'
Multi-step workflow --steps='["add-to-cart", "checkout", "payment"]'
```

**Monitor Changes:**
```
Monitor price changes --selector=".price" --alert-threshold=10
Monitor availability --selector=".available" --alert-on="true"
```

**PDF Conversion:**
```
Convert to PDF --format=A4 --margins=default
```

**Options:**
- `--headless`: Headless mode (default: true)
- `--viewport`: Size (e.g., "1920x1080")
- `--wait-for`: Condition (load, domcontentloaded, networkidle)
- `--timeout`: Seconds (default: 30)
- `--user-agent`: Custom UA string
- `--cookies`: Load from file
- `--proxy`: Proxy server

**MCP Tools:**
- `mcp__browser-tools__navigate`
- `mcp__browser-tools__screenshot`
- `mcp__browser-tools__extract_data`
- `mcp__browser-tools__fill_form`
- `mcp__browser-tools__click_element`
- `mcp__browser-tools__wait_for_element`
- `mcp__browser-tools__execute_script`
- `mcp__browser-tools__get_page_content`
- `mcp__browser-tools__save_as_pdf`

## Research Workflow Example

```
User: "Research latest AI coding tools, analyze GitHub stats, create MCP implementation guide"

Response:
1. Narrate: "Launching three specialized agents in parallel..."
2. Spawn:
   - Research Coordinator → AI tools research via Brave Search
   - Web Analyst → GitHub statistics via browser automation
   - Documentation Researcher → MCP implementation guide from official docs
3. Voice updates as agents work
4. Synthesize unified results with citations
5. Save as structured markdown reports
```

## Token Cost: ~200 tokens
Replaces 5 slash commands (283 lines, ~1,130 tokens) = **930 token savings**
