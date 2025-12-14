# Semantic Cache Integration Example

Quick copy-paste examples for integrating semantic cache into your AGI components.

## 1. AGI Orchestrator Integration

Add to `/mnt/agentic-system/intelligent-agents/agi_orchestrator.py`:

```python
# At top of file
from agi_semantic_cache_integration import AGISemanticCache

class AGIOrchestrator:
    def __init__(self):
        # ... existing code ...

        # Add semantic caches
        self.reasoning_cache = AGISemanticCache(
            cache_domain="reasoning",
            threshold=0.92  # Higher precision for reasoning
        )

        self.api_cache = AGISemanticCache(
            cache_domain="api_calls",
            threshold=0.90
        )

        print("✓ Semantic caching enabled")

    def reason_about(self, query: str, context: dict = None) -> str:
        """Reason with automatic caching"""
        return self.reasoning_cache.cached_call(
            query,
            fallback=lambda: self._complex_reasoning(query, context),
            context=str(context) if context else None,
            estimated_fallback_latency_ms=2000
        )

    def get_cache_stats(self) -> dict:
        """Get caching statistics for monitoring"""
        return {
            "reasoning": self.reasoning_cache.get_metrics(),
            "api_calls": self.api_cache.get_metrics(),
        }
```

## 2. Memory Consolidation Integration

Add to `/mnt/agentic-system/intelligent-agents/autonomous_improvement_daemon.py`:

```python
from agi_semantic_cache_integration import AGISemanticCache

class MemoryConsolidation:
    def __init__(self):
        # Cache for pattern extraction (long TTL - patterns don't change often)
        self.consolidation_cache = AGISemanticCache(
            cache_domain="consolidation",
            ttl_hours=168  # 7 days
        )

    def extract_patterns(self, memory_type: str, time_window_hours: int = 24):
        """Extract patterns with caching"""
        cache_key = f"patterns:{memory_type}:window_{time_window_hours}h"

        return self.consolidation_cache.cached_call(
            cache_key,
            fallback=lambda: self._expensive_pattern_extraction(
                memory_type, time_window_hours
            ),
            estimated_fallback_latency_ms=3000
        )

    def run_consolidation(self):
        """Run full consolidation with caching"""
        results = {}

        for mem_type in ["episodic", "semantic", "procedural"]:
            print(f"Consolidating {mem_type} memories...")
            patterns = self.extract_patterns(mem_type)
            results[mem_type] = patterns

        # Show cache effectiveness
        metrics = self.consolidation_cache.get_metrics()
        print(f"Cache hit rate: {metrics['session_metrics']['hit_rate']}")
        print(f"Time saved: {metrics['session_metrics']['latency_saved_sec']}")

        return results
```

## 3. Research Pipeline Integration

Add to research agent:

```python
from agi_semantic_cache_integration import AGISemanticCache

class ResearchPipeline:
    def __init__(self):
        # Research cache with medium TTL
        self.research_cache = AGISemanticCache(
            cache_domain="research",
            threshold=0.88,  # Lower threshold for broader matching
            ttl_hours=72     # 3 days
        )

    def research_topic(self, topic: str) -> dict:
        """Research with caching"""
        return self.research_cache.cached_call(
            topic,
            fallback=lambda: self._fetch_and_analyze_papers(topic),
            estimated_fallback_latency_ms=5000  # Research is slow
        )

    def get_insights(self, topic: str) -> list:
        """Get cached insights if available"""
        research_data = self.research_topic(topic)
        return research_data.get("insights", [])
```

## 4. Claude API Wrapper (For External Calls)

Replace Anthropic client with cached version:

```python
# Before:
from anthropic import Anthropic
client = Anthropic()

# After:
from semantic_cache_claude_wrapper import CachedClaudeClient
client = CachedClaudeClient(
    cache_threshold=0.90,
    cache_ttl_hours=24
)

# Use exactly the same as before
response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    messages=[{"role": "user", "content": query}]
)

# Check if cached
if hasattr(response, 'from_cache') and response.from_cache:
    print(f"✓ Served from cache (similarity: {response.cache_similarity:.3f})")

# Periodically check stats
stats = client.get_cache_stats()
print(f"Hit rate: {stats['savings']['cache_hit_rate']}")
```

## 5. Darwin Godel Machine Integration

Add to `/mnt/agentic-system/intelligent-agents/darwin_godel_machine.py`:

```python
from agi_semantic_cache_integration import AGISemanticCache

class DarwinGodelMachine:
    def __init__(self):
        # Cache for self-modification analysis
        self.analysis_cache = AGISemanticCache(
            cache_domain="reasoning",
            threshold=0.95  # Very high precision for safety
        )

    def analyze_modification(self, modification_code: str) -> dict:
        """Analyze self-modification with caching"""
        # Safety-critical - use high threshold
        return self.analysis_cache.cached_call(
            f"safety_analysis:{hash(modification_code)}",
            fallback=lambda: self._detailed_safety_analysis(modification_code),
            estimated_fallback_latency_ms=4000
        )
```

## 6. Auto Implementation Engine

Add to `/mnt/agentic-system/intelligent-agents/auto_implementation_engine.py`:

