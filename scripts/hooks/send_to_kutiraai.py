#!/usr/bin/env python3
"""
Send Claude Code hook events to KutiraAI observability dashboard.

This script is designed to be called from Claude Code hook scripts.
It reads hook event data from stdin and sends it to the KutiraAI API.

Usage:
    cat hook-data.json | python3 send_to_kutiraai.py

    Or from a hook script:
    echo "$INPUT" | python3 /home/marc/agentic-system/scripts/hooks/send_to_kutiraai.py
"""

import json
import sys
import requests
import os
import socket
from datetime import datetime

# Configuration
KUTIRAAI_URL = os.environ.get('KUTIRAAI_URL', 'http://localhost:3002')  # API server port
API_ENDPOINT = f'{KUTIRAAI_URL}/api/hook-events'
TIMEOUT = 2  # seconds - keep it fast to not slow down hooks
SOURCE_APP = os.environ.get('CLAUDE_SOURCE_APP', 'Claude Code')

def get_node_id():
    """Get the current node identifier."""
    hostname = socket.gethostname()
    return hostname

def parse_hook_event(data):
    """Parse hook event data and prepare for API."""
    # Hook event structure from Claude Code
    # {
    #   "event_type": "PreToolUse",
    #   "session_id": "...",
    #   "tool_name": "...",
    #   "parameters": {...},
    #   "model_name": "...",
    #   "chat": [...],
    #   ...
    # }

    # Determine event type
    event_type = data.get('event_type', 'Unknown')

    # Extract session ID
    session_id = data.get('session_id', 'unknown-session')

    # Build payload
    payload = {
        'source_app': SOURCE_APP,
        'session_id': session_id,
        'hook_event_type': event_type,
        'timestamp': int(datetime.now().timestamp() * 1000),  # milliseconds
        'model_name': data.get('model_name'),
        'payload': json.dumps({
            'tool_name': data.get('tool_name'),
            'parameters': data.get('parameters', {}),
            'raw_data': data  # Include full event for debugging
        }),
    }

    # Add chat history if available (might be large)
    if data.get('chat'):
        payload['chat'] = json.dumps(data['chat'])

    # Add summary if available
    if data.get('summary'):
        payload['summary'] = data['summary']

    # Add human-in-the-loop data if present
    if data.get('human_in_the_loop'):
        payload['human_in_the_loop'] = json.dumps(data['human_in_the_loop'])
        payload['human_in_the_loop_status'] = data.get('human_in_the_loop_status')

    return payload

def send_to_kutiraai(payload):
    """Send event to KutiraAI API."""
    try:
        response = requests.post(
            API_ENDPOINT,
            json=payload,
            timeout=TIMEOUT,
            headers={'Content-Type': 'application/json'}
        )

        if response.status_code in [200, 201]:
            # Success - log minimally
            print(f"✓ Sent {payload['hook_event_type']} to KutiraAI", file=sys.stderr)
            return True
        else:
            print(f"✗ KutiraAI API error: {response.status_code}", file=sys.stderr)
            return False

    except requests.exceptions.Timeout:
        print(f"✗ KutiraAI API timeout", file=sys.stderr)
        return False
    except requests.exceptions.ConnectionError:
        # Don't spam errors if KutiraAI is down
        print(f"✗ KutiraAI not reachable", file=sys.stderr)
        return False
    except Exception as e:
        print(f"✗ Error sending to KutiraAI: {e}", file=sys.stderr)
        return False

def main():
    """Main entry point."""
    try:
        # Read hook event from stdin
        input_data = sys.stdin.read()

        if not input_data.strip():
            print("No input data received", file=sys.stderr)
            return 1

        # Parse JSON
        try:
            data = json.loads(input_data)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON input: {e}", file=sys.stderr)
            return 1

        # Parse and send event
        payload = parse_hook_event(data)
        success = send_to_kutiraai(payload)

        return 0 if success else 1

    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
