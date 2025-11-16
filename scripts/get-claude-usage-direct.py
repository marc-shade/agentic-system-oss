#!/usr/bin/env python3
"""
Query Claude Code's own metrics endpoint for accurate usage data

Claude Code exposes Prometheus metrics on port 9464 with:
- claude_code_cost_usage_total (in USD)
- claude_code_token_usage_total (by type and model)
- Session-specific metrics

This is THE authoritative source for this Claude Code session's usage.
"""

import requests
import re
import json
from pathlib import Path

def parse_prometheus_metrics(text):
    """Parse Prometheus text format"""
    metrics = {}

    for line in text.split('\n'):
        # Skip comments and empty lines
        if line.startswith('#') or not line.strip():
            continue

        # Parse metric line: metric_name{labels} value
        match = re.match(r'([a-z_]+)\{([^}]+)\}\s+(.+)', line)
        if match:
            metric_name = match.group(1)
            labels_str = match.group(2)
            value = float(match.group(3))

            # Parse labels
            labels = {}
            for label_pair in labels_str.split(','):
                key, val = label_pair.split('=', 1)
                labels[key.strip()] = val.strip('"')

            if metric_name not in metrics:
                metrics[metric_name] = []

            metrics[metric_name].append({
                'labels': labels,
                'value': value
            })

    return metrics

def get_claude_code_usage():
    """Get usage from Claude Code's own metrics endpoint"""
    try:
        response = requests.get('http://localhost:9464/metrics', timeout=2)
        if response.status_code != 200:
            return None

        metrics = parse_prometheus_metrics(response.text)

        # Get cost total (sum across all models for current session)
        cost_metrics = metrics.get('claude_code_cost_usage_total', [])
        total_cost = sum(m['value'] for m in cost_metrics)

        # Get token counts
        token_metrics = metrics.get('claude_code_token_usage_total', [])

        tokens_by_type = {}
        for m in token_metrics:
            token_type = m['labels'].get('type')
            tokens_by_type[token_type] = tokens_by_type.get(token_type, 0) + m['value']

        # Calculate session context (toward 200k limit)
        session_context = int(
            tokens_by_type.get('input', 0) +
            tokens_by_type.get('output', 0) +
            tokens_by_type.get('cacheCreation', 0)
        )

        session_pct = int((session_context / 200000) * 100)

        return {
            'source': 'claude_code_metrics',
            'cost_usd': round(total_cost, 4),
            'session_context_tokens': session_context,
            'session_context_pct': session_pct,
            'tokens': {
                'input': int(tokens_by_type.get('input', 0)),
                'output': int(tokens_by_type.get('output', 0)),
                'cache_creation': int(tokens_by_type.get('cacheCreation', 0)),
                'cache_read': int(tokens_by_type.get('cacheRead', 0))
            }
        }

    except Exception as e:
        return None

if __name__ == '__main__':
    usage = get_claude_code_usage()
    if usage:
        print(json.dumps(usage, indent=2))
        print()
        print(f"Session Cost: ${usage['cost_usd']:.4f}")
        print(f"Session Context: {usage['session_context_tokens']:,} tokens ({usage['session_context_pct']}%)")
    else:
        print("Could not retrieve usage from Claude Code metrics endpoint")
