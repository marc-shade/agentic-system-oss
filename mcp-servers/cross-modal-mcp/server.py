#!/usr/bin/env python3
"""
Cross-Modal MCP Server

Provides unified access to cross-modal memory capabilities:
- Cross-modal semantic search (visual + text + code)
- Temporal context retrieval
- Code change tracking
- Text memory recording
- Unified AGI context

STATUS: Production Ready
"""

import asyncio
import json
import logging
import sys
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.types import Tool, TextContent

sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/intelligent-agents')
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/shared')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Server("cross-modal-mcp")


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available cross-modal tools."""
    return [
        Tool(
            name="cross_modal_search",
            description="Search across visual, text, and code memories simultaneously. Returns ranked results by semantic similarity.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    },
                    "modalities": {
                        "type": "string",
                        "description": "Comma-separated modalities to search: visual,text,code or 'all'",
                        "default": "all"
                    },
                    "hours": {
                        "type": "integer",
                        "description": "Time range in hours",
                        "default": 24
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return",
                        "default": 20
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_temporal_context",
            description="Get all memories across modalities within a time window around a specific timestamp. Useful for understanding what was happening at a point in time.",
            inputSchema={
                "type": "object",
                "properties": {
                    "timestamp": {
                        "type": "string",
                        "description": "ISO format timestamp (e.g., 2024-01-15T10:30:00)"
                    },
                    "window_minutes": {
                        "type": "integer",
                        "description": "Time window in minutes before and after",
                        "default": 10
                    }
                },
                "required": ["timestamp"]
            }
        ),
        Tool(
            name="get_unified_summary",
            description="Get a unified summary of memory activity across all modalities. Shows counts, correlations, and activity patterns.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hours": {
                        "type": "integer",
                        "description": "Time range in hours",
                        "default": 24
                    }
                }
            }
        ),
        Tool(
            name="record_code_change",
            description="Record a code change event to the cross-modal memory. Automatically finds correlations with visual and text memories.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the changed file"
                    },
                    "change_type": {
                        "type": "string",
                        "description": "Type of change: add, modify, delete, refactor"
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of the change"
                    },
                    "diff_summary": {
                        "type": "string",
                        "description": "Summary of the diff (optional)"
                    }
                },
                "required": ["file_path", "change_type", "description"]
            }
        ),
        Tool(
            name="record_text_memory",
            description="Record text content as a memory. Useful for capturing important notes, decisions, or conversation highlights.",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The text content to record"
                    },
                    "text_type": {
                        "type": "string",
                        "description": "Type of text: note, decision, conversation, insight",
                        "default": "note"
                    },
                    "summary": {
                        "type": "string",
                        "description": "Brief summary (optional)"
                    }
                },
                "required": ["content"]
            }
        ),
        Tool(
            name="get_file_context",
            description="Get all cross-modal context related to a specific file. Shows code changes, visual context during changes, and related text memories.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file"
                    },
                    "hours": {
                        "type": "integer",
                        "description": "Time range in hours",
                        "default": 48
                    }
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="find_correlations",
            description="Find cross-modal correlations in a time range. Discovers what visual, text, and code activities happened together.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hours": {
                        "type": "integer",
                        "description": "Time range in hours",
                        "default": 24
                    },
                    "min_strength": {
                        "type": "number",
                        "description": "Minimum correlation strength (0-1)",
                        "default": 0.5
                    }
                }
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls."""
    try:
        from cross_modal_integration import (
            CrossModalMemoryManager,
            MemoryModality
        )

        manager = CrossModalMemoryManager()
        result = {}

        if name == "cross_modal_search":
            query = arguments.get("query", "")
            modalities_str = arguments.get("modalities", "all")
            hours = arguments.get("hours", 24)
            limit = arguments.get("limit", 20)

            mod_list = None
            if modalities_str != "all":
                mod_list = [MemoryModality(m.strip()) for m in modalities_str.split(",")]

            results = await manager.search(query, mod_list, hours=hours, limit=limit)

            result = {
                "success": True,
                "query": query,
                "modalities": modalities_str,
                "results": [
                    {
                        "id": m.id,
                        "modality": m.modality.value,
                        "timestamp": m.timestamp,
                        "content_summary": str(m.content)[:300],
                        "concepts": m.concepts[:5]
                    }
                    for m in results
                ],
                "count": len(results)
            }

        elif name == "get_temporal_context":
            timestamp = arguments.get("timestamp", "")
            window = arguments.get("window_minutes", 10)

            ctx = manager.get_temporal_context(timestamp, window)

            result = {
                "success": True,
                "center_time": ctx.center_time,
                "window_minutes": ctx.window_minutes,
                "visual_memories": [
                    {
                        "id": m.id,
                        "timestamp": m.timestamp,
                        "content": str(m.content)[:200]
                    }
                    for m in ctx.visual_memories[:10]
                ],
                "text_memories": [
                    {
                        "id": m.id,
                        "timestamp": m.timestamp,
                        "content": str(m.content)[:200]
                    }
                    for m in ctx.text_memories[:10]
                ],
                "code_memories": [
                    {
                        "id": m.id,
                        "timestamp": m.timestamp,
                        "content": str(m.content)[:200]
                    }
                    for m in ctx.code_memories[:10]
                ],
                "correlations": ctx.correlations[:10],
                "summary": {
                    "visual_count": len(ctx.visual_memories),
                    "text_count": len(ctx.text_memories),
                    "code_count": len(ctx.code_memories),
                    "total_correlations": len(ctx.correlations)
                }
            }

        elif name == "get_unified_summary":
            hours = arguments.get("hours", 24)
            result = manager.get_unified_summary(hours)
            result["success"] = True

        elif name == "record_code_change":
            file_path = arguments.get("file_path", "")
            change_type = arguments.get("change_type", "modify")
            description = arguments.get("description", "")
            diff_summary = arguments.get("diff_summary", "")

            memory = await manager.record_code_change(
                file_path=file_path,
                change_type=change_type,
                description=description,
                diff_summary=diff_summary
            )

            result = {
                "success": True,
                "memory_id": memory.id,
                "concepts": memory.concepts,
                "correlations_found": len(memory.context_links)
            }

        elif name == "record_text_memory":
            content = arguments.get("content", "")
            text_type = arguments.get("text_type", "note")
            summary = arguments.get("summary", "")

            memory = await manager.record_text(
                content=content,
                text_type=text_type,
                summary=summary
            )

            result = {
                "success": True,
                "memory_id": memory.id,
                "concepts": memory.concepts
            }

        elif name == "get_file_context":
            file_path = arguments.get("file_path", "")
            hours = arguments.get("hours", 48)

            result = manager.get_context_for_file(file_path, hours)
            result["success"] = True

        elif name == "find_correlations":
            hours = arguments.get("hours", 24)
            min_strength = arguments.get("min_strength", 0.5)

            # Get correlations from the database
            import sqlite3
            from datetime import datetime, timedelta
            import os

            db_path = os.path.join(manager.storage_path, "cross_modal_index.db")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

            cursor.execute('''
                SELECT memory_id_1, modality_1, memory_id_2, modality_2,
                       time_delta_seconds, correlation_strength, context_type
                FROM temporal_correlations
                WHERE created_at > ? AND correlation_strength >= ?
                ORDER BY correlation_strength DESC
                LIMIT 50
            ''', (cutoff, min_strength))

            correlations = []
            for row in cursor.fetchall():
                correlations.append({
                    "memory_1": {"id": row[0], "modality": row[1]},
                    "memory_2": {"id": row[2], "modality": row[3]},
                    "time_delta_seconds": row[4],
                    "strength": row[5],
                    "context_type": row[6]
                })

            conn.close()

            result = {
                "success": True,
                "hours": hours,
                "min_strength": min_strength,
                "correlations": correlations,
                "count": len(correlations)
            }

        else:
            result = {"success": False, "error": f"Unknown tool: {name}"}

        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

    except Exception as e:
        logger.error(f"Tool {name} failed: {e}")
        return [TextContent(
            type="text",
            text=json.dumps({"success": False, "error": str(e)})
        )]


async def main():
    """Run the MCP server."""
    from mcp.server.stdio import stdio_server

    logger.info("Starting Cross-Modal MCP Server...")

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
