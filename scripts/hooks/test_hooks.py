#!/usr/bin/env python3
"""
Hook Testing & Benchmarking Suite
==================================

Tests all Claude Code hooks for:
1. Functionality - correct behavior
2. Performance - execution time
3. Non-blocking - background operations work
4. Error handling - graceful failure

Run: python3 test_hooks.py [--verbose] [--benchmark]
"""

import json
import subprocess
import time
import sys
import os
from pathlib import Path
from typing import Dict, Any, Tuple, List
from datetime import datetime

HOOKS_DIR = Path("/home/marc/agentic-system/scripts/hooks")
LOGS_DIR = Path("/home/marc/agentic-system/logs")
DB_PATH = Path("/home/marc/agentic-system/databases/hook_metrics.db")

# Test payloads for each hook type
TEST_PAYLOADS = {
    "session-start": {
        "session_id": "test_session_123",
        "transcript_path": "/tmp/test_transcript.json",
        "cwd": "/home/marc",
        "permission_mode": "default",
        "hook_event_name": "SessionStart"
    },
    "session-end": {
        "session_id": "test_session_123",
        "transcript_path": "/tmp/test_transcript.json",
        "cwd": "/home/marc",
        "permission_mode": "default",
        "hook_event_name": "SessionEnd",
        "reason": "user_exit"
    },
    "pre-tool-use": {
        "tool_name": "Bash",
        "tool_input": {"command": "echo 'test'"},
        "tool_use_id": "test_tool_123",
        "session_id": "test_session_123",
        "hook_event_name": "PreToolUse"
    },
    "post-tool-use": {
        "tool_name": "Bash",
        "tool_input": {"command": "echo 'test'"},
        "tool_response": "test output",
        "tool_use_id": "test_tool_123",
        "session_id": "test_session_123",
        "hook_event_name": "PostToolUse"
    },
    "stop": {
        "stop_hook_active": True,
        "session_id": "test_session_123",
        "hook_event_name": "Stop"
    },
    "subagent-start": {
        "agent_id": "test_agent_123",
        "agent_transcript_path": "/tmp/test_agent_transcript.json",
        "session_id": "test_session_123",
        "hook_event_name": "SubagentStart",
        "subagent_type": "Explore",
        "task": "Test exploration task"
    },
    "subagent-stop": {
        "stop_hook_active": True,
        "agent_id": "test_agent_123",
        "session_id": "test_session_123",
        "hook_event_name": "SubagentStop",
        "subagent_type": "Explore"
    },
    "user-prompt-submit": {
        "prompt": "Test user prompt for hook testing",
        "session_id": "test_session_123",
        "hook_event_name": "UserPromptSubmit"
    },
    "pre-compact": {
        "session_id": "test_session_123",
        "hook_event_name": "PreCompact",
        "custom_instructions": "Test compaction"
    },
    "notification": {
        "type": "test_notification",
        "message": "Test notification message",
        "severity": "info",
        "session_id": "test_session_123",
        "hook_event_name": "Notification"
    },
    "permission-request": {
        "permission_type": "tool_use",
        "tool_name": "Write",
        "tool_input": {"file_path": "/tmp/test.txt"},
        "reason": "Test permission request",
        "session_id": "test_session_123",
        "hook_event_name": "PermissionRequest"
    }
}

# Performance thresholds (milliseconds)
PERF_THRESHOLDS = {
    "pre-tool-use": 100,    # Critical path - must be fast
    "post-tool-use": 200,   # Semi-critical
    "session-start": 500,   # Can be slower
    "session-end": 500,
    "stop": 200,
    "subagent-start": 200,
    "subagent-stop": 200,
    "user-prompt-submit": 150,
    "pre-compact": 300,
    "notification": 150,
    "permission-request": 150
}


