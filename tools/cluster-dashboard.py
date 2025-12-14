#!/usr/bin/env python3
"""
Agentic Cluster Statusline Dashboard
Real-time status view across all cluster nodes
"""
import platform
from pathlib import Path

import subprocess
import json
import time
import sys
import os
import socket
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Try rich for beautiful output, fall back to basic
try:
    from rich.console import Console
    from rich.table import Table
    from rich.live import Live
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.text import Text
    from rich.style import Style
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Cluster node configuration
CLUSTER_NODES = {
    "macpro51": {
        "host": "192.168.1.183",
        "role": "builder",
        "emoji": "🔨",
        "os": "linux",
        "storage": str(_STORAGE_BASE)
    },
    "mac-studio": {
        "host": "192.168.1.16",
        "role": "orchestrator",
        "emoji": "🎯",
        "os": "macos",
        "storage": str(_STORAGE_BASE)
    },
    "macbook-air": {
        "host": "192.168.1.76",
        "role": "researcher",
        "emoji": "🔬",
        "os": "macos",
        "storage": "/Users/marc/agentic-system"
    },
    "completeu-server": {
        "host": "192.168.1.186",
        "role": "inference",
        "emoji": "🧠",
        "os": "macos",
        "storage": str(_STORAGE_BASE)
    }
}

def get_local_hostname():
    """Get current node's hostname"""
    hostname = socket.gethostname().lower()
    for node_name in CLUSTER_NODES:
        if node_name in hostname or hostname in node_name:
            return node_name
    return hostname.split('.')[0]

def run_ssh_command(host: str, command: str, timeout: int = 5) -> str:
    """Run command on remote host via SSH"""
    try:
        result = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", f"ConnectTimeout={timeout}",
             "-o", "StrictHostKeyChecking=no", host, command],
            capture_output=True, text=True, timeout=timeout + 2
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        return ""

def run_local_command(command: str, timeout: int = 5) -> str:
    """Run command locally"""
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        return ""

def gather_node_status(node_name: str, node_info: dict, is_local: bool = False) -> dict:
    """Gather comprehensive status from a node"""
    host = node_info["host"]
    os_type = node_info["os"]
    status = {
        "name": node_name,
        "role": node_info["role"],
        "emoji": node_info["emoji"],
        "online": False,
        "memory_pct": None,
        "cpu_load": None,
        "services": 0,
        "mcp_count": 0,
        "containers": 0,
        "claude_active": False,
        "git_branch": None,
        "uptime": None,
        "raid_status": None,
        "ollama_models": 0,
        "last_update": datetime.now().strftime("%H:%M:%S")
    }

    def run_cmd(cmd):
        if is_local:
            return run_local_command(cmd)
        return run_ssh_command(host, cmd)

    # Check if online with ping (cross-platform)
    import platform

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    elif system == "Linux":
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()

    if platform.system() == "Darwin":
        # macOS: -t is timeout
        ping_result = run_local_command(f"ping -c 1 -t 1 {host} >/dev/null 2>&1 && echo 1 || echo 0")
    else:
        # Linux: -W is timeout
        ping_result = run_local_command(f"ping -c 1 -W 1 {host} >/dev/null 2>&1 && echo 1 || echo 0")
    if ping_result.strip() != "1":
        return status

    status["online"] = True

    # Memory usage
    if os_type == "linux":
        mem_info = run_cmd("cat /proc/meminfo | grep -E 'MemTotal|MemAvailable' | awk '{print $2}'")
        if mem_info:
            lines = mem_info.split('\n')
            if len(lines) >= 2:
                try:
                    total = int(lines[0])
                    avail = int(lines[1])
                    status["memory_pct"] = int((1 - avail/total) * 100)
                except:
                    pass
    else:
        # macOS memory pressure
        mem_cmd = run_cmd("memory_pressure 2>/dev/null | grep 'System-wide memory free percentage' | awk '{print $NF}' | tr -d '%'")
        if mem_cmd:
            try:
                status["memory_pct"] = 100 - int(mem_cmd)
            except:
                pass

    # CPU load
    load_cmd = run_cmd("uptime | awk -F'load average:' '{print $2}' | awk -F',' '{print $1}' | tr -d ' '")
    if load_cmd:
        try:
            status["cpu_load"] = float(load_cmd)
        except:
            pass

    # Services count
    if os_type == "linux":
        svc_cmd = run_cmd("systemctl --user list-units --state=running 2>/dev/null | grep -c '.service' || echo 0")
    else:
        svc_cmd = run_cmd("pm2 jlist 2>/dev/null | jq 'length' 2>/dev/null || echo 0")
    try:
        status["services"] = int(svc_cmd) if svc_cmd else 0
    except:
        pass

    # MCP servers
    mcp_cmd = run_cmd("jq '.mcpServers | length' ~/.claude.json 2>/dev/null || echo 0")
    try:
        status["mcp_count"] = int(mcp_cmd) if mcp_cmd else 0
    except:
        pass

    # Containers
    if os_type == "linux":
        containers_cmd = run_cmd("podman ps -q 2>/dev/null | wc -l || docker ps -q 2>/dev/null | wc -l")
    else:
        containers_cmd = run_cmd("docker ps -q 2>/dev/null | wc -l")
    try:
        status["containers"] = int(containers_cmd.strip()) if containers_cmd else 0
    except:
        pass

    # Claude active
    claude_cmd = run_cmd("pgrep -f 'claude' >/dev/null && echo 1 || echo 0")
    status["claude_active"] = claude_cmd == "1"

    # Git branch
    storage = node_info["storage"]
    git_cmd = run_cmd(f"cd {storage} 2>/dev/null && git branch --show-current 2>/dev/null")
    status["git_branch"] = git_cmd if git_cmd else None

    # Uptime
    uptime_cmd = run_cmd("uptime -p 2>/dev/null || uptime | awk -F'up ' '{print $2}' | awk -F',' '{print $1}'")
    status["uptime"] = uptime_cmd[:20] if uptime_cmd else None

    # Linux-specific: RAID status
    if os_type == "linux":
        raid_cmd = run_cmd("cat /proc/mdstat 2>/dev/null | grep -o '\\[U*_*U*\\]' | head -1")
        if raid_cmd:
            if "_" in raid_cmd:
                status["raid_status"] = "degraded"
            else:
                status["raid_status"] = "healthy"

    # Inference node: Ollama models
    if node_info["role"] == "inference":
        ollama_cmd = run_cmd("ollama list 2>/dev/null | tail -n +2 | wc -l")
        try:
            status["ollama_models"] = int(ollama_cmd.strip()) if ollama_cmd else 0
        except:
            pass

    return status

