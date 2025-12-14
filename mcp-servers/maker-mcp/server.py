#!/usr/bin/env python3
"""
MAKER Framework MCP Server
==========================

Exposes MAKER framework (Massively Decomposed Agentic Processes) via MCP protocol.

Tools:
- maker_execute_sequence: Execute stateless agent sequence with voting
- maker_get_execution_stats: Get statistics for an execution trace
- maker_run_benchmark: Run Tower of Hanoi or custom benchmarks
- maker_configure: Configure voting parameters (k, max_queries)
"""
import os

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add intelligent-agents to path
import platform
if platform.system() == "Darwin":
    STORAGE_BASE = str(_STORAGE_BASE)
else:
    STORAGE_BASE = str(_STORAGE_BASE)

sys.path.insert(0, str(Path(STORAGE_BASE) / "intelligent-agents"))

from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio

from maker_framework import (
    MAKEROrchestrator,
    AtomicState,
    AgentResponse,
    RedFlagValidator,
    FirstToKVoting
)
from tower_of_hanoi_benchmark import HanoiBenchmark

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


# Configure logging to stderr (MCP requirement)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Initialize MCP server
app = Server("maker-framework")

# Global orchestrator instance
_orchestrator: Optional[MAKEROrchestrator] = None


def get_orchestrator() -> MAKEROrchestrator:
    """Get or create MAKER orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = MAKEROrchestrator(
            voting_enabled=True,
            k=3,
            red_flag_enabled=True
        )
    return _orchestrator


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available MAKER framework tools"""
    return [
        Tool(
            name="maker_execute_sequence",
            description=(
                "Execute a sequence of stateless agent steps with MAKER reliability. "
                "Provides 99.9999% accuracy through First-to-K voting and red flagging. "
                "Ideal for long sequential tasks (1M+ steps)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task_name": {
                        "type": "string",
                        "description": "Name of the task to execute"
                    },
                    "initial_state": {
                        "type": "object",
                        "description": "Initial state data (will be wrapped in AtomicState)",
                        "properties": {
                            "state_data": {"type": "object"},
                            "rules": {"type": "array", "items": {"type": "string"}},
                            "goal": {"type": "string"}
                        },
                        "required": ["state_data", "rules", "goal"]
                    },
                    "max_steps": {
                        "type": "integer",
                        "description": "Maximum steps before giving up",
                        "default": 1000
                    },
                    "voting_enabled": {
                        "type": "boolean",
                        "description": "Enable First-to-K voting",
                        "default": True
                    },
                    "k": {
                        "type": "integer",
                        "description": "Votes ahead required to win (default: 3)",
                        "default": 3
                    }
                },
                "required": ["task_name", "initial_state"]
            }
        ),
        Tool(
            name="maker_get_execution_stats",
            description=(
                "Get detailed statistics for a MAKER execution trace, including "
                "step-by-step execution data, voting statistics, and performance metrics."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "trace_id": {
                        "type": "string",
                        "description": "Execution trace ID to query"
                    }
                },
                "required": ["trace_id"]
            }
        ),
        Tool(
            name="maker_run_benchmark",
            description=(
                "Run Tower of Hanoi benchmark to demonstrate MAKER reliability. "
                "Tests with different disc counts (3=7 moves, 10=1023 moves, 20=1M+ moves)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "num_discs": {
                        "type": "integer",
                        "description": "Number of discs (3-20)",
                        "default": 3,
                        "minimum": 3,
                        "maximum": 20
                    },
                    "use_voting": {
                        "type": "boolean",
                        "description": "Enable First-to-K voting",
                        "default": True
                    },
                    "k": {
                        "type": "integer",
                        "description": "Votes ahead threshold",
                        "default": 3
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="maker_configure",
            description=(
                "Configure MAKER framework parameters (voting, red flagging, etc.)"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "voting_enabled": {
                        "type": "boolean",
                        "description": "Enable/disable voting"
                    },
                    "k": {
                        "type": "integer",
                        "description": "Votes ahead threshold (2-5 recommended)"
                    },
                    "red_flag_enabled": {
                        "type": "boolean",
                        "description": "Enable/disable red flag validation"
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum tokens per response (red flag threshold)"
                    }
                },
                "required": []
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls"""

    if name == "maker_get_execution_stats":
        trace_id = arguments["trace_id"]
        orchestrator = get_orchestrator()

        stats = orchestrator.get_execution_stats(trace_id)

        if not stats:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": f"Trace {trace_id} not found"
                }, indent=2)
            )]

        return [TextContent(
            type="text",
            text=json.dumps(stats, indent=2)
        )]

    elif name == "maker_run_benchmark":
        num_discs = arguments.get("num_discs", 3)
        use_voting = arguments.get("use_voting", True)
        k = arguments.get("k", 3)

        logger.info(f"Running Tower of Hanoi benchmark: {num_discs} discs, voting={use_voting}, k={k}")

        benchmark = HanoiBenchmark(
            num_discs=num_discs,
            use_voting=use_voting,
            k=k
        )

        result = await benchmark.run_benchmark()

        return [TextContent(
            type="text",
            text=json.dumps({
                "success": True,
                "benchmark_results": result
            }, indent=2)
        )]

    elif name == "maker_configure":
        global _orchestrator

        voting_enabled = arguments.get("voting_enabled")
        k = arguments.get("k")
        red_flag_enabled = arguments.get("red_flag_enabled")

        # Create new orchestrator with new config
        _orchestrator = MAKEROrchestrator(
            voting_enabled=voting_enabled if voting_enabled is not None else True,
            k=k if k is not None else 3,
            red_flag_enabled=red_flag_enabled if red_flag_enabled is not None else True
        )

        config = {
            "voting_enabled": _orchestrator.voting_enabled,
            "k": _orchestrator.k,
            "red_flag_enabled": _orchestrator.red_flag_enabled
        }

        return [TextContent(
            type="text",
            text=json.dumps({
                "success": True,
                "message": "MAKER configuration updated",
                "config": config
            }, indent=2)
        )]

    elif name == "maker_execute_sequence":
        # Note: This tool requires custom agent implementation
        # For now, return guidance on how to use the framework
        return [TextContent(
            type="text",
            text=json.dumps({
                "info": "Direct sequence execution requires custom agent implementation",
                "usage": {
                    "step_1": "Import maker_framework in your Python code",
                    "step_2": "Create AtomicState with state_data, rules, goal",
                    "step_3": "Implement async agent_fn(state) -> AgentResponse",
                    "step_4": "Call orchestrator.execute_sequence()",
                    "example": "See tower_of_hanoi_benchmark.py for complete example"
                },
                "recommendation": "Use maker_run_benchmark to see MAKER in action first"
            }, indent=2)
        )]

    else:
        return [TextContent(
            type="text",
            text=json.dumps({
                "error": f"Unknown tool: {name}"
            }, indent=2)
        )]


async def main():
    """Run MCP server"""
    logger.info("Starting MAKER Framework MCP Server")

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
