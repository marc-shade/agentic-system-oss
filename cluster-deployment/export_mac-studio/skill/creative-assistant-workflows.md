# Creative & Assistant Workflows

Comprehensive personal AI assistant and professional design automation workflows.

## Ka Mode - Personal AI Assistant

**Marc's high-powered AI assistant** inspired by Kenny's Claude Agent SDK parallel execution pattern.

### Operating Mode

**1. Listen** - User requests tasks
**2. Decompose** - Break into parallel components
**3. Narrate** - Voice explanation of approach
**4. Execute** - Spawn specialized agents simultaneously
**5. Synthesize** - Combine results into unified response

### Available Specialized Agents

**Research & Analysis:**
- `research-coordinator` - Multi-source research with citations
- `documentation-researcher` - Official docs and implementation guides
- `compounding-engineering:best-practices-researcher` - Framework best practices
- `compounding-engineering:framework-docs-researcher` - Framework documentation

**Automation & Data:**
- `web-analyst` - Browser automation (YouTube, analytics, forms)

**Development:**
- `compounding-engineering:kieran-python-reviewer` - Python code review
- `compounding-engineering:kieran-rails-reviewer` - Rails code review
- `compounding-engineering:kieran-typescript-reviewer` - TypeScript code review
- `compounding-engineering:architecture-strategist` - Architecture review
- `compounding-engineering:security-sentinel` - Security audits
- `compounding-engineering:performance-oracle` - Performance optimization

**Content & Business:**
- `Image Generator` - Visual content creation
- `Landing Page Specialist` - Professional landing pages
- `Market Research Coordinator` - Market research studies

### Parallel Execution Pattern

```python
# Spawn multiple agents simultaneously
[
  Task("research-coordinator", "Research AI tools"),
  Task("web-analyst", "Extract YouTube analytics"),
  Task("documentation-researcher", "Create implementation guide")
]

# Voice narration throughout
mcp__voice-mode__converse(
    "I've spawned three specialized agents working in parallel...",
    wait_for_response=False
)
```

### Voice Narration Protocol

**Starting:**
```python
"I'm going to handle that by spawning [N] specialized agents to work in parallel"
```

**Progress Updates:**
```python
"The web analyst is navigating your dashboard while the researcher searches for latest info..."
```

**Completion:**
```python
"All agents have finished. Let me show you what they found"
```

### Production Standards

Every deliverable must be:
- ✅ Production-ready (no POCs, no demos)
- ✅ Complete and functional
- ✅ Properly cited (for research)
- ✅ Well-structured (markdown, sections)
- ✅ With working code examples (for guides)

### Example Workflows

**Multi-Source Research:**
```
"Analyze my LinkedIn engagement and research competitor content strategies"
→ Spawn: Web Analyst (LinkedIn) + Research Coordinator (competitor analysis)
→ Deliver: Engagement report + Strategy research document
```

**Code Quality Review:**
```
"Review this Python code and create performance improvements"
→ Spawn: Kieran Python Reviewer + Performance Oracle
→ Deliver: Code review + Optimization recommendations
```

**Content Creation:**
```
"Research Playwright MCP, check my GitHub stats, generate a system diagram"
→ Spawn: Documentation Researcher + Web Analyst + Image Generator
→ Deliver: Implementation guide + GitHub analytics + System diagram
```

## Professional Design Automation

**Complete design toolkit** for brand creation, asset generation, and consistency management.

### Logo Creation

**Generate AI-Powered Logos:**
- Modern, vintage, minimal, bold styles
- Wordmark, badge, or icon-based designs
- Custom color schemes
- Multiple variations

**Usage:**
```
Create logo for "TechCorp" --style=modern --type=wordmark --colors="#000000,#00FF00"
Create logo for "Craft Coffee" --style=vintage --type=badge --include-icon=coffee
```

**MCP Tool:** `mcp__design-tools__create_logo`

### Color Palette Generation

**Color Scheme Creation:**
- Complementary, analogous, triadic schemes
- Extract from images
- Brand-consistent palettes
- Accessibility-compliant combinations

**Usage:**
```
Generate color palette --base-color="#3498DB" --scheme=complementary --count=5
Extract brand colors from logo.png --extract-dominant=5
```

**MCP Tool:** `mcp__design-tools__generate_palette`

### Typography Pairing

**Font Combinations:**
- Primary/secondary pairings
- Purpose-specific (website, print, mobile)
- Style matching (modern, classic, playful)
- Accessibility considerations

**Usage:**
```
Suggest typography --primary="Helvetica" --purpose=website --style=modern
```

**MCP Tool:** `mcp__design-tools__suggest_typography`

### Layout Templates

**Generate Layouts:**
- Landing pages, dashboards, presentations
- Customizable sections and widgets
- Responsive design patterns
- Light/dark theme support

**Usage:**
```
Create layout --type=landing-page --sections=["hero","features","pricing","footer"] --style=saas
Create layout --type=dashboard --widgets=["chart","stats","table"] --theme=dark
```

**MCP Tool:** `mcp__design-tools__create_layout`

### Product Mockups

**Device Mockups:**
- Desktop, mobile, tablet
- Multiple devices simultaneously
- Screenshot integration
- Professional presentation

**Usage:**
```
Generate mockup --product=website --device=["desktop","mobile"] --image="screenshot.png"
```

**MCP Tool:** `mcp__design-tools__generate_mockup`

### Complete Brand Kits

**Full Brand Identity:**
- Logo variations
- Color palettes
- Typography systems
- Design guidelines
- Asset templates

**Usage:**
```
Create brand kit --company="2 Acre Studios" --industry=tech --style=professional
```

**MCP Tool:** `mcp__design-tools__create_brand_kit`

### Brand Consistency

**Quality Control:**
- Check consistency across assets
- Apply brand styles to templates
- Automated validation
- Style guide enforcement

**Usage:**
```
Check consistency --brand-guide="guide.pdf" --assets-folder="./designs"
Apply brand styles --template="presentation.pptx" --brand-kit="brand.json"
```

**MCP Tools:**
- `mcp__design-tools__check_consistency`
- `mcp__design-tools__process_assets`

### Asset Management

**Organization & Optimization:**
- Categorize by type/purpose
- Generate size variations (1x, 2x, 3x)
- Multi-format export (PNG, SVG, PDF)
- Batch processing

**Usage:**
```
Organize assets --folder="./designs" --categorize-by=type
Generate variations --image="logo.png" --sizes=["1x","2x","3x"] --formats=["png","svg"]
```

## Design Options

**Common Parameters:**
- `--style`: modern, vintage, minimal, bold
- `--colors`: Hex codes for color scheme
- `--format`: png, svg, pdf
- `--resolution`: 72, 150, 300 dpi
- `--variations`: Number to generate

## Complete MCP Integration

**All operations use design-tools MCP:**
- Logo creation and branding
- Color palette generation
- Typography suggestions
- Layout template creation
- Mockup generation
- Brand kit assembly
- Consistency checking
- Asset processing and optimization

## Token Cost: ~200 tokens
Replaces 2 large workflow commands (226 lines, ~904 tokens) = **704 token savings**
