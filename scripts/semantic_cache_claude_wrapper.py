#!/usr/bin/env python3
"""Claude API Wrapper with Semantic Caching

Integrates semantic cache with Claude API calls for automatic speedup.

Usage:
    from semantic_cache_claude_wrapper import CachedClaudeClient

    client = CachedClaudeClient(api_key="your-key")

    # Automatically uses cache
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        messages=[{"role": "user", "content": "Explain binary search"}]
    )

    # Check cache stats
    print(client.get_cache_stats())
"""

import os
import json
import time
from typing import Dict, List, Optional, Any
from anthropic import Anthropic
from semantic_cache_module import SemanticCache


class CachedClaudeClient:
    """Claude API client with transparent semantic caching"""

    def __init__(self,
                 api_key: Optional[str] = None,
                 cache_threshold: float = 0.92,
                 cache_ttl_hours: int = 24,
                 enable_cache: bool = True):
        """
        Initialize cached Claude client

        Args:
            api_key: Anthropic API key (or set ANTHROPIC_API_KEY env var)
            cache_threshold: Similarity threshold for cache hits
            cache_ttl_hours: Cache entry TTL
            enable_cache: Enable/disable caching
        """
        self.client = Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
        self.enable_cache = enable_cache

        if enable_cache:
            self.cache = SemanticCache(
                similarity_threshold=cache_threshold,
                ttl_hours=cache_ttl_hours
            )
        else:
            self.cache = None

        self.call_stats = {
            "cached_calls": 0,
            "api_calls": 0,
            "tokens_saved": 0,
            "latency_saved_ms": 0
        }

    def _extract_user_message(self, messages: List[Dict]) -> str:
        """Extract user message content from messages list"""
        for msg in reversed(messages):  # Get last user message
            if msg["role"] == "user":
                content = msg["content"]
                if isinstance(content, str):
                    return content
                elif isinstance(content, list):
                    # Extract text from content blocks
                    text_parts = [
                        block["text"] for block in content
                        if isinstance(block, dict) and "text" in block
                    ]
                    return " ".join(text_parts)
        return ""

    def _extract_response_text(self, response: Any) -> str:
        """Extract text content from Claude response"""
        if hasattr(response, 'content') and response.content:
            text_parts = [
                block.text for block in response.content
                if hasattr(block, 'text')
            ]
            return " ".join(text_parts)
        return ""

    def _create_cache_key(self, model: str, messages: List[Dict],
                         system: Optional[str] = None,
                         temperature: float = 1.0) -> str:
        """Create cache key from request parameters"""
        user_msg = self._extract_user_message(messages)

        # Include model, system prompt, and temperature in cache key
        key_parts = [user_msg]
        if system:
            key_parts.append(f"[SYS: {system[:100]}]")
        key_parts.append(f"[MODEL: {model}]")
        key_parts.append(f"[TEMP: {temperature}]")

        return " ".join(key_parts)

    class Messages:
        """Messages API with caching"""

        def __init__(self, parent):
            self.parent = parent

        def create(self, model: str, messages: List[Dict],
                  system: Optional[str] = None,
                  max_tokens: int = 4096,
                  temperature: float = 1.0,
                  **kwargs) -> Any:
            """
            Create Claude message with transparent caching

            Args:
                model: Model identifier
                messages: List of message dicts
                system: System prompt
                max_tokens: Maximum tokens to generate
                temperature: Sampling temperature
                **kwargs: Additional Claude API parameters

            Returns:
                Claude API response object (with .from_cache attribute added)
            """
            # Check cache if enabled
            if self.parent.enable_cache:
                cache_key = self.parent._create_cache_key(
                    model, messages, system, temperature
                )

                cached_result = self.parent.cache.get(cache_key)
                if cached_result:
                    cached_text, similarity = cached_result

                    # Reconstruct response-like object
                    class CachedResponse:
                        def __init__(self, text, similarity):
                            self.content = [type('obj', (object,), {'text': text})]
                            self.from_cache = True
                            self.cache_similarity = similarity
                            self.model = model
                            self.usage = type('obj', (object,), {
                                'input_tokens': 0,
                                'output_tokens': 0
                            })

                    self.parent.call_stats["cached_calls"] += 1
                    self.parent.call_stats["latency_saved_ms"] += 2000  # Avg API latency

                    # Estimate tokens saved (rough approximation)
                    tokens_saved = len(cached_text.split()) * 1.3
                    self.parent.call_stats["tokens_saved"] += int(tokens_saved)

                    return CachedResponse(cached_text, similarity)

            # Cache miss - make API call
            start_time = time.time()

            response = self.parent.client.messages.create(
                model=model,
                messages=messages,
                system=system,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )

            api_latency = (time.time() - start_time) * 1000

            # Store in cache
            if self.parent.enable_cache:
                response_text = self.parent._extract_response_text(response)
                cache_key = self.parent._create_cache_key(
                    model, messages, system, temperature
                )
                self.parent.cache.store(
                    cache_key,
                    response_text,
                    metadata={
                        "model": model,
                        "temperature": temperature,
                        "api_latency_ms": api_latency
                    }
                )

            response.from_cache = False
            self.parent.call_stats["api_calls"] += 1

            return response

    @property
    def messages(self):
        """Access Messages API"""
        return self.Messages(self)

    def get_cache_stats(self) -> Dict:
        """Get combined cache and API call statistics"""
        stats = {
            "call_stats": self.call_stats.copy(),
            "cache_enabled": self.enable_cache
        }

        if self.enable_cache:
            stats["cache_stats"] = self.cache.get_stats()

            # Calculate savings
            total_calls = self.call_stats["cached_calls"] + self.call_stats["api_calls"]
            if total_calls > 0:
                stats["savings"] = {
                    "cache_hit_rate": f"{self.call_stats['cached_calls'] / total_calls:.1%}",
                    "estimated_cost_saved": f"${self.call_stats['tokens_saved'] * 0.000003:.4f}",
                    "latency_saved_sec": f"{self.call_stats['latency_saved_ms'] / 1000:.1f}s"
                }

        return stats

    def clear_cache(self):
        """Clear all cache entries"""
        if self.enable_cache:
            deleted = self.cache.cleanup(force=True)
            return {"deleted": deleted}
        return {"deleted": 0}


# Example usage
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Cached Claude API Demo")
    parser.add_argument("--query", type=str, help="Query to send")
    parser.add_argument("--stats", action="store_true", help="Show stats only")
    parser.add_argument("--clear", action="store_true", help="Clear cache")

    args = parser.parse_args()

    # Initialize client
    client = CachedClaudeClient()

    if args.clear:
        result = client.clear_cache()
        print(f"Cleared {result['deleted']} cache entries")
        exit(0)

    if args.stats:
        print(json.dumps(client.get_cache_stats(), indent=2))
        exit(0)

    if args.query:
        print(f"\nQuery: {args.query}\n")

        # Make request
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            messages=[{"role": "user", "content": args.query}],
            max_tokens=500
        )

        # Print response
        if response.from_cache:
            print(f"[CACHED - Similarity: {response.cache_similarity:.4f}]")
        else:
            print("[API CALL]")

        print(f"\n{response.content[0].text}\n")

        # Show stats
        print("\n" + "="*60)
        print(json.dumps(client.get_cache_stats(), indent=2))
    else:
        print("Use --query to send a query, --stats to view statistics, or --clear to clear cache")
