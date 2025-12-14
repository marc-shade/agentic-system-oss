#!/usr/bin/env python3
"""
Agent Eval MCP Server

MCP server wrapper for the Agent Eval Framework.
Implements Eugene Yan's 3-step eval methodology:
1. Label data (add_labeled_example)
2. Align evaluator (run_alignment_check)
3. Run eval harness (evaluate_output)
"""

import sys
import os

# Add intelligent-agents to path
sys.path.insert(0, '/mnt/agentic-system/intelligent-agents')

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import json

from agent_eval_framework import (
    EvalHarness, EvalDataset, EvalCriteria, LabeledExample,
    AGENTIC_CRITERIA
)

server = Server("agent-eval")
harness = EvalHarness()
dataset = EvalDataset()


@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="eval_add_criteria",
            description="Add a new evaluation criteria definition",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Unique criteria name"},
                    "description": {"type": "string", "description": "What this criteria evaluates"},
                    "pass_description": {"type": "string", "description": "What constitutes a PASS"},
                    "fail_description": {"type": "string", "description": "What constitutes a FAIL"},
                    "examples_pass": {"type": "array", "items": {"type": "string"}, "description": "Example passing outputs"},
                    "examples_fail": {"type": "array", "items": {"type": "string"}, "description": "Example failing outputs"}
                },
                "required": ["name", "description", "pass_description", "fail_description"]
            }
        ),
        Tool(
            name="eval_add_labeled_example",
            description="Step 1: Add a human-labeled example to the dataset for alignment",
            inputSchema={
                "type": "object",
                "properties": {
                    "criteria_name": {"type": "string", "description": "Which criteria this example is for"},
                    "output_text": {"type": "string", "description": "The output to label"},
                    "label": {"type": "string", "enum": ["pass", "fail"], "description": "Human judgment"},
                    "reasoning": {"type": "string", "description": "Why this label was chosen"},
                    "input_text": {"type": "string", "description": "Optional input context"}
                },
                "required": ["criteria_name", "output_text", "label", "reasoning"]
            }
        ),
        Tool(
            name="eval_run_alignment",
            description="Step 2: Check if LLM judge aligns with human labels. Returns alignment score.",
            inputSchema={
                "type": "object",
                "properties": {
                    "criteria_name": {"type": "string", "description": "Criteria to check alignment for"}
                },
                "required": ["criteria_name"]
            }
        ),
        Tool(
            name="eval_evaluate_output",
            description="Step 3: Evaluate an output using the aligned LLM judge",
            inputSchema={
                "type": "object",
                "properties": {
                    "criteria_name": {"type": "string", "description": "Which criteria to evaluate against"},
                    "output_text": {"type": "string", "description": "Output text to evaluate"},
                    "input_text": {"type": "string", "description": "Optional input context"}
                },
                "required": ["criteria_name", "output_text"]
            }
        ),
        Tool(
            name="eval_list_criteria",
            description="List all available evaluation criteria",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="eval_get_stats",
            description="Get evaluation statistics and alignment scores",
            inputSchema={
                "type": "object",
                "properties": {
                    "criteria_name": {"type": "string", "description": "Optional criteria filter"}
                }
            }
        ),
        Tool(
            name="eval_batch_evaluate",
            description="Evaluate multiple outputs at once",
            inputSchema={
                "type": "object",
                "properties": {
                    "criteria_name": {"type": "string", "description": "Which criteria to evaluate against"},
                    "outputs": {"type": "array", "items": {"type": "string"}, "description": "List of outputs to evaluate"}
                },
                "required": ["criteria_name", "outputs"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    try:
        if name == "eval_add_criteria":
            criteria = EvalCriteria(
                name=arguments["name"],
                description=arguments["description"],
                pass_description=arguments["pass_description"],
                fail_description=arguments["fail_description"],
                examples_pass=arguments.get("examples_pass", []),
                examples_fail=arguments.get("examples_fail", [])
            )
            dataset.add_criteria(criteria)
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "message": f"Added criteria: {criteria.name}"
                })
            )]

        elif name == "eval_add_labeled_example":
            example = LabeledExample(
                id="",
                input_text=arguments.get("input_text", ""),
                output_text=arguments["output_text"],
                label=arguments["label"],
                criteria_name=arguments["criteria_name"],
                reasoning=arguments["reasoning"]
            )
            dataset.add_example(example)
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "example_id": example.id,
                    "message": f"Added {arguments['label']} example for {arguments['criteria_name']}"
                })
            )]

        elif name == "eval_run_alignment":
            result = harness.run_alignment_check(arguments["criteria_name"])
            return [TextContent(
                type="text",
                text=json.dumps(result, default=str)
            )]

        elif name == "eval_evaluate_output":
            result = harness.evaluate_output(
                arguments["criteria_name"],
                arguments["output_text"],
                arguments.get("input_text", "")
            )
            return [TextContent(
                type="text",
                text=json.dumps({
                    "label": result.predicted_label,
                    "confidence": result.confidence,
                    "reasoning": result.reasoning,
                    "criteria": result.criteria_name
                })
            )]

        elif name == "eval_list_criteria":
            # List predefined + custom criteria
            import sqlite3
            conn = sqlite3.connect(dataset.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT name, description FROM criteria')
            rows = cursor.fetchall()
            conn.close()

            criteria_list = [{"name": r[0], "description": r[1]} for r in rows]
            return [TextContent(
                type="text",
                text=json.dumps({
                    "criteria": criteria_list,
                    "count": len(criteria_list)
                })
            )]

        elif name == "eval_get_stats":
            stats = harness.get_stats(arguments.get("criteria_name"))
            alignment = dataset.get_alignment_score(arguments.get("criteria_name", "")) if arguments.get("criteria_name") else 0
            stats["current_alignment"] = alignment
            return [TextContent(
                type="text",
                text=json.dumps(stats)
            )]

        elif name == "eval_batch_evaluate":
            results = []
            for output in arguments["outputs"]:
                result = harness.evaluate_output(
                    arguments["criteria_name"],
                    output
                )
                results.append({
                    "output_preview": output[:100] + "..." if len(output) > 100 else output,
                    "label": result.predicted_label,
                    "confidence": result.confidence
                })

            pass_count = sum(1 for r in results if r["label"] == "pass")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "results": results,
                    "summary": {
                        "total": len(results),
                        "pass": pass_count,
                        "fail": len(results) - pass_count,
                        "pass_rate": pass_count / len(results) if results else 0
                    }
                })
            )]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps({"error": str(e)})
        )]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
