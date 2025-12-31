"""Tmux-based provider execution for persistent, interactive contexts.

Provides execution modes:
1. Headless: Quick queries with `-p` flag (no tools/files)
2. Interactive: Full agent mode in tmux session (tools, files, context)
3. Streaming: Real-time output for long operations

Integrates with enhanced-memory for context persistence.
"""

import asyncio
import os
import json
import uuid
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class ExecutionMode(Enum):
    """Provider execution modes."""
    HEADLESS = "headless"      # Quick query, no tools
    INTERACTIVE = "interactive"  # Full agent mode in tmux
    STREAMING = "streaming"     # Real-time output stream


@dataclass
class TmuxProvider:
    """Provider that runs in a tmux session for persistence."""
    name: str
    session_prefix: str = "provider"
    timeout: float = 300.0

    def get_session_name(self, task_id: Optional[str] = None) -> str:
        """Generate unique session name."""
        task_id = task_id or uuid.uuid4().hex[:8]
        return f"{self.session_prefix}-{self.name}-{task_id}"


async def query_in_tmux(
    provider_name: str,
    prompt: str,
    mode: ExecutionMode = ExecutionMode.INTERACTIVE,
    session_name: Optional[str] = None,
    timeout: float = 300.0,
    capture_output: bool = True
) -> Dict[str, Any]:
    """
    Run a provider query in a tmux session.

    For INTERACTIVE mode:
    - Creates persistent tmux session
    - Runs provider in full agent mode (can use tools, edit files)
    - Session persists for inspection/debugging
    - Context preserved for follow-up queries

    For HEADLESS mode:
    - Uses -p flag for quick queries
    - No persistent session
    - Falls back to cli_providers

    Args:
        provider_name: claude, codex, or gemini
        prompt: The query/task
        mode: ExecutionMode (HEADLESS, INTERACTIVE, STREAMING)
        session_name: Optional custom session name
        timeout: Max execution time
        capture_output: Whether to capture session output

    Returns:
        Dict with content, session_name, mode, and metadata
    """
    if mode == ExecutionMode.HEADLESS:
        # Use headless CLI directly
        from .cli_providers import query_cli_provider
        result = await query_cli_provider(provider_name, prompt, timeout)
        if result:
            result["mode"] = "headless"
            result["session_name"] = None
        return result

    # Interactive/Streaming mode - use tmux
    provider = TmuxProvider(name=provider_name)
    session = session_name or provider.get_session_name()

    # Build the interactive command
    if provider_name == "claude":
        # Claude interactive mode (no -p flag)
        inner_cmd = f'claude'
    elif provider_name == "codex":
        # Codex interactive mode
        inner_cmd = f'codex'
    elif provider_name == "gemini":
        # Gemini interactive mode
        inner_cmd = f'gemini'
    else:
        return {"error": f"Unknown provider: {provider_name}"}

    # Create tmux session with the provider
    create_cmd = [
        "tmux", "new-session", "-d",
        "-s", session,
        "-x", "200", "-y", "50"  # Wide terminal for output
    ]

    env = os.environ.copy()
    env["NO_COLOR"] = "1"

    # Force OAuth for Claude
    if provider_name == "claude":
        env["ANTHROPIC_API_KEY"] = ""

    try:
        # Create session
        process = await asyncio.create_subprocess_exec(
            *create_cmd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()

        # Send the provider command
        send_cmd = ["tmux", "send-keys", "-t", session, inner_cmd, "Enter"]
        process = await asyncio.create_subprocess_exec(*send_cmd)
        await process.communicate()

        # Wait for provider to start
        await asyncio.sleep(2)

        # Send the prompt
        # Escape special characters for tmux
        escaped_prompt = prompt.replace("'", "'\\''")
        send_prompt = ["tmux", "send-keys", "-t", session, escaped_prompt, "Enter"]
        process = await asyncio.create_subprocess_exec(*send_prompt)
        await process.communicate()

        # Wait for response (with timeout)
        if capture_output:
            output = await _wait_for_completion(session, timeout, provider_name)
        else:
            output = None

        return {
            "content": output,
            "session_name": session,
            "mode": mode.value,
            "provider": provider_name,
            "timestamp": datetime.now().isoformat(),
            "status": "completed" if output else "running"
        }

    except asyncio.TimeoutError:
        return {
            "content": None,
            "session_name": session,
            "mode": mode.value,
            "provider": provider_name,
            "error": f"Timeout after {timeout}s",
            "status": "timeout"
        }
    except Exception as e:
        return {
            "content": None,
            "session_name": session,
            "mode": mode.value,
            "provider": provider_name,
            "error": str(e),
            "status": "error"
        }


async def _wait_for_completion(
    session: str,
    timeout: float,
    provider_name: str
) -> Optional[str]:
    """Wait for provider to complete and capture output."""

    # Poll for completion indicators
    start_time = asyncio.get_event_loop().time()
    last_content = ""

    while (asyncio.get_event_loop().time() - start_time) < timeout:
        # Capture current pane content
        capture_cmd = ["tmux", "capture-pane", "-t", session, "-p", "-S", "-1000"]
        process = await asyncio.create_subprocess_exec(
            *capture_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()
        content = stdout.decode()

        # Check for completion indicators based on provider
        if provider_name == "claude":
            # Claude shows prompt when done: "> " or "claude>"
            if content.rstrip().endswith(">") or "claude>" in content:
                # Extract the response (between prompt and next prompt)
                return _extract_response(content, provider_name)
        elif provider_name == "codex":
            # Codex shows prompt or exits
            if "codex>" in content or content.rstrip().endswith("$"):
                return _extract_response(content, provider_name)
        elif provider_name == "gemini":
            # Gemini shows prompt
            if "gemini>" in content or content.rstrip().endswith(">"):
                return _extract_response(content, provider_name)

        # Check if content hasn't changed (provider might be done)
        if content == last_content:
            await asyncio.sleep(2)  # Wait a bit more
            if content == last_content:
                # No new output, assume done
                return _extract_response(content, provider_name)
        else:
            last_content = content

        await asyncio.sleep(1)

    return None  # Timeout


def _extract_response(content: str, provider_name: str) -> str:
    """Extract the actual response from tmux capture."""
    lines = content.split('\n')

    # Find the prompt line and extract response after it
    response_lines = []
    in_response = False

    for line in lines:
        # Skip empty lines at start
        if not in_response and not line.strip():
            continue

        # Detect end of response (new prompt)
        if in_response:
            if line.strip().endswith(">") or ">" in line[:10]:
                break
            response_lines.append(line)
        else:
            # Start capturing after we see the first non-prompt line
            if not line.strip().startswith(">") and line.strip():
                in_response = True
                response_lines.append(line)

    return '\n'.join(response_lines).strip()


async def query_providers_in_tmux(
    provider_names: List[str],
    prompt: str,
    mode: ExecutionMode = ExecutionMode.INTERACTIVE
) -> Dict[str, Dict[str, Any]]:
    """Query multiple providers in parallel tmux sessions."""
    tasks = [query_in_tmux(name, prompt, mode) for name in provider_names]
    responses = await asyncio.gather(*tasks, return_exceptions=True)

    results = {}
    for name, response in zip(provider_names, responses):
        if isinstance(response, Exception):
            results[name] = {"error": str(response), "provider": name}
        else:
            results[name] = response

    return results


async def get_tmux_session_content(session_name: str) -> Optional[str]:
    """Get the full content of a tmux session."""
    capture_cmd = ["tmux", "capture-pane", "-t", session_name, "-p", "-S", "-"]
    process = await asyncio.create_subprocess_exec(
        *capture_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        return None

    return stdout.decode()


async def list_provider_sessions() -> List[Dict[str, Any]]:
    """List all active provider tmux sessions."""
    list_cmd = ["tmux", "list-sessions", "-F", "#{session_name}:#{session_created}"]
    process = await asyncio.create_subprocess_exec(
        *list_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await process.communicate()

    if process.returncode != 0:
        return []

    sessions = []
    for line in stdout.decode().strip().split('\n'):
        if ':' in line and line.startswith('provider-'):
            name, created = line.split(':', 1)
            # Parse provider from session name
            parts = name.split('-')
            if len(parts) >= 2:
                provider = parts[1]
                sessions.append({
                    "session_name": name,
                    "provider": provider,
                    "created_timestamp": created
                })

    return sessions


async def kill_provider_session(session_name: str) -> bool:
    """Kill a provider tmux session."""
    kill_cmd = ["tmux", "kill-session", "-t", session_name]
    process = await asyncio.create_subprocess_exec(*kill_cmd)
    await process.communicate()
    return process.returncode == 0


# Quick test
if __name__ == "__main__":
    async def test():
        print("Testing tmux providers...")

        # Test headless mode (should work like cli_providers)
        print("\n1. Testing HEADLESS mode...")
        result = await query_in_tmux(
            "claude",
            "Say hello in 5 words",
            mode=ExecutionMode.HEADLESS
        )
        print(f"   Result: {result}")

        # Test interactive mode
        print("\n2. Testing INTERACTIVE mode...")
        result = await query_in_tmux(
            "claude",
            "What is 2+2?",
            mode=ExecutionMode.INTERACTIVE,
            timeout=60
        )
        print(f"   Result: {result}")

        # List sessions
        print("\n3. Listing provider sessions...")
        sessions = await list_provider_sessions()
        print(f"   Sessions: {sessions}")

    asyncio.run(test())
