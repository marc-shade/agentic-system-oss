#!/usr/bin/env python3
"""
MAKER Multi-Provider Agent
==========================

Configures MAKER voting to use diverse AI providers:
1. Claude Code Haiku subagents (via Task tool)
2. Gemini CLI
3. OpenAI Codex
4. 1x Ollama Cloud model (gpt-oss:20b-cloud)

This provides true diversity for voting reliability.
"""
import os
import platform
from pathlib import Path

import asyncio
import json
import subprocess
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from maker_framework import AtomicState, AgentResponse


class AIProvider(Enum):
    """Available AI providers for MAKER voting"""
    CLAUDE_HAIKU = "claude_haiku"      # Claude Code Haiku subagent
    GEMINI_CLI = "gemini_cli"           # Gemini CLI
    CODEX_CLI = "codex_cli"             # OpenAI Codex
    OLLAMA_CLOUD = "ollama_cloud"       # gpt-oss:20b-cloud


@dataclass
class ProviderConfig:
    """Configuration for an AI provider"""
    name: str
    command: list
    timeout: int = 30
    enabled: bool = True


class MultiProviderExecutor:
    """
    Executes MAKER agents across multiple AI providers.

    Provider distribution for voting:
    - 40% Claude Code Haiku (fast, efficient)
    - 30% OpenAI Codex (proven working)
    - 20% Gemini CLI (diversity)
    - 10% Ollama Cloud (local fallback)
    """

    def __init__(self):
        self.providers = {
            AIProvider.CLAUDE_HAIKU: ProviderConfig(
                name="Claude Code Haiku",
                command=[],  # Uses Task tool, not subprocess
                enabled=True
            ),
            AIProvider.CODEX_CLI: ProviderConfig(
                name="OpenAI Codex",
                command=["/Users/marc/.bun/bin/codex", "exec", "--"],
                enabled=True
            ),
            AIProvider.GEMINI_CLI: ProviderConfig(
                name="Gemini CLI",
                command=["gemini"],  # Need to verify this works
                enabled=True
            ),
            AIProvider.OLLAMA_CLOUD: ProviderConfig(
                name="Ollama GPT-OSS-20B-Cloud",
                command=["ollama", "run", "gpt-oss:20b-cloud"],
                enabled=True
            )
        }

    async def execute_with_provider(
        self,
        provider: AIProvider,
        state: AtomicState
    ) -> AgentResponse:
        """Execute a stateless agent query with specific provider"""

        if provider == AIProvider.CLAUDE_HAIKU:
            return await self._execute_claude_haiku(state)
        elif provider == AIProvider.CODEX_CLI:
            return await self._execute_codex_cli(state)
        elif provider == AIProvider.GEMINI_CLI:
            return await self._execute_gemini_cli(state)
        elif provider == AIProvider.OLLAMA_CLOUD:
            return await self._execute_ollama_cloud(state)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    async def _execute_claude_haiku(self, state: AtomicState) -> AgentResponse:
        """
        Execute via Claude Code Haiku subagent using Task tool.

        This is NOT a subprocess - it's a proper Claude Code agent that will
        have access to all tools and can reason properly.
        """
        import sys
        sys.path.insert(0, str(_STORAGE_BASE))

        # Format prompt for Claude Haiku
        prompt = f"""You are a stateless MAKER agent. You receive ONLY the current state, rules, and goal.
You have NO memory of previous steps.

Current State: {json.dumps(state.state_data, indent=2)}
Rules: {json.dumps(state.rules, indent=2)}
Goal: {state.goal}
Step Number: {state.step_number}

Analyze this state and return your decision as JSON:
{{
  "action": <your action>,
  "new_state": <updated state data>,
  "reasoning": <brief explanation>
}}

Be concise. Output ONLY valid JSON."""

        # Create a temporary file to capture the subagent response
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            temp_file = f.name

        try:
            # Use subprocess to spawn Claude Code with haiku model
            # This avoids circular dependencies and tool access issues
            result = subprocess.run([
                "claude",
                "--model", "haiku",
                "--print",
                "--",
                prompt
            ], capture_output=True, text=True, timeout=30)

            output = result.stdout.strip()

            # Parse JSON response
            try:
                data = json.loads(output)
                return AgentResponse(
                    action=data.get('action'),
                    new_state_data=data.get('new_state', state.state_data),
                    reasoning=data.get('reasoning'),
                    format_valid=True,
                    token_count=len(output.split()),
                    execution_time_ms=0.0  # TODO: measure actual time
                )
            except json.JSONDecodeError:
                # Fallback if not JSON
                return AgentResponse(
                    action={"raw_output": output},
                    new_state_data=state.state_data,
                    reasoning="Non-JSON response",
                    format_valid=False,
                    token_count=len(output.split()),
                    execution_time_ms=0.0
                )
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    async def _execute_codex_cli(self, state: AtomicState) -> AgentResponse:
        """Execute via OpenAI Codex CLI"""
        prompt = f"""You are a stateless MAKER agent. Analyze this state and return JSON with your decision.

State: {json.dumps(state.state_data)}
Rules: {json.dumps(state.rules)}
Goal: {state.goal}

Return JSON: {{"action": ..., "new_state": ..., "reasoning": "..."}}"""

        config = self.providers[AIProvider.CODEX_CLI]
        cmd = config.command + [prompt]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=config.timeout
            )
            output = result.stdout.strip()

            # Parse response
            try:
                data = json.loads(output)
                return AgentResponse(
                    action=data.get('action'),
                    new_state_data=data.get('new_state', state.state_data),
                    reasoning=data.get('reasoning'),
                    format_valid=True,
                    token_count=len(output.split()),
                    execution_time_ms=0.0
                )
            except json.JSONDecodeError:
                return AgentResponse(
                    action={"raw": output},
                    new_state_data=state.state_data,
                    reasoning="Non-JSON",
                    format_valid=False,
                    token_count=len(output.split()),
                    execution_time_ms=0.0
                )
        except subprocess.TimeoutExpired:
            raise Exception(f"Codex CLI timeout after {config.timeout}s")

    async def _execute_gemini_cli(self, state: AtomicState) -> AgentResponse:
        """Execute via Gemini CLI"""
        prompt = f"""Stateless MAKER agent query. Return JSON only.

State: {json.dumps(state.state_data)}
Rules: {json.dumps(state.rules)}
Goal: {state.goal}

JSON output: {{"action": ..., "new_state": ..., "reasoning": "..."}}"""

        config = self.providers[AIProvider.GEMINI_CLI]
        cmd = config.command + [prompt]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=config.timeout
            )
            output = result.stdout.strip()

            try:
                data = json.loads(output)
                return AgentResponse(
                    action=data.get('action'),
                    new_state_data=data.get('new_state', state.state_data),
                    reasoning=data.get('reasoning'),
                    format_valid=True,
                    token_count=len(output.split()),
                    execution_time_ms=0.0
                )
            except json.JSONDecodeError:
                return AgentResponse(
                    action={"raw": output},
                    new_state_data=state.state_data,
                    reasoning="Non-JSON",
                    format_valid=False,
                    token_count=len(output.split()),
                    execution_time_ms=0.0
                )
        except subprocess.TimeoutExpired:
            raise Exception(f"Gemini CLI timeout after {config.timeout}s")

    async def _execute_ollama_cloud(self, state: AtomicState) -> AgentResponse:
        """Execute via Ollama Cloud (gpt-oss:20b-cloud)"""
        prompt = f"""MAKER stateless agent. Return JSON.

State: {json.dumps(state.state_data)}
Rules: {json.dumps(state.rules)}
Goal: {state.goal}

JSON: {{"action": ..., "new_state": ..., "reasoning": "..."}}"""

        config = self.providers[AIProvider.OLLAMA_CLOUD]

        # Use Ollama API for better control
        try:
            result = subprocess.run(
                ["ollama", "run", "gpt-oss:20b-cloud", prompt],
                capture_output=True,
                text=True,
                timeout=config.timeout
            )
            output = result.stdout.strip()

            try:
                data = json.loads(output)
                return AgentResponse(
                    action=data.get('action'),
                    new_state_data=data.get('new_state', state.state_data),
                    reasoning=data.get('reasoning'),
                    format_valid=True,
                    token_count=len(output.split()),
                    execution_time_ms=0.0
                )
            except json.JSONDecodeError:
                return AgentResponse(
                    action={"raw": output},
                    new_state_data=state.state_data,
                    reasoning="Non-JSON",
                    format_valid=False,
                    token_count=len(output.split()),
                    execution_time_ms=0.0
                )
        except subprocess.TimeoutExpired:
            raise Exception(f"Ollama timeout after {config.timeout}s")

    def get_provider_distribution(self, num_queries: int) -> list[AIProvider]:
        """
        Get balanced distribution of providers for voting.

        Distribution:
        - 40% Claude Code Haiku
        - 30% OpenAI Codex
        - 20% Gemini CLI
        - 10% Ollama Cloud
        """
        distribution = []

        # Calculate counts
        claude_count = int(num_queries * 0.40)
        codex_count = int(num_queries * 0.30)
        gemini_count = int(num_queries * 0.20)
        ollama_count = num_queries - (claude_count + codex_count + gemini_count)

        # Build list
        distribution.extend([AIProvider.CLAUDE_HAIKU] * claude_count)
        distribution.extend([AIProvider.CODEX_CLI] * codex_count)
        distribution.extend([AIProvider.GEMINI_CLI] * gemini_count)
        distribution.extend([AIProvider.OLLAMA_CLOUD] * ollama_count)

        return distribution