def run_hook(hook_name: str, payload: Dict[str, Any], timeout: float = 5.0) -> Tuple[bool, float, str, str]:
    """
    Run a hook script with payload and measure execution time.

    Returns: (success, duration_ms, stdout, stderr)
    """
    hook_path = HOOKS_DIR / f"{hook_name}.sh"

    if not hook_path.exists():
        return False, 0, "", f"Hook not found: {hook_path}"

    start_time = time.perf_counter()

    try:
        result = subprocess.run(
            [str(hook_path)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "CLAUDE_SESSION_ID": "test_session_123"}
        )

        duration_ms = (time.perf_counter() - start_time) * 1000
        success = result.returncode == 0

        return success, duration_ms, result.stdout, result.stderr

    except subprocess.TimeoutExpired:
        duration_ms = (time.perf_counter() - start_time) * 1000
        return False, duration_ms, "", f"Hook timed out after {timeout}s"
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        return False, duration_ms, "", str(e)


def test_safety_blocking():
    """Test that pre-tool-use correctly blocks dangerous commands."""
    print("\n=== Safety Blocking Test ===")

    dangerous_payloads = [
        {"tool_name": "Bash", "tool_input": {"command": "rm -rf /home"}},
        {"tool_name": "Bash", "tool_input": {"command": "dd if=/dev/zero of=/dev/sda"}},
        {"tool_name": "Bash", "tool_input": {"command": "mkfs.ext4 /dev/sda1"}},
    ]

    safe_payloads = [
        {"tool_name": "Bash", "tool_input": {"command": "ls -la"}},
        {"tool_name": "Bash", "tool_input": {"command": "echo 'hello'"}},
        {"tool_name": "Read", "tool_input": {"file_path": "/tmp/test.txt"}},
    ]

    results = []

    # Test dangerous commands (should return exit code 2)
    for payload in dangerous_payloads:
        hook_path = HOOKS_DIR / "pre-tool-use.sh"
        result = subprocess.run(
            [str(hook_path)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=5
        )
        blocked = result.returncode == 2
        cmd = payload["tool_input"]["command"][:30]
        status = "✓ BLOCKED" if blocked else "✗ NOT BLOCKED"
        print(f"  {status}: {cmd}...")
        results.append(("dangerous", cmd, blocked))

    # Test safe commands (should return exit code 0)
    for payload in safe_payloads:
        hook_path = HOOKS_DIR / "pre-tool-use.sh"
        result = subprocess.run(
            [str(hook_path)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=5
        )
        allowed = result.returncode == 0
        tool = payload.get("tool_name", "unknown")
        status = "✓ ALLOWED" if allowed else "✗ BLOCKED"
        print(f"  {status}: {tool}")
        results.append(("safe", tool, allowed))

    return results


def benchmark_hooks(iterations: int = 5) -> Dict[str, Dict[str, float]]:
    """Benchmark all hooks multiple times."""
    print(f"\n=== Hook Performance Benchmark ({iterations} iterations) ===")

    benchmarks = {}

    for hook_name, payload in TEST_PAYLOADS.items():
        times = []
        for i in range(iterations):
            success, duration, _, _ = run_hook(hook_name, payload)
            if success:
                times.append(duration)

        if times:
            avg = sum(times) / len(times)
            min_t = min(times)
            max_t = max(times)
            threshold = PERF_THRESHOLDS.get(hook_name, 500)
            status = "✓" if avg < threshold else "⚠️"

            benchmarks[hook_name] = {
                "avg_ms": round(avg, 2),
                "min_ms": round(min_t, 2),
                "max_ms": round(max_t, 2),
                "threshold_ms": threshold,
                "passed": avg < threshold
            }

            print(f"  {status} {hook_name}: avg={avg:.1f}ms (min={min_t:.1f}, max={max_t:.1f}, threshold={threshold}ms)")
        else:
            print(f"  ✗ {hook_name}: FAILED all iterations")
            benchmarks[hook_name] = {"error": "All iterations failed"}

    return benchmarks


def test_all_hooks() -> Dict[str, Dict[str, Any]]:
    """Test all hooks for basic functionality."""
    print("\n=== Hook Functionality Tests ===")

    results = {}

    for hook_name, payload in TEST_PAYLOADS.items():
        success, duration, stdout, stderr = run_hook(hook_name, payload)

        results[hook_name] = {
            "success": success,
            "duration_ms": round(duration, 2),
            "has_output": bool(stdout.strip()),
            "has_errors": bool(stderr.strip() and "WARNING" not in stderr and "⚠️" not in stderr)
        }

        status = "✓" if success else "✗"
        print(f"  {status} {hook_name}: {duration:.1f}ms")

        if stderr and "BLOCKED" not in stderr and "WARNING" not in stderr:
            print(f"    stderr: {stderr[:100]}")

    return results


def check_log_integration():
    """Verify hooks are writing to logs correctly."""
    print("\n=== Log Integration Check ===")

    log_files = [
        ("tool-usage.log", "Tool usage events"),
        ("meta-learning.jsonl", "AGI meta-learning"),
        ("agi-activity.jsonl", "AGI activity"),
        ("claude-sessions.log", "Session events"),
        ("file-operations.log", "File operations"),
    ]

    for log_file, description in log_files:
        log_path = LOGS_DIR / log_file
        if log_path.exists():
            size = log_path.stat().st_size
            lines = sum(1 for _ in open(log_path))
            mtime = datetime.fromtimestamp(log_path.stat().st_mtime)
            age_mins = (datetime.now() - mtime).total_seconds() / 60

            status = "✓" if age_mins < 60 else "⚠️"
            print(f"  {status} {log_file}: {lines} entries, {size/1024:.1f}KB, updated {age_mins:.0f}m ago")
        else:
            print(f"  ✗ {log_file}: NOT FOUND")


def check_integration_connectivity():
    """Test connectivity to integration endpoints."""
    import urllib.request

    print("\n=== Integration Connectivity Test ===")

    endpoints = {
        "TPU Warm Service": "http://localhost:8780/health",
        "Activity Dashboard": "http://localhost:4100/health",
        "Voice Mode": "http://localhost:8765/health",
        "Enhanced Memory": "http://localhost:8101/health",
    }

    results = {}

    for name, url in endpoints.items():
        print(f"  {name}: ", end="", flush=True)
        try:
            req = urllib.request.Request(url, method='GET')
            start = time.perf_counter()
            with urllib.request.urlopen(req, timeout=1.0) as response:
                latency = (time.perf_counter() - start) * 1000
                if response.status == 200:
                    print(f"✓ OK ({latency:.0f}ms)")
                    results[name] = {"status": "ok", "latency_ms": latency}
                else:
                    print(f"⚠️ WARN (status {response.status})")
                    results[name] = {"status": "warn", "code": response.status}
        except Exception as e:
            print(f"✗ DOWN ({type(e).__name__})")
            results[name] = {"status": "down", "error": str(e)}

    return results


def check_circuit_breaker_states():
    """Check current circuit breaker states."""
    print("\n=== Circuit Breaker States ===")

    cb_file = Path("/home/marc/agentic-system/databases/circuit_breaker_states.json")

    if cb_file.exists():
        try:
            with open(cb_file) as f:
                states = json.load(f)

            for name, state in states.items():
                is_open = state.get('open', False)
                failures = state.get('failures', 0)
                status = "✗ OPEN" if is_open else "✓ CLOSED"
                print(f"  {status}: {name} (failures: {failures})")

            return states
        except (json.JSONDecodeError, IOError) as e:
            print(f"  ⚠️ Error reading circuit breaker file: {e}")
            return {}
    else:
        print("  ✓ No circuit breaker file (all circuits healthy)")
        return {}


def check_hook_metrics():
    """Check hook metrics database."""
    print("\n=== Hook Metrics Database ===")

    import sqlite3

    if not DB_PATH.exists():
        print("  ⚠️ Metrics database not found")
        return

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Check for recent metrics (handle different schema versions)
    try:
        cursor.execute("""
            SELECT hook_type, COUNT(*) as count,
                   AVG(execution_time_ms) as avg_ms,
                   SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                   SUM(CASE WHEN timeout = 1 THEN 1 ELSE 0 END) as timeout_count
            FROM hook_metrics
            WHERE timestamp > strftime('%s', 'now') - 3600
            GROUP BY hook_type
            ORDER BY count DESC
        """)
    except sqlite3.OperationalError:
        # Try alternate schema
        cursor.execute("""
            SELECT hook_type, COUNT(*) as count,
                   AVG(COALESCE(execution_time_ms, duration_ms)) as avg_ms,
                   SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                   SUM(CASE WHEN timeout = 1 THEN 1 ELSE 0 END) as timeout_count
            FROM hook_metrics
            GROUP BY hook_type
            ORDER BY count DESC
            LIMIT 20
        """)

    recent = cursor.fetchall()

    if recent:
        print("  Recent hook metrics (last hour):")
        for hook_type, count, avg_ms, success, timeouts in recent:
            success_rate = (success / count * 100) if count > 0 else 0
            status = "✓" if success_rate > 95 else "⚠️"
            print(f"    {status} {hook_type}: {count} calls, avg={avg_ms:.1f}ms, success={success_rate:.0f}%")
    else:
        print("  ⚠️ No metrics in last hour")

    conn.close()


def check_memory_integration():
    """Verify hooks are updating memory database."""
    print("\n=== Memory Integration Check ===")

    import sqlite3
    db_path = Path("/home/marc/agentic-system/.claude/enhanced_memories/memory.db")

    if not db_path.exists():
        print("  ✗ Memory database not found")
        return

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Check for recent activity
    cursor.execute("""
        SELECT entity_type, COUNT(*) as count,
               MAX(datetime(last_accessed, 'localtime')) as latest
        FROM entities
        WHERE datetime(last_accessed) > datetime('now', '-1 hour')
        GROUP BY entity_type
        ORDER BY count DESC
        LIMIT 10
    """)

    recent = cursor.fetchall()

    if recent:
        print("  Recent memory activity (last hour):")
        for entity_type, count, latest in recent:
            print(f"    ✓ {entity_type}: {count} entities (latest: {latest})")
    else:
        print("  ⚠️ No memory activity in last hour")

    # Check session activity specifically
    cursor.execute("""
        SELECT name, access_count, datetime(last_accessed, 'localtime')
        FROM entities
        WHERE name LIKE 'session_activity%'
        ORDER BY last_accessed DESC
        LIMIT 1
    """)

    session = cursor.fetchone()
    if session:
        print(f"  ✓ Session activity: {session[1]} accesses, last: {session[2]}")
    else:
        print("  ⚠️ No session activity entity found")

    conn.close()


def main():
    """Run comprehensive hook tests."""
    import argparse

    parser = argparse.ArgumentParser(description="Hook Testing Suite")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--benchmark", "-b", action="store_true", help="Run benchmarks")
    parser.add_argument("--safety", "-s", action="store_true", help="Run safety tests only")
    parser.add_argument("--iterations", "-i", type=int, default=5, help="Benchmark iterations")

    args = parser.parse_args()

    print("=" * 60)
    print("Claude Code Hook Testing Suite")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 60)

    if args.safety:
        test_safety_blocking()
        return

    # Run all tests
    functionality_results = test_all_hooks()
    safety_results = test_safety_blocking()

    if args.benchmark:
        benchmark_results = benchmark_hooks(args.iterations)

    check_log_integration()
    check_integration_connectivity()
    check_circuit_breaker_states()
    check_hook_metrics()
    check_memory_integration()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = sum(1 for r in functionality_results.values() if r["success"])
    total = len(functionality_results)
    print(f"Functionality: {passed}/{total} hooks passed")

    if args.benchmark:
        perf_passed = sum(1 for r in benchmark_results.values() if r.get("passed", False))
        print(f"Performance: {perf_passed}/{total} hooks within threshold")

    # Return exit code based on results
    if passed == total:
        print("\n✓ All hooks operational")
        sys.exit(0)
    else:
        print(f"\n⚠️ {total - passed} hooks have issues")
        sys.exit(1)


if __name__ == "__main__":
    main()
