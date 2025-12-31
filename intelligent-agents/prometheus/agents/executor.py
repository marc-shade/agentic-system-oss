"""
Executor Agent - Runs ONE tool per iteration with VISUAL GROUNDING.

CRITICAL RULE: Only one tool call per iteration.
This prevents runaway execution and allows proper observation.

VISUAL GROUNDING: After browser/visual actions, we capture screenshots
and analyze them to inform the next action decision. This is the
"screenshot-in-loop" pattern that makes Manus feel magical.

Integrates with:
- Claude-in-Chrome for browser automation
- Apple Container for local macOS sandboxed execution
- cluster-execution-mcp for Linux sandbox tasks (fallback)
- Local tools for file/code operations
- Visual grounding for screenshot analysis
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)

# Import visual grounding (lazy to avoid circular imports)
_visual_grounding = None

def get_visual_grounding():
    """Lazy import of visual grounding module."""
    global _visual_grounding
    if _visual_grounding is None:
        try:
            from ..visual_grounding import VisualGrounding, VisualContext, VisualObservation
            _visual_grounding = {
                "VisualGrounding": VisualGrounding,
                "VisualContext": VisualContext,
                "VisualObservation": VisualObservation
            }
        except ImportError:
            _visual_grounding = {}
    return _visual_grounding


class ToolCategory(Enum):
    """Categories of available tools."""
    FILE = "file"
    SHELL = "shell"
    BROWSER = "browser"
    SEARCH = "search"
    VOICE = "voice"
    MESSAGE = "message"
    MEMORY = "memory"


class SandboxMode(Enum):
    """Sandbox execution mode."""
    LOCAL = "local"       # Apple Container (macOS native)
    CLUSTER = "cluster"   # cluster-execution-mcp (Linux node)
    AUTO = "auto"         # Auto-detect: prefer local, fallback to cluster


# Lazy import for Apple Container
_apple_container = None


def get_apple_container():
    """Lazy import of Apple Container module."""
    global _apple_container
    if _apple_container is None:
        try:
            # Try relative import first (when used as package)
            from ..apple_container import AppleContainerSandbox, get_sandbox, ContainerResult
            _apple_container = {
                "AppleContainerSandbox": AppleContainerSandbox,
                "get_sandbox": get_sandbox,
                "ContainerResult": ContainerResult
            }
        except ImportError:
            try:
                # Fallback to absolute import (when running directly)
                from apple_container import AppleContainerSandbox, get_sandbox, ContainerResult
                _apple_container = {
                    "AppleContainerSandbox": AppleContainerSandbox,
                    "get_sandbox": get_sandbox,
                    "ContainerResult": ContainerResult
                }
            except ImportError:
                _apple_container = {}
    return _apple_container


@dataclass
class Action:
    """Single tool action to execute."""
    tool: str
    params: dict
    category: ToolCategory
    expected_outcome: Optional[str] = None
    step_number: int = 0

    def to_dict(self) -> dict:
        return {
            "tool": self.tool,
            "params": self.params,
            "category": self.category.value,
            "expected_outcome": self.expected_outcome
        }


# Tool mappings for different categories
TOOL_MAPPINGS = {
    # File operations (use Claude Code native tools)
    "read": {"category": ToolCategory.FILE, "native": "Read"},
    "write": {"category": ToolCategory.FILE, "native": "Write"},
    "edit": {"category": ToolCategory.FILE, "native": "Edit"},
    "glob": {"category": ToolCategory.FILE, "native": "Glob"},
    "grep": {"category": ToolCategory.FILE, "native": "Grep"},

    # Shell operations (use Bash or cluster)
    "bash": {"category": ToolCategory.SHELL, "native": "Bash"},
    "bash_sandboxed": {"category": ToolCategory.SHELL, "native": "Bash", "sandbox": True},
    "shell_on_node": {"category": ToolCategory.SHELL, "mcp": "cluster-execution-mcp"},

    # Browser operations (use claude-in-chrome)
    "browser_navigate": {"category": ToolCategory.BROWSER, "mcp": "claude-in-chrome", "tool": "navigate"},
    "browser_view": {"category": ToolCategory.BROWSER, "mcp": "claude-in-chrome", "tool": "read_page"},
    "browser_click": {"category": ToolCategory.BROWSER, "mcp": "claude-in-chrome", "tool": "computer"},
    "browser_input": {"category": ToolCategory.BROWSER, "mcp": "claude-in-chrome", "tool": "form_input"},
    "browser_screenshot": {"category": ToolCategory.BROWSER, "mcp": "claude-in-chrome", "tool": "computer"},
    "browser_find": {"category": ToolCategory.BROWSER, "mcp": "claude-in-chrome", "tool": "find"},

    # Search operations
    "web_search": {"category": ToolCategory.SEARCH, "native": "WebSearch"},
    "memory_search": {"category": ToolCategory.MEMORY, "mcp": "enhanced-memory-mcp"},

    # Voice operations
    "speak": {"category": ToolCategory.VOICE, "mcp": "voice-mode"},
    "listen": {"category": ToolCategory.VOICE, "mcp": "voice-mode"},

    # Message operations
    "notify_user": {"category": ToolCategory.MESSAGE, "native": "message"},
    "ask_user": {"category": ToolCategory.MESSAGE, "native": "AskUserQuestion"},
}


EXECUTOR_SYSTEM_PROMPT = """Executor Agent - select ONE tool to run.

