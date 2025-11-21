# YouTube Research Quick Reference

**MCP Tool**: `video-transcript-mcp` (active)
**Status**: Ready for manual URL collection

## Quick Start

### 1. Manual Search (YouTube.com)

**Top Priority Queries**:
```
recursive self-improving AI implementation
meta-learning autonomous agents
AGI self-modification architecture
neural architecture search tutorial
autonomous agent system design patterns
```

**Filters**: Last year | >10 min | Subtitles/CC

**Priority Channels**:
- NeurIPS, ICML, ICLR (conferences)
- DeepMind, OpenAI, Anthropic (labs)
- Yannic Kilcher, Andrej Karpathy (technical)

### 2. Collect URLs

Create `urls.txt`:
```
https://youtube.com/watch?v=VIDEO_ID_1
https://youtube.com/watch?v=VIDEO_ID_2
https://youtube.com/watch?v=VIDEO_ID_3
```

### 3. Process with MCP Tools

```python
# Fetch transcript
result = mcp__video-transcript-mcp__fetch_youtube_transcript({
    "url": "https://youtube.com/watch?v=VIDEO_ID",
    "auto_clean": true
})

# Extract concepts
concepts = mcp__video-transcript-mcp__extract_concepts({
    "transcript": result["transcript"],
    "focus_domains": ["recursive", "AGI", "meta-learning"]
})

# Extract methods
methods = mcp__video-transcript-mcp__extract_methodologies({
    "transcript": result["transcript"],
    "extract_code": true
})

# Store knowledge
mcp__video-transcript-mcp__store_video_knowledge({
    "video_metadata": {"url": result["url"], "title": "Title"},
    "concepts": concepts["concepts"],
    "methodologies": methods["methodologies"]
})
```

### 4. Batch Processing

```bash
python3 video_research_example.py --batch urls.txt --output results.json
```

## Production-Ready Flags

**✅ Look For**:
- Code examples and GitHub repos
- Live system demos
- Performance metrics
- Production deployment stories
- Error handling discussions

**❌ Skip**:
- Pure theory (no implementation)
- POC/demo only
- "Future work" proposals
- Marketing content

## Key Search Patterns

| Pattern | Keywords | Repos Expected |
|---------|----------|----------------|
| Recursive Code Gen | code generation, self-modification | Sandboxes, safety frameworks |
| Meta-Learning | learning to learn, few-shot | MAML, Reptile implementations |
| Neural Arch Search | NAS, AutoML | ENAS, DARTS frameworks |
| Autonomous Agents | multi-agent, tool use | ReAct, AutoGPT patterns |
| Self-Supervised | contrastive learning | SimCLR, BERT pretrain |

## Quality Threshold

**Minimum 50% production-readiness score**
- Has code: 25%
- Has repos: 25%
- Has metrics: 25%
- Has deployment info: 25%

## Target Metrics

- **10-15 videos** processed
- **50-100 concepts** extracted
- **20-30 patterns** identified
- **5-10 GitHub repos** discovered

## Files

- **Full Guide**: `YOUTUBE_RECURSIVE_AI_RESEARCH_GUIDE.md`
- **Summary**: `YOUTUBE_RESEARCH_SUMMARY.md`
- **Example Script**: `video_research_example.py`
- **This Reference**: `YOUTUBE_RESEARCH_QUICK_REF.md`

## Enhanced Memory Entities

Search for video research knowledge:
```python
mcp__enhanced-memory__search_nodes({
    "query": "youtube video research workflow recursive",
    "limit": 10
})
```

**Entities**:
- `youtube_video_research_workflow_2025`
- `recursive_ai_video_search_queries`
- `video_transcript_production_patterns`

---

**Next**: Execute manual YouTube search → Collect URLs → Run automated processing
