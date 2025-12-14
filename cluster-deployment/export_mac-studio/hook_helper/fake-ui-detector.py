#!/usr/bin/env python3
"""
Fake UI Detector Hook
Enforces "See Something, Say Something" policy for production code
Scans for fake/placeholder UI elements and blocks operations if found
"""

import json
import sys
import re
from pathlib import Path

# Patterns that indicate fake/placeholder UI
FAKE_UI_PATTERNS = [
    # Hardcoded fake data
    r"Cristina\s+danny",
    r"Aida\s+Burg",
    r"Lorem\s+ipsum",
    r"John\s+Doe",
    r"jane\.doe@",
    r"test@test\.",
    r"example@example\.",

    # Common placeholder text
    r"Your\s+Profile\s+is\s+Complete.*60%",
    r"It's.*birthday\s+today",
    r"commented\s+your\s+post",
    r"invited\s+to\s+join\s+Meeting",

    # Fake timestamps
    r"2\s+min\s+ago",
    r"5\s+August",
    r"7\s+hours\s+ago",

    # Static/fake functionality indicators
    r"TODO:|FIXME:|XXX:|HACK:",
    r"console\.log\(['\"]test",
    r"return\s+\[\];?\s*//\s*temporary",
    r"setTimeout\(\(\)\s*=>\s*\{[^}]*\},\s*\d+\);\s*//\s*fake",

    # Mock API responses
    r"mockData|dummyData|fakeData|testData",
    r"status:\s*['\"]success['\"].*//\s*mock",

    # Non-functional buttons
    r"onClick=\{.*=>\s*\{\s*\}\}",
    r"handleClick.*{\s*//\s*TODO",
    r"alert\(['\"]Not\s+implemented",
]

EXCLUDED_PATHS = [
    "node_modules",
    ".git",
    "build",
    "dist",
    "__pycache__",
    "*.test.js",
    "*.spec.js",
    "*.test.tsx",
    "*.spec.tsx",
]

def scan_file(filepath):
    """Scan a single file for fake UI patterns"""
    violations = []

    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = content.splitlines()

            for i, line in enumerate(lines, 1):
                for pattern in FAKE_UI_PATTERNS:
                    if re.search(pattern, line, re.IGNORECASE):
                        violations.append({
                            'file': str(filepath),
                            'line': i,
                            'pattern': pattern,
                            'content': line.strip()
                        })
    except Exception:
        pass  # Skip files that can't be read

    return violations

def should_scan_file(filepath):
    """Check if file should be scanned"""
    path_str = str(filepath)

    # Skip excluded paths
    for excluded in EXCLUDED_PATHS:
        if excluded in path_str:
            return False

    # Only scan relevant file types
    extensions = ['.js', '.jsx', '.ts', '.tsx', '.vue', '.html']
    return any(path_str.endswith(ext) for ext in extensions)

def scan_directory(directory):
    """Recursively scan directory for fake UI"""
    all_violations = []
    path = Path(directory)

    if not path.exists():
        return all_violations

    for filepath in path.rglob('*'):
        if filepath.is_file() and should_scan_file(filepath):
            violations = scan_file(filepath)
            all_violations.extend(violations)

    return all_violations

def main():
    """Main hook execution"""
    # Get the current working directory or specific path
    scan_path = sys.argv[1] if len(sys.argv) > 1 else '.'

    # Skip if explicitly disabled
    if os.environ.get('SKIP_FAKE_UI_CHECK') == 'true':
        return 0

    # Scan for violations
    violations = scan_directory(scan_path)

    if violations:
        print("\n" + "="*80)
        print("🚨 FAKE UI DETECTED - SEE SOMETHING, SAY SOMETHING 🚨")
        print("="*80)
        print(f"\nFound {len(violations)} fake/placeholder UI element(s):\n")

        # Group by file
        by_file = {}
        for v in violations:
            if v['file'] not in by_file:
                by_file[v['file']] = []
            by_file[v['file']].append(v)

        # Display violations
        for filepath, file_violations in by_file.items():
            print(f"\n📁 {filepath}")
            for v in file_violations[:5]:  # Show max 5 per file
                print(f"  Line {v['line']}: {v['content'][:80]}...")
            if len(file_violations) > 5:
                print(f"  ... and {len(file_violations) - 5} more")

        print("\n" + "="*80)
        print("⚠️  ACTION REQUIRED:")
        print("1. Fix all fake UI elements immediately")
        print("2. Replace with real, functional implementations")
        print("3. No placeholders, no mock data, no 'TODO' functionality")
        print("="*80 + "\n")

        # Write report
        report_path = Path.home() / '.claude' / 'fake-ui-report.json'
        report_path.parent.mkdir(exist_ok=True)
        with open(report_path, 'w') as f:
            json.dump({
                'timestamp': __import__('datetime').datetime.now().isoformat(),
                'violations_count': len(violations),
                'violations': violations[:100]  # Limit to 100 for performance
            }, f, indent=2)

        return 1  # Block operation

    return 0

if __name__ == '__main__':
    import os
    sys.exit(main())