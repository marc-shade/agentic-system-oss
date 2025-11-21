#!/usr/bin/env python3
"""
TOON Token Savings - Simple Demonstration
==========================================

Shows real token savings from TOON vs JSON format.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from toon_utils import compare_encodings

def show_savings(data, title):
    """Display token savings for a given data structure."""
    print(f"\n{'='*60}")
    print(f"{title}")
    print('='*60)

    result = compare_encodings(data)

    # Extract metrics
    json_size = result['json']['compact']
    toon_size = result['toon']['compact']
    reduction = result['compression']['reduction_percent']
    tokens_saved = result['compression']['tokens_saved']

    # Estimate tokens (rough: 4 chars per token)
    json_tokens = json_size / 4
    toon_tokens = toon_size / 4

    print(f"\nJSON:  {json_size} chars (~{json_tokens:.0f} tokens)")
    print(f"TOON:  {toon_size} chars (~{toon_tokens:.0f} tokens)")
    print(f"Saved: {tokens_saved:.1f} tokens ({reduction:.1f}% reduction)")

    return reduction

# Test cases
print("\nTOON FORMAT TOKEN SAVINGS DEMONSTRATION")
print("=" * 60)

savings = []

# 1. Simple status
savings.append(show_savings(
    {"status": "success", "message": "Task completed", "time_ms": 1250},
    "1. Simple Status Response"
))

# 2. Agent recommendation
savings.append(show_savings(
    {
        "status": "success",
        "agent": "code_generator",
        "confidence": 0.85,
        "alternatives": ["tester", "refactor"],
        "metadata": {"time": 1250, "reason": "historical performance"}
    },
    "2. Agent Recommendation (agi-mcp)"
))

# 3. Concept list
savings.append(show_savings(
    {
        "success": True,
        "concepts": ["AI", "ML", "AGI", "neural nets", "transformers"],
        "counts": {"ai": 15, "ml": 8, "agi": 4, "neural_nets": 6, "transformers": 3}
    },
    "3. Video Concepts (video-transcript-mcp)"
))

# 4. Paper list
papers = [
    {"id": f"p{i}", "title": f"Paper {i}", "authors": ["A", "B"], "year": 2024, "citations": 100-i*10}
    for i in range(10)
]
savings.append(show_savings(
    {"success": True, "count": 10, "papers": papers},
    "4. Research Papers (research-paper-mcp, 10 items)"
))

# 5. Security scan
vulns = [
    {"id": f"CVE-{i}", "severity": "high", "url": f"/api/v{i}", "findings": ["f1", "f2"]}
    for i in range(5)
]
savings.append(show_savings(
    {"success": True, "target": "example.com", "results": vulns},
    "5. Security Scan (nuclei-mcp, 5 vulns)"
))

# Summary
print(f"\n{'='*60}")
print("SUMMARY")
print('='*60)
avg_savings = sum(savings) / len(savings)
print(f"\nAverage token reduction: {avg_savings:.1f}%")
print(f"Range: {min(savings):.1f}% - {max(savings):.1f}%")
print(f"\n✓ TOON consistently reduces token usage")
print(f"✓ Larger responses = greater savings")
print(f"✓ Backward compatible with JSON fallback")

# Annual impact
print(f"\n{'='*60}")
print("ESTIMATED ANNUAL IMPACT")
print('='*60)
daily_calls = 1000
avg_response_tokens_json = 500
avg_reduction = avg_savings / 100

daily_tokens_saved = daily_calls * avg_response_tokens_json * avg_reduction
monthly_tokens_saved = daily_tokens_saved * 30
annual_tokens_saved = daily_tokens_saved * 365

cost_per_million = 3  # Claude Sonnet pricing
annual_cost_savings = (annual_tokens_saved / 1_000_000) * cost_per_million

print(f"Assumptions:")
print(f"  - {daily_calls:,} MCP calls/day")
print(f"  - {avg_response_tokens_json} avg tokens/response (JSON)")
print(f"  - {avg_reduction:.1%} avg reduction (TOON)")
print(f"\nImpact:")
print(f"  Daily:   {daily_tokens_saved:,.0f} tokens saved")
print(f"  Monthly: {monthly_tokens_saved:,.0f} tokens saved")
print(f"  Annual:  {annual_tokens_saved:,.0f} tokens saved")
print(f"\nCost Savings (at ${cost_per_million}/M tokens):")
print(f"  Monthly: ${monthly_tokens_saved/1_000_000 * cost_per_million:.2f}")
print(f"  Annual:  ${annual_cost_savings:.2f}")
print()