```python
from agi_semantic_cache_integration import AGISemanticCache

class AutoImplementationEngine:
    def __init__(self):
        # Cache for code generation patterns
        self.code_cache = AGISemanticCache(
            cache_domain="reasoning",
            threshold=0.90
        )

    def generate_implementation(self, spec: str, language: str = "python") -> str:
        """Generate code with pattern caching"""
        cache_key = f"codegen:{language}:{spec}"

        return self.code_cache.cached_call(
            cache_key,
            fallback=lambda: self._generate_code(spec, language),
            estimated_fallback_latency_ms=3000
        )
```

## 7. Monitoring Integration

Add to your monitoring dashboard:

```python
from agi_semantic_cache_integration import AGISemanticCache
import json

def get_all_cache_stats() -> dict:
    """Collect stats from all caches"""

    caches = {
        "reasoning": AGISemanticCache("reasoning"),
        "consolidation": AGISemanticCache("consolidation"),
        "research": AGISemanticCache("research"),
        "api_calls": AGISemanticCache("api_calls"),
    }

    all_stats = {}
    for name, cache in caches.items():
        all_stats[name] = cache.get_metrics()

    # Calculate totals
    total_hits = sum(s['session_metrics']['cache_hits'] for s in all_stats.values())
    total_calls = sum(s['session_metrics']['total_calls'] for s in all_stats.values())
    overall_hit_rate = total_hits / max(1, total_calls)

    all_stats['overall'] = {
        "total_hits": total_hits,
        "total_calls": total_calls,
        "hit_rate": f"{overall_hit_rate:.1%}"
    }

    return all_stats

# Use in monitoring
stats = get_all_cache_stats()
print(json.dumps(stats, indent=2))
```

## 8. Cron Job Setup

Add to weekly maintenance cron:

```bash
# /etc/cron.d/semantic-cache-cleanup
0 3 * * 0 marc cd /mnt/agentic-system/scripts && \
    /mnt/agentic-system/.venv/bin/python3 semantic_cache_module.py cleanup && \
    /mnt/agentic-system/.venv/bin/python3 semantic_cache_module.py stats \
    --export /var/log/cache_stats_$(date +\%Y\%m\%d).json
```

## 9. Testing Integration

Verify cache is working:

```python
def test_cache_integration():
    """Test that caching is working"""
    cache = AGISemanticCache("reasoning")

    # First call - should be cache miss
    start = time.time()
    result1 = cache.cached_call(
        "Test query",
        fallback=lambda: "Test response"
    )
    time1 = (time.time() - start) * 1000

    # Second call - should be cache hit
    start = time.time()
    result2 = cache.cached_call(
        "Test query",
        fallback=lambda: "Test response"
    )
    time2 = (time.time() - start) * 1000

    # Verify
    assert result1 == result2
    assert time2 < time1 / 10  # Should be >10x faster

    metrics = cache.get_metrics()
    assert metrics['session_metrics']['cache_hits'] > 0

    print("✓ Cache integration test passed")
    print(f"  First call: {time1:.1f}ms")
    print(f"  Second call: {time2:.1f}ms")
    print(f"  Speedup: {time1/time2:.1f}x")

test_cache_integration()
```

## 10. Performance Dashboard

Add cache metrics to your dashboard:

```python
def cache_dashboard():
    """Display cache performance dashboard"""
    stats = get_all_cache_stats()

    print("\n" + "="*70)
    print("SEMANTIC CACHE PERFORMANCE DASHBOARD")
    print("="*70)

    print(f"\nOverall Performance:")
    print(f"  Total calls: {stats['overall']['total_calls']}")
    print(f"  Total hits: {stats['overall']['total_hits']}")
    print(f"  Hit rate: {stats['overall']['hit_rate']}")

    print(f"\nBy Domain:")
    for domain, domain_stats in stats.items():
        if domain == 'overall':
            continue
        session = domain_stats['session_metrics']
        print(f"\n  {domain.upper()}:")
        print(f"    Calls: {session['total_calls']}")
        print(f"    Hits: {session['cache_hits']}")
        print(f"    Hit rate: {session['hit_rate']}")
        print(f"    Time saved: {session['latency_saved_sec']}")

    print("\n" + "="*70)

# Run daily
cache_dashboard()
```

## Quick Integration Checklist

- [ ] Import `AGISemanticCache` in your component
- [ ] Create cache instance with appropriate domain
- [ ] Replace expensive calls with `cached_call()`
- [ ] Set appropriate threshold (0.90 recommended)
- [ ] Set appropriate TTL (24h default)
- [ ] Add cache stats to monitoring
- [ ] Test cache effectiveness
- [ ] Set up weekly cleanup cron job

## Performance Tuning

### If hit rate is too low (<20%):
```python
# Lower threshold
cache = AGISemanticCache(cache_domain="reasoning", threshold=0.88)
```

### If getting false positives:
```python
# Raise threshold
cache = AGISemanticCache(cache_domain="reasoning", threshold=0.93)
```

### If cache growing too large:
```python
# Shorter TTL
cache = AGISemanticCache(cache_domain="reasoning", ttl_hours=12)

# Or cleanup more frequently
cache.cache.cleanup()
```

## Done!

Your AGI components now have semantic caching enabled. Monitor hit rates and adjust thresholds as needed.

For more details:
- Read: `README-semantic-cache.md`
- See: `QUICKSTART-semantic-cache.md`
- Review: `SEMANTIC-CACHE-SUMMARY.md`