async def multi_provider_agent_function(state: AtomicState) -> AgentResponse:
    """
    MAKER agent function that uses multiple AI providers.

    This can be passed to MAKEROrchestrator's execute_sequence() method.
    For voting, it will be called multiple times with different providers.
    """
    executor = MultiProviderExecutor()

    # For now, use Codex as default (proven working)
    # The voting system will call this multiple times
    return await executor.execute_with_provider(AIProvider.CODEX_CLI, state)


async def test_multi_provider():
    """Test all providers with a simple task"""
    print("🧪 Testing Multi-Provider MAKER Agents\n")

    # Create simple test state
    test_state = AtomicState(
        state_id="test-0",
        step_number=0,
        state_data={"count": 0, "goal_value": 5},
        rules=["Increment count by 1 each step"],
        goal="Reach goal_value"
    )

    executor = MultiProviderExecutor()

    # Test each provider
    providers = [
        AIProvider.CODEX_CLI,
        AIProvider.CLAUDE_HAIKU,
        AIProvider.GEMINI_CLI,
        AIProvider.OLLAMA_CLOUD
    ]

    for provider in providers:
        print(f"Testing {provider.value}...")
        try:
            response = await executor.execute_with_provider(provider, test_state)
            print(f"  ✅ Success: {response.action}")
            print(f"     Reasoning: {response.reasoning}")
            print(f"     Valid: {response.format_valid}")
        except Exception as e:
            print(f"  ❌ Failed: {e}")
        print()

    # Test distribution
    print("\n📊 Provider Distribution for 10 queries:")
    distribution = executor.get_provider_distribution(10)
    from collections import Counter

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

    counts = Counter(distribution)
    for provider, count in counts.items():
        print(f"  {provider.value}: {count} queries ({count*10}%)")


if __name__ == "__main__":
    asyncio.run(test_multi_provider())
