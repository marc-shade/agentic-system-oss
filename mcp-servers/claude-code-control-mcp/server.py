#!/usr/bin/env python3
"""
Claude Code Control MCP Server
Programmatic task execution using Claude AI for autonomous coding workflows

Enables:
- Programmatic code task execution
- Codebase reading and searching
- File modification tracking
- Command execution
- Status monitoring

Architecture:
- Uses Anthropic API for Claude Sonnet 4.5
- MCP protocol for tool integration
- File tracking for change monitoring
- Async execution for performance
"""
import platform

import asyncio
import json
import logging
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio

from executor import TaskExecutor
from file_tracker import FileTracker

# Set up logging - CRITICAL: Must use stderr for MCP compatibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("claude-code-control")

# Initialize MCP server
app = Server("claude-code-control")

# Global state
executor: Optional[TaskExecutor] = None
current_execution: Optional[Dict] = None
execution_lock = asyncio.Lock()


def init_executor():
    """Initialize the task executor"""
    global executor
    try:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            logger.error("ANTHROPIC_API_KEY not found in environment")
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")

        executor = TaskExecutor(api_key=api_key)
        logger.info("Task executor initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize executor: {e}")
        raise


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available MCP tools"""
    return [
        Tool(
            name="execute_code_task",
            description=(
                "Execute a coding task using Claude AI. The AI will autonomously "
                "read files, write code, modify files, and run commands to complete the task. "
                "Returns execution results with file changes and outputs."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task_description": {
                        "type": "string",
                        "description": "Natural language description of the coding task to execute"
                    },
                    "working_directory": {
                        "type": "string",
                        "description": "Base directory for operations (default: /mnt/agentic-system)"
                    },
                    "context_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of relevant files to provide as context"
                    },
                    "max_iterations": {
                        "type": "integer",
                        "description": "Maximum number of tool use iterations (default: 20)"
                    }
                },
                "required": ["task_description"]
            }
        ),
        Tool(
            name="read_codebase",
            description=(
                "Read and analyze files in the codebase. Supports glob patterns "
                "for batch reading. Returns file contents and metadata."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "patterns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Glob patterns for files to read (e.g., '*.py', 'src/**/*.ts')"
                    },
                    "working_directory": {
                        "type": "string",
                        "description": "Base directory (default: /mnt/agentic-system)"
                    },
                    "max_files": {
                        "type": "integer",
                        "description": "Maximum number of files to read (default: 50)"
                    }
                },
                "required": ["patterns"]
            }
        ),
        Tool(
            name="search_code",
            description=(
                "Search for code patterns across the codebase using grep-like functionality. "
                "Supports regex patterns and file filtering."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search pattern (supports regex)"
                    },
                    "working_directory": {
                        "type": "string",
                        "description": "Base directory to search (default: /mnt/agentic-system)"
                    },
                    "file_pattern": {
                        "type": "string",
                        "description": "File pattern to filter (e.g., '*.py', '*.js')"
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "Case sensitive search (default: true)"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results to return (default: 100)"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="modify_files",
            description=(
                "Modify multiple files with specified changes. Provides batch file "
                "modification capability with change tracking."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "changes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string"},
                                "action": {"type": "string", "enum": ["write", "edit", "delete"]},
                                "content": {"type": "string"},
                                "old_content": {"type": "string"},
                                "new_content": {"type": "string"}
                            }
                        },
                        "description": "List of file modifications to apply"
                    },
                    "working_directory": {
                        "type": "string",
                        "description": "Base directory (default: /mnt/agentic-system)"
                    }
                },
                "required": ["changes"]
            }
        ),
        Tool(
            name="run_commands",
            description=(
                "Execute one or more shell commands in the working directory. "
                "Useful for testing, building, installing dependencies, etc."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "commands": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of shell commands to execute"
                    },
                    "working_directory": {
                        "type": "string",
                        "description": "Working directory for commands (default: /mnt/agentic-system)"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout per command in seconds (default: 30)"
                    }
                },
                "required": ["commands"]
            }
        ),
        Tool(
            name="get_execution_status",
            description=(
                "Get status of current or recent task execution. "
                "Returns execution progress, file changes, and results."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "include_history": {
                        "type": "boolean",
                        "description": "Include execution history (default: false)"
                    }
                }
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> List[TextContent]:
    """Handle tool calls"""
    global current_execution

    try:
        if name == "execute_code_task":
            async with execution_lock:
                if not executor:
                    return [TextContent(
                        type="text",
                        text=json.dumps({"error": "Executor not initialized"})
                    )]

                task_description = arguments["task_description"]
                working_directory = arguments.get("working_directory", os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE)))
                context_files = arguments.get("context_files", [])
                max_iterations = arguments.get("max_iterations", 20)

                logger.info(f"Executing task: {task_description[:100]}...")

                result = await executor.execute_task(
                    task_description=task_description,
                    working_directory=working_directory,
                    context_files=context_files,
                    max_iterations=max_iterations
                )

                current_execution = result

                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]

        elif name == "read_codebase":
            patterns = arguments["patterns"]
            working_directory = arguments.get("working_directory", os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE)))
            max_files = arguments.get("max_files", 50)

            working_dir = Path(working_directory)
            files_read = []

            for pattern in patterns:
                matching_files = list(working_dir.glob(pattern))[:max_files - len(files_read)]
                for file_path in matching_files:
                    if file_path.is_file():
                        try:
                            with open(file_path, 'r') as f:
                                content = f.read()
                            files_read.append({
                                "path": str(file_path.relative_to(working_dir)),
                                "size": len(content),
                                "content": content[:10000]  # Limit per file
                            })
                        except Exception as e:
                            logger.warning(f"Failed to read {file_path}: {e}")

                if len(files_read) >= max_files:
                    break

            result = {
                "files_read": len(files_read),
                "files": files_read
            }

            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        elif name == "search_code":
            import subprocess

            query = arguments["query"]
            working_directory = arguments.get("working_directory", os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE)))
            file_pattern = arguments.get("file_pattern", "*")
            case_sensitive = arguments.get("case_sensitive", True)
            max_results = arguments.get("max_results", 100)

            cmd = ["grep", "-r", "-n"]
            if not case_sensitive:
                cmd.append("-i")
            cmd.append(query)
            cmd.append(working_directory)
            if file_pattern != "*":
                cmd.extend(["--include", file_pattern])

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                lines = result.stdout.split('\n')[:max_results]
                matches = {
                    "query": query,
                    "total_matches": len(lines),
                    "matches": lines
                }

                return [TextContent(
                    type="text",
                    text=json.dumps(matches, indent=2)
                )]
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)})
                )]

        elif name == "modify_files":
            changes = arguments["changes"]
            working_directory = arguments.get("working_directory", os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE)))
            working_dir = Path(working_directory)

            file_tracker = FileTracker(working_directory)
            results = []

            for change in changes:
                path = working_dir / change["path"]
                action = change["action"]

                try:
                    if action == "write":
                        file_tracker.track_file(change["path"])
                        path.parent.mkdir(parents=True, exist_ok=True)
                        with open(path, 'w') as f:
                            f.write(change["content"])
                        results.append({"path": change["path"], "status": "written"})

                    elif action == "edit":
                        file_tracker.track_file(change["path"])
                        with open(path, 'r') as f:
                            content = f.read()
                        new_content = content.replace(
                            change["old_content"],
                            change["new_content"]
                        )
                        with open(path, 'w') as f:
                            f.write(new_content)
                        results.append({"path": change["path"], "status": "edited"})

                    elif action == "delete":
                        file_tracker.track_file(change["path"])
                        path.unlink()
                        results.append({"path": change["path"], "status": "deleted"})

                except Exception as e:
                    results.append({"path": change["path"], "status": "error", "error": str(e)})

            file_changes = file_tracker.check_changes()
            summary = file_tracker.get_summary()

            result = {
                "modifications": results,
                "file_changes": summary
            }

            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        elif name == "run_commands":
            import subprocess

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


            commands = arguments["commands"]
            working_directory = arguments.get("working_directory", os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE)))
            timeout = arguments.get("timeout", 30)

            results = []
            for cmd in commands:
                try:
                    result = subprocess.run(
                        shlex.split(cmd),
                        shell=False,
                        cwd=working_directory,
                        capture_output=True,
                        text=True,
                        timeout=timeout
                    )
                    results.append({
                        "command": cmd,
                        "exit_code": result.returncode,
                        "stdout": result.stdout[:1000],
                        "stderr": result.stderr[:1000]
                    })
                except Exception as e:
                    results.append({
                        "command": cmd,
                        "error": str(e)
                    })

            return [TextContent(
                type="text",
                text=json.dumps({"command_results": results}, indent=2)
            )]

        elif name == "get_execution_status":
            include_history = arguments.get("include_history", False)

            status = {
                "current_execution": current_execution,
                "executor_initialized": executor is not None
            }

            if include_history and executor:
                status["execution_history"] = executor.get_execution_history()

            return [TextContent(
                type="text",
                text=json.dumps(status, indent=2)
            )]

        else:
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Unknown tool: {name}"})
            )]

    except Exception as e:
        logger.error(f"Tool execution error ({name}): {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=json.dumps({"error": str(e)})
        )]


async def main():
    """Main entry point"""
    try:
        # Initialize executor
        init_executor()

        # Run MCP server
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            logger.info("Claude Code Control MCP Server started")
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options()
            )
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
