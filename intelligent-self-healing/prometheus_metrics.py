"""
Claude Code metrics client for statusline
Queries Claude Code's own metrics endpoint (port 9464)

This provides ACCURATE session-level data directly from Claude Code.
For weekly usage, users should use /usage command in Claude Code.
"""

import requests
import re
from typing import Dict, Optional, Any

class ClaudeCodeMetricsClient:
    def __init__(self, metrics_url: str = "http://127.0.0.1:9464/metrics"):
        self.metrics_url = metrics_url

    def _parse_prometheus_text(self, text: str) -> Dict[str, list]:
        """Parse Prometheus text format metrics"""
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

    def get_session_usage(self) -> Optional[Dict[str, Any]]:
        """Get current session usage from Claude Code's own metrics

        Queries Claude Code's metrics endpoint (port 9464) for accurate session data:
        - Session cost (USD)
        - Session tokens (input, output, cache)
        - Session context size (toward 200k limit)

        This is THE authoritative source for current session metrics.
        """
        try:
            response = requests.get(self.metrics_url, timeout=2)
            if response.status_code != 200:
                return None

            metrics = self._parse_prometheus_text(response.text)

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
            # Note: This is cumulative for the session, NOT sliding window
            session_context = int(
                tokens_by_type.get('input', 0) +
                tokens_by_type.get('output', 0) +
                tokens_by_type.get('cacheCreation', 0)
            )

            session_pct = min(int((session_context / 200000) * 100), 999)  # Cap at 999%

            return {
                'source': 'claude_code_metrics',
                'cost_usd': round(total_cost, 4),
                'context_tokens': session_context,
                'context_pct': session_pct,
                'cache_read_tokens': int(tokens_by_type.get('cacheRead', 0))
            }

        except Exception:
            return None

    def get_weekly_usage(self) -> Optional[Dict[str, Any]]:
        """Get weekly usage information

        NOTE: Claude Code's metrics endpoint does NOT provide weekly usage data.
        Weekly usage comes from Anthropic's API and is only accessible via
        Claude Code's /usage command.

        Returns None to indicate weekly data is not available.
        """
        # Weekly usage requires Anthropic API access
        # Users should use /usage command in Claude Code
        return None

    def get_usage_metrics(self) -> Dict[str, Optional[Dict[str, Any]]]:
        """Get all available usage metrics"""
        return {
            'session': self.get_session_usage(),
            'weekly': self.get_weekly_usage()
        }

def get_prometheus_usage() -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Get usage metrics from Claude Code's own metrics endpoint
    Returns dict with 'session' and 'weekly' keys

    Session data comes from Claude Code's port 9464 metrics endpoint.
    Weekly data is not available (use /usage command).
    """
    client = ClaudeCodeMetricsClient()
    return client.get_usage_metrics()

if __name__ == "__main__":
    # Test the client
    import json
    metrics = get_prometheus_usage()
    print(json.dumps(metrics, indent=2))

    session = metrics.get('session')
    if session:
        print()
        print(f"Session Cost: ${session['cost_usd']:.4f}")
        print(f"Session Context: {session['context_tokens']:,} tokens ({session['context_pct']}%)")
        print(f"Cache Reads: {session['cache_read_tokens']:,} tokens")
