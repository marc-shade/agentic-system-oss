#!/usr/bin/env python3
"""
Environmental Awareness V2 - With Ember Integration
Startup hook that loads complete system context including Ember watchdog data

Provides Phoenix with:
1. System state (services, ports, MCP servers)
2. Ember watchdog context (violations, patterns, learning)
3. Recent activity patterns
4. Self-improvement insights
"""

import json
import subprocess
import sys
from pathlib import Path

def get_ember_context() -> str:
    """Get Ember watchdog context summary"""
    try:
        result = subprocess.run(
            ["python3", str(Path.home() / ".claude" / "hooks" / "ember_memory_sync.py"), "summary"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            return result.stdout
        else:
            return "# Ember Context: Not available"

    except Exception as e:
        return f"# Ember Context: Error - {e}"

def get_system_state() -> dict:
    """Get system state from existing monitoring"""
    system_state_file = Path.home() / ".claude" / "system-state.json"

    if system_state_file.exists():
        try:
            with open(system_state_file) as f:
                return json.load(f)
        except:
            pass

    return {}

def get_mcp_status() -> dict:
    """Get MCP server status"""
    # Check which MCPs are active
    mcp_config = Path.home() / ".claude.json"

    if mcp_config.exists():
        try:
            with open(mcp_config) as f:
                config = json.load(f)
                return {
                    "mcpServers": list(config.get("mcpServers", {}).keys())
                }
        except:
            pass

    return {"mcpServers": []}

def generate_environmental_awareness() -> str:
    """
    Generate complete environmental awareness context

    Combines:
    - System state (services, ports)
    - MCP server status
    - Ember watchdog context (NEW!)
    - Git repository info
    - Current working directory
    """
    output = []

    # Header
    output.append("=" * 70)
    output.append("PHOENIX ENVIRONMENTAL AWARENESS - Session Startup Context")
    output.append("=" * 70)
    output.append("")

    # Ember Watchdog Context (NEW - Priority 1)
    output.append(get_ember_context())
    output.append("")

    # System State
    output.append("## System State")
    state = get_system_state()
    summary = state.get("summary", {})

    if summary:
        output.append(f"- Services: {summary.get('healthy', 0)} healthy, {summary.get('down', 0)} down")
        output.append(f"- Total ports: {summary.get('total_ports', 0)}")

        # Key services
        services = state.get("services", {})
        for service, info in services.items():
            status = info.get("status", "unknown")
            if status == "healthy":
                output.append(f"  ✓ {service}: {status}")
            elif status == "down":
                output.append(f"  ✗ {service}: {status}")
    else:
        output.append("- System state not available")

    output.append("")

    # MCP Status
    output.append("## MCP Servers")
    mcp_status = get_mcp_status()
    servers = mcp_status.get("mcpServers", [])

    if servers:
        output.append(f"- Active: {len(servers)}")
        for server in servers[:10]:  # Limit to 10
            output.append(f"  - {server}")
    else:
        output.append("- No active MCP servers detected")

    output.append("")

    # Working Directory
    output.append("## Current Context")
    try:
        import os
        cwd = os.getcwd()
        output.append(f"- Working directory: {cwd}")

        # Check if git repo
        git_check = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            cwd=cwd
        )

        if git_check.returncode == 0:
            # Get branch
            branch_result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                cwd=cwd
            )

            if branch_result.returncode == 0:
                branch = branch_result.stdout.strip()
                output.append(f"- Git branch: {branch}")

            # Get uncommitted changes
            status_result = subprocess.run(
                ["git", "status", "--short"],
                capture_output=True,
                text=True,
                cwd=cwd
            )

            if status_result.returncode == 0:
                changes = status_result.stdout.strip().split("\n")
                if changes and changes[0]:
                    output.append(f"- Uncommitted changes: {len(changes)} files")

    except:
        pass

    output.append("")

    # Self-Improvement Directive
    output.append("## Phoenix Self-Improvement Directive")
    output.append("")
    output.append("Based on Ember's learning:")
    output.append("1. Review patterns I should avoid (high correction rate)")
    output.append("2. Recognize intentional patterns (exceptions)")
    output.append("3. Apply learned risk adjustments to decisions")
    output.append("4. Query enhanced-memory for similar past violations before acting")
    output.append("5. Continuously improve based on Ember's feedback")

    output.append("")
    output.append("=" * 70)

    return "\n".join(output)

def main():
    """Main entry point for startup hook"""
    context = generate_environmental_awareness()
    print(context)

    # Also output as JSON for programmatic access
    import time
    json_output = {
        "ember_context_available": True,
        "system_state_available": True,
        "mcp_status_available": True,
        "timestamp": int(time.time())
    }

    json_file = Path.home() / ".claude" / "startup_context.json"
    with open(json_file, "w") as f:
        json.dump(json_output, f, indent=2)

if __name__ == "__main__":
    main()
