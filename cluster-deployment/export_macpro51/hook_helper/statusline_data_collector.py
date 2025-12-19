#!/usr/bin/env python3
"""
StatusLine Data Collector - Gathers live metrics for dynamic statusline
Updates /home/marc/.claude/health-status.json every 5 seconds
"""

import json
import os
import subprocess
import time
from pathlib import Path
from datetime import datetime

def get_mcp_status():
    """Get MCP server status from settings.json"""
    settings_path = Path.home() / '.claude' / 'settings.json'
    if not settings_path.exists():
        return {"healthy": 0, "total": 0}

    try:
        with open(settings_path) as f:
            settings = json.load(f)

        servers = settings.get('mcpServers', {})
        total = len(servers)

        # Check which servers are running by looking for their processes
        healthy = 0
        for name, config in servers.items():
            command = config.get('command', '')
            if 'python' in command:
                # Look for the server.py process
                args = config.get('args', [])
                if args and 'server.py' in str(args):
                    server_name = Path(config.get('cwd', '')).name if config.get('cwd') else name
                    result = subprocess.run(
                        ['pgrep', '-f', server_name],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        healthy += 1
            elif 'node' in command:
                # Node.js server
                args = config.get('args', [])
                if args:
                    server_file = Path(args[0]).name
                    result = subprocess.run(
                        ['pgrep', '-f', server_file],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        healthy += 1

        return {"healthy": healthy, "total": total}
    except Exception as e:
        return {"healthy": 0, "total": 0}

def get_hooks_status():
    """Check if hooks are active"""
    result = subprocess.run(
        ['pgrep', '-f', 'pre-tool-use.py'],
        capture_output=True,
        text=True
    )
    return result.returncode == 0

def get_memory_usage():
    """Get enhanced-memory database size"""
    memory_db = Path.home() / '.claude' / 'memory_optimized.db'
    if memory_db.exists():
        size = memory_db.stat().st_size
        # Convert to human-readable
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"
    return "?"

def get_agent_count():
    """Get active agent count from orchestrator"""
    try:
        import requests
        response = requests.get('http://localhost:8881/api/status', timeout=0.5)
        if response.status_code == 200:
            data = response.json()
            return data.get('active_tasks', 0)
    except:
        pass
    return 0

def get_tmux_status():
    """Check if claude-hierarchy tmux session exists"""
    result = subprocess.run(
        ['tmux', 'list-sessions'],
        capture_output=True,
        text=True
    )
    return 'claude-hierarchy' in result.stdout

def get_context_usage():
    """Estimate context usage from recent logs"""
    # This would need integration with actual Claude Code context tracking
    # For now, return placeholder
    return "?"

def collect_status():
    """Collect all status metrics"""
    mcp = get_mcp_status()

    status = {
        "timestamp": datetime.now().isoformat(),
        "mcp": {
            "healthy": mcp["healthy"],
            "total": mcp["total"]
        },
        "hooks": {
            "active": get_hooks_status()
        },
        "memory": {
            "size": get_memory_usage()
        },
        "agents": {
            "active": get_agent_count(),
            "max": 8
        },
        "tmux": {
            "running": get_tmux_status()
        },
        "context": {
            "percentage": get_context_usage()
        },
        "services": []  # For backward compatibility
    }

    # Add individual MCP servers status
    settings_path = Path.home() / '.claude' / 'settings.json'
    if settings_path.exists():
        try:
            with open(settings_path) as f:
                settings = json.load(f)

            for name, config in settings.get('mcpServers', {}).items():
                command = config.get('command', '')
                is_running = False

                if 'python' in command or 'node' in command:
                    search_term = name
                    result = subprocess.run(
                        ['pgrep', '-f', search_term],
                        capture_output=True,
                        text=True
                    )
                    is_running = result.returncode == 0

                status["services"].append({
                    "name": name,
                    "status": "healthy" if is_running else "down"
                })
        except:
            pass

    return status

def main():
    """Main loop - update status every 5 seconds"""
    output_path = Path.home() / '.claude' / 'health-status.json'

    print(f"StatusLine Data Collector started")
    print(f"Writing to: {output_path}")
    print("Press Ctrl+C to stop")

    try:
        while True:
            status = collect_status()

            # Write atomically
            temp_path = output_path.with_suffix('.tmp')
            with open(temp_path, 'w') as f:
                json.dump(status, f, indent=2)
            temp_path.replace(output_path)

            time.sleep(5)
    except KeyboardInterrupt:
        print("\nStopping collector...")

if __name__ == '__main__':
    main()
