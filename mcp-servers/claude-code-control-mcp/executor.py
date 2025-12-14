#!/usr/bin/env python3
"""
Task Execution Engine for Claude Code Control MCP
Executes coding tasks using Claude AI with tool use
"""
import platform

import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from anthropic import Anthropic
from file_tracker import FileTracker

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


logger = logging.getLogger("claude-code-control.executor")


class TaskExecutor:
    """Executes coding tasks using Claude AI"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment or constructor")

        self.client = Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-5-20250929"
        self.execution_history: List[Dict] = []

    def _build_system_prompt(self, working_directory: str, context_files: List[str] = None) -> str:
        """Build system prompt for the coding assistant"""
        prompt = f"""You are an expert coding assistant executing tasks in the directory: {working_directory}

Your capabilities:
1. Read and analyze code files
2. Write new code files
3. Modify existing files
4. Execute shell commands
5. Search through codebases

Guidelines:
- Always verify file existence before modifying
- Use relative paths from working directory
- Provide clear explanations for changes
- Follow best practices and existing code style
- Handle errors gracefully
- Test changes when possible

Current working directory: {working_directory}
"""

        if context_files:
            prompt += f"\nRelevant context files:\n"
            for f in context_files:
                prompt += f"- {f}\n"

        return prompt

    def _build_tools(self) -> List[Dict]:
        """Build tool definitions for Claude"""
        return [
            {
                "name": "read_file",
                "description": "Read the contents of a file. Use this before modifying files to understand current state.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path to the file from working directory"
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "write_file",
                "description": "Write content to a file. Creates new file or overwrites existing.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path to the file from working directory"
                        },
                        "content": {
                            "type": "string",
                            "description": "Full content to write to the file"
                        }
                    },
                    "required": ["path", "content"]
                }
            },
            {
                "name": "edit_file",
                "description": "Edit a file by replacing specific content. More precise than rewriting entire file.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path to the file from working directory"
                        },
                        "old_content": {
                            "type": "string",
                            "description": "Exact content to find and replace"
                        },
                        "new_content": {
                            "type": "string",
                            "description": "New content to insert"
                        }
                    },
                    "required": ["path", "old_content", "new_content"]
                }
            },
            {
                "name": "list_files",
                "description": "List files in a directory with optional glob pattern",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Directory path (relative to working directory)"
                        },
                        "pattern": {
                            "type": "string",
                            "description": "Optional glob pattern (e.g., '*.py', '**/*.ts')"
                        },
                        "recursive": {
                            "type": "boolean",
                            "description": "Search recursively"
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "search_code",
                "description": "Search for text patterns in files (grep-like)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Search pattern (supports regex)"
                        },
                        "path": {
                            "type": "string",
                            "description": "Directory to search in"
                        },
                        "file_pattern": {
                            "type": "string",
                            "description": "File pattern to filter (e.g., '*.py')"
                        },
                        "case_sensitive": {
                            "type": "boolean",
                            "description": "Case sensitive search"
                        }
                    },
                    "required": ["pattern"]
                }
            },
            {
                "name": "run_command",
                "description": "Execute a shell command. Use for testing, building, installing dependencies.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Shell command to execute"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds (default: 30)"
                        }
                    },
                    "required": ["command"]
                }
            }
        ]

    async def _handle_tool_use(self, tool_name: str, tool_input: Dict,
                               working_directory: Path, file_tracker: FileTracker) -> str:
        """Handle tool execution and return result"""
        try:
            if tool_name == "read_file":
                path = working_directory / tool_input["path"]
                file_tracker.record_read(tool_input["path"])
                with open(path, 'r') as f:
                    content = f.read()
                return f"File content ({len(content)} chars):\n{content}"

            elif tool_name == "write_file":
                path = working_directory / tool_input["path"]
                file_tracker.track_file(tool_input["path"])
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, 'w') as f:
                    f.write(tool_input["content"])
                return f"Successfully wrote {len(tool_input['content'])} chars to {tool_input['path']}"

            elif tool_name == "edit_file":
                path = working_directory / tool_input["path"]
                file_tracker.track_file(tool_input["path"])
                with open(path, 'r') as f:
                    content = f.read()
                if tool_input["old_content"] not in content:
                    return f"Error: Old content not found in {tool_input['path']}"
                new_content = content.replace(tool_input["old_content"], tool_input["new_content"])
                with open(path, 'w') as f:
                    f.write(new_content)
                return f"Successfully edited {tool_input['path']}"

            elif tool_name == "list_files":
                path = working_directory / tool_input["path"]
                pattern = tool_input.get("pattern", "*")
                recursive = tool_input.get("recursive", False)

                if recursive:
                    files = list(path.rglob(pattern))
                else:
                    files = list(path.glob(pattern))

                file_list = [str(f.relative_to(working_directory)) for f in files if f.is_file()]
                return f"Found {len(file_list)} files:\n" + "\n".join(file_list[:100])

            elif tool_name == "search_code":
                pattern = tool_input["pattern"]
                search_path = working_directory / tool_input.get("path", ".")
                file_pattern = tool_input.get("file_pattern", "*")
                case_sensitive = tool_input.get("case_sensitive", True)

                # Use grep for searching
                cmd = ["grep", "-r"]
                if not case_sensitive:
                    cmd.append("-i")
                cmd.extend(["-n", pattern, str(search_path)])
                if file_pattern != "*":
                    cmd.extend(["--include", file_pattern])

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                matches = result.stdout[:5000]  # Limit output
                return f"Search results:\n{matches}" if matches else "No matches found"

            elif tool_name == "run_command":
                command = tool_input["command"]
                timeout = tool_input.get("timeout", 30)

                logger.info(f"Executing command: {command}")
                result = subprocess.run(
                    command,
                    shell=True,
                    cwd=working_directory,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )

                output = f"Exit code: {result.returncode}\n"
                if result.stdout:
                    output += f"STDOUT:\n{result.stdout[:2000]}\n"
                if result.stderr:
                    output += f"STDERR:\n{result.stderr[:2000]}\n"

                return output

            else:
                return f"Unknown tool: {tool_name}"

        except Exception as e:
            logger.error(f"Tool execution error ({tool_name}): {e}")
            return f"Error executing {tool_name}: {str(e)}"

    async def execute_task(
        self,
        task_description: str,
        working_directory: str = os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE)),
        context_files: List[str] = None,
        max_iterations: int = 20
    ) -> Dict[str, Any]:
        """
        Execute a coding task using Claude AI

        Args:
            task_description: Natural language description of the task
            working_directory: Base directory for operations
            context_files: List of relevant files for context
            max_iterations: Maximum number of tool use iterations

        Returns:
            Dictionary with execution results
        """
        start_time = datetime.utcnow()
        working_dir = Path(working_directory)
        file_tracker = FileTracker(working_directory)

        # Build system prompt
        system_prompt = self._build_system_prompt(working_directory, context_files)

        # Initialize conversation
        messages = [
            {
                "role": "user",
                "content": task_description
            }
        ]

        tools = self._build_tools()
        iteration = 0
        tool_uses = []

        try:
            while iteration < max_iterations:
                iteration += 1
                logger.info(f"Iteration {iteration}/{max_iterations}")

                # Call Claude API
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=system_prompt,
                    messages=messages,
                    tools=tools
                )

                # Process response
                assistant_message = {
                    "role": "assistant",
                    "content": response.content
                }
                messages.append(assistant_message)

                # Check if we're done
                if response.stop_reason == "end_turn":
                    logger.info("Task completed (end_turn)")
                    break

                # Handle tool uses
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input
                        tool_use_id = block.id

                        logger.info(f"Tool use: {tool_name} with input: {json.dumps(tool_input)[:100]}")

                        # Execute tool
                        result = await self._handle_tool_use(
                            tool_name, tool_input, working_dir, file_tracker
                        )

                        tool_uses.append({
                            "tool": tool_name,
                            "input": tool_input,
                            "result": result[:500]  # Truncate for storage
                        })

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": result
                        })

                # Add tool results to conversation
                if tool_results:
                    messages.append({
                        "role": "user",
                        "content": tool_results
                    })
                else:
                    # No tool use but not end_turn - might be error
                    logger.warning("No tool use and not end_turn")
                    break

            # Check for file changes
            changes = file_tracker.check_changes()
            summary = file_tracker.get_summary()

            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            # Build result
            result = {
                "success": True,
                "task_description": task_description,
                "working_directory": working_directory,
                "iterations": iteration,
                "tool_uses": tool_uses,
                "file_changes": summary,
                "duration_seconds": duration,
                "timestamp": start_time.isoformat(),
                "final_message": self._extract_final_text(messages[-1]) if messages else ""
            }

            # Store in history
            self.execution_history.append(result)

            return result

        except Exception as e:
            logger.error(f"Task execution failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "task_description": task_description,
                "iterations": iteration,
                "tool_uses": tool_uses,
                "timestamp": start_time.isoformat()
            }

    def _extract_final_text(self, message: Dict) -> str:
        """Extract text content from final message"""
        if "content" in message:
            content = message["content"]
            if isinstance(content, list):
                text_parts = [
                    block.text if hasattr(block, 'text') else str(block)
                    for block in content
                    if hasattr(block, 'type') and block.type == 'text'
                ]
                return "\n".join(text_parts)
            return str(content)
        return ""

    def get_execution_history(self) -> List[Dict]:
        """Get history of all task executions"""
        return self.execution_history