def render_basic_dashboard(statuses: list):
    """Render dashboard without rich library"""
    os.system('clear' if os.name != 'nt' else 'cls')

    print("=" * 80)
    print("           🌐 AGENTIC CLUSTER DASHBOARD 🌐")
    print("=" * 80)
    print(f"  Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 80)

    header = f"{'Node':<20} {'Status':<8} {'Mem%':<6} {'CPU':<6} {'Svc':<5} {'MCP':<5} {'Claude':<8}"
    print(header)
    print("-" * 80)

    for s in statuses:
        online = "✅ ON" if s["online"] else "❌ OFF"
        mem = f"{s['memory_pct']}%" if s["memory_pct"] else "-"
        cpu = f"{s['cpu_load']:.1f}" if s["cpu_load"] else "-"
        svc = str(s["services"]) if s["services"] else "0"
        mcp = str(s["mcp_count"]) if s["mcp_count"] else "0"
        claude = "🟢 YES" if s["claude_active"] else "⚪ no"

        print(f"{s['emoji']} {s['name']:<17} {online:<8} {mem:<6} {cpu:<6} {svc:<5} {mcp:<5} {claude:<8}")

    print("-" * 80)
    print("\n  Press Ctrl+C to exit")

def render_rich_dashboard(statuses: list, console: Console) -> Table:
    """Render beautiful dashboard with rich library"""

    # Main status table
    table = Table(
        title="🌐 Agentic Cluster Dashboard",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
        border_style="blue",
        title_style="bold white on blue",
        caption=f"Updated: {datetime.now().strftime('%H:%M:%S')} | Press Ctrl+C to exit",
        caption_style="dim"
    )

    table.add_column("Node", style="bold", width=20, no_wrap=True)
    table.add_column("Status", justify="center", width=6)
    table.add_column("Mem", justify="right", width=5)
    table.add_column("CPU", justify="right", width=5)
    table.add_column("Svc", justify="center", width=4)
    table.add_column("MCP", justify="center", width=4)
    table.add_column("🐳", justify="center", width=3)
    table.add_column("Claude", justify="center", width=7)
    table.add_column("Info", width=18)

    for s in statuses:
        # Status indicator
        if s["online"]:
            status = Text("● ON", style="bold green")
        else:
            status = Text("● OFF", style="bold red")

        # Memory with color coding
        if s["memory_pct"] is not None:
            if s["memory_pct"] > 85:
                mem_style = "bold red"
            elif s["memory_pct"] > 70:
                mem_style = "yellow"
            else:
                mem_style = "green"
            memory = Text(f"{s['memory_pct']}%", style=mem_style)
        else:
            memory = Text("-", style="dim")

        # CPU load
        if s["cpu_load"] is not None:
            if s["cpu_load"] > 4:
                cpu_style = "bold red"
            elif s["cpu_load"] > 2:
                cpu_style = "yellow"
            else:
                cpu_style = "green"
            cpu = Text(f"{s['cpu_load']:.1f}", style=cpu_style)
        else:
            cpu = Text("-", style="dim")

        # Services
        services = Text(str(s["services"]), style="cyan" if s["services"] > 0 else "dim")

        # MCP
        mcp = Text(str(s["mcp_count"]), style="magenta" if s["mcp_count"] > 0 else "dim")

        # Containers
        containers = Text(str(s["containers"]), style="blue" if s["containers"] > 0 else "dim")

        # Claude active
        if s["claude_active"]:
            claude = Text("🟢 YES", style="bold green")
        else:
            claude = Text("⚪ no", style="dim")

        # Extra info based on role
        extra_parts = []
        if s["raid_status"]:
            if s["raid_status"] == "healthy":
                extra_parts.append("🛡️✓")
            else:
                extra_parts.append("🛡️⚠️")
        if s["ollama_models"]:
            extra_parts.append(f"🤖{s['ollama_models']}")
        if s["git_branch"]:
            extra_parts.append(f"⎇{s['git_branch'][:10]}")
        extra = Text(" ".join(extra_parts), style="dim")

        # Node name with emoji
        node_name = Text(f"{s['emoji']} {s['name']}", style="bold white")

        table.add_row(
            node_name, status, memory, cpu, services, mcp, containers, claude, extra
        )

    return table

def create_summary_panel(statuses: list) -> Panel:
    """Create a summary panel"""
    online_count = sum(1 for s in statuses if s["online"])
    total_services = sum(s["services"] for s in statuses if s["online"])
    total_mcp = sum(s["mcp_count"] for s in statuses if s["online"])
    total_containers = sum(s["containers"] for s in statuses if s["online"])
    claude_active = sum(1 for s in statuses if s["claude_active"])

    summary = Text()
    summary.append(f"  Nodes Online: ", style="dim")
    summary.append(f"{online_count}/{len(statuses)}", style="bold green" if online_count == len(statuses) else "yellow")
    summary.append(f"  |  Services: ", style="dim")
    summary.append(f"{total_services}", style="cyan")
    summary.append(f"  |  MCP Servers: ", style="dim")
    summary.append(f"{total_mcp}", style="magenta")
    summary.append(f"  |  Containers: ", style="dim")
    summary.append(f"{total_containers}", style="blue")
    summary.append(f"  |  Claude Sessions: ", style="dim")
    summary.append(f"{claude_active}", style="bold green" if claude_active > 0 else "dim")

    return Panel(summary, title="Cluster Summary", border_style="green", box=box.ROUNDED)

def main():
    parser = argparse.ArgumentParser(description="Agentic Cluster Dashboard")
    parser.add_argument("-r", "--refresh", type=int, default=5, help="Refresh interval in seconds")
    parser.add_argument("-1", "--once", action="store_true", help="Run once and exit")
    parser.add_argument("--no-rich", action="store_true", help="Disable rich output")
    args = parser.parse_args()

    use_rich = RICH_AVAILABLE and not args.no_rich
    local_node = get_local_hostname()

    if use_rich:
        console = Console()

    def gather_all_statuses():
        statuses = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {}
            for node_name, node_info in CLUSTER_NODES.items():
                is_local = node_name in local_node or local_node in node_name
                futures[executor.submit(gather_node_status, node_name, node_info, is_local)] = node_name

            for future in as_completed(futures):
                try:
                    status = future.result()
                    statuses.append(status)
                except Exception as e:
                    node_name = futures[future]
                    statuses.append({
                        "name": node_name,
                        "role": CLUSTER_NODES[node_name]["role"],
                        "emoji": CLUSTER_NODES[node_name]["emoji"],
                        "online": False,
                        "memory_pct": None,
                        "cpu_load": None,
                        "services": 0,
                        "mcp_count": 0,
                        "containers": 0,
                        "claude_active": False,
                        "git_branch": None,
                        "uptime": None,
                        "raid_status": None,
                        "ollama_models": 0,
                        "last_update": datetime.now().strftime("%H:%M:%S")
                    })

        # Sort by role priority
        role_order = {"orchestrator": 0, "builder": 1, "researcher": 2, "inference": 3}
        statuses.sort(key=lambda x: role_order.get(x["role"], 99))
        return statuses

    if args.once:
        statuses = gather_all_statuses()
        if use_rich:
            console.print(render_rich_dashboard(statuses, console))
            console.print(create_summary_panel(statuses))
        else:
            render_basic_dashboard(statuses)
        return

    # Live updating dashboard
    if use_rich:
        try:
            with Live(console=console, refresh_per_second=1, screen=True) as live:
                while True:
                    statuses = gather_all_statuses()
                    layout = Layout()
                    layout.split_column(
                        Layout(render_rich_dashboard(statuses, console), name="main"),
                        Layout(create_summary_panel(statuses), name="summary", size=3)
                    )
                    live.update(layout)
                    time.sleep(args.refresh)
        except KeyboardInterrupt:
            console.print("\n[dim]Dashboard stopped.[/dim]")
    else:
        try:
            while True:
                statuses = gather_all_statuses()
                render_basic_dashboard(statuses)
                time.sleep(args.refresh)
        except KeyboardInterrupt:
            print("\nDashboard stopped.")

if __name__ == "__main__":
    main()
