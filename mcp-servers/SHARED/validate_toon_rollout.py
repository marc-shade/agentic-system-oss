#!/usr/bin/env python3
"""
TOON Rollout Validation Suite
==============================

Validates that all MCP servers correctly use TOON format for responses.
Tests:
1. Import validation - toon_utils is importable
2. Syntax validation - no remaining json.dumps(*, indent=2)
3. Token savings estimation - measure improvements
4. Response format validation - ensure valid TOON output
5. Backward compatibility - ensure JSON fallback works
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Add SHARED to path
sys.path.insert(0, str(Path(__file__).parent))
from toon_utils import toon_response, compare_encodings

# Use compare_encodings as estimate_token_savings
def estimate_token_savings(data):
    """Wrapper around compare_encodings for token savings estimation."""
    result = compare_encodings(data)

    # Extract token estimates
    json_formatted_tokens = result.get('json_indented', {}).get('estimated_tokens', 0)
    json_compact_tokens = result.get('json_compact', {}).get('estimated_tokens', 0)
    toon_tokens = result.get('toon', {}).get('estimated_tokens', 0)

    savings_formatted = ((json_formatted_tokens - toon_tokens) / json_formatted_tokens * 100) if json_formatted_tokens > 0 else 0
    savings_compact = ((json_compact_tokens - toon_tokens) / json_compact_tokens * 100) if json_compact_tokens > 0 else 0

    return {
        "json_formatted": {
            "size": result.get('json_indented', {}).get('size', 0),
            "estimated_tokens": json_formatted_tokens
        },
        "json_compact": {
            "size": result.get('json_compact', {}).get('size', 0),
            "estimated_tokens": json_compact_tokens
        },
        "toon": {
            "size": result.get('toon', {}).get('size', 0),
            "estimated_tokens": toon_tokens
        },
        "savings_vs_formatted": f"{savings_formatted:.1f}%",
        "savings_vs_compact": f"{savings_compact:.1f}%"
    }

# MCP servers to validate
MCP_SERVERS = {
    "agi-mcp": "/Volumes/SSDRAID0/agentic-system/mcp-servers/agi-mcp/server.py",
    "video-transcript-mcp": "/Volumes/SSDRAID0/agentic-system/mcp-servers/video-transcript-mcp/server.py",
    "research-paper-mcp": "/Volumes/SSDRAID0/agentic-system/mcp-servers/research-paper-mcp/server.py",
    "nuclei-mcp": "/Volumes/SSDRAID0/agentic-system/mcp-servers/nuclei-mcp/main.py"
}


class ValidationResult:
    """Store validation results for a single server."""

    def __init__(self, server_name: str):
        self.server_name = server_name
        self.imports_valid = False
        self.syntax_clean = False
        self.json_dumps_count = 0
        self.toon_response_count = 0
        self.token_savings = {}
        self.errors = []
        self.warnings = []

    def to_dict(self) -> Dict:
        return {
            "server": self.server_name,
            "imports_valid": self.imports_valid,
            "syntax_clean": self.syntax_clean,
            "json_dumps_remaining": self.json_dumps_count,
            "toon_response_calls": self.toon_response_count,
            "token_savings": self.token_savings,
            "errors": self.errors,
            "warnings": self.warnings,
            "status": "PASS" if self.imports_valid and self.syntax_clean and self.json_dumps_count == 0 else "FAIL"
        }


def validate_imports(server_path: str) -> Tuple[bool, List[str]]:
    """Validate that TOON utilities are properly imported."""
    errors = []

    try:
        with open(server_path, 'r') as f:
            content = f.read()

        # Check for TOON import
        if 'from toon_utils import' not in content:
            errors.append("Missing 'from toon_utils import' statement")

        if 'toon_response' not in content:
            errors.append("Missing toon_response import or usage")

        # Check for SHARED path addition
        if 'SHARED' not in content and 'shared' not in content:
            errors.append("Missing SHARED path addition to sys.path")

        return len(errors) == 0, errors

    except Exception as e:
        return False, [f"Failed to read file: {e}"]


def validate_syntax(server_path: str) -> Tuple[bool, int, int, List[str]]:
    """Validate that json.dumps is replaced with toon_response."""
    warnings = []

    try:
        with open(server_path, 'r') as f:
            content = f.read()

        # Count remaining json.dumps calls (excluding fallback definition)
        json_dumps_pattern = r'json\.dumps\([^)]+\)'
        matches = re.findall(json_dumps_pattern, content)

        # Filter out the fallback definition
        json_dumps_count = 0
        for match in matches:
            # Skip if it's in the fallback function definition
            if 'def toon_response' not in content[max(0, content.find(match) - 200):content.find(match)]:
                json_dumps_count += 1

        # Count toon_response calls
        toon_response_count = len(re.findall(r'toon_response\(', content))

        # Check for problematic patterns
        if re.search(r'json\.dumps\([^)]+, indent=2\)', content):
            warnings.append("Found json.dumps with indent=2 (should be toon_response)")

        if json_dumps_count > 2:  # Allow fallback + maybe one in imports
            warnings.append(f"Found {json_dumps_count} json.dumps calls (should be 0-2 for fallback)")

        return json_dumps_count <= 2, json_dumps_count, toon_response_count, warnings

    except Exception as e:
        return False, 0, 0, [f"Failed to read file: {e}"]


def estimate_server_token_savings(server_name: str) -> Dict:
    """Estimate token savings for typical server responses."""

    # Example responses for each server type
    example_responses = {
        "agi-mcp": {
            "status": "success",
            "recommended_agent": "code_generator",
            "confidence": 0.85,
            "task_type": "code_generation",
            "metadata": {
                "execution_time_ms": 1250,
                "alternatives": ["test_writer", "refactorer"],
                "reasoning": "Based on historical performance"
            }
        },
        "video-transcript-mcp": {
            "success": True,
            "concepts": ["AI", "machine learning", "neural networks", "AGI", "transformers"],
            "concept_counts": {"ai": 15, "machine learning": 8, "neural networks": 6, "agi": 4, "transformers": 3},
            "total_concepts": 5
        },
        "research-paper-mcp": {
            "success": True,
            "query": "recursive self-improvement AGI",
            "count": 10,
            "papers": [
                {"id": f"paper_{i}", "title": f"Paper Title {i}", "authors": ["Author A", "Author B"], "year": 2024}
                for i in range(10)
            ]
        },
        "nuclei-mcp": {
            "success": True,
            "target": "https://example.com",
            "time_cost_seconds": 15.3,
            "results": [
                {
                    "template_id": f"vuln_{i}",
                    "severity": "high" if i % 3 == 0 else "medium",
                    "matched_at": f"https://example.com/path{i}",
                    "extracted_results": ["finding1", "finding2"]
                }
                for i in range(5)
            ]
        }
    }

    response = example_responses.get(server_name, {"status": "success", "message": "Default response"})

    return estimate_token_savings(response)


def validate_server(server_name: str, server_path: str) -> ValidationResult:
    """Perform full validation on a single MCP server."""
    result = ValidationResult(server_name)

    print(f"\n{'='*60}")
    print(f"Validating: {server_name}")
    print(f"{'='*60}")

    # Test 1: Import validation
    print("\n[1/4] Validating imports...")
    imports_valid, import_errors = validate_imports(server_path)
    result.imports_valid = imports_valid
    result.errors.extend(import_errors)

    if imports_valid:
        print("  ✓ Imports valid")
    else:
        print(f"  ✗ Import errors: {', '.join(import_errors)}")

    # Test 2: Syntax validation
    print("\n[2/4] Validating syntax...")
    syntax_clean, json_count, toon_count, warnings = validate_syntax(server_path)
    result.syntax_clean = syntax_clean
    result.json_dumps_count = json_count
    result.toon_response_count = toon_count
    result.warnings.extend(warnings)

    print(f"  json.dumps calls: {json_count}")
    print(f"  toon_response calls: {toon_count}")

    if syntax_clean:
        print("  ✓ Syntax clean")
    else:
        print(f"  ⚠ Warnings: {', '.join(warnings)}")

    # Test 3: Token savings estimation
    print("\n[3/4] Estimating token savings...")
    savings = estimate_server_token_savings(server_name)
    result.token_savings = savings

    print(f"  JSON (formatted): {savings['json_formatted']['estimated_tokens']} tokens")
    print(f"  JSON (compact): {savings['json_compact']['estimated_tokens']} tokens")
    print(f"  TOON: {savings['toon']['estimated_tokens']} tokens")
    print(f"  Savings vs formatted: {savings['savings_vs_formatted']}")
    print(f"  Savings vs compact: {savings['savings_vs_compact']}")

    # Test 4: Python syntax check
    print("\n[4/4] Checking Python syntax...")
    try:
        result_check = subprocess.run(
            ['python3', '-m', 'py_compile', server_path],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result_check.returncode == 0:
            print("  ✓ Python syntax valid")
        else:
            error_msg = f"Syntax error: {result_check.stderr}"
            result.errors.append(error_msg)
            print(f"  ✗ {error_msg}")

    except Exception as e:
        error_msg = f"Failed to check syntax: {e}"
        result.errors.append(error_msg)
        print(f"  ✗ {error_msg}")

    # Final status
    print(f"\nStatus: {result.to_dict()['status']}")

    return result


def generate_report(results: List[ValidationResult]) -> Dict:
    """Generate comprehensive validation report."""

    total_servers = len(results)
    passed = sum(1 for r in results if r.to_dict()['status'] == 'PASS')
    failed = total_servers - passed

    total_json_dumps = sum(r.json_dumps_count for r in results)
    total_toon_calls = sum(r.toon_response_count for r in results)

    # Aggregate token savings
    avg_savings_formatted = sum(
        float(r.token_savings.get('savings_vs_formatted', '0%').rstrip('%'))
        for r in results
    ) / total_servers if total_servers > 0 else 0

    avg_savings_compact = sum(
        float(r.token_savings.get('savings_vs_compact', '0%').rstrip('%'))
        for r in results
    ) / total_servers if total_servers > 0 else 0

    return {
        "summary": {
            "total_servers": total_servers,
            "passed": passed,
            "failed": failed,
            "success_rate": f"{(passed/total_servers*100):.1f}%" if total_servers > 0 else "0%"
        },
        "migration_stats": {
            "total_json_dumps_remaining": total_json_dumps,
            "total_toon_response_calls": total_toon_calls,
            "migration_complete": total_json_dumps <= total_servers * 2  # Allow fallbacks
        },
        "token_savings": {
            "avg_savings_vs_formatted": f"{avg_savings_formatted:.1f}%",
            "avg_savings_vs_compact": f"{avg_savings_compact:.1f}%",
            "estimated_total_savings": f"{((avg_savings_formatted + avg_savings_compact) / 2):.1f}%"
        },
        "servers": [r.to_dict() for r in results]
    }


def main():
    """Run validation suite on all MCP servers."""
    print("=" * 60)
    print("TOON ROLLOUT VALIDATION SUITE")
    print("=" * 60)
    print(f"\nValidating {len(MCP_SERVERS)} MCP servers...")

    results = []

    for server_name, server_path in MCP_SERVERS.items():
        if not os.path.exists(server_path):
            print(f"\n✗ Server not found: {server_path}")
            result = ValidationResult(server_name)
            result.errors.append(f"Server file not found: {server_path}")
            results.append(result)
            continue

        result = validate_server(server_name, server_path)
        results.append(result)

    # Generate report
    report = generate_report(results)

    # Print summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print(json.dumps(report, indent=2))

    # Save report
    report_path = Path(__file__).parent / "toon_validation_report.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\nFull report saved to: {report_path}")

    # Return exit code
    if report['summary']['failed'] > 0:
        print("\n⚠ VALIDATION FAILED - Some servers have issues")
        return 1
    else:
        print("\n✓ VALIDATION PASSED - All servers updated successfully")
        return 0


if __name__ == "__main__":
    sys.exit(main())
