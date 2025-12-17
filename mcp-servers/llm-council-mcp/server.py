#!/usr/bin/env python3
"""
LLM Council MCP Server
======================

Multi-provider LLM deliberation system exposed via Model Context Protocol.

A 3-stage deliberation process where multiple LLMs collaboratively answer questions:
1. Collect individual responses from all council models
2. Anonymized peer review - models rank each other's responses
3. Chairman synthesizes final answer from all inputs

Also supports 9 deliberation patterns for different use cases.

MCP Tools:
- council_deliberate: Run full 3-stage deliberation
- council_quick_query: Quick single-provider query
- council_get_providers: List available CLI providers
- council_list_patterns: List deliberation patterns
- council_run_pattern: Run specific pattern
- council_compare_providers: Compare all providers on same prompt

Requirements:
- pip install mcp
- CLI tools installed: claude, codex, gemini (any combination)

Environment Variables:
- PROVIDER_MODE: "cli" (default) or "openrouter"
- CLI_COUNCIL_MODELS: Comma-separated providers (default: claude,codex,gemini)
- CLI_CHAIRMAN_MODEL: Synthesis provider (default: codex)
- LLM_COUNCIL_DATA_DIR: Data directory for saved conversations
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

try:
    from mcp.server.models import InitializationOptions
    from mcp.server import NotificationOptions, Server
    import mcp.server.stdio
    import mcp.types as types
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install mcp")
    sys.exit(1)

# Import backend modules
from backend.config import (
    PROVIDER_MODE,
    CLI_COUNCIL_MODELS,
    CLI_CHAIRMAN_MODEL,
    get_active_config,
)
from backend.council import run_full_council
from backend.cli_providers import (
    get_available_providers,
    query_cli_provider,
    query_providers_parallel,
)
from backend.patterns import list_patterns, run_pattern

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("llm-council-mcp")

# Configuration
DATA_DIR = Path(os.environ.get(
    "LLM_COUNCIL_DATA_DIR",
    Path.home() / ".llm-council"
))
DATA_DIR.mkdir(parents=True, exist_ok=True)
CONVERSATIONS_DIR = DATA_DIR / "conversations"
CONVERSATIONS_DIR.mkdir(exist_ok=True)

# Create MCP server
server = Server("llm-council")


def save_conversation(question: str, result: Dict[str, Any]) -> str:
    """Save conversation to disk and return conversation ID."""
    conv_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    conv_file = CONVERSATIONS_DIR / f"{conv_id}.json"

    conversation = {
        "id": conv_id,
        "created_at": datetime.now().isoformat(),
        "question": question,
        "result": result,
    }

    conv_file.write_text(json.dumps(conversation, indent=2))
    return conv_id


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available LLM Council tools."""
    return [
        types.Tool(
            name="council_deliberate",
            description="Run full 3-stage council deliberation on a question",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Question to deliberate"
                    },
                    "save": {
                        "type": "boolean",
                        "description": "Save conversation",
                        "default": True
                    }
                },
                "required": ["question"]
            }
        ),
        types.Tool(
            name="council_quick_query",
            description="Query a single provider for a fast response",
            inputSchema={
                "type": "object",
                "properties": {
                    "provider": {
                        "type": "string",
                        "enum": ["claude", "codex", "gemini"],
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Prompt to send"
                    },
                    "timeout": {
                        "type": "number",
                        "description": "Timeout in seconds",
                        "default": 60
                    }
                },
                "required": ["provider", "prompt"]
            }
        ),
        types.Tool(
            name="council_get_providers",
            description="List available LLM providers",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="council_list_patterns",
            description="List all available deliberation patterns",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="council_run_pattern",
            description="Run a specific deliberation pattern (debate, socratic, red_team, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "enum": [
                            "deliberation", "debate", "devils_advocate",
                            "socratic", "red_team", "tree_of_thought",
                            "self_consistency", "round_robin", "expert_panel"
                        ]
                    },
                    "question": {
                        "type": "string"
                    },
                    "rounds": {
                        "type": "integer",
                        "default": 2
                    },
                    "branches": {
                        "type": "integer",
                        "default": 3
                    }
                },
                "required": ["pattern", "question"]
            }
        ),
        types.Tool(
            name="council_compare_providers",
            description="Compare all providers on the same prompt",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string"
                    }
                },
                "required": ["prompt"]
            }
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool calls."""

    if not arguments:
        arguments = {}

    if name == "council_deliberate":
        question = arguments.get("question", "")
        save = arguments.get("save", True)

        if not question:
            return [types.TextContent(
                type="text",
                text=json.dumps({"error": "No question provided"})
            )]

        logger.info(f"Starting deliberation: {question[:50]}...")

        try:
            result = await run_full_council(question)

            if save and result.get("success"):
                conv_id = save_conversation(question, result)
                result["conversation_id"] = conv_id

            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        except Exception as e:
            logger.error(f"Deliberation failed: {e}")
            return [types.TextContent(
                type="text",
                text=json.dumps({"error": str(e)})
            )]

    elif name == "council_quick_query":
        provider = arguments.get("provider", "claude")
        prompt = arguments.get("prompt", "")
        timeout = arguments.get("timeout", 60)

        if not prompt:
            return [types.TextContent(
                type="text",
                text=json.dumps({"error": "No prompt provided"})
            )]

        result = await query_cli_provider(provider, prompt, timeout)

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "provider": provider,
                "response": result.get("content"),
                "error": result.get("error"),
            }, indent=2)
        )]

    elif name == "council_get_providers":
        available = get_available_providers()
        config = get_active_config()

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "available_providers": available,
                "config": config,
            }, indent=2)
        )]

    elif name == "council_list_patterns":
        patterns = list_patterns()

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "patterns": patterns
            }, indent=2)
        )]

    elif name == "council_run_pattern":
        pattern_id = arguments.get("pattern", "deliberation")
        question = arguments.get("question", "")
        rounds = arguments.get("rounds", 2)
        branches = arguments.get("branches", 3)

        if not question:
            return [types.TextContent(
                type="text",
                text=json.dumps({"error": "No question provided"})
            )]

        logger.info(f"Running pattern {pattern_id}: {question[:50]}...")

        result = await run_pattern(
            pattern_id,
            question,
            rounds=rounds,
            branches=branches
        )

        return [types.TextContent(
            type="text",
            text=json.dumps(result, indent=2, default=str)
        )]

    elif name == "council_compare_providers":
        prompt = arguments.get("prompt", "")

        if not prompt:
            return [types.TextContent(
                type="text",
                text=json.dumps({"error": "No prompt provided"})
            )]

        available = get_available_providers()
        results = await query_providers_parallel(available, prompt)

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "prompt": prompt,
                "providers_queried": available,
                "results": {
                    p: {
                        "response": r.get("content"),
                        "error": r.get("error"),
                        "length": len(r.get("content", "")) if r.get("content") else 0
                    }
                    for p, r in results.items()
                }
            }, indent=2)
        )]

    else:
        return [types.TextContent(
            type="text",
            text=json.dumps({"error": f"Unknown tool: {name}"})
        )]


async def main():
    """Run the MCP server."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info("LLM Council MCP Server starting...")
        logger.info(f"Available providers: {get_available_providers()}")
        logger.info(f"Data directory: {DATA_DIR}")

        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="llm-council",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
