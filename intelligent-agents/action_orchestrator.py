#!/usr/bin/env python3
"""
Action Orchestrator - Voice Command Execution Coordinator
==========================================================

Routes voice intents to appropriate handlers and executes multi-step actions.

This orchestrator:
1. Routes intents to appropriate handlers (COMMAND, QUERY, CONVERSATION, META)
2. Decomposes complex tasks into executable steps
3. Executes actions via Anthropic API with tool use
4. Tracks execution progress and state
5. Handles errors with recovery strategies
6. Generates execution summaries and learnings

Integrates with:
- Conversation Manager: Receives classified intents
- Enhanced Memory MCP: Stores execution outcomes
- Agent Runtime MCP: Creates persistent tasks
- Voice Mode MCP: Speaks responses

Usage:
    orchestrator = ActionOrchestrator(api_key=os.getenv("ANTHROPIC_API_KEY"))
    result = await orchestrator.execute_intent(intent, context)
    print(f"Success: {result.success}, Output: {result.output}")
"""

import asyncio
import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import anthropic

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("action_orchestrator")

# Configuration
EXECUTION_LOG = Path.home() / "agentic-system" / "logs" / "action_executions.log"
EXECUTION_LOG.parent.mkdir(parents=True, exist_ok=True)

# Voice feedback integration
VOICE_FEEDBACK_ENABLED = True

# Anthropic model configuration
CLAUDE_MODEL = "claude-sonnet-4-5-20250929"
MAX_TOKENS = 8000
TEMPERATURE = 0.0  # Deterministic for code execution


class IntentType(Enum):
    """Intent classification types"""
    COMMAND = "COMMAND"      # Code execution, file operations
    QUERY = "QUERY"          # Information retrieval, search
    CONVERSATION = "CONVERSATION"  # Natural conversation
    META = "META"            # System control, configuration


