#!/usr/bin/env python3
"""
Prometheus CLI - Command-line interface for autonomous agent system.

Usage:
    python -m prometheus.cli "Build a website for my portfolio"
    python -m prometheus.cli --interactive
    python -m prometheus.cli --status
"""

import argparse
import asyncio
import sys
import logging
from pathlib import Path

from .agent_loop import PrometheusAgentLoop, TaskResult, TaskStatus
from .llm_client import get_llm_client, LLMClient
from .mcp_client import get_mcp_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("prometheus")


def print_banner():
    """Print Prometheus banner."""
    banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                    PROJECT PROMETHEUS                      ║
    ║           Local-First Autonomous Agent System              ║
    ║                   Surpassing Manus                         ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_result(result: TaskResult):
    """Print task result."""
    status_emoji = {
        TaskStatus.COMPLETED: "✅",
        TaskStatus.FAILED: "❌",
        TaskStatus.BLOCKED: "⏸️",
        TaskStatus.EXECUTING: "🔄",
        TaskStatus.PLANNING: "📋",
        TaskStatus.PENDING: "⏳",
        TaskStatus.VERIFYING: "🔍",
    }

    emoji = status_emoji.get(result.status, "❓")
    print(f"\n{emoji} Task {result.task_id}: {result.status.value}")
    print(f"   Summary: {result.summary}")
    print(f"   Progress: {result.steps_completed}/{result.steps_total} steps")
    print(f"   Time: {result.execution_time:.2f}s")

    if result.outputs:
        print(f"   Outputs:")
        for output in result.outputs:
            print(f"     - {output.get('name', output.get('path', 'unknown'))}")

    if result.errors:
        print(f"   Errors:")
        for error in result.errors[:3]:  # Show first 3
            print(f"     - {error[:100]}")


async def run_task(task: str, context: dict = None) -> TaskResult:
    """Run a single task."""
    loop = PrometheusAgentLoop()
    return await loop.execute_task(task, context)


async def interactive_mode():
    """Run in interactive mode."""
    print_banner()
    print("Type your task and press Enter. Type 'quit' to exit.\n")

    loop = PrometheusAgentLoop()

    while True:
        try:
            task = input("🔥 Task> ").strip()

            if not task:
                continue

            if task.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break

            if task.lower() == "status":
                print_status()
                continue

            if task.lower() == "help":
                print_help()
                continue

            # Execute task
            print(f"\n⚡ Executing: {task[:50]}...")
            result = await loop.execute_task(task)
            print_result(result)
            print()

        except KeyboardInterrupt:
            print("\nInterrupted. Type 'quit' to exit.")
        except Exception as e:
            print(f"Error: {e}")


def print_status():
    """Print system status."""
    print("\n📊 System Status")
    print("-" * 40)

    # LLM status
    llm = get_llm_client()
    llm_status = "✅ Available" if llm.is_available else "❌ Not configured"
    print(f"LLM Client: {llm_status}")

    # MCP status
    mcp = get_mcp_client()
    print(f"MCP Servers: {len(mcp.available_servers)} configured")
    for server in list(mcp.available_servers.keys())[:5]:
        print(f"  - {server}")

    print()


def print_help():
    """Print help."""
    print("""
Available commands:
    <task>   - Execute an autonomous task
    status   - Show system status
    help     - Show this help
    quit     - Exit interactive mode

Example tasks:
    "Create a Python script that calculates fibonacci numbers"
    "Search for recent papers on transformer architectures"
    "Build a simple todo list web app"
    """)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Prometheus - Autonomous Agent System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s "Build a website"
    %(prog)s --interactive
    %(prog)s --status
        """
    )

    parser.add_argument(
        "task",
        nargs="?",
        help="Task to execute"
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Run in interactive mode"
    )
    parser.add_argument(
        "-s", "--status",
        action="store_true",
        help="Show system status"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path("/tmp/prometheus"),
        help="Workspace directory"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.status:
        print_banner()
        print_status()
        return 0

    if args.interactive:
        asyncio.run(interactive_mode())
        return 0

    if args.task:
        print_banner()
        print(f"⚡ Executing: {args.task[:50]}...")
        result = asyncio.run(run_task(args.task))
        print_result(result)
        return 0 if result.success else 1

    # No arguments - show help
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
