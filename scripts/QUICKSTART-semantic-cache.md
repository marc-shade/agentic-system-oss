# Semantic Cache - Quick Start Guide

Get started with semantic caching in 5 minutes.

## Installation

Already installed! Dependencies are in the main venv:
```bash
source /mnt/agentic-system/.venv/bin/activate
```

## 30-Second Test

```bash
cd /mnt/agentic-system/scripts
python3 semantic_cache_module.py test
```

Expected output:
- Cache HITs with 1.0000 similarity (exact matches)
- Sub-20ms retrieval latency
- Statistics showing hit rate

## Basic Usage (Python)

```python
from semantic_cache_module import SemanticCache

# 1. Create cache
cache = SemanticCache(similarity_threshold=0.90)

# 2. Check before expensive operation
result = cache.get("How does binary search work?")

if result:
    response, similarity = result
    print(f"✓ Cache HIT (similarity: {similarity:.3f})")
else:
    print("✗ Cache MISS - calling API...")
    response = expensive_llm_call(query)
    cache.store(query, response)
```

## Claude API Integration

```python
from semantic_cache_claude_wrapper import CachedClaudeClient

# Drop-in replacement for Anthropic client
client = CachedClaudeClient()

response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    messages=[{"role": "user", "content": "Explain quicksort"}]
)

# Check if cached
if response.from_cache:
    print(f"Served from cache! ({response.cache_similarity:.3f})")
```

## AGI Integration (Best for Production)

```python
from agi_semantic_cache_integration import AGISemanticCache

# Pre-configured for different use cases
reasoning_cache = AGISemanticCache(cache_domain="reasoning")
research_cache = AGISemanticCache(cache_domain="research")

# Automatic caching with fallback
result = reasoning_cache.cached_call(
    query="How to optimize memory consolidation?",
    fallback=lambda: self.expensive_reasoning()
)

# View metrics
print(reasoning_cache.get_metrics())
```

## CLI Commands

```bash
# View statistics
python3 semantic_cache_module.py stats

# Search for similar queries
python3 semantic_cache_module.py search --query "your query"

# Cleanup expired entries
python3 semantic_cache_module.py cleanup

# Clear everything
python3 semantic_cache_module.py cleanup --force
```

## Run Examples

```bash
# See 6 usage demonstrations
python3 example-semantic-cache-usage.py

# See AGI integration examples
python3 agi-semantic-cache-integration.py

# Run comprehensive test suite
python3 test-semantic-cache.py
```

## Key Parameters

| Parameter | Recommended | Effect |
|-----------|-------------|--------|
| `similarity_threshold` | **0.90** | Lower = more hits, higher = more precise |
| `ttl_hours` | **24** | How long to keep cache entries |
| `model_name` | `all-MiniLM-L6-v2` | Embedding model (default is good) |

## Similarity Threshold Guide

- **0.85-0.88**: High hit rate (~50%), some false positives
- **0.90-0.92**: RECOMMENDED - Best balance (~30-40% hit rate)
- **0.93-0.95**: Very precise, lower hit rate (~15-25%)
- **0.96+**: Near-exact matches only (<10% hit rate)

## Expected Performance

Based on testing:

| Metric | Value |
|--------|-------|
| Cache hit rate | 30-50% |
| Retrieval latency | 15-50ms |
| API call latency | ~2000ms |
| **Speedup on hits** | **40-130x faster** |
| Token cost savings | ~35-40% |

## Common Use Cases

### 1. Speed up repeated questions

```python
cache = SemanticCache()

queries = [
    "How does binary search work?",
    "Explain binary search algorithm",  # Similar - will hit cache!
]

for query in queries:
    result = cache.get(query)
    if result:
        print("✓ HIT")
    else:
        response = expensive_call()
        cache.store(query, response)
```

### 2. Cache research insights

```python
research_cache = AGISemanticCache(
    cache_domain="research",
    ttl_hours=72  # 3 days
)

insights = research_cache.cached_call(
    "neural architecture search",
    fallback=lambda: fetch_papers_and_analyze()
)
```

### 3. Cache reasoning patterns

```python
reasoning_cache = AGISemanticCache(
    cache_domain="reasoning",
    threshold=0.92  # Higher precision for reasoning
)

result = reasoning_cache.cached_call(
    "How to optimize database queries?",
    fallback=lambda: complex_reasoning()
)
```

## Monitoring

```python
# Get statistics
stats = cache.get_stats()
print(f"Hit rate: {stats['session_stats']['hit_rate']}")
print(f"Total entries: {stats['total_entries']}")

# Export for analysis
cache.export_stats("/tmp/cache_report.json")
```

## Troubleshooting

**Low hit rate?**
- Lower threshold to 0.88-0.90
- Check that queries are semantically similar

**False positives?**
- Increase threshold to 0.93-0.95
- Use domain-specific caches

**Slow performance?**
- Run cleanup: `cache.cleanup()`
- Check database size: `du -h ~/.claude/enhanced_memories/`

## Next Steps

1. Read full documentation: `README-semantic-cache.md`
2. Review test results: `test-semantic-cache.py`
3. See integration examples: `example-semantic-cache-usage.py`
4. Check AGI integration: `agi-semantic-cache-integration.py`
5. Read implementation summary: `SEMANTIC-CACHE-SUMMARY.md`

## Integration Checklist

- [ ] Choose appropriate threshold (start with 0.90)
- [ ] Set TTL based on use case (24h default)
- [ ] Use domain-specific caches for different components
- [ ] Monitor hit rates and adjust threshold
- [ ] Set up periodic cleanup (weekly recommended)
- [ ] Export stats for analysis

## Support

Files location: `/mnt/agentic-system/scripts/`

All scripts are executable and ready to use:
- `semantic_cache_module.py` - Core implementation
- `semantic_cache_claude_wrapper.py` - Claude API wrapper
- `agi-semantic-cache-integration.py` - AGI integration
- `test-semantic-cache.py` - Test suite
- `example-semantic-cache-usage.py` - Usage examples

---

**Ready to use!** Start with the AGI integration for production or the basic module for custom implementations.
