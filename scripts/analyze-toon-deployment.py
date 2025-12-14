#!/usr/bin/env python3
"""
System-Wide TOON Deployment Analyzer

Analyzes TOON format usage across the entire agentic system and generates
comprehensive metrics on token savings and deployment status.
"""

import json
from pathlib import Path
from collections import defaultdict

def count_tokens_rough(text: str) -> int:
    """Rough token count estimation"""
    return len(text.split()) + text.count(',') + text.count(':') + text.count('{') + text.count('}')

def analyze_directory(base_path: Path, name: str) -> dict:
    """Analyze TOON usage in a directory"""
    toon_files = list(base_path.rglob('*.toon'))
    json_files = list(base_path.rglob('*.json'))

    # Filter out unwanted paths
    exclude_patterns = ['node_modules', '.venv', 'tests', 'testing', 'data', 'models', 'benchmarks']
    toon_files = [f for f in toon_files if not any(p in str(f) for p in exclude_patterns)]
    json_files = [f for f in json_files if not any(p in str(f) for p in exclude_patterns)]

    # Calculate savings
    total_json_tokens = 0
    total_toon_tokens = 0
    file_comparisons = []

    for toon_file in toon_files:
        json_file = toon_file.with_suffix('.json')
        if json_file.exists():
            try:
                with open(json_file, 'r') as f:
                    json_text = f.read()
                with open(toon_file, 'r') as f:
                    toon_text = f.read()

                json_tokens = count_tokens_rough(json_text)
                toon_tokens = count_tokens_rough(toon_text)

                total_json_tokens += json_tokens
                total_toon_tokens += toon_tokens

                savings = ((json_tokens - toon_tokens) / json_tokens * 100) if json_tokens > 0 else 0
                file_comparisons.append({
                    'file': toon_file.name,
                    'json_tokens': json_tokens,
                    'toon_tokens': toon_tokens,
                    'savings_pct': savings
                })
            except:
                pass

    overall_savings = ((total_json_tokens - total_toon_tokens) / total_json_tokens * 100) if total_json_tokens > 0 else 0

    return {
        'name': name,
        'toon_files': len(toon_files),
        'json_files': len(json_files),
        'toon_coverage': (len(toon_files) / max(len(json_files), 1)) * 100,
        'total_json_tokens': total_json_tokens,
        'total_toon_tokens': total_toon_tokens,
        'tokens_saved': total_json_tokens - total_toon_tokens,
        'savings_pct': overall_savings,
        'file_comparisons': file_comparisons
    }

def main():
    print("╔" + "=" * 60 + "╗")
    print("║" + " " * 10 + "TOON Deployment Analysis" + " " * 27 + "║")
    print("╚" + "=" * 60 + "╝")
    print()

    # Analyze different sections
    sections = {
        'Node Configs': Path.home() / '.claude',
        'Cluster Deployment': Path('/mnt/agentic-system/cluster-deployment'),
        'MCP Servers': Path('/mnt/agentic-system/mcp-servers'),
        'Intelligent Agents': Path('/mnt/agentic-system/intelligent-agents'),
        'Scripts': Path('/mnt/agentic-system/scripts'),
    }

    results = {}
    total_toon_files = 0
    total_json_tokens = 0
    total_toon_tokens = 0

    for name, path in sections.items():
        if path.exists():
            results[name] = analyze_directory(path, name)
            total_toon_files += results[name]['toon_files']
            total_json_tokens += results[name]['total_json_tokens']
            total_toon_tokens += results[name]['total_toon_tokens']

    # Print results
    print("📊 TOON Usage by Section")
    print("━" * 60)
    print()

    for name, result in results.items():
        print(f"  {name}:")
        print(f"    • TOON files: {result['toon_files']}")
        print(f"    • Token savings: {result['savings_pct']:.1f}%")
        print(f"    • Tokens saved: ~{result['tokens_saved']}")
        print()

    # Overall statistics
    total_savings_pct = ((total_json_tokens - total_toon_tokens) / total_json_tokens * 100) if total_json_tokens > 0 else 0

    print("=" * 60)
    print()
    print("📈 Overall System Statistics")
    print("━" * 60)
    print()
    print(f"  Total TOON files:        {total_toon_files}")
    print(f"  Total JSON tokens:       ~{total_json_tokens}")
    print(f"  Total TOON tokens:       ~{total_toon_tokens}")
    print(f"  Total tokens saved:      ~{total_json_tokens - total_toon_tokens}")
    print(f"  Overall savings:         {total_savings_pct:.1f}%")
    print()

    # Top savings
    all_files = []
    for result in results.values():
        all_files.extend(result['file_comparisons'])

    if all_files:
        all_files.sort(key=lambda x: x['savings_pct'], reverse=True)
        print("=" * 60)
        print()
        print("🏆 Top 5 Token Savers")
        print("━" * 60)
        print()
        for i, file in enumerate(all_files[:5], 1):
            print(f"  {i}. {file['file']}")
            print(f"     Savings: {file['savings_pct']:.1f}% ({file['json_tokens']} → {file['toon_tokens']} tokens)")
            print()

    print("=" * 60)
    print()
    print("✅ Analysis complete!")
    print()

    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