class ActionStatus(Enum):
    """Action execution status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class Intent:
    """
    Structured intent from voice command

    Attributes:
        type: Intent classification (COMMAND, QUERY, etc.)
        text: Original user utterance
        entities: Extracted entities (file_path, search_term, etc.)
        confidence: Classification confidence (0.0-1.0)
        requires_confirmation: Whether action needs user approval
    """
    type: IntentType
    text: str
    entities: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    requires_confirmation: bool = False


@dataclass
class ExecutionStep:
    """
    Single step in multi-step execution

    Attributes:
        step_number: Step sequence number
        description: Human-readable step description
        tool: Tool to execute (bash, read, edit, write, grep, etc.)
        parameters: Tool parameters
        status: Execution status
        result: Execution result
        error: Error message if failed
        duration_ms: Execution time in milliseconds
    """
    step_number: int
    description: str
    tool: str
    parameters: Dict[str, Any]
    status: ActionStatus = ActionStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: Optional[int] = None


@dataclass
class ExecutionResult:
    """
    Complete execution result

    Attributes:
        success: Whether execution completed successfully
        intent: Original intent
        steps: List of execution steps
        output: Final output/response
        summary: Human-readable summary
        errors: List of errors encountered
        total_duration_ms: Total execution time
        tokens_used: Anthropic API tokens consumed
        learned_patterns: Patterns learned for future execution
    """
    success: bool
    intent: Intent
    steps: List[ExecutionStep]
    output: str
    summary: str
    errors: List[str] = field(default_factory=list)
    total_duration_ms: int = 0
    tokens_used: Dict[str, int] = field(default_factory=dict)
    learned_patterns: List[str] = field(default_factory=list)


@dataclass
class ConversationState:
    """
    Persistent conversation state

    Attributes:
        active_context: Current working directory, files, etc.
        recent_actions: Recent execution results for context
        file_modifications: Files modified in this session
        pending_confirmations: Actions awaiting user approval
    """
    active_context: Dict[str, Any] = field(default_factory=dict)
    recent_actions: List[ExecutionResult] = field(default_factory=list)
    file_modifications: Dict[str, List[str]] = field(default_factory=dict)
    pending_confirmations: List[Intent] = field(default_factory=list)


class ActionOrchestrator:
    """
    Coordinates multi-step task execution for voice commands

    Routes intents to handlers, decomposes tasks, executes via Anthropic API,
    tracks progress, handles errors, and generates summaries.
    """

    def __init__(self, anthropic_api_key: str, working_dir: Optional[Path] = None):
        """
        Initialize action orchestrator

        Args:
            anthropic_api_key: Anthropic API key
            working_dir: Working directory for code execution (default: cwd)
        """
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.conversation_state = ConversationState()
        self.working_dir = working_dir or Path.cwd()

        # Initialize context
        self.conversation_state.active_context = {
            "working_directory": str(self.working_dir),
            "current_branch": self._get_git_branch(),
            "open_files": []
        }

        logger.info(f"Action orchestrator initialized in {self.working_dir}")

    def _get_git_branch(self) -> Optional[str]:
        """Get current git branch if in repo"""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    async def execute_intent(
        self,
        intent: Intent,
        context: Optional[Dict] = None
    ) -> ExecutionResult:
        """
        Execute user intent with appropriate actions

        Args:
            intent: Classified intent with entities
            context: Additional context (current files, visual state, etc.)

        Returns:
            ExecutionResult with actions taken, outputs, errors
        """
        start_time = time.time()

        logger.info(f"Executing intent: {intent.type.value} - {intent.text}")

        # Update context
        if context:
            self.conversation_state.active_context.update(context)

        # Route to appropriate handler
        try:
            if intent.type == IntentType.COMMAND:
                result = await self._execute_command(intent, context or {})
            elif intent.type == IntentType.QUERY:
                result = await self._execute_query(intent, context or {})
            elif intent.type == IntentType.CONVERSATION:
                result = await self._execute_conversation(intent, context or {})
            elif intent.type == IntentType.META:
                result = await self._execute_meta(intent, context or {})
            else:
                result = ExecutionResult(
                    success=False,
                    intent=intent,
                    steps=[],
                    output="",
                    summary=f"Unknown intent type: {intent.type}",
                    errors=[f"Unsupported intent type: {intent.type}"]
                )
        except Exception as e:
            logger.error(f"Intent execution failed: {e}", exc_info=True)
            result = ExecutionResult(
                success=False,
                intent=intent,
                steps=[],
                output="",
                summary=f"Execution failed: {str(e)}",
                errors=[str(e)]
            )

        # Calculate total duration
        result.total_duration_ms = int((time.time() - start_time) * 1000)

        # Log execution
        self._log_execution(result)

        # Add to recent actions
        self.conversation_state.recent_actions.append(result)
        if len(self.conversation_state.recent_actions) > 10:
            self.conversation_state.recent_actions.pop(0)

        return result

    async def _execute_command(
        self,
        intent: Intent,
        context: Dict[str, Any]
    ) -> ExecutionResult:
        """
        Execute coding commands (file operations, bash commands, etc.)

        Uses Anthropic API with tool use to execute multi-step coding tasks.

        Args:
            intent: COMMAND intent
            context: Execution context

        Returns:
            ExecutionResult with command execution details
        """
        logger.info(f"Executing COMMAND: {intent.text}")

        steps: List[ExecutionStep] = []
        errors: List[str] = []
        tokens_used = {"input": 0, "output": 0}

        try:
            # Build system prompt with context
            system_prompt = self._build_system_prompt(context)

            # Build user message with intent and context
            user_message = self._build_command_message(intent, context)

            # Execute via Anthropic API
            messages = [{"role": "user", "content": user_message}]

            # Iterative tool execution loop
            iteration = 0
            max_iterations = 10

            while iteration < max_iterations:
                iteration += 1

                response = self.client.messages.create(
                    model=CLAUDE_MODEL,
                    max_tokens=MAX_TOKENS,
                    temperature=TEMPERATURE,
                    system=system_prompt,
                    messages=messages,
                    tools=self._get_available_tools()
                )

                # Track token usage
                tokens_used["input"] += response.usage.input_tokens
                tokens_used["output"] += response.usage.output_tokens

                # Check stop reason
                if response.stop_reason == "end_turn":
                    # Extract final response
                    for block in response.content:
                        if hasattr(block, "text"):
                            output = block.text
                            break
                    break

                elif response.stop_reason == "tool_use":
                    # Execute tool calls
                    tool_results = []

                    for block in response.content:
                        if block.type == "tool_use":
                            step_start = time.time()

                            step = ExecutionStep(
                                step_number=len(steps) + 1,
                                description=f"Execute {block.name}",
                                tool=block.name,
                                parameters=block.input,
                                status=ActionStatus.RUNNING
                            )
                            steps.append(step)

                            # Execute tool
                            try:
                                tool_result = await self._execute_tool(
                                    block.name,
                                    block.input
                                )

                                step.status = ActionStatus.SUCCESS
                                step.result = tool_result
                                step.duration_ms = int((time.time() - step_start) * 1000)

                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": str(tool_result)
                                })

                            except Exception as e:
                                logger.error(f"Tool execution failed: {e}")
                                step.status = ActionStatus.FAILED
                                step.error = str(e)
                                step.duration_ms = int((time.time() - step_start) * 1000)
                                errors.append(f"{block.name}: {str(e)}")

                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": f"Error: {str(e)}",
                                    "is_error": True
                                })

                    # Add assistant message and tool results to conversation
                    messages.append({"role": "assistant", "content": response.content})
                    messages.append({"role": "user", "content": tool_results})

                else:
                    logger.warning(f"Unexpected stop reason: {response.stop_reason}")
                    break

            # Generate summary
            success = len(errors) == 0
            summary = self._generate_execution_summary(steps, success)

            return ExecutionResult(
                success=success,
                intent=intent,
                steps=steps,
                output=output if 'output' in locals() else "",
                summary=summary,
                errors=errors,
                tokens_used=tokens_used
            )

        except Exception as e:
            logger.error(f"Command execution error: {e}", exc_info=True)
            return ExecutionResult(
                success=False,
                intent=intent,
                steps=steps,
                output="",
                summary=f"Execution failed: {str(e)}",
                errors=[str(e)],
                tokens_used=tokens_used
            )

    async def _execute_query(
        self,
        intent: Intent,
        context: Dict[str, Any]
    ) -> ExecutionResult:
        """
        Execute information queries (code search, file reading, analysis)

        Args:
            intent: QUERY intent
            context: Query context

        Returns:
            ExecutionResult with query results
        """
        logger.info(f"Executing QUERY: {intent.text}")

        steps: List[ExecutionStep] = []
        tokens_used = {"input": 0, "output": 0}

        try:
            # Build query message
            system_prompt = self._build_system_prompt(context)
            user_message = self._build_query_message(intent, context)

            # Execute query via Anthropic API
            response = self.client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
                tools=self._get_query_tools()
            )

            tokens_used["input"] = response.usage.input_tokens
            tokens_used["output"] = response.usage.output_tokens

            # Extract response
            output = ""
            for block in response.content:
                if hasattr(block, "text"):
                    output = block.text

            return ExecutionResult(
                success=True,
                intent=intent,
                steps=steps,
                output=output,
                summary=f"Query completed: {intent.text[:50]}...",
                tokens_used=tokens_used
            )

        except Exception as e:
            logger.error(f"Query execution error: {e}", exc_info=True)
            return ExecutionResult(
                success=False,
                intent=intent,
                steps=steps,
                output="",
                summary=f"Query failed: {str(e)}",
                errors=[str(e)],
                tokens_used=tokens_used
            )

    async def _execute_conversation(
        self,
        intent: Intent,
        context: Dict[str, Any]
    ) -> ExecutionResult:
        """
        Execute conversational intents (greetings, explanations, etc.)

        Args:
            intent: CONVERSATION intent
            context: Conversation context

        Returns:
            ExecutionResult with conversational response
        """
        logger.info(f"Executing CONVERSATION: {intent.text}")

        tokens_used = {"input": 0, "output": 0}

        try:
            # Build conversational message with context
            system_prompt = """You are a helpful AI assistant integrated into a voice-controlled coding system.

