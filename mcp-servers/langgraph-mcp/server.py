#!/usr/bin/env python3
"""LangGraph MCP Server - Stateful agent workflows with persistence."""
import asyncio
import json
import uuid
from typing import Any, Optional
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import persistence
from checkpointing import get_checkpointer, SQLiteCheckpointer
from human_loop import create_human_approval, wait_for_approval, ApprovalType
from graphs import create_research_graph, create_code_review_graph, create_autonomous_task_graph

server = Server("langgraph-mcp")

# LLM setup - lazy loaded
_llm = None

def get_llm():
    """Lazy load LLM to avoid import issues."""
    global _llm
    if _llm is None:
        try:
            from langchain_anthropic import ChatAnthropic
            _llm = ChatAnthropic(model="claude-sonnet-4-20250514", max_tokens=4096)
        except Exception:
            from langchain_openai import ChatOpenAI
            _llm = ChatOpenAI(model="gpt-4o", max_tokens=4096)
    return _llm

# Graph registry
_graphs = {}

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available LangGraph tools."""
    return [
        Tool(
            name="langgraph_run_research",
            description="Run a multi-step research agent with source tracking and synthesis",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Research query/topic"},
                    "thread_id": {"type": "string", "description": "Thread ID for persistence (optional)"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="langgraph_run_code_review",
            description="Run iterative code review with improvement suggestions",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Code to review"},
                    "language": {"type": "string", "description": "Programming language"},
                    "thread_id": {"type": "string", "description": "Thread ID for persistence (optional)"},
                    "max_iterations": {"type": "integer", "description": "Max review iterations (default 3)"}
                },
                "required": ["code", "language"]
            }
        ),
        Tool(
            name="langgraph_run_task",
            description="Run autonomous self-directing task completion agent",
            inputSchema={
                "type": "object",
                "properties": {
                    "objective": {"type": "string", "description": "Task objective to complete"},
                    "context": {"type": "object", "description": "Additional context (optional)"},
                    "thread_id": {"type": "string", "description": "Thread ID for persistence (optional)"}
                },
                "required": ["objective"]
            }
        ),
        Tool(
            name="langgraph_resume",
            description="Resume a paused or interrupted graph execution",
            inputSchema={
                "type": "object",
                "properties": {
                    "graph_id": {"type": "string", "description": "Graph type (research/code_review/task)"},
                    "thread_id": {"type": "string", "description": "Thread ID to resume"},
                    "checkpoint_id": {"type": "string", "description": "Specific checkpoint to resume from (optional)"}
                },
                "required": ["graph_id", "thread_id"]
            }
        ),
        Tool(
            name="langgraph_list_checkpoints",
            description="List all checkpoints for a thread",
            inputSchema={
                "type": "object",
                "properties": {
                    "graph_id": {"type": "string", "description": "Graph type"},
                    "thread_id": {"type": "string", "description": "Thread ID"}
                },
                "required": ["graph_id", "thread_id"]
            }
        ),
        Tool(
            name="langgraph_get_state",
            description="Get current state of a graph execution",
            inputSchema={
                "type": "object",
                "properties": {
                    "graph_id": {"type": "string", "description": "Graph type"},
                    "thread_id": {"type": "string", "description": "Thread ID"}
                },
                "required": ["graph_id", "thread_id"]
            }
        ),
        Tool(
            name="langgraph_request_approval",
            description="Request human approval with optional Arduino Surface integration",
            inputSchema={
                "type": "object",
                "properties": {
                    "thread_id": {"type": "string", "description": "Thread ID"},
                    "title": {"type": "string", "description": "Approval title"},
                    "description": {"type": "string", "description": "Approval description"},
                    "approval_type": {"type": "string", "enum": ["confirm", "review", "choice", "input"]},
                    "use_arduino": {"type": "boolean", "description": "Use Arduino for physical approval"}
                },
                "required": ["thread_id", "title", "description"]
            }
        ),
        Tool(
            name="langgraph_list_pending_approvals",
            description="List all pending human approval requests",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="langgraph_resolve_approval",
            description="Resolve a pending approval request",
            inputSchema={
                "type": "object",
                "properties": {
                    "approval_id": {"type": "integer", "description": "Approval request ID"},
                    "approved": {"type": "boolean", "description": "Whether to approve"},
                    "response_data": {"type": "object", "description": "Optional response data"}
                },
                "required": ["approval_id", "approved"]
            }
        ),
        Tool(
            name="langgraph_save_memory",
            description="Save memory entry for a thread",
            inputSchema={
                "type": "object",
                "properties": {
                    "thread_id": {"type": "string", "description": "Thread ID"},
                    "memory_type": {"type": "string", "description": "Memory type (short_term/long_term/episodic)"},
                    "content": {"type": "string", "description": "Memory content"},
                    "metadata": {"type": "object", "description": "Optional metadata"}
                },
                "required": ["thread_id", "memory_type", "content"]
            }
        ),
        Tool(
            name="langgraph_get_memories",
            description="Retrieve memories for a thread",
            inputSchema={
                "type": "object",
                "properties": {
                    "thread_id": {"type": "string", "description": "Thread ID"},
                    "memory_type": {"type": "string", "description": "Filter by memory type (optional)"},
                    "limit": {"type": "integer", "description": "Max memories to return (default 100)"}
                },
                "required": ["thread_id"]
            }
        ),
        Tool(
            name="langgraph_visualize",
            description="Generate visualization of a graph structure",
            inputSchema={
                "type": "object",
                "properties": {
                    "graph_id": {"type": "string", "description": "Graph type to visualize"}
                },
                "required": ["graph_id"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    try:
        await persistence.init_db()

        if name == "langgraph_run_research":
            thread_id = arguments.get("thread_id", str(uuid.uuid4()))
            checkpointer = get_checkpointer("research")
            graph = create_research_graph(get_llm(), checkpointer=checkpointer)
            config = {"configurable": {"thread_id": thread_id}}
            result = await graph.ainvoke({
                "thread_id": thread_id,
                "query": arguments["query"],
                "sources": [],
                "findings": [],
                "synthesis": "",
                "approved": False,
                "messages": []
            }, config)
            return [TextContent(type="text", text=json.dumps({
                "thread_id": thread_id,
                "synthesis": result.get("synthesis", ""),
                "sources_count": len(result.get("sources", [])),
                "findings_count": len(result.get("findings", []))
            }, indent=2))]

        elif name == "langgraph_run_code_review":
            thread_id = arguments.get("thread_id", str(uuid.uuid4()))
            checkpointer = get_checkpointer("code_review")
            graph = create_code_review_graph(
                get_llm(),
                checkpointer=checkpointer,
                max_iterations=arguments.get("max_iterations", 3)
            )
            config = {"configurable": {"thread_id": thread_id}}
            result = await graph.ainvoke({
                "thread_id": thread_id,
                "code": arguments["code"],
                "language": arguments["language"],
                "review_iterations": 0,
                "issues": [],
                "suggestions": [],
                "improved_code": "",
                "approved": False,
                "messages": []
            }, config)
            return [TextContent(type="text", text=json.dumps({
                "thread_id": thread_id,
                "iterations": result.get("review_iterations", 0),
                "issues_count": len(result.get("issues", [])),
                "improved_code": result.get("improved_code", "")[:2000]
            }, indent=2))]

        elif name == "langgraph_run_task":
            thread_id = arguments.get("thread_id", str(uuid.uuid4()))
            checkpointer = get_checkpointer("task")
            graph = create_autonomous_task_graph(get_llm(), checkpointer=checkpointer)
            config = {"configurable": {"thread_id": thread_id}}
            result = await graph.ainvoke({
                "thread_id": thread_id,
                "objective": arguments["objective"],
                "current_step": "",
                "completed_steps": [],
                "pending_steps": [],
                "context": arguments.get("context", {}),
                "result": "",
                "status": "pending",
                "error": "",
                "approved": False,
                "messages": []
            }, config)
            return [TextContent(type="text", text=json.dumps({
                "thread_id": thread_id,
                "status": result.get("status", ""),
                "result": result.get("result", "")[:2000],
                "completed_steps": len(result.get("completed_steps", []))
            }, indent=2))]

        elif name == "langgraph_resume":
            graph_id = arguments["graph_id"]
            thread_id = arguments["thread_id"]
            checkpoint_id = arguments.get("checkpoint_id")

            state = await persistence.load_state(graph_id, thread_id, checkpoint_id)
            if not state:
                return [TextContent(type="text", text=json.dumps({"error": "No state found for thread"}))]

            checkpointer = get_checkpointer(graph_id)
            if graph_id == "research":
                graph = create_research_graph(get_llm(), checkpointer=checkpointer)
            elif graph_id == "code_review":
                graph = create_code_review_graph(get_llm(), checkpointer=checkpointer)
            elif graph_id == "task":
                graph = create_autonomous_task_graph(get_llm(), checkpointer=checkpointer)
            else:
                return [TextContent(type="text", text=json.dumps({"error": f"Unknown graph: {graph_id}"}))]

            config = {"configurable": {"thread_id": thread_id}}
            if checkpoint_id:
                config["configurable"]["checkpoint_id"] = checkpoint_id

            result = await graph.ainvoke(None, config)
            return [TextContent(type="text", text=json.dumps({"resumed": True, "thread_id": thread_id, "result": str(result)[:2000]}, indent=2))]

        elif name == "langgraph_list_checkpoints":
            checkpoints = await persistence.list_checkpoints(arguments["graph_id"], arguments["thread_id"])
            return [TextContent(type="text", text=json.dumps({"checkpoints": checkpoints}, indent=2))]

        elif name == "langgraph_get_state":
            state = await persistence.load_state(arguments["graph_id"], arguments["thread_id"])
            return [TextContent(type="text", text=json.dumps({"state": state}, indent=2))]

        elif name == "langgraph_request_approval":
            result = await create_human_approval(
                thread_id=arguments["thread_id"],
                approval_type=ApprovalType(arguments.get("approval_type", "confirm")),
                title=arguments["title"],
                description=arguments["description"],
                use_arduino=arguments.get("use_arduino", True)
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "langgraph_list_pending_approvals":
            approvals = await persistence.get_pending_approvals()
            return [TextContent(type="text", text=json.dumps({"pending_approvals": approvals}, indent=2))]

        elif name == "langgraph_resolve_approval":
            result = await persistence.resolve_approval(
                arguments["approval_id"],
                arguments["approved"],
                arguments.get("response_data")
            )
            return [TextContent(type="text", text=json.dumps({"resolved": result}, indent=2))]

        elif name == "langgraph_save_memory":
            memory_id = await persistence.save_memory(
                arguments["thread_id"],
                arguments["memory_type"],
                arguments["content"],
                arguments.get("metadata")
            )
            return [TextContent(type="text", text=json.dumps({"memory_id": memory_id}, indent=2))]

        elif name == "langgraph_get_memories":
            memories = await persistence.get_memories(
                arguments["thread_id"],
                arguments.get("memory_type"),
                arguments.get("limit", 100)
            )
            return [TextContent(type="text", text=json.dumps({"memories": memories}, indent=2))]

        elif name == "langgraph_visualize":
            graph_id = arguments["graph_id"]
            if graph_id == "research":
                structure = "plan -> gather -> [gather_more | analyze] -> synthesize -> END"
            elif graph_id == "code_review":
                structure = "analyze -> suggest -> improve -> [iterate:analyze | done:END]"
            elif graph_id == "task":
                structure = "plan -> execute -> evaluate -> [execute | replan | synthesize | error] -> END"
            else:
                structure = "Unknown graph type"

            return [TextContent(type="text", text=json.dumps({
                "graph_id": graph_id,
                "structure": structure,
                "mermaid": f"""graph TD
    A[Start] --> B[{graph_id}]
    B --> C[Process]
    C --> D{{Decision}}
    D --> E[End]"""
            }, indent=2))]

        else:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

async def main():
    """Run the MCP server."""
    await persistence.init_db()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
