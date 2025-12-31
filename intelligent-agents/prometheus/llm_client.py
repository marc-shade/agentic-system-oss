"""
LLM Client - Multi-Provider Synthesis for Prometheus Agents.

PROVIDER SYNTHESIS ARCHITECTURE:
┌─────────────────────────────────────────────────────────────┐
│  TIER 1 - Speed (Local, <5s)                                │
│  → Ollama (custom-prometheus/qwen2.5-coder) - Specialized   │
│  → Supports BOTH headless (API) and interactive (tmux)      │
├─────────────────────────────────────────────────────────────┤
│  TIER 2 - Intelligence (OAuth CLI)                          │
│  → Codex: headless=`exec`, interactive=tmux session         │
│  → Gemini: headless=`--yolo`, interactive=browser context   │
├─────────────────────────────────────────────────────────────┤
│  TIER 3 - API Fallback (Requires keys)                      │
│  → Claude API, OpenAI API (headless only)                   │
└─────────────────────────────────────────────────────────────┘

DUAL MODE SUPPORT:
- Headless: Fast, subprocess-based, for automated agent tasks
- Interactive: Full context, for complex multi-step operations

TRAINING DATA COLLECTION:
- Every successful interaction logged for fine-tuning
- Custom Prometheus model improves over time
"""

import os
import json
import logging
import hashlib
import subprocess
import shutil
import httpx
import time
import asyncio
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable, Tuple
from enum import Enum
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================================================
# PROVIDER DETECTION
# ============================================================================

CLAUDE_CODE_AVAILABLE = shutil.which("claude") is not None
GEMINI_CLI_AVAILABLE = shutil.which("gemini") is not None
CODEX_CLI_AVAILABLE = shutil.which("codex") is not None
OLLAMA_AVAILABLE = shutil.which("ollama") is not None

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

# Optional API clients
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


# ============================================================================
# EXECUTION MODES - HEADLESS vs INTERACTIVE
# ============================================================================

class ExecutionMode(Enum):
    """Execution modes for each provider."""
    HEADLESS = "headless"       # Fast subprocess, automated tasks
    INTERACTIVE = "interactive"  # Full context, complex multi-step

# Mode capabilities per provider
PROVIDER_MODES = {
    "ollama": {
        ExecutionMode.HEADLESS: "api",           # Direct HTTP API
        ExecutionMode.INTERACTIVE: "tmux",       # Full session in tmux
    },
    "codex": {
        ExecutionMode.HEADLESS: "exec",          # codex exec "prompt"
        ExecutionMode.INTERACTIVE: "tmux",       # Full REPL session
    },
    "gemini": {
        ExecutionMode.HEADLESS: "yolo",          # gemini --yolo "prompt"
        ExecutionMode.INTERACTIVE: "browser",    # Full browser context
    },
    "claude_code": {
        ExecutionMode.HEADLESS: "print",         # claude -p --output-format json
        ExecutionMode.INTERACTIVE: "tmux",       # Full Claude Code session
    },
    "claude_api": {
        ExecutionMode.HEADLESS: "api",           # API only, no interactive
        ExecutionMode.INTERACTIVE: None,         # Not supported
    },
    "openai_api": {
        ExecutionMode.HEADLESS: "api",           # API only
        ExecutionMode.INTERACTIVE: None,         # Not supported
    },
}


# ============================================================================
# TASK TYPES FOR INTELLIGENT ROUTING
# ============================================================================

class TaskType(Enum):
    """Task types for intelligent model routing."""
    # Speed-optimized (local models)
    JSON_OUTPUT = "json"            # Structured output → Ollama (fast)
    SIMPLE = "simple"               # Quick tasks → Ollama
    ITERATION = "iteration"         # Rapid feedback loops → Ollama

    # Intelligence-required (CLI tools)
    PLANNING = "planning"           # Complex decomposition → Codex
    CODE_GENERATION = "code"        # Code output → Codex/Ollama
    COMPLEX = "complex"             # Deep reasoning → Codex
    VERIFICATION = "verify"         # Different model than generator

    # Multimodal (Gemini)
    MULTIMODAL = "multimodal"       # Images/vision → Gemini
    BROWSER = "browser"             # Web interaction → Gemini

    # Multi-step (Interactive mode)
    RESEARCH = "research"           # Deep exploration → Interactive
    DEBUG = "debug"                 # Interactive debugging → Interactive