Provide natural, conversational responses while being aware of the user's current context (working directory, recent actions, etc.).

Keep responses concise and suitable for voice output (avoid long lists, complex formatting)."""

            # Include recent actions for context
            recent_context = self._format_recent_actions()

            user_message = f"""User: {intent.text}

Current Context:
- Working directory: {self.conversation_state.active_context.get('working_directory')}
- Git branch: {self.conversation_state.active_context.get('current_branch', 'N/A')}

{recent_context}

Respond naturally to the user."""

            response = self.client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=2000,
                temperature=0.7,  # More creative for conversation
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}]
            )

            tokens_used["input"] = response.usage.input_tokens
            tokens_used["output"] = response.usage.output_tokens

            # Extract response
            output = ""
            for block in response.content:
                if hasattr(block, "text"):
                    output = block.text

            return ExecutionResult(
                success=True,
                intent=intent,
                steps=[],
                output=output,
                summary="Conversational response generated",
                tokens_used=tokens_used
            )

        except Exception as e:
            logger.error(f"Conversation error: {e}", exc_info=True)
            return ExecutionResult(
                success=False,
                intent=intent,
                steps=[],
                output="I'm having trouble processing that right now.",
                summary=f"Conversation failed: {str(e)}",
                errors=[str(e)],
                tokens_used=tokens_used
            )

    async def _execute_meta(
        self,
        intent: Intent,
        context: Dict[str, Any]
    ) -> ExecutionResult:
        """
        Execute meta commands (system control, configuration, status)

        Args:
            intent: META intent
            context: System context

        Returns:
            ExecutionResult with meta command result
        """
        logger.info(f"Executing META: {intent.text}")

        # Handle common meta commands
        text_lower = intent.text.lower()

        if "status" in text_lower or "health" in text_lower:
            output = self._get_system_status()
        elif "context" in text_lower or "what are you doing" in text_lower:
            output = self._get_current_context()
        elif "recent" in text_lower or "what did you do" in text_lower:
            output = self._format_recent_actions()
        else:
            output = f"Meta command not yet implemented: {intent.text}"

        return ExecutionResult(
            success=True,
            intent=intent,
            steps=[],
            output=output,
            summary="Meta command executed",
            tokens_used={"input": 0, "output": 0}
        )

    async def _execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> Any:
        """
        Execute a single tool call

        Args:
            tool_name: Tool to execute
            parameters: Tool parameters

        Returns:
            Tool execution result
        """
        logger.debug(f"Executing tool: {tool_name} with {parameters}")

        if tool_name == "bash":
            return await self._tool_bash(parameters)
        elif tool_name == "read_file":
            return await self._tool_read_file(parameters)
        elif tool_name == "write_file":
            return await self._tool_write_file(parameters)
        elif tool_name == "edit_file":
            return await self._tool_edit_file(parameters)
        elif tool_name == "grep":
            return await self._tool_grep(parameters)
        elif tool_name == "list_files":
            return await self._tool_list_files(parameters)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    async def _tool_bash(self, params: Dict[str, Any]) -> str:
        """Execute bash command"""
        command = params.get("command", "")

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=30
            )

            output = result.stdout
            if result.stderr:
                output += f"\nSTDERR: {result.stderr}"

            return output or "(no output)"

        except subprocess.TimeoutExpired:
            raise Exception("Command timed out after 30 seconds")
        except Exception as e:
            raise Exception(f"Bash execution failed: {str(e)}")

    async def _tool_read_file(self, params: Dict[str, Any]) -> str:
        """Read file contents"""
        file_path = Path(params.get("file_path", ""))

        if not file_path.is_absolute():
            file_path = self.working_dir / file_path

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, 'r') as f:
            content = f.read()

        # Add to open files
        if str(file_path) not in self.conversation_state.active_context.get("open_files", []):
            self.conversation_state.active_context.setdefault("open_files", []).append(str(file_path))

        return content

    async def _tool_write_file(self, params: Dict[str, Any]) -> str:
        """Write file contents"""
        file_path = Path(params.get("file_path", ""))
        content = params.get("content", "")

        if not file_path.is_absolute():
            file_path = self.working_dir / file_path

        # Create parent directories
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'w') as f:
            f.write(content)

        # Track modification
        self.conversation_state.file_modifications.setdefault(str(file_path), []).append(
            f"Written at {datetime.now().isoformat()}"
        )

        return f"File written: {file_path}"

    async def _tool_edit_file(self, params: Dict[str, Any]) -> str:
        """Edit file with search/replace"""
        file_path = Path(params.get("file_path", ""))
        old_text = params.get("old_text", "")
        new_text = params.get("new_text", "")

        if not file_path.is_absolute():
            file_path = self.working_dir / file_path

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, 'r') as f:
            content = f.read()

        if old_text not in content:
            raise ValueError(f"Old text not found in file: {old_text[:50]}...")

        new_content = content.replace(old_text, new_text)

        with open(file_path, 'w') as f:
            f.write(new_content)

        # Track modification
        self.conversation_state.file_modifications.setdefault(str(file_path), []).append(
            f"Edited at {datetime.now().isoformat()}"
        )

        return f"File edited: {file_path}"

    async def _tool_grep(self, params: Dict[str, Any]) -> str:
        """Search for pattern in files"""
        pattern = params.get("pattern", "")
        path = params.get("path", ".")

        search_path = self.working_dir / path

        try:
            result = subprocess.run(
                ["grep", "-r", "-n", pattern, str(search_path)],
                capture_output=True,
                text=True,
                timeout=10
            )

            return result.stdout or "(no matches)"

        except Exception as e:
            raise Exception(f"Grep failed: {str(e)}")

    async def _tool_list_files(self, params: Dict[str, Any]) -> str:
        """List files in directory"""
        path = params.get("path", ".")
        pattern = params.get("pattern", "*")

        search_path = self.working_dir / path

        if not search_path.exists():
            raise FileNotFoundError(f"Directory not found: {search_path}")

        files = list(search_path.glob(pattern))

        return "\n".join(str(f.relative_to(self.working_dir)) for f in files[:100])

    def _get_available_tools(self) -> List[Dict[str, Any]]:
        """Get tool definitions for Anthropic API"""
        return [
            {
                "name": "bash",
                "description": "Execute bash command in working directory",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Bash command to execute"}
                    },
                    "required": ["command"]
                }
            },
            {
                "name": "read_file",
                "description": "Read contents of a file",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to file (relative or absolute)"}
                    },
                    "required": ["file_path"]
                }
            },
            {
                "name": "write_file",
                "description": "Write content to a file",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to file"},
                        "content": {"type": "string", "description": "File content"}
                    },
                    "required": ["file_path", "content"]
                }
            },
            {
                "name": "edit_file",
                "description": "Edit file with search/replace",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to file"},
                        "old_text": {"type": "string", "description": "Text to find"},
                        "new_text": {"type": "string", "description": "Replacement text"}
                    },
                    "required": ["file_path", "old_text", "new_text"]
                }
            },
            {
                "name": "grep",
                "description": "Search for pattern in files",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "Search pattern"},
                        "path": {"type": "string", "description": "Search path (default: .)"}
                    },
                    "required": ["pattern"]
                }
            },
            {
                "name": "list_files",
                "description": "List files in directory",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Directory path (default: .)"},
                        "pattern": {"type": "string", "description": "Glob pattern (default: *)"}
                    }
                }
            }
        ]

    def _get_query_tools(self) -> List[Dict[str, Any]]:
        """Get tool definitions for query operations"""
        return [
            {
                "name": "read_file",
                "description": "Read contents of a file",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to file"}
                    },
                    "required": ["file_path"]
                }
            },
            {
                "name": "grep",
                "description": "Search for pattern in files",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "Search pattern"},
                        "path": {"type": "string", "description": "Search path"}
                    },
                    "required": ["pattern"]
                }
            },
            {
                "name": "list_files",
                "description": "List files in directory",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Directory path"},
                        "pattern": {"type": "string", "description": "Glob pattern"}
                    }
                }
            }
        ]

    def _build_system_prompt(self, context: Dict[str, Any]) -> str:
        """Build system prompt with context"""
        return f"""You are an AI assistant executing voice commands in a coding environment.

