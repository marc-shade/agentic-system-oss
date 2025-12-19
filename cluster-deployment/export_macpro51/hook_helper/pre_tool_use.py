#!/usr/bin/env python3
"""
Pre-Tool-Use Hook - Integrated with Ember and Arduino
Runs checks BEFORE tool execution

Integrations:
- Danger detection (rm -rf, .env access)
- Ember violation checks (production-only policy)
- Arduino pre-operation display

Version: 2.0 - Unified Hook Orchestrator
"""

import json
import sys
from pathlib import Path

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from unified_hook_orchestrator import run_pre_tool_checks
    ORCHESTRATOR_AVAILABLE = True
except Exception as e:
    print(f"WARNING: Hook orchestrator unavailable: {e}", file=sys.stderr)
    ORCHESTRATOR_AVAILABLE = False

def main():
    try:
        # Read JSON input from stdin
        input_data = json.load(sys.stdin)

        if not ORCHESTRATOR_AVAILABLE:
            # Fallback: Basic safety checks only
            tool_name = input_data.get('tool_name', '')
            tool_input = input_data.get('tool_input', {})

            # Basic rm -rf check
            if tool_name == 'Bash':
                command = tool_input.get('command', '')
                if 'rm' in command and '-rf' in command and ('/' in command or '/home/marc' in command):
                    print("BLOCKED: Dangerous rm -rf command", file=sys.stderr)
                    sys.exit(2)

            # Allow execution
            sys.exit(0)

        # Convert to orchestrator format
        hook_input = {
            "tool": input_data.get('tool_name', ''),
            "arguments": input_data.get('tool_input', {}),
            "session_id": input_data.get('session_id', 'unknown')
        }

        # Run all pre-tool checks
        result = run_pre_tool_checks(hook_input)

        if result["allow"]:
            # Allow execution
            sys.exit(0)
        else:
            # Block execution and show error
            error_msg = result.get("error", "Operation blocked by hook")
            print(error_msg, file=sys.stderr)

            # Provide additional context if available
            if "violation" in result:
                violation = result["violation"]
                print(f"Violation type: {violation.get('type', 'unknown')}", file=sys.stderr)
                print(f"Severity: {violation.get('severity', 'unknown')}", file=sys.stderr)

            sys.exit(2)  # Exit code 2 blocks tool call

    except json.JSONDecodeError:
        # Invalid JSON, allow execution
        sys.exit(0)
    except Exception as e:
        # Unexpected error, log and allow execution (fail open)
        print(f"Pre-tool hook error: {e}", file=sys.stderr)
        sys.exit(0)

if __name__ == '__main__':
    main()
