# Research Paper Ingestion MCP Server

Autonomous knowledge acquisition from academic research papers for AGI self-improvement.

## Features

### Paper Discovery
- **arXiv Integration**: Search and download from arXiv.org
- **Semantic Scholar**: Citation analysis and academic impact metrics
- **PDF Download**: Automatic paper retrieval and storage

### Knowledge Extraction
- **Insight Extraction**: Identify key findings and contributions
- **Citation Analysis**: Understand paper influence and relationships
- **Technique Identification**: Extract novel methods and approaches

### Memory Integration
- **Enhanced Memory**: Store extracted knowledge for AGI learning
- **Structured Entities**: Create searchable memory representations
- **Citation Graphs**: Track knowledge lineage

## Installation

```bash
cd /Volumes/SSDRAID0/agentic-system/mcp-servers/research-paper-mcp
pip install -r requirements.txt
```

## Configuration

Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "research-paper-mcp": {
      "command": "python3",
      "args": [
        "/Volumes/SSDRAID0/agentic-system/mcp-servers/research-paper-mcp/server.py"
      ],
      "env": {},
      "disabled": false
    }
  }
}
```

## Available Tools

### search_arxiv
Search arXiv for research papers by query.

**Parameters**:
- `query` (required): Search query (e.g., "recursive self-improvement AGI")
- `max_results`: Maximum results (default: 10)
- `sort_by`: Sort order - relevance, lastUpdatedDate, submittedDate

**Example**:
```python
results = mcp__research-paper-mcp__search_arxiv({
    "query": "meta-learning neural networks",
    "max_results": 20,
    "sort_by": "relevance"
})
```

### search_semantic_scholar
Search Semantic Scholar for papers with citation metrics.

**Parameters**:
- `query` (required): Search query
- `fields`: Metadata fields to retrieve
- `limit`: Maximum results (default: 10)

**Example**:
```python
results = mcp__research-paper-mcp__search_semantic_scholar({
    "query": "transformer architecture attention",
    "fields": ["title", "authors", "citationCount", "year"],
    "limit": 15
})
```

### download_paper
Download research paper PDF from URL.

**Parameters**:
- `url` (required): PDF URL
- `paper_id` (required): Unique identifier for filename

**Example**:
```python
result = mcp__research-paper-mcp__download_paper({
    "url": "https://arxiv.org/pdf/1234.5678.pdf",
    "paper_id": "arxiv-1234.5678"
})
```

### extract_insights
Extract key insights and findings from paper text.

**Parameters**:
- `paper_text` (required): Full paper text or abstract
- `focus_areas`: Optional specific areas to focus on

**Example**:
```python
insights = mcp__research-paper-mcp__extract_insights({
    "paper_text": paper_abstract,
    "focus_areas": ["methodology", "results"]
})
```

### analyze_citations
Analyze citation relationships and paper influence.

**Parameters**:
- `paper_id` (required): Semantic Scholar or arXiv paper ID
- `depth`: Citation graph depth 1-3 (default: 1)

**Example**:
```python
analysis = mcp__research-paper-mcp__analyze_citations({
    "paper_id": "arxiv:1706.03762",  # "Attention Is All You Need"
    "depth": 2
})
```

### store_paper_knowledge
Store extracted knowledge in enhanced-memory for AGI learning.

**Parameters**:
- `paper_metadata` (required): Paper metadata dict
- `insights` (required): List of key insights
- `techniques`: List of novel techniques

**Example**:
```python
stored = mcp__research-paper-mcp__store_paper_knowledge({
    "paper_metadata": {
        "id": "arxiv-1234.5678",
        "title": "Novel AGI Approach",
        "authors": ["Smith", "Jones"],
        "year": 2024
    },
    "insights": [
        "Achieves 95% accuracy on benchmark",
        "10x faster than previous methods"
    ],
    "techniques": [
        "Recursive meta-optimization",
        "Self-modifying architectures"
    ]
})
```

## Usage Patterns

### Autonomous Research Workflow

```python
# 1. Search for relevant papers
arxiv_results = mcp__research-paper-mcp__search_arxiv({
    "query": "recursive self-improvement",
    "max_results": 10
})

# 2. Get citation metrics
for paper in arxiv_results['papers']:
    scholar_data = mcp__research-paper-mcp__search_semantic_scholar({
        "query": paper['title'],
        "limit": 1
    })

    # 3. Download high-impact papers
    if scholar_data['papers'][0]['citationCount'] > 50:
        pdf = mcp__research-paper-mcp__download_paper({
            "url": paper['pdf_url'],
            "paper_id": paper['id']
        })

        # 4. Extract and store insights
        insights = mcp__research-paper-mcp__extract_insights({
            "paper_text": paper['abstract']
        })

        mcp__research-paper-mcp__store_paper_knowledge({
            "paper_metadata": paper,
            "insights": insights['insights']
        })
```

### Citation Network Analysis

```python
# Analyze citation influence
analysis = mcp__research-paper-mcp__analyze_citations({
    "paper_id": "influential-paper-id",
    "depth": 2
})

# Identify most influential papers in field
if analysis['citation_graph']['influential_citations'] > 100:
    # Download and study this foundational paper
    pass
```

## Storage

- **Papers Directory**: `/Volumes/SSDRAID0/agentic-system/research-papers/`
- **PDFs**: Saved as `{paper_id}.pdf`
- **Memory Integration**: Via enhanced-memory-mcp create_entities

## Dependencies

- **arxiv**: arXiv API Python wrapper
- **aiohttp**: Async HTTP client for Semantic Scholar API
- **mcp**: Model Context Protocol SDK

## Future Enhancements

1. **PDF Text Extraction**: Parse full paper text from PDFs
2. **Figure/Diagram Analysis**: Extract visual insights
3. **Code Repository Links**: Find implementation code
4. **Related Papers**: Automatic discovery of connected research
5. **Trend Detection**: Identify emerging research directions
6. **LLM-Powered Insight Extraction**: Use GPT-4 for deeper analysis

## Integration with AGI System

This MCP server closes Gap #1 from AGI_GAP_ANALYSIS.md:

**Knowledge Acquisition Infrastructure** ✅
- ✓ Research Paper Ingestion (arXiv + Semantic Scholar)
- ⏳ Video Transcript Processing (separate MCP)
- ⏳ GitHub Repository Analysis (future)
- ⏳ Documentation Scraping (future)
- ⏳ Knowledge Graph Integration (future)

**Impact**: System can now autonomously learn from the latest AI research!