Current Context:
- Working Directory: {self.conversation_state.active_context.get('working_directory')}
- Git Branch: {self.conversation_state.active_context.get('current_branch', 'N/A')}
- Open Files: {', '.join(self.conversation_state.active_context.get('open_files', [])[:5])}

Instructions:
1. Execute the user's request using available tools
2. Break complex tasks into clear steps
3. Handle errors gracefully with informative messages
4. Keep responses concise for voice output
5. Always use absolute paths when reading/writing files

Available tools: bash, read_file, write_file, edit_file, grep, list_files"""

    def _build_command_message(self, intent: Intent, context: Dict[str, Any]) -> str:
        """Build user message for command execution"""
        entities_str = json.dumps(intent.entities, indent=2) if intent.entities else "None"

        return f"""Execute this voice command:

Command: {intent.text}

Extracted Entities:
{entities_str}

Additional Context:
{json.dumps(context, indent=2) if context else 'None'}

Execute the command using available tools. Provide clear feedback on what you're doing."""

    def _build_query_message(self, intent: Intent, context: Dict[str, Any]) -> str:
        """Build user message for query execution"""
        return f"""Answer this query about the codebase:

Query: {intent.text}

Context:
- Working Directory: {self.conversation_state.active_context.get('working_directory')}

Use available tools to search, read files, and analyze code. Provide a clear, concise answer suitable for voice output."""

    def _generate_execution_summary(self, steps: List[ExecutionStep], success: bool) -> str:
        """Generate human-readable execution summary"""
        if not steps:
            return "No steps executed"

        step_summaries = []
        for step in steps:
            status_icon = "✓" if step.status == ActionStatus.SUCCESS else "✗"
            step_summaries.append(f"{status_icon} {step.description}")

        summary = f"Executed {len(steps)} step(s):\n" + "\n".join(step_summaries)

        if success:
            summary += "\n\nAll steps completed successfully."
        else:
            failed = [s for s in steps if s.status == ActionStatus.FAILED]
            summary += f"\n\n{len(failed)} step(s) failed."

        return summary

    def _format_recent_actions(self) -> str:
        """Format recent actions for context"""
        if not self.conversation_state.recent_actions:
            return "No recent actions."

        recent = self.conversation_state.recent_actions[-3:]
        lines = ["Recent Actions:"]

        for action in recent:
            status = "✓" if action.success else "✗"
            lines.append(f"  {status} {action.intent.text[:50]}...")

        return "\n".join(lines)

    def _get_system_status(self) -> str:
        """Get current system status"""
        return f"""System Status:
- Working Directory: {self.conversation_state.active_context.get('working_directory')}
- Git Branch: {self.conversation_state.active_context.get('current_branch', 'N/A')}
- Open Files: {len(self.conversation_state.active_context.get('open_files', []))}
- Recent Actions: {len(self.conversation_state.recent_actions)}
- Modified Files: {len(self.conversation_state.file_modifications)}"""

    def _get_current_context(self) -> str:
        """Get current context description"""
        ctx = self.conversation_state.active_context
        return f"""Current Context:
- Working in: {ctx.get('working_directory')}
- Branch: {ctx.get('current_branch', 'N/A')}
- Open files: {', '.join(ctx.get('open_files', [])[:3])}
- Recent activity: {len(self.conversation_state.recent_actions)} actions"""

    def _log_execution(self, result: ExecutionResult):
        """Log execution result"""
        try:
            timestamp = datetime.now().isoformat()

            log_entry = {
                "timestamp": timestamp,
                "intent_type": result.intent.type.value,
                "intent_text": result.intent.text,
                "success": result.success,
                "steps": len(result.steps),
                "duration_ms": result.total_duration_ms,
                "tokens_used": result.tokens_used,
                "errors": result.errors
            }

            with open(EXECUTION_LOG, 'a') as f:
                f.write(json.dumps(log_entry) + "\n")

        except Exception as e:
            logger.error(f"Failed to log execution: {e}")


async def main():
    """Test execution"""
    import os

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set")
        return

    orchestrator = ActionOrchestrator(api_key)

    # Test command intent
    test_intent = Intent(
        type=IntentType.COMMAND,
        text="Create a Python file called hello.py that prints hello world",
        entities={"file_name": "hello.py"},
        confidence=0.9
    )

    print(f"Executing: {test_intent.text}")
    result = await orchestrator.execute_intent(test_intent)

    print(f"\nSuccess: {result.success}")
    print(f"Steps: {len(result.steps)}")
    print(f"Output: {result.output}")
    print(f"Summary: {result.summary}")
    print(f"Tokens: {result.tokens_used}")


if __name__ == "__main__":
    asyncio.run(main())