# ============================================================================
# TRAINING DATA COLLECTION
# ============================================================================

class TrainingDataCollector:
    """
    Collects successful interactions for fine-tuning custom models.

    Data Format (JSONL):
    {"task_type": "json", "system": "...", "user": "...", "response": "...",
     "provider": "ollama", "success": true, "latency_ms": 150, "timestamp": "..."}
    """

    TRAINING_DATA_DIR = Path("/Volumes/SSDRAID0/agentic-system/training-data/prometheus")

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.TRAINING_DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._current_file = None

    def log_interaction(
        self,
        task_type: TaskType,
        system: str,
        user: str,
        response: str,
        provider: str,
        success: bool,
        latency_ms: float
    ):
        """Log interaction for training data."""
        if not self.enabled:
            return

        entry = {
            "task_type": task_type.value if task_type else "unknown",
            "system": system[:2000],  # Truncate for storage
            "user": user[:2000],
            "response": response[:4000],
            "provider": provider,
            "success": success,
            "latency_ms": round(latency_ms, 2),
            "timestamp": datetime.now().isoformat()
        }

        # Write to daily file
        date_str = datetime.now().strftime("%Y-%m-%d")
        filepath = self.TRAINING_DATA_DIR / f"interactions_{date_str}.jsonl"

        try:
            with open(filepath, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.warning(f"Failed to log training data: {e}")

    def get_training_stats(self) -> Dict[str, Any]:
        """Get statistics on collected training data."""
        stats = {"total_files": 0, "total_entries": 0, "by_provider": {}, "by_task_type": {}}

        for filepath in self.TRAINING_DATA_DIR.glob("interactions_*.jsonl"):
            stats["total_files"] += 1
            with open(filepath) as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        stats["total_entries"] += 1
                        provider = entry.get("provider", "unknown")
                        task_type = entry.get("task_type", "unknown")
                        stats["by_provider"][provider] = stats["by_provider"].get(provider, 0) + 1
                        stats["by_task_type"][task_type] = stats["by_task_type"].get(task_type, 0) + 1
                    except json.JSONDecodeError:
                        pass

        return stats


@dataclass
class LLMResponse:
    """Response from LLM with metadata."""
    content: str
    model: str
    provider: str
    latency_ms: float = 0
    cached: bool = False


# ============================================================================
# LLM CLIENT - PROVIDER SYNTHESIS
# ============================================================================

class LLMClient:
    """
    Multi-Provider Synthesis LLM Client.

    Features:
    - Dual mode: HEADLESS (fast) and INTERACTIVE (full context)
    - Intelligent task-to-model routing
    - Ollama model caching (no repeated API calls)
    - Training data collection for custom model fine-tuning
    - Provider fallback chain with graceful degradation
    - Nested control: Claude Code can orchestrate Codex/Gemini in tmux

    Modes:
    - HEADLESS: subprocess-based, fast, for automated agent tasks
    - INTERACTIVE: tmux sessions, full context, for complex multi-step work
    """

    # Preferred models for each provider (priority order)
    OLLAMA_PREFERRED = [
        "prometheus-agent:latest",      # Custom fine-tuned model (future)
        "qwen2.5-coder:14b",            # Best general-purpose
        "qwen2.5-coder:latest",
        "deepcoder:14b",
        "llama3.1:8b-instruct-q8_0",
        "mistral-small3.2:latest",
        "qwen3:14b",
    ]

    # Task-to-model specialization (for future custom models)
    SPECIALIZED_MODELS = {
        TaskType.JSON_OUTPUT: "prometheus-json:latest",      # JSON output specialist
        TaskType.PLANNING: "prometheus-planner:latest",      # Plan decomposition
        TaskType.CODE_GENERATION: "prometheus-coder:latest", # Code generation
        TaskType.VERIFICATION: "prometheus-verify:latest",   # Verification tasks
    }

    def __init__(
        self,
        cache_enabled: bool = True,
        provider: str = "auto",
        default_mode: ExecutionMode = ExecutionMode.HEADLESS,
        collect_training_data: bool = True,
    ):
        self.cache_enabled = cache_enabled
        self.provider = provider
        self.default_mode = default_mode
        self._cache = {}
        self._active_provider = None
        self._active_mode = None

        # Cached Ollama model (avoid repeated detection)
        self._ollama_model: Optional[str] = None
        self._ollama_models_cache: Optional[List[str]] = None

        # Training data collector
        self._training_collector = TrainingDataCollector(enabled=collect_training_data)

        # Interactive session registry (tmux session names)
        self._interactive_sessions: Dict[str, str] = {}

        # API clients (optional)
        self._anthropic_client = None
        self._openai_client = None

        if ANTHROPIC_AVAILABLE and os.environ.get("ANTHROPIC_API_KEY"):
            self._anthropic_client = anthropic.Anthropic()

        if OPENAI_AVAILABLE and os.environ.get("OPENAI_API_KEY"):
            self._openai_client = openai.OpenAI()

    # ========================================================================
    # INTELLIGENT ROUTING
    # ========================================================================

    def route_task(
        self,
        system: str,
        user: str,
        task_type: TaskType = None
    ) -> tuple[str, ExecutionMode]:
        """
        Route task to optimal provider AND mode based on content analysis.

        Returns: (provider_name, execution_mode)
        """
        combined = (system + user).lower()
        mode = self.default_mode

        # Determine mode first - some tasks require interactive
        if task_type in (TaskType.RESEARCH, TaskType.DEBUG):
            mode = ExecutionMode.INTERACTIVE
        elif "debug" in combined or "explore" in combined or "investigate" in combined:
            mode = ExecutionMode.INTERACTIVE
        elif len(combined) > 10000:  # Very long context → interactive
            mode = ExecutionMode.INTERACTIVE

        # Multimodal → Gemini (native vision)
        if "image" in combined or "screenshot" in combined or "visual" in combined:
            if GEMINI_CLI_AVAILABLE:
                return "gemini", mode

        # Complex planning → Codex (GPT 5.2 strong reasoning)
        if "plan" in combined and ("complex" in combined or len(combined) > 2000):
            if CODEX_CLI_AVAILABLE:
                return "codex", mode

        # Browser interaction → Gemini (has browser context)
        if "browser" in combined or "navigate" in combined or "click" in combined:
            if GEMINI_CLI_AVAILABLE:
                return "gemini", ExecutionMode.INTERACTIVE

        # Simple JSON output → Ollama (fast local)
        if "json" in combined and len(combined) < 1000:
            if OLLAMA_AVAILABLE:
                return "ollama", ExecutionMode.HEADLESS  # Always fast for JSON

        # Code generation → prefer Codex, fallback Ollama
        if "code" in combined or "function" in combined or "implement" in combined:
            if CODEX_CLI_AVAILABLE:
                return "codex", mode
            if OLLAMA_AVAILABLE:
                return "ollama", mode

        # Verification → use different model than last used (diversity)
        if task_type == TaskType.VERIFICATION:
            if self._active_provider == "ollama" and CODEX_CLI_AVAILABLE:
                return "codex", mode
            elif self._active_provider == "codex" and GEMINI_CLI_AVAILABLE:
                return "gemini", mode
            elif OLLAMA_AVAILABLE:
                return "ollama", mode

        # Default: fast local model, headless
        if OLLAMA_AVAILABLE:
            return "ollama", ExecutionMode.HEADLESS
        if GEMINI_CLI_AVAILABLE:
            return "gemini", mode
        if CODEX_CLI_AVAILABLE:
            return "codex", mode

        return "fallback", ExecutionMode.HEADLESS

    def select_specialized_model(self, task_type: TaskType) -> Optional[str]:
        """
        Select specialized model for task type if available.

        Returns model name or None to use default.
        """
        if task_type not in self.SPECIALIZED_MODELS:
            return None

        specialized = self.SPECIALIZED_MODELS[task_type]

        # Check if specialized model exists in Ollama
        if self._ollama_models_cache:
            for model in self._ollama_models_cache:
                if specialized.split(":")[0] in model:
                    logger.info(f"Using specialized model: {model}")
                    return model

        return None

    # ========================================================================
    # MAIN GENERATE METHOD
    # ========================================================================

    async def generate(
        self,
        system: str,
        user: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        use_cache: bool = True,
        task_type: TaskType = None,
        force_provider: str = None,
        force_mode: ExecutionMode = None,
    ) -> str:
        """
        Generate response using optimal provider and mode.

        Args:
            system: System prompt
            user: User message
            max_tokens: Max response tokens
            temperature: Sampling temperature
            use_cache: Use response cache
            task_type: Optional task type for routing
            force_provider: Force specific provider
            force_mode: Force specific execution mode

        Returns:
            Generated text
        """
        start_time = time.time()

        # Check cache
        if self.cache_enabled and use_cache:
            cache_key = self._cache_key(system, user)
            if cache_key in self._cache:
                logger.debug("Cache hit")
                return self._cache[cache_key]

        # Determine provider and mode
        if force_provider:
            provider = force_provider
            mode = force_mode or self.default_mode
        elif self.provider != "auto":
            provider = self.provider
            mode = force_mode or self.default_mode
        else:
            provider, mode = self.route_task(system, user, task_type)

        if force_mode:
            mode = force_mode

        # Check for specialized model
        specialized_model = self.select_specialized_model(task_type) if task_type else None

        # Try providers in order
        response = None
        providers_tried = []
        success = False

        # Primary provider
        response = await self._try_provider(provider, system, user, max_tokens, mode, specialized_model)
        providers_tried.append(provider)
        success = response is not None

        # Fallback chain if primary fails
        if response is None:
            fallback_order = ["ollama", "gemini", "codex", "claude_api", "openai_api"]
            for fallback in fallback_order:
                if fallback not in providers_tried:
                    response = await self._try_provider(fallback, system, user, max_tokens, mode)
                    providers_tried.append(fallback)
                    if response:
                        success = True
                        break

        # Final fallback
        if response is None:
            response = self._fallback_response(system, user)
            self._active_provider = "fallback"
            logger.warning(f"All providers failed ({providers_tried}), using fallback")

        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000

        # Log for training data collection
        self._training_collector.log_interaction(
            task_type=task_type,
            system=system,
            user=user,
            response=response,
            provider=self._active_provider or "fallback",
            success=success,
            latency_ms=latency_ms
        )

        # Cache
        if self.cache_enabled and use_cache and response:
            self._cache[cache_key] = response

        return response

    async def _try_provider(
        self,
        provider: str,
        system: str,
        user: str,
        max_tokens: int,
        mode: ExecutionMode = ExecutionMode.HEADLESS,
        specialized_model: str = None
    ) -> Optional[str]:
        """
        Try a specific provider in specified mode.

        Args:
            provider: Provider name
            system: System prompt
            user: User message
            max_tokens: Max response tokens
            mode: HEADLESS or INTERACTIVE
            specialized_model: Override model for Ollama

        Returns:
            Response text or None on failure
        """
        try:
            if provider == "ollama" and OLLAMA_AVAILABLE:
                if mode == ExecutionMode.INTERACTIVE:
                    result = await self._call_ollama_interactive(system, user, max_tokens)
                else:
                    result = await self._call_ollama(system, user, max_tokens, specialized_model)
                self._active_provider = "ollama"
                self._active_mode = mode
                logger.info(f"Used Ollama ({self._ollama_model}) in {mode.value} mode")
                return result

            elif provider == "gemini" and GEMINI_CLI_AVAILABLE:
                if mode == ExecutionMode.INTERACTIVE:
                    result = await self._call_gemini_interactive(system, user)
                else:
                    result = await self._call_gemini_cli(system, user, max_tokens)
                self._active_provider = "gemini"
                self._active_mode = mode
                logger.info(f"Used Gemini CLI in {mode.value} mode")
                return result

            elif provider == "codex" and CODEX_CLI_AVAILABLE:
                if mode == ExecutionMode.INTERACTIVE:
                    result = await self._call_codex_interactive(system, user)
                else:
                    result = await self._call_codex_cli(system, user, max_tokens)
                self._active_provider = "codex"
                self._active_mode = mode
                logger.info(f"Used Codex CLI in {mode.value} mode")
                return result

            elif provider == "claude_code" and CLAUDE_CODE_AVAILABLE:
                if mode == ExecutionMode.INTERACTIVE:
                    result = await self._call_claude_code_interactive(system, user)
                else:
                    result = await self._call_claude_code_headless(system, user)
                self._active_provider = "claude_code"
                self._active_mode = mode
                logger.info(f"Used Claude Code in {mode.value} mode")
                return result

            elif provider == "claude_api" and self._anthropic_client:
                # API only supports headless
                result = await self._call_claude_api(system, user, max_tokens)
                self._active_provider = "claude_api"
                self._active_mode = ExecutionMode.HEADLESS
                logger.info("Used Claude API")
                return result

            elif provider == "openai_api" and self._openai_client:
                # API only supports headless
                result = await self._call_openai_api(system, user, max_tokens)
                self._active_provider = "openai_api"
                self._active_mode = ExecutionMode.HEADLESS
                logger.info("Used OpenAI API")
                return result

        except Exception as e:
            logger.warning(f"{provider} ({mode.value}) error: {e}")

        return None

    # ========================================================================
    # OLLAMA - Fast Local LLM
    # ========================================================================

    async def _get_ollama_model(self) -> str:
        """Get best available Ollama model (cached)."""
        if self._ollama_model:
            return self._ollama_model

        if self._ollama_models_cache is None:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
                    if response.status_code == 200:
                        data = response.json()
                        self._ollama_models_cache = [m.get("name", "") for m in data.get("models", [])]
            except Exception:
                self._ollama_models_cache = []

        # Find best model
        for preferred in self.OLLAMA_PREFERRED:
            for available in self._ollama_models_cache:
                if preferred in available.lower() or available.lower() in preferred:
                    self._ollama_model = available
                    logger.info(f"Selected Ollama model: {self._ollama_model}")
                    return self._ollama_model

        # Use first available
        if self._ollama_models_cache:
            self._ollama_model = self._ollama_models_cache[0]
            return self._ollama_model

        raise RuntimeError("No Ollama models available")

    async def _call_ollama(
        self,
        system: str,
        user: str,
        max_tokens: int,
        specialized_model: str = None
    ) -> str:
        """Call Ollama with JSON format support (HEADLESS mode)."""
        model = specialized_model or await self._get_ollama_model()

        # Detect if JSON output requested
        use_json = "json" in system.lower() or "{" in system

        async with httpx.AsyncClient(timeout=120.0) as client:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                "stream": False,
                "options": {"num_predict": max_tokens}
            }
            if use_json:
                payload["format"] = "json"

            response = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)

            if response.status_code != 200:
                raise RuntimeError(f"Ollama error: {response.text}")

            return response.json().get("message", {}).get("content", "")

    async def _call_ollama_interactive(self, system: str, user: str, max_tokens: int) -> str:
        """
        Call Ollama in INTERACTIVE mode via tmux.

        Starts a persistent tmux session for multi-turn conversations.
        """
        session_name = f"ollama-{hash(system[:50]) % 10000}"

        # Check if session exists
        result = subprocess.run(
            ["tmux", "has-session", "-t", session_name],
            capture_output=True
        )

        if result.returncode != 0:
            # Create new session with ollama
            model = await self._get_ollama_model()
            subprocess.run(
                ["tmux", "new-session", "-d", "-s", session_name, f"ollama run {model}"],
                check=True
            )
            await asyncio.sleep(2)  # Wait for model to load

        # Send message and capture response
        full_prompt = f"{system}\n\n{user}"
        subprocess.run(
            ["tmux", "send-keys", "-t", session_name, full_prompt, "Enter"],
            check=True
        )

        # Wait for response (poll for completion)
        await asyncio.sleep(5)  # Initial wait

        # Capture output
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", session_name, "-p"],
            capture_output=True,
            text=True
        )

        self._interactive_sessions["ollama"] = session_name
        return result.stdout.strip()

    # ========================================================================
    # GEMINI CLI - OAuth, Multimodal
    # ========================================================================

    async def _call_gemini_cli(self, system: str, user: str, max_tokens: int) -> str:
        """
        Call Gemini CLI with --yolo for auto-approve.

        Features:
        - --yolo: Auto-approve all actions (faster)
        - --output-format json: Structured output for parsing
        - Positional prompt for one-shot mode
        """
        full_prompt = f"{system}\n\n{user}"

        # Truncate if too long (Gemini CLI limit)
        if len(full_prompt) > 8000:
            available = 8000 - len(user) - 100
            system = system[:available] + "..."
            full_prompt = f"{system}\n\n{user}"

        # Use --yolo for auto-approve, speeds up execution
        cmd = [
            "gemini",
            "--yolo",  # Auto-approve all actions
            full_prompt
        ]

        logger.debug(f"Gemini CLI: prompt len {len(full_prompt)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=90
        )

        if result.returncode != 0:
            raise RuntimeError(f"Gemini failed: {result.stderr[:200]}")

        return result.stdout.strip()

    async def _call_gemini_interactive(self, system: str, user: str) -> str:
        """
        Call Gemini in INTERACTIVE mode via tmux.

        Full browser context with file access and tool execution.
        """
        session_name = f"gemini-{hash(system[:50]) % 10000}"

        # Check if session exists
        result = subprocess.run(
            ["tmux", "has-session", "-t", session_name],
            capture_output=True
        )

        if result.returncode != 0:
            # Create new session with gemini (interactive mode)
            subprocess.run(
                ["tmux", "new-session", "-d", "-s", session_name, "gemini"],
                check=True
            )
            await asyncio.sleep(3)  # Wait for Gemini to start

        # Send initial context (system prompt)
        subprocess.run(
            ["tmux", "send-keys", "-t", session_name, system, "Enter"],
            check=True
        )
        await asyncio.sleep(2)

        # Send user message
        subprocess.run(
            ["tmux", "send-keys", "-t", session_name, user, "Enter"],
            check=True
        )

        # Wait for response
        await asyncio.sleep(10)  # Gemini can take time

        # Capture output
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", session_name, "-p", "-S", "-100"],
            capture_output=True,
            text=True
        )

        self._interactive_sessions["gemini"] = session_name
        return result.stdout.strip()

    # ========================================================================
    # CODEX CLI - GPT 5.2 / o3
    # ========================================================================

    async def _call_codex_cli(self, system: str, user: str, max_tokens: int) -> str:
        """
        Call Codex CLI in exec mode (non-interactive).

        Uses GPT 5.2 or o3 depending on configuration.
        """
        full_prompt = f"{system}\n\n{user}"

        cmd = ["codex", "exec", full_prompt]

        logger.debug("Codex CLI exec mode")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode != 0:
            raise RuntimeError(f"Codex failed: {result.stderr[:200]}")

        return result.stdout.strip()

    async def _call_codex_interactive(self, system: str, user: str) -> str:
        """
        Call Codex in INTERACTIVE mode via tmux.

        Full REPL with code execution and file access.
        """
        session_name = f"codex-{hash(system[:50]) % 10000}"

        # Check if session exists
        result = subprocess.run(
            ["tmux", "has-session", "-t", session_name],
            capture_output=True
        )

        if result.returncode != 0:
            # Create new session with codex (interactive mode)
            subprocess.run(
                ["tmux", "new-session", "-d", "-s", session_name, "codex"],
                check=True
            )
            await asyncio.sleep(3)  # Wait for Codex to start

        # Send initial context (system prompt)
        subprocess.run(
            ["tmux", "send-keys", "-t", session_name, system, "Enter"],
            check=True
        )
        await asyncio.sleep(2)

        # Send user message
        subprocess.run(
            ["tmux", "send-keys", "-t", session_name, user, "Enter"],
            check=True
        )

        # Wait for response
        await asyncio.sleep(10)  # Codex can take time

        # Capture output
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", session_name, "-p", "-S", "-100"],
            capture_output=True,
            text=True
        )

        self._interactive_sessions["codex"] = session_name
        return result.stdout.strip()

    # ========================================================================
    # CLAUDE CODE CLI
    # ========================================================================

    async def _call_claude_code_headless(self, system: str, user: str) -> str:
        """
        Call Claude Code in HEADLESS mode.

        Uses -p (print mode) with --output-format json for structured output.
        """
        full_prompt = f"{system}\n\n{user}"

        cmd = [
            "claude",
            "-p", full_prompt,
            "--output-format", "json"
        ]

        logger.debug("Claude Code headless mode")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode != 0:
            raise RuntimeError(f"Claude Code failed: {result.stderr[:200]}")

        # Parse JSON output
        try:
            data = json.loads(result.stdout)
            return data.get("result", result.stdout)
        except json.JSONDecodeError:
            return result.stdout.strip()

    async def _call_claude_code_interactive(self, system: str, user: str) -> str:
        """
        Call Claude Code in INTERACTIVE mode via tmux.

        Full Claude Code session with tool access, memory, and MCP servers.
        This is the most powerful mode - Claude orchestrating other tools.
        """
        session_name = f"claude-{hash(system[:50]) % 10000}"

        # Check if session exists
        result = subprocess.run(
            ["tmux", "has-session", "-t", session_name],
            capture_output=True
        )

        if result.returncode != 0:
            # Create new session with claude (interactive mode)
            subprocess.run(
                ["tmux", "new-session", "-d", "-s", session_name, "claude"],
                check=True
            )
            await asyncio.sleep(5)  # Wait for Claude to start (longer for MCP)

        # Send initial context (system prompt)
        subprocess.run(
            ["tmux", "send-keys", "-t", session_name, system, "Enter"],
            check=True
        )
        await asyncio.sleep(3)

        # Send user message
        subprocess.run(
            ["tmux", "send-keys", "-t", session_name, user, "Enter"],
            check=True
        )

        # Wait for response (Claude can be slow)
        await asyncio.sleep(15)

        # Capture output
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", session_name, "-p", "-S", "-200"],
            capture_output=True,
            text=True
        )

        self._interactive_sessions["claude"] = session_name
        return result.stdout.strip()

    # ========================================================================
    # API FALLBACKS
    # ========================================================================

    async def _call_claude_api(self, system: str, user: str, max_tokens: int) -> str:
        """Call Claude API (requires ANTHROPIC_API_KEY)."""
        message = self._anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}]
        )
        return message.content[0].text

    async def _call_openai_api(self, system: str, user: str, max_tokens: int) -> str:
        """Call OpenAI API (requires OPENAI_API_KEY)."""
        response = self._openai_client.chat.completions.create(
            model="gpt-4o",
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ]
        )
        return response.choices[0].message.content

    # ========================================================================
    # FALLBACK & UTILITIES
    # ========================================================================

    def _fallback_response(self, system: str, user: str) -> str:
        """Fallback when all providers fail."""
        if "json" in system.lower():
            return json.dumps({
                "tool": "notify_user",
                "params": {"message": "All LLM providers unavailable"},
                "error": True
            })
        return "Error: All LLM providers unavailable"

    def _cache_key(self, system: str, user: str) -> str:
        """Generate cache key."""
        return hashlib.md5(f"{system}|||{user}".encode()).hexdigest()

    def clear_cache(self):
        """Clear response cache."""
        self._cache.clear()

    @property
    def active_provider(self) -> str:
        return self._active_provider or "none"

    @property
    def available_providers(self) -> List[str]:
        """List available providers."""
        providers = []
        if OLLAMA_AVAILABLE:
            providers.append("ollama")
        if GEMINI_CLI_AVAILABLE:
            providers.append("gemini")
        if CODEX_CLI_AVAILABLE:
            providers.append("codex")
        if CLAUDE_CODE_AVAILABLE:
            providers.append("claude_code")
        if self._anthropic_client:
            providers.append("claude_api")
        if self._openai_client:
            providers.append("openai_api")
        return providers

    @property
    def active_mode(self) -> str:
        """Return current execution mode."""
        return self._active_mode.value if self._active_mode else "none"

    def get_training_stats(self) -> Dict[str, Any]:
        """Get training data statistics."""
        return self._training_collector.get_training_stats()

    def list_interactive_sessions(self) -> Dict[str, str]:
        """List active interactive tmux sessions."""
        return self._interactive_sessions.copy()

    def close_interactive_session(self, provider: str) -> bool:
        """Close an interactive tmux session."""
        if provider not in self._interactive_sessions:
            return False

        session_name = self._interactive_sessions[provider]
        try:
            subprocess.run(
                ["tmux", "kill-session", "-t", session_name],
                check=True
            )
            del self._interactive_sessions[provider]
            return True
        except subprocess.CalledProcessError:
            return False

    def close_all_sessions(self):
        """Close all interactive sessions."""
        for provider in list(self._interactive_sessions.keys()):
            self.close_interactive_session(provider)


# ============================================================================
# GLOBAL CLIENT
# ============================================================================

_default_client: Optional[LLMClient] = None

def get_llm_client() -> LLMClient:
    """Get or create default LLM client."""
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client

def set_llm_client(client: LLMClient):
    """Set default LLM client."""
    global _default_client
    _default_client = client
