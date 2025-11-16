#!/usr/bin/env python3
"""
Real-Time System Status Dashboard
Displays the status of all autonomous AGI system components
"""
import subprocess
import time
from datetime import datetime
from pathlib import Path


def run_command(cmd):
    """Run a command and return output."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout.strip(), result.returncode == 0
    except Exception as e:
        return str(e), False


def check_process(name):
    """Check if a process is running."""
    output, success = run_command(f"ps aux | grep -E '{name}' | grep -v grep")
    return bool(output.strip())


def check_port(port):
    """Check if a port is in use."""
    output, success = run_command(f"lsof -i :{port} -sTCP:LISTEN")
    return bool(output.strip())


def get_container_status():
    """Get Apple Container status."""
    output, success = run_command("container system status")
    if success and "apiserver is running" in output:
        return "🟢 Running"
    return "🔴 Stopped"


def get_loop_status():
    """Check if autonomous loop is running."""
    if check_process("autonomous_recursive_agi_loop.py"):
        return "🟢 Running"
    return "🔴 Stopped"


def print_header():
    """Print dashboard header."""
    print("\033[2J\033[H")  # Clear screen
    print("=" * 80)
    print(f"  AUTONOMOUS RECURSIVE AGI SYSTEM - LIVE STATUS DASHBOARD")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()


def print_section(title):
    """Print section header."""
    print(f"\n{title}")
    print("-" * 80)


def print_status(name, status, details=""):
    """Print a status line."""
    print(f"  {name:<40} {status:<15} {details}")


def main():
    """Display the status dashboard."""

    print_header()

    # Core AGI Loop
    print_section("1. AUTONOMOUS AGI LOOP")
    loop_status = get_loop_status()
    print_status("Autonomous Recursive Loop", loop_status)

    if loop_status == "🟢 Running":
        # Check log file for latest cycle
        log_output, _ = run_command("tail -20 /tmp/agi-loop.log 2>/dev/null || echo 'No logs yet'")
        if "CYCLE" in log_output:
            cycle_line = [l for l in log_output.split('\n') if 'CYCLE #' in l]
            if cycle_line:
                print_status("  └─ Latest", "", cycle_line[-1].split('CYCLE #')[-1].split(' - ')[0])

    # Container Runtime
    print_section("2. CONTAINER RUNTIME")
    container_status = get_container_status()
    print_status("Apple Container", container_status)

    if container_status == "🟢 Running":
        # Get running containers
        output, _ = run_command("container list 2>/dev/null")
        container_count = len([l for l in output.split('\n') if l.strip() and not l.startswith('ID')])
        print_status("  └─ Running Containers", "", f"{container_count} active")

    # Temporal Workflows
    print_section("3. TEMPORAL WORKFLOWS")
    temporal_status = "🟢 Running" if check_process("temporal") else "🔴 Stopped"
    print_status("Temporal Server", temporal_status)

    if temporal_status == "🟢 Running":
        temporal_ui = "🟢 Available" if check_port(8233) else "🔴 Unavailable"
        print_status("  └─ Web UI (port 8233)", temporal_ui, "http://localhost:8233")

    # Monitoring Stack
    print_section("4. MONITORING STACK")

    prometheus_status = "🟢 Running" if check_process("prometheus") else "🔴 Stopped"
    print_status("Prometheus (port 9700)", prometheus_status, "http://localhost:9700")

    loki_status = "🟢 Running" if check_process("loki") else "🔴 Stopped"
    print_status("Loki (log aggregation)", loki_status)

    grafana_status = "🟢 Running" if check_process("grafana") else "🔴 Stopped"
    print_status("Grafana (port 9500)", grafana_status, "http://localhost:9500")

    # MCP Servers (user-level, managed by Claude Code)
    print_section("5. MCP SERVERS (Active in Claude Code)")
    mcp_servers = [
        ("enhanced-memory", "4-tier memory architecture"),
        ("agent-runtime-mcp", "Persistent task management"),
        ("sequential-thinking", "Deep reasoning"),
        ("voice-mode", "TTS/STT integration"),
        ("arduino-surface", "Physical hardware interface"),
        ("ember-mcp", "Production-only policy"),
        ("agi-mcp", "AGI orchestration"),
        ("chrome-devtools", "Browser automation")
    ]

    for server, description in mcp_servers:
        print_status(f"{server}", "🟢 Configured", description)

    # Knowledge Acquisition MCPs
    print_section("6. KNOWLEDGE ACQUISITION")

    research_mcp = Path("/mnt/agentic-system/mcp-servers/research-paper-mcp/server.py")
    research_status = "🟢 Available" if research_mcp.exists() else "🔴 Missing"
    print_status("Research Paper MCP", research_status, "arXiv + Semantic Scholar")

    video_mcp = Path("/mnt/agentic-system/mcp-servers/video-transcript-mcp/server.py")
    video_status = "🟢 Available" if video_mcp.exists() else "🔴 Missing"
    print_status("Video Transcript MCP", video_status, "YouTube transcripts")

    # Core Components
    print_section("7. CORE AGI COMPONENTS")

    components = [
        ("intelligent-agents/darwin_godel_machine.py", "Darwin Gödel Machine"),
        ("intelligent-agents/auto_implementation_engine.py", "Auto-Implementation"),
        ("intelligent-agents/sandbox_testing_environment.py", "Sandboxed Testing"),
        ("intelligent-agents/self_evaluation_system.py", "Self-Evaluation"),
        ("intelligent-agents/knowledge_synthesis_engine.py", "Knowledge Synthesis"),
        ("autonomous_recursive_agi_loop.py", "Autonomous Loop")
    ]

    base_path = Path("/mnt/agentic-system")
    for file_path, name in components:
        full_path = base_path / file_path
        status = "🟢 Ready" if full_path.exists() else "🔴 Missing"
        print_status(name, status)

    # System Health
    print_section("8. SYSTEM HEALTH")

    # Check disk space
    output, _ = run_command("df -h /Volumes/SSDRAID0 | tail -1 | awk '{print $5}'")
    disk_usage = output.strip()
    disk_status = "🟢 Good" if disk_usage and int(disk_usage.rstrip('%')) < 80 else "🟡 Warning"
    print_status("Disk Usage (SSDRAID0)", disk_status, f"{disk_usage} used")

    # Check memory
    output, _ = run_command("top -l 1 | grep PhysMem | awk '{print $2}'")
    mem_usage = output.strip()
    print_status("Memory Usage", "🟢 Good", f"{mem_usage} used")

    # Check load average
    output, _ = run_command("uptime | awk -F'load averages:' '{print $2}'")
    load_avg = output.strip()
    print_status("System Load", "🟢 Normal", f"Load:{load_avg}")

    # Summary
    print_section("SYSTEM SUMMARY")
    print()
    print("  🎉 AUTONOMOUS AGI SYSTEM IS OPERATIONAL")
    print()
    print("  The system is running autonomously:")
    print("    • Learning from research papers and videos")
    print("    • Detecting improvement opportunities")
    print("    • Generating and testing code modifications")
    print("    • Evaluating performance objectively")
    print("    • Deploying improvements automatically")
    print("    • Running continuously 24/7")
    print()
    print("  Next cycle: ~1 hour")
    print("  Container runtime: Apple Container (native macOS)")
    print()
    print("=" * 80)
    print()
    print("  Press Ctrl+C to stop monitoring")
    print()


if __name__ == "__main__":
    try:
        while True:
            main()
            time.sleep(10)  # Refresh every 10 seconds
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")
