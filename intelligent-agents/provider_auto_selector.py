#!/usr/bin/env python3
"""
Multi-Provider Auto-Selector with Health Monitoring

Intelligently routes AI tasks to the best available provider based on:
- Provider health/availability
- Task type suitability
- Cost optimization
- Historical success rates
- Response latency

Supported Providers:
  CLI-Based (run headless in tmux/scripts/workflows):
  - Claude Code CLI - Best for complex reasoning, code, agentic tasks
  - Codex CLI (OpenAI) - Code generation, debugging, interactive coding
  - Gemini CLI (Google) - Fast responses, good for summarization

  API-Based:
  - Claude API (Anthropic) - Direct API access
  - OpenAI API - GPT-4, embeddings
  - Google API - Gemini models via API

  Self-Hosted:
  - Ollama (Local/Remote) - Zero cost, privacy, specialized models

Usage:
    from provider_auto_selector import ProviderAutoSelector

    selector = ProviderAutoSelector()
    provider = selector.select_provider(task_type="code_generation")
    # Returns: ProviderSelection with provider, model, endpoint, reasoning

Run as daemon:
    python3 provider_auto_selector.py --daemon --interval 60
"""

import os
import sys
import json
import time
import signal
import logging
import argparse
import threading
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Task types for provider routing"""
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    REASONING = "reasoning"
    SUMMARIZATION = "summarization"
    CHAT = "chat"
    TOOL_USE = "tool_use"
    VISION = "vision"
    EMBEDDING = "embedding"
    RESEARCH = "research"
    CREATIVE = "creative"


class ProviderType(Enum):
    """Provider execution type"""
    CLI = "cli"        # CLI tool (claude, codex, gemini)
    API = "api"        # HTTP API (Anthropic, OpenAI, Google APIs)
    LOCAL = "local"    # Self-hosted (Ollama)


class Provider(Enum):
    """Available AI providers"""
    # CLI-based providers (run headless in tmux/scripts)
    CLAUDE_CLI = "claude_cli"      # Claude Code CLI
    CODEX_CLI = "codex_cli"        # OpenAI Codex CLI
    GEMINI_CLI = "gemini_cli"      # Google Gemini CLI
    # API-based providers
    CLAUDE_API = "claude_api"      # Anthropic API
    OPENAI_API = "openai_api"      # OpenAI API
    GEMINI_API = "gemini_api"      # Google Gemini API
    # Self-hosted
    OLLAMA = "ollama"              # Ollama (local/remote)


@dataclass
class ProviderHealth:
    """Health status for a provider"""
    provider: str
    available: bool = False
    latency_ms: float = 0.0
    last_check: Optional[datetime] = None
    consecutive_failures: int = 0
    error_message: Optional[str] = None
    models_available: List[str] = field(default_factory=list)


@dataclass
class ProviderSelection:
    """Result of provider selection"""
    provider: Provider
    model: str
    endpoint: Optional[str]
    reasoning: str
    cost_tier: str  # "free", "low", "medium", "high"
    expected_latency: str  # "fast", "medium", "slow"
    confidence: float  # 0.0 to 1.0


@dataclass
class ProviderConfig:
    """Configuration for a provider"""
    name: str
    enabled: bool
    provider_type: ProviderType
    api_key_env: Optional[str]        # For API providers
    cli_command: Optional[str]        # For CLI providers
    base_url: Optional[str]           # For API/local providers
    models: Dict[str, List[str]]      # task_type -> [models]
    cost_per_1k_tokens: float
    priority: int                     # Lower = higher priority
    max_consecutive_failures: int = 5


class ProviderAutoSelector:
    """
    Intelligent multi-provider selector with health monitoring
    """

    # Provider configurations
    PROVIDER_CONFIGS = {
        # CLI-based providers (run headless in tmux/scripts/workflows)
        Provider.CLAUDE_CLI: ProviderConfig(
            name="Claude Code CLI",
            enabled=True,
            provider_type=ProviderType.CLI,
            api_key_env="ANTHROPIC_API_KEY",
            cli_command="claude",
            base_url=None,
            models={
                TaskType.CODE_GENERATION.value: ["claude-sonnet-4-20250514"],
                TaskType.CODE_REVIEW.value: ["claude-sonnet-4-20250514"],
                TaskType.REASONING.value: ["claude-sonnet-4-20250514"],
                TaskType.RESEARCH.value: ["claude-sonnet-4-20250514"],
                TaskType.TOOL_USE.value: ["claude-sonnet-4-20250514"],
                TaskType.CHAT.value: ["claude-sonnet-4-20250514"],
                TaskType.CREATIVE.value: ["claude-sonnet-4-20250514"],
            },
            cost_per_1k_tokens=0.003,
            priority=1,
        ),
        Provider.CODEX_CLI: ProviderConfig(
            name="Codex CLI (OpenAI)",
            enabled=True,
            provider_type=ProviderType.CLI,
            api_key_env="OPENAI_API_KEY",
            cli_command="codex",
            base_url=None,
            models={
                TaskType.CODE_GENERATION.value: ["codex"],
                TaskType.CODE_REVIEW.value: ["codex"],
                TaskType.REASONING.value: ["codex"],
                TaskType.CHAT.value: ["codex"],
            },
            cost_per_1k_tokens=0.005,
            priority=2,
        ),
        Provider.GEMINI_CLI: ProviderConfig(
            name="Gemini CLI (Google)",
            enabled=True,
            provider_type=ProviderType.CLI,
            api_key_env="GOOGLE_API_KEY",
            cli_command="gemini",
            base_url=None,
            models={
                TaskType.CODE_GENERATION.value: ["gemini"],
                TaskType.REASONING.value: ["gemini"],
                TaskType.SUMMARIZATION.value: ["gemini"],
                TaskType.CHAT.value: ["gemini"],
                TaskType.RESEARCH.value: ["gemini"],
            },
            cost_per_1k_tokens=0.00025,
            priority=3,
        ),
        # API-based providers (for programmatic access)
        Provider.CLAUDE_API: ProviderConfig(
            name="Claude API (Anthropic)",
            enabled=True,
            provider_type=ProviderType.API,
            api_key_env="ANTHROPIC_API_KEY",
            cli_command=None,
            base_url="https://api.anthropic.com",
            models={
                TaskType.CODE_GENERATION.value: ["claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022"],
                TaskType.CODE_REVIEW.value: ["claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022"],
                TaskType.REASONING.value: ["claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022"],
                TaskType.RESEARCH.value: ["claude-sonnet-4-20250514"],
                TaskType.TOOL_USE.value: ["claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022"],
                TaskType.CHAT.value: ["claude-3-5-haiku-20241022", "claude-3-5-sonnet-20241022"],
                TaskType.SUMMARIZATION.value: ["claude-3-5-haiku-20241022"],
                TaskType.CREATIVE.value: ["claude-sonnet-4-20250514"],
            },
            cost_per_1k_tokens=0.003,
            priority=4,
        ),
        Provider.OPENAI_API: ProviderConfig(
            name="OpenAI API",
            enabled=True,
            provider_type=ProviderType.API,
            api_key_env="OPENAI_API_KEY",
            cli_command=None,
            base_url="https://api.openai.com",
            models={
                TaskType.CODE_GENERATION.value: ["gpt-4o", "gpt-4-turbo"],
                TaskType.CODE_REVIEW.value: ["gpt-4o", "gpt-4-turbo"],
                TaskType.REASONING.value: ["o1-preview", "gpt-4o"],
                TaskType.VISION.value: ["gpt-4o", "gpt-4-vision-preview"],
                TaskType.TOOL_USE.value: ["gpt-4o", "gpt-4-turbo"],
                TaskType.CHAT.value: ["gpt-4o-mini", "gpt-3.5-turbo"],
                TaskType.SUMMARIZATION.value: ["gpt-4o-mini", "gpt-3.5-turbo"],
                TaskType.EMBEDDING.value: ["text-embedding-3-small", "text-embedding-ada-002"],
            },
            cost_per_1k_tokens=0.005,
            priority=5,
        ),
        Provider.GEMINI_API: ProviderConfig(
            name="Gemini API (Google)",
            enabled=True,
            provider_type=ProviderType.API,
            api_key_env="GOOGLE_API_KEY",
            cli_command=None,
            base_url="https://generativelanguage.googleapis.com",
            models={
                TaskType.CODE_GENERATION.value: ["gemini-1.5-pro", "gemini-1.5-flash"],
                TaskType.REASONING.value: ["gemini-1.5-pro"],
                TaskType.SUMMARIZATION.value: ["gemini-1.5-flash"],
                TaskType.CHAT.value: ["gemini-1.5-flash"],
                TaskType.VISION.value: ["gemini-1.5-pro"],
                TaskType.RESEARCH.value: ["gemini-1.5-pro"],
            },
            cost_per_1k_tokens=0.00025,
            priority=6,
        ),
        # Self-hosted (Ollama)
        Provider.OLLAMA: ProviderConfig(
            name="Ollama (Local/Remote)",
            enabled=True,
            provider_type=ProviderType.LOCAL,
            api_key_env=None,
            cli_command=None,
            base_url=None,  # Dynamic based on cluster
            models={
                TaskType.CODE_GENERATION.value: ["qwen3-coder:30b", "deepseek-coder:33b"],
                TaskType.REASONING.value: ["deepseek-r1:32b-qwen-distill-fp16"],
                TaskType.TOOL_USE.value: ["llama3-groq-tool-use:8b-fp16"],
                TaskType.CHAT.value: ["llama3.2:latest", "mistral:latest"],
                TaskType.VISION.value: ["llama3.2-vision:11b-instruct-q8_0"],
                TaskType.EMBEDDING.value: ["nomic-embed-text:latest"],
            },
            cost_per_1k_tokens=0.0,  # Free (self-hosted)
            priority=7,
        ),
    }

    # Task-to-provider preferences (ordered by suitability)
    # CLI providers preferred for interactive/agentic work
    TASK_PREFERENCES = {
        TaskType.CODE_GENERATION: [Provider.CLAUDE_CLI, Provider.CODEX_CLI, Provider.GEMINI_CLI, Provider.OLLAMA, Provider.CLAUDE_API],
        TaskType.CODE_REVIEW: [Provider.CLAUDE_CLI, Provider.CODEX_CLI, Provider.GEMINI_CLI, Provider.CLAUDE_API],
        TaskType.REASONING: [Provider.CLAUDE_CLI, Provider.CODEX_CLI, Provider.OLLAMA, Provider.CLAUDE_API],
        TaskType.SUMMARIZATION: [Provider.GEMINI_CLI, Provider.CLAUDE_CLI, Provider.OLLAMA, Provider.GEMINI_API],
        TaskType.CHAT: [Provider.GEMINI_CLI, Provider.OLLAMA, Provider.CODEX_CLI, Provider.CLAUDE_CLI],
        TaskType.TOOL_USE: [Provider.CLAUDE_CLI, Provider.CODEX_CLI, Provider.OLLAMA, Provider.CLAUDE_API],
        TaskType.VISION: [Provider.OPENAI_API, Provider.GEMINI_API, Provider.OLLAMA],  # Vision needs API
        TaskType.EMBEDDING: [Provider.OLLAMA, Provider.OPENAI_API],  # Local preferred for embeddings
        TaskType.RESEARCH: [Provider.CLAUDE_CLI, Provider.GEMINI_CLI, Provider.CLAUDE_API],
        TaskType.CREATIVE: [Provider.CLAUDE_CLI, Provider.CODEX_CLI, Provider.GEMINI_CLI],
    }

    # Ollama endpoints (cluster nodes)
    OLLAMA_ENDPOINTS = [
        ("completeu-server", "http://192.168.1.186:11434"),
        ("mac-studio", "http://192.168.1.16:11434"),
    ]

    def __init__(self, config_path: Optional[str] = None):
        self.health_status: Dict[Provider, ProviderHealth] = {}
        self.success_history: Dict[Provider, List[Tuple[datetime, bool]]] = {p: [] for p in Provider}
        self.config_path = config_path or str(Path.home() / ".claude" / "provider_selector.json")
        self.running = True
        self._lock = threading.Lock()

        # Initialize health status
        for provider in Provider:
            self.health_status[provider] = ProviderHealth(provider=provider.value)

        # Load persisted state
        self._load_state()

        # Initial health check
        self.check_all_providers()

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown gracefully"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        self._save_state()

    def _load_state(self):
        """Load persisted state from disk"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path) as f:
                    state = json.load(f)
                    # Restore success history
                    for provider_name, history in state.get("success_history", {}).items():
                        try:
                            provider = Provider(provider_name)
                            self.success_history[provider] = [
                                (datetime.fromisoformat(ts), success)
                                for ts, success in history[-100:]  # Keep last 100
                            ]
                        except ValueError:
                            pass
                logger.info(f"Loaded state from {self.config_path}")
        except Exception as e:
            logger.warning(f"Could not load state: {e}")

    def _save_state(self):
        """Persist state to disk"""
        try:
            state = {
                "success_history": {
                    p.value: [(ts.isoformat(), s) for ts, s in hist[-100:]]
                    for p, hist in self.success_history.items()
                },
                "last_updated": datetime.now().isoformat()
            }
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save state: {e}")

    def _has_api_key(self, provider: Provider) -> bool:
        """Check if API key is configured for provider"""
        config = self.PROVIDER_CONFIGS[provider]
        return bool(os.environ.get(config.api_key_env))

    def check_provider_health(self, provider: Provider) -> ProviderHealth:
        """Check health of a single provider"""
        config = self.PROVIDER_CONFIGS[provider]
        health = ProviderHealth(provider=provider.value)

        if not config.enabled:
            health.error_message = "Provider disabled"
            return health

        # Check API key requirement (skip for Ollama and CLI providers without key requirement)
        if config.api_key_env and not os.environ.get(config.api_key_env):
            if config.provider_type == ProviderType.API:
                health.error_message = f"Missing API key: {config.api_key_env}"
                return health
            # CLI providers may work without key if already authenticated
            elif config.provider_type == ProviderType.CLI:
                logger.debug(f"{provider.value}: API key not set, checking CLI anyway")

        start_time = time.time()

        try:
            # Route based on provider type
            if config.provider_type == ProviderType.CLI:
                health = self._check_cli_health(provider, config)
            elif config.provider_type == ProviderType.LOCAL:
                health = self._check_ollama_health(config)
            elif config.provider_type == ProviderType.API:
                # Route API providers to specific health checks
                if provider == Provider.CLAUDE_API:
                    health = self._check_claude_api_health(config)
                elif provider == Provider.OPENAI_API:
                    health = self._check_openai_api_health(config)
                elif provider == Provider.GEMINI_API:
                    health = self._check_gemini_api_health(config)

            health.latency_ms = (time.time() - start_time) * 1000
            health.last_check = datetime.now()

        except Exception as e:
            health.available = False
            health.error_message = str(e)
            health.last_check = datetime.now()

        with self._lock:
            old_health = self.health_status.get(provider)
            if old_health and not health.available:
                health.consecutive_failures = old_health.consecutive_failures + 1
            elif health.available:
                health.consecutive_failures = 0
            self.health_status[provider] = health

        return health

    def _check_cli_health(self, provider: Provider, config: ProviderConfig) -> ProviderHealth:
        """Check CLI provider health by verifying binary exists and responds"""
        import subprocess
        import shutil

        health = ProviderHealth(provider=provider.value)

        if not config.cli_command:
            health.error_message = "No CLI command configured"
            return health

        # Check if CLI binary exists
        cli_path = shutil.which(config.cli_command)
        if not cli_path:
            health.error_message = f"CLI not found: {config.cli_command}"
            return health

        try:
            # Try to get version to verify CLI is functional
            if config.cli_command == "claude":
                # Claude Code CLI - check with --version
                result = subprocess.run(
                    [config.cli_command, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    health.available = True
                    health.models_available = list(config.models.get(TaskType.CODE_GENERATION.value, []))
                    logger.debug(f"Claude CLI available: {result.stdout.strip()}")
                else:
                    health.error_message = f"CLI error: {result.stderr.strip()}"

            elif config.cli_command == "codex":
                # Codex CLI - check with --version
                result = subprocess.run(
                    [config.cli_command, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    health.available = True
                    health.models_available = list(config.models.get(TaskType.CODE_GENERATION.value, []))
                    logger.debug(f"Codex CLI available: {result.stdout.strip()}")
                else:
                    health.error_message = f"CLI error: {result.stderr.strip()}"

            elif config.cli_command == "gemini":
                # Gemini CLI - check with --version
                result = subprocess.run(
                    [config.cli_command, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    health.available = True
                    health.models_available = list(config.models.get(TaskType.CODE_GENERATION.value, []))
                    logger.debug(f"Gemini CLI available: {result.stdout.strip()}")
                else:
                    health.error_message = f"CLI error: {result.stderr.strip()}"

            else:
                # Generic CLI check
                result = subprocess.run(
                    [config.cli_command, "--help"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                health.available = result.returncode == 0
                if not health.available:
                    health.error_message = f"CLI error: {result.stderr.strip()}"

        except subprocess.TimeoutExpired:
            health.error_message = "CLI timeout"
        except Exception as e:
            health.error_message = f"CLI check failed: {e}"

        return health

    def _check_claude_api_health(self, config: ProviderConfig) -> ProviderHealth:
        """Check Claude API health"""
        health = ProviderHealth(provider="claude_api")
        api_key = os.environ.get(config.api_key_env)

        # Simple ping - check if API responds
        try:
            response = requests.get(
                f"{config.base_url}/v1/models",
                headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
                timeout=5
            )
            # Claude doesn't have a models endpoint, but we can check auth
            if response.status_code in [200, 404]:  # 404 is expected, but means API is up
                health.available = True
                health.models_available = list(config.models.get(TaskType.CODE_GENERATION.value, []))
            else:
                health.error_message = f"HTTP {response.status_code}"
        except requests.Timeout:
            health.error_message = "Timeout"
        except Exception as e:
            health.error_message = str(e)

        return health

    def _check_openai_api_health(self, config: ProviderConfig) -> ProviderHealth:
        """Check OpenAI API health"""
        health = ProviderHealth(provider="openai_api")
        api_key = os.environ.get(config.api_key_env)

        try:
            response = requests.get(
                f"{config.base_url}/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=5
            )
            if response.status_code == 200:
                health.available = True
                data = response.json()
                health.models_available = [m["id"] for m in data.get("data", [])][:10]
            else:
                health.error_message = f"HTTP {response.status_code}"
        except requests.Timeout:
            health.error_message = "Timeout"
        except Exception as e:
            health.error_message = str(e)

        return health

    def _check_gemini_api_health(self, config: ProviderConfig) -> ProviderHealth:
        """Check Gemini API health"""
        health = ProviderHealth(provider="gemini_api")
        api_key = os.environ.get(config.api_key_env)

        try:
            response = requests.get(
                f"{config.base_url}/v1/models?key={api_key}",
                timeout=5
            )
            if response.status_code == 200:
                health.available = True
                data = response.json()
                health.models_available = [m["name"].split("/")[-1] for m in data.get("models", [])][:10]
            else:
                health.error_message = f"HTTP {response.status_code}"
        except requests.Timeout:
            health.error_message = "Timeout"
        except Exception as e:
            health.error_message = str(e)

        return health

    def _check_ollama_health(self, config: ProviderConfig) -> ProviderHealth:
        """Check Ollama endpoints health"""
        health = ProviderHealth(provider="ollama")

        for name, endpoint in self.OLLAMA_ENDPOINTS:
            try:
                response = requests.get(f"{endpoint}/api/tags", timeout=3)
                if response.status_code == 200:
                    health.available = True
                    data = response.json()
                    models = [m["name"] for m in data.get("models", [])]
                    health.models_available.extend(models)
                    logger.debug(f"Ollama {name} available with {len(models)} models")
            except Exception as e:
                logger.debug(f"Ollama {name} unavailable: {e}")

        if not health.available:
            health.error_message = "No Ollama endpoints available"

        return health

    def check_all_providers(self) -> Dict[Provider, ProviderHealth]:
        """Check health of all providers"""
        results = {}
        for provider in Provider:
            results[provider] = self.check_provider_health(provider)
            logger.debug(f"{provider.value}: {'✓' if results[provider].available else '✗'}")
        return results

    def get_success_rate(self, provider: Provider, hours: int = 24) -> float:
        """Calculate success rate for provider over time window"""
        cutoff = datetime.now() - timedelta(hours=hours)
        with self._lock:
            recent = [(ts, s) for ts, s in self.success_history[provider] if ts > cutoff]

        if not recent:
            return 0.5  # No data, assume neutral

        successes = sum(1 for _, s in recent if s)
        return successes / len(recent)

    def record_result(self, provider: Provider, success: bool):
        """Record success/failure for learning"""
        with self._lock:
            self.success_history[provider].append((datetime.now(), success))
            # Keep only last 1000 entries
            if len(self.success_history[provider]) > 1000:
                self.success_history[provider] = self.success_history[provider][-500:]

    def select_provider(
        self,
        task_type: str,
        prefer_cost: bool = False,
        require_local: bool = False,
        exclude_providers: Optional[List[str]] = None
    ) -> ProviderSelection:
        """
        Select best provider for a task

        Args:
            task_type: Type of task (code_generation, reasoning, etc.)
            prefer_cost: Prefer cheaper providers
            require_local: Require local/private processing (Ollama only)
            exclude_providers: Providers to exclude

        Returns:
            ProviderSelection with chosen provider and reasoning
        """
        try:
            task = TaskType(task_type)
        except ValueError:
            task = TaskType.CHAT

        exclude_set = set(exclude_providers or [])

        # Get preference order for this task
        preferences = self.TASK_PREFERENCES.get(task, list(Provider))

        # If require_local, only consider Ollama
        if require_local:
            preferences = [Provider.OLLAMA]

        # If prefer_cost, sort by cost
        if prefer_cost:
            preferences = sorted(
                preferences,
                key=lambda p: self.PROVIDER_CONFIGS[p].cost_per_1k_tokens
            )

        # Find first available provider
        for provider in preferences:
            if provider.value in exclude_set:
                continue

            config = self.PROVIDER_CONFIGS[provider]
            health = self.health_status.get(provider)

            # Skip if not healthy
            if not health or not health.available:
                continue

            # Skip if too many failures
            if health.consecutive_failures >= config.max_consecutive_failures:
                continue

            # Skip if no models for this task
            if task.value not in config.models:
                continue

            # Found a suitable provider
            models = config.models[task.value]
            model = models[0] if models else "default"

            success_rate = self.get_success_rate(provider)

            # Determine endpoint for Ollama
            endpoint = config.base_url
            if provider == Provider.OLLAMA:
                for name, url in self.OLLAMA_ENDPOINTS:
                    try:
                        response = requests.get(f"{url}/api/tags", timeout=2)
                        if response.status_code == 200:
                            endpoint = url
                            break
                    except:
                        continue

            # Build reasoning
            reasons = []
            if provider == preferences[0]:
                reasons.append(f"Best match for {task.value}")
            if success_rate > 0.8:
                reasons.append(f"High success rate ({success_rate:.0%})")
            if config.cost_per_1k_tokens == 0:
                reasons.append("Zero cost")
            elif prefer_cost:
                reasons.append(f"Low cost (${config.cost_per_1k_tokens}/1k tokens)")
            if health.latency_ms < 500:
                reasons.append(f"Fast response ({health.latency_ms:.0f}ms)")

            return ProviderSelection(
                provider=provider,
                model=model,
                endpoint=endpoint,
                reasoning="; ".join(reasons) if reasons else "Available",
                cost_tier=self._get_cost_tier(config.cost_per_1k_tokens),
                expected_latency=self._get_latency_tier(health.latency_ms),
                confidence=min(1.0, success_rate + 0.2)
            )

        # No provider available - return fallback
        return ProviderSelection(
            provider=Provider.OLLAMA,
            model="llama3.2:latest",
            endpoint=self.OLLAMA_ENDPOINTS[0][1],
            reasoning="Fallback - no preferred providers available",
            cost_tier="free",
            expected_latency="slow",
            confidence=0.3
        )

    def _get_cost_tier(self, cost: float) -> str:
        """Categorize cost into tier"""
        if cost == 0:
            return "free"
        elif cost < 0.001:
            return "low"
        elif cost < 0.01:
            return "medium"
        else:
            return "high"

    def _get_latency_tier(self, latency_ms: float) -> str:
        """Categorize latency into tier"""
        if latency_ms < 500:
            return "fast"
        elif latency_ms < 2000:
            return "medium"
        else:
            return "slow"

    def get_status_report(self) -> Dict[str, Any]:
        """Generate status report"""
        return {
            "timestamp": datetime.now().isoformat(),
            "providers": {
                p.value: {
                    "available": h.available,
                    "latency_ms": h.latency_ms,
                    "consecutive_failures": h.consecutive_failures,
                    "success_rate_24h": self.get_success_rate(p),
                    "models": h.models_available[:5],
                    "error": h.error_message
                }
                for p, h in self.health_status.items()
            },
            "recommendations": self._generate_recommendations()
        }

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on current state"""
        recs = []

        for provider, health in self.health_status.items():
            config = self.PROVIDER_CONFIGS[provider]

            if not health.available and provider != Provider.OLLAMA:
                if not self._has_api_key(provider):
                    recs.append(f"Set {config.api_key_env} to enable {config.name}")
                else:
                    recs.append(f"{config.name} is down - check API status")

            success_rate = self.get_success_rate(provider)
            if success_rate < 0.5 and health.available:
                recs.append(f"{config.name} has low success rate ({success_rate:.0%})")

        return recs

    def run_daemon(self, check_interval: int = 60):
        """Run as background daemon checking provider health"""
        logger.info(f"Provider Auto-Selector daemon starting (interval: {check_interval}s)")

        while self.running:
            try:
                results = self.check_all_providers()

                available = sum(1 for h in results.values() if h.available)
                logger.info(f"Provider health: {available}/{len(results)} available")

                # Save state periodically
                self._save_state()

                # Sleep with interrupt checking
                for _ in range(check_interval):
                    if not self.running:
                        break
                    time.sleep(1)

            except Exception as e:
                logger.error(f"Error in daemon loop: {e}")
                time.sleep(10)

        self._save_state()
        logger.info("Provider Auto-Selector daemon stopped")


def main():
    parser = argparse.ArgumentParser(description="Multi-Provider Auto-Selector")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--interval", type=int, default=60, help="Check interval (seconds)")
    parser.add_argument("--check-once", action="store_true", help="Check once and exit")
    parser.add_argument("--select", type=str, help="Select provider for task type")
    parser.add_argument("--prefer-cost", action="store_true", help="Prefer cheaper providers")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    selector = ProviderAutoSelector()

    if args.select:
        selection = selector.select_provider(args.select, prefer_cost=args.prefer_cost)
        print(json.dumps({
            "provider": selection.provider.value,
            "model": selection.model,
            "endpoint": selection.endpoint,
            "reasoning": selection.reasoning,
            "cost_tier": selection.cost_tier,
            "expected_latency": selection.expected_latency,
            "confidence": selection.confidence
        }, indent=2))
        return 0

    if args.check_once:
        report = selector.get_status_report()
        print(json.dumps(report, indent=2))
        return 0

    if args.daemon:
        return selector.run_daemon(check_interval=args.interval)

    # Default: show status
    report = selector.get_status_report()
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
