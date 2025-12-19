#!/usr/bin/env python3
"""
Post-Tool-Use Hook - Integrated with Ember and Arduino
Runs actions AFTER tool execution

Integrations:
- Ember auto-care (feed/play/clean/pet)
- Arduino feedback (LED + LCD)
- Behavioral learning
- Operation logging

Version: 2.0 - Unified Hook Orchestrator
"""

import json
import sys
from pathlib import Path

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from unified_hook_orchestrator import run_post_tool_actions
    ORCHESTRATOR_AVAILABLE = True
except Exception as e:
    print(f"WARNING: Hook orchestrator unavailable: {e}", file=sys.stderr)
    ORCHESTRATOR_AVAILABLE = False

def fallback_logging(input_data):
    """
    Fallback behavior if orchestrator unavailable
    Just logs to file
    """
    try:
        session_id = input_data.get('session_id', 'unknown')
        log_dir = Path.home() / '.claude' / 'sessions' / session_id
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / 'post_tool_use.json'

        # Read existing log data or initialize empty list
        if log_path.exists():
            with open(log_path, 'r') as f:
                try:
                    log_data = json.load(f)
                except (json.JSONDecodeError, ValueError):
                    log_data = []
        else:
            log_data = []

        # Append new data
        log_data.append(input_data)

        # Write back to file with formatting
        with open(log_path, 'w') as f:
            json.dump(log_data, f, indent=2)

    except Exception:
        pass  # Fail silently

def main():
    try:
        # Read JSON input from stdin
        input_data = json.load(sys.stdin)

        if not ORCHESTRATOR_AVAILABLE:
            # Fallback: Just log
            fallback_logging(input_data)
            sys.exit(0)

        # Convert to orchestrator format
        hook_input = {
            "tool": input_data.get('tool_name', ''),
            "arguments": input_data.get('tool_input', {}),
            "session_id": input_data.get('session_id', 'unknown'),
            "success": input_data.get('success', True)
        }

        # Run all post-tool actions (async, never blocks)
        run_post_tool_actions(hook_input)

        # Save to enhanced memory (non-blocking)
        try:
            sys.path.insert(0, str(Path.home() / ".claude" / "hooks"))
            from memory_integration import save_tool_memory

            save_tool_memory(
                session_id=hook_input['session_id'],
                tool_name=hook_input['tool'],
                tool_input=hook_input['arguments'],
                success=hook_input['success']
            )
        except Exception as memory_err:
            # Fail silently - don't block tool execution
            print(f"Memory save warning: {memory_err}", file=sys.stderr)

        # Also do fallback logging
        fallback_logging(input_data)

        # Always succeed (post-tool-use should never block)
        sys.exit(0)

    except json.JSONDecodeError:
        # Invalid JSON, exit gracefully
        sys.exit(0)
    except Exception as e:
        # Unexpected error, log and exit gracefully
        print(f"Post-tool hook error: {e}", file=sys.stderr)
        sys.exit(0)

if __name__ == '__main__':
    main()