Tools: write (file_path, content), read (file_path), bash (command), glob (pattern), grep (pattern, path)
Browser: browser_navigate (url), browser_click (coordinate), browser_input (ref, value), browser_screenshot

Output JSON: {{"tool": "...", "params": {{...}}}}

Step: {current_step}
Workspace: {workspace}
{file_context}
{visual_context}

CRITICAL: Use EXACT file paths from previous outputs. Do not invent paths.
For browser tasks: Use visual observations to guide next action.
"""

# Tools that should trigger visual capture after execution
VISUAL_TRIGGER_TOOLS = {
    "browser_navigate", "browser_click", "browser_input",
    "browser_screenshot", "browser_view", "browser_find"
}


class ExecutorAgent:
    """
    Executes ONE tool per iteration with VISUAL GROUNDING.

    This is the workhorse agent that actually runs tools.
    It enforces the one-tool-per-iteration rule and routes
    to appropriate backends (native, MCP, sandbox).

    VISUAL GROUNDING: After browser actions, captures screenshots
    and analyzes them to provide context for next action decisions.
    """

    def __init__(
        self,
        sandbox_node: str = "macpro51",
        llm_client=None,
        enable_visual_grounding: bool = True,
        visual_provider: str = "gemini",
        sandbox_mode: SandboxMode = SandboxMode.AUTO
    ):
        """
        Initialize executor with visual grounding and sandboxing support.

        Args:
            sandbox_node: Node to use for cluster sandbox operations
            llm_client: LLM client for action selection
            enable_visual_grounding: Whether to capture/analyze screenshots
            visual_provider: Vision model provider (gemini, claude, ollama)
            sandbox_mode: LOCAL (Apple Container), CLUSTER (Linux node), AUTO
        """
        self.sandbox_node = sandbox_node
        self.llm_client = llm_client
        self.tools = TOOL_MAPPINGS
        self.browser_tab_id = None  # Will be set when browser is used
        self.sandbox_mode = sandbox_mode

        # Track file outputs for context
        self.files_written: list[str] = []
        self.files_read: list[str] = []
        self.bash_outputs: list[dict] = []

        # Visual grounding setup
        self.enable_visual_grounding = enable_visual_grounding
        self.visual_provider = visual_provider
        self.visual_grounding = None
        self.last_visual_observation = None

        # Apple Container sandbox (lazy init)
        self._local_sandbox = None
        self._local_sandbox_available = None

        if enable_visual_grounding:
            self._init_visual_grounding()

    def _is_local_sandbox_available(self) -> bool:
        """Check if Apple Container is available for local sandboxing."""
        if self._local_sandbox_available is not None:
            return self._local_sandbox_available

        ac_module = get_apple_container()
        if "get_sandbox" not in ac_module:
            self._local_sandbox_available = False
            return False

        try:
            sandbox = ac_module["get_sandbox"]()
            self._local_sandbox_available = sandbox.is_available()
            if self._local_sandbox_available:
                self._local_sandbox = sandbox
                logger.info("Apple Container sandbox available for local execution")
            else:
                logger.info("Apple Container not running, will use cluster sandbox")
        except Exception as e:
            logger.warning(f"Apple Container check failed: {e}")
            self._local_sandbox_available = False

        return self._local_sandbox_available

    def _should_use_local_sandbox(self) -> bool:
        """Determine if local sandbox should be used."""
        if self.sandbox_mode == SandboxMode.CLUSTER:
            return False
        if self.sandbox_mode == SandboxMode.LOCAL:
            return self._is_local_sandbox_available()
        # AUTO mode: prefer local if available
        return self._is_local_sandbox_available()

    async def _execute_in_local_sandbox(self, command: str, timeout: int = 60) -> str:
        """Execute command in Apple Container sandbox."""
        if not self._local_sandbox:
            return "Error: Local sandbox not available"

        try:
            # Import ContainerConfig with fallback
            try:
                from ..apple_container import ContainerConfig
            except ImportError:
                from apple_container import ContainerConfig

            config = ContainerConfig(timeout=timeout, network=False)
            result = await self._local_sandbox.execute(command, config)

            # Track output
            self.bash_outputs.append({
                "cmd": command[:50],
                "result": result.stdout[:100] if result.stdout else f"exit:{result.exit_code}",
                "sandbox": "apple_container"
            })

            return result.to_observation()

        except Exception as e:
            logger.error(f"Local sandbox execution failed: {e}")
            return f"Error: {str(e)}"

    def _init_visual_grounding(self):
        """Initialize visual grounding system."""
        vg_module = get_visual_grounding()
        if "VisualGrounding" in vg_module:
            try:
                self.visual_grounding = vg_module["VisualGrounding"](
                    preferred_provider=self.visual_provider,
                    browser_tab_id=self.browser_tab_id
                )
                logger.info(f"Visual grounding initialized with {self.visual_provider}")
            except Exception as e:
                logger.warning(f"Failed to init visual grounding: {e}")
                self.visual_grounding = None
        else:
            logger.warning("Visual grounding module not available")

    def _get_file_context(self) -> str:
        """Build file context for executor prompt."""
        lines = []
        if self.files_written:
            lines.append(f"Files written: {', '.join(self.files_written[-5:])}")
        if self.files_read:
            lines.append(f"Files read: {', '.join(self.files_read[-5:])}")
        if self.bash_outputs:
            recent = self.bash_outputs[-3:]
            for bo in recent:
                lines.append(f"Bash '{bo['cmd'][:30]}' → {bo['result'][:50]}")
        return "\n".join(lines) if lines else "No previous outputs."

    def _get_visual_context(self) -> str:
        """Build visual context from recent observations."""
        if not self.visual_grounding:
            return ""

        if not self.last_visual_observation:
            return ""

        return self.last_visual_observation.to_prompt_context()

    async def capture_visual_state(
        self,
        action_taken: str = "",
        expected_outcome: str = ""
    ) -> Optional[Any]:
        """
        Capture and analyze visual state after an action.

        This is the core of visual grounding - screenshot-in-loop.

        Args:
            action_taken: Description of the action just executed
            expected_outcome: What we expected to happen

        Returns:
            VisualObservation or None if visual grounding disabled
        """
        if not self.visual_grounding:
            return None

        vg_module = get_visual_grounding()
        if "VisualContext" not in vg_module:
            return None

        VisualContext = vg_module["VisualContext"]

        try:
            # Determine context type based on whether we're in browser mode
            context_type = (
                VisualContext.BROWSER if self.browser_tab_id
                else VisualContext.DESKTOP
            )

            observation = await self.visual_grounding.capture_and_analyze(
                context_type=context_type,
                action_just_taken=action_taken,
                expected_outcome=expected_outcome
            )

            self.last_visual_observation = observation
            logger.info(f"Visual observation: {observation.description[:100]}")

            return observation

        except Exception as e:
            logger.warning(f"Visual capture failed: {e}")
            return None

    def reset(self):
        """Reset tracking for new task."""
        self.files_written.clear()
        self.files_read.clear()
        self.bash_outputs.clear()
        self.last_visual_observation = None
        if self.visual_grounding:
            self.visual_grounding.reset()

    async def select_action(
        self,
        current_step: dict,
        state: dict,
        event_context: str
    ) -> Optional[Action]:
        """
        Select ONE action to execute, informed by visual state.

        Args:
            current_step: Current step from plan
            state: Current execution state
            event_context: Recent events for context

        Returns:
            Action to execute, or None if blocked
        """
        logger.info(f"Selecting action for step: {current_step.get('description', 'unknown')}")

        # Simplified prompt for faster LLM response
        step_desc = current_step.get('description', 'unknown')
        workspace = state.get('workspace', '/tmp')

        # Include visual context if available
        visual_context = self._get_visual_context()

        prompt = EXECUTOR_SYSTEM_PROMPT.format(
            current_step=step_desc,
            workspace=workspace,
            file_context=self._get_file_context(),
            visual_context=visual_context
        )

        try:
            if self.llm_client:
                response = await self.llm_client.generate(
                    system=prompt,
                    user=f"Execute step: {step_desc}"
                )
                return self._parse_action(response, current_step)
            else:
                # Without LLM, try to infer from step tools
                return self._infer_action(current_step)

        except Exception as e:
            logger.exception(f"Action selection failed: {e}")
            return None

    async def execute(self, action: Action) -> str:
        """
        Execute action and return observation.

        Routes to appropriate backend based on tool category.
        VISUAL GROUNDING: Captures screenshot after browser/visual actions.
        """
        logger.info(f"Executing: {action.tool} with {action.params}")

        tool_info = self.tools.get(action.tool)
        if not tool_info:
            return f"Error: Unknown tool '{action.tool}'"

        try:
            if "native" in tool_info:
                result = await self._execute_native(action, tool_info["native"])
            elif "mcp" in tool_info:
                result = await self._execute_mcp(action, tool_info)
            else:
                return f"Error: No execution method for '{action.tool}'"

            # VISUAL GROUNDING: Capture visual state after browser actions
            if action.tool in VISUAL_TRIGGER_TOOLS and self.enable_visual_grounding:
                logger.info(f"Capturing visual state after {action.tool}")
                await self.capture_visual_state(
                    action_taken=f"{action.tool}: {str(action.params)[:100]}",
                    expected_outcome=action.expected_outcome or ""
                )

            return result

        except Exception as e:
            logger.exception(f"Execution failed: {e}")
            return f"Error: {str(e)}"

    async def _execute_native(self, action: Action, native_tool: str) -> str:
        """Execute using native Python implementations."""
        import subprocess
        import os
        from pathlib import Path

        params = action.params

        if native_tool == "Read":
            file_path = params.get("file_path") or params.get("path") or params.get("file")
            if not file_path:
                return "Error: file_path required"
            try:
                content = Path(file_path).read_text()
                self.files_read.append(file_path)  # Track file read
                return f"File content ({len(content)} chars):\n{content[:2000]}"
            except Exception as e:
                return f"Error reading file: {e}"

        elif native_tool == "Write":
            file_path = params.get("file_path") or params.get("path") or params.get("file")
            content = params.get("content", "")
            if not file_path:
                return "Error: file_path required"
            try:
                Path(file_path).parent.mkdir(parents=True, exist_ok=True)
                Path(file_path).write_text(content)
                self.files_written.append(file_path)  # Track file written
                return f"Successfully wrote {len(content)} chars to {file_path}"
            except Exception as e:
                return f"Error writing file: {e}"

        elif native_tool == "Bash":
            command = params.get("command", "")
            if not command:
                return "Error: command required"

            # Check if sandboxed execution is requested or recommended
            use_sandbox = params.get("sandbox", False) or params.get("isolated", False)

            # Use local sandbox if available and requested
            if use_sandbox and self._should_use_local_sandbox():
                return await self._execute_in_local_sandbox(
                    command,
                    timeout=params.get("timeout", 60)
                )

            # Direct execution (non-sandboxed)
            try:
                import subprocess
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=params.get("timeout", 60),
                    cwd=params.get("cwd")
                )
                output = result.stdout + result.stderr
                # Track bash output
                self.bash_outputs.append({
                    "cmd": command[:50],
                    "result": output[:100] if output else f"exit:{result.returncode}"
                })
                return f"Exit code: {result.returncode}\n{output[:2000]}"
            except subprocess.TimeoutExpired:
                return "Error: Command timed out"
            except Exception as e:
                return f"Error running command: {e}"

        elif native_tool == "Glob":
            pattern = params.get("pattern", "*")
            path = params.get("path", ".")
            try:
                matches = list(Path(path).glob(pattern))
                return f"Found {len(matches)} files:\n" + "\n".join(str(m) for m in matches[:50])
            except Exception as e:
                return f"Error in glob: {e}"

        elif native_tool == "Grep":
            pattern = params.get("pattern", "")
            path = params.get("path", ".")
            try:
                result = subprocess.run(
                    ["grep", "-r", "-n", pattern, path],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                return result.stdout[:2000] or "No matches found"
            except Exception as e:
                return f"Error in grep: {e}"

        else:
            return f"[Native tool {native_tool} not implemented - params: {params}]"

    async def _execute_mcp(self, action: Action, tool_info: dict) -> str:
        """Execute using MCP server (placeholder for actual MCP calls)."""
        mcp_server = tool_info["mcp"]
        mcp_tool = tool_info.get("tool", action.tool)

        # TODO: Implement actual MCP calls via httpx/subprocess
        return f"[MCP {mcp_server}.{mcp_tool} executed with {action.params}]"

    async def execute_browser_action(
        self,
        action_type: str,
        params: dict,
        tab_id: int = None,
        capture_visual: bool = True
    ) -> str:
        """
        Execute browser action via claude-in-chrome WITH VISUAL GROUNDING.

        After each browser action, captures a screenshot and analyzes it
        to provide context for the next action decision.

        Args:
            action_type: Type of browser action (navigate, click, type, etc.)
            params: Action parameters
            tab_id: Browser tab ID
            capture_visual: Whether to capture visual state after action

        Returns:
            Result string with action outcome
        """
        tab_id = tab_id or self.browser_tab_id
        result = ""

        if action_type == "navigate":
            # mcp__claude-in-chrome__navigate
            result = f"[Navigated to {params.get('url')}]"

        elif action_type == "click":
            # mcp__claude-in-chrome__computer with action=left_click
            result = f"[Clicked at {params.get('coordinate')}]"

        elif action_type == "type":
            # mcp__claude-in-chrome__computer with action=type
            result = f"[Typed: {params.get('text', '')[:20]}...]"

        elif action_type == "screenshot":
            # mcp__claude-in-chrome__computer with action=screenshot
            result = f"[Screenshot captured]"

        elif action_type == "read_page":
            # mcp__claude-in-chrome__read_page
            result = f"[Page content retrieved]"

        else:
            result = f"[Unknown browser action: {action_type}]"

        # VISUAL GROUNDING: Capture and analyze visual state after browser action
        if capture_visual and self.enable_visual_grounding:
            observation = await self.capture_visual_state(
                action_taken=f"browser_{action_type}: {str(params)[:50]}",
                expected_outcome=params.get("expected_outcome", "")
            )
            if observation:
                result += f"\nVisual: {observation.description}"

        return result

    async def execute_with_visual_verification(
        self,
        action: Action,
        success_criteria: str = ""
    ) -> tuple[str, bool]:
        """
        Execute action and verify success visually.

        This is useful for browser tasks where we need to confirm
        the action had the expected effect.

        Args:
            action: Action to execute
            success_criteria: What success looks like (for vision model)

        Returns:
            Tuple of (result_string, success_bool)
        """
        # Execute the action
        result = await self.execute(action)

        if "Error" in result:
            return result, False

        # For visual actions, check if outcome matches criteria
        if action.tool in VISUAL_TRIGGER_TOOLS and self.last_visual_observation:
            obs = self.last_visual_observation

            # Check if visual observation suggests success
            success_indicators = [
                obs.confidence > 0.7,
                "error" not in obs.description.lower(),
                "fail" not in obs.description.lower()
            ]

            if success_criteria:
                # Check if any suggested actions indicate we achieved our goal
                criteria_lower = success_criteria.lower()
                success_indicators.append(
                    any(criteria_lower in s.lower() for s in obs.suggested_actions)
                    or criteria_lower in obs.description.lower()
                )

            success = all(success_indicators)
            return result, success

        # For non-visual actions, assume success if no error
        return result, True

    def _format_tools(self) -> str:
        """Format available tools for prompt."""
        lines = []
        by_category = {}

        for tool_name, info in self.tools.items():
            cat = info["category"].value
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(tool_name)

        for cat, tools in by_category.items():
            lines.append(f"\n{cat.upper()}:")
            for tool in tools:
                lines.append(f"  - {tool}")

        return "\n".join(lines)

    def _parse_action(self, response: str, step: dict) -> Optional[Action]:
        """Parse action from LLM response."""
        try:
            # Try to find JSON
            if "```json" in response:
                start = response.index("```json") + 7
                end = response.index("```", start)
                response = response[start:end]
            elif "```" in response:
                start = response.index("```") + 3
                end = response.index("```", start)
                response = response[start:end]

            data = json.loads(response.strip())

            tool_name = data.get("tool")
            if not tool_name or tool_name not in self.tools:
                return None

            return Action(
                tool=tool_name,
                params=data.get("params", {}),
                category=self.tools[tool_name]["category"],
                expected_outcome=data.get("expected_result"),
                step_number=step.get("number", 0)
            )

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse action: {e}")
            return None

    def _infer_action(self, step: dict) -> Optional[Action]:
        """Infer action from step tools without LLM."""
        tools = step.get("tools", [])
        if not tools:
            return None

        # Pick first available tool
        for tool_name in tools:
            if tool_name in self.tools:
                return Action(
                    tool=tool_name,
                    params={},  # Would need to be filled
                    category=self.tools[tool_name]["category"],
                    step_number=step.get("number", 0)
                )

        return None
