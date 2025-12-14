#!/usr/bin/env python3
"""
MAKER Headless Multi-Provider Agent
====================================

Diverse AI provider voting for 99.9999% reliability:
1. Claude Code Haiku (claude --print --model haiku)
2. Gemini CLI (gemini "prompt")
3. OpenAI Codex (codex exec -- "prompt")
4. Ollama Cloud (ollama run gpt-oss:20b-cloud)

Distribution: Claude 40%, Codex 30%, Gemini 20%, Ollama 10%
"""

import asyncio
import json
import subprocess
import re
from typing import Dict, Any
from dataclasses import dataclass
from enum import Enum
from maker_framework import AtomicState, AgentResponse


class AIProvider(Enum):
    """Available AI providers for MAKER voting"""
    CLAUDE_HAIKU = "claude_haiku"
    GEMINI = "gemini"
    CODEX = "codex"
    OLLAMA = "ollama"


@dataclass
class ProviderConfig:
    """Configuration for headless AI provider"""
    command_path: str
    args_template: list
    timeout: int = 45


class HeadlessMultiProvider:
    """Execute MAKER agents across multiple providers in headless mode"""

    def __init__(self):
        self.providers = {
            AIProvider.CLAUDE_HAIKU: ProviderConfig(
                command_path="/Users/marc/.nvm/versions/node/v24.7.0/bin/claude",
                args_template=["--print", "--model", "haiku", "--"],
                timeout=45
            ),
            AIProvider.GEMINI: ProviderConfig(
                command_path="/Users/marc/.nvm/versions/node/v24.7.0/bin/gemini",
                args_template=[],  # Positional prompt
                timeout=45
            ),
            AIProvider.CODEX: ProviderConfig(
                command_path="/Users/marc/.bun/bin/codex",
                args_template=["exec", "--"],
                timeout=45
            ),
            AIProvider.OLLAMA: ProviderConfig(
                command_path="ollama",
                args_template=["run", "gpt-oss:20b-cloud"],
                timeout=60
            )
        }

    def _extract_json_from_output(self, output: str) -> dict:
        """Extract JSON from potentially messy output"""
        # Try direct parse first
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            pass

        # Try to find JSON block in output
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, output, re.DOTALL)

        for match in matches:
            try:
                data = json.loads(match)
                # Validate it has expected keys
                if 'action' in data or 'new_state' in data:
                    return data
            except json.JSONDecodeError:
                continue

        # Fallback: wrap as raw output
        return {"raw_output": output}

    async def execute_with_provider(
        self,
        provider: AIProvider,
        state: AtomicState
    ) -> AgentResponse:
        """Execute stateless MAKER query with specific provider"""

        # Build prompt
        prompt = f"""You are a stateless MAKER agent. Return ONLY valid JSON.

State: {json.dumps(state.state_data)}
Rules: {json.dumps(state.rules)}
Goal: {state.goal}
Step: {state.step_number}

Return JSON with this exact structure:
{{"action": <your_action>, "new_state": <updated_state>, "reasoning": "<brief_explanation>"}}

Output ONLY the JSON object, no other text."""

        config = self.providers[provider]

        # Build command
        cmd = [config.command_path] + config.args_template + [prompt]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=config.timeout
            )

            output = result.stdout.strip()
            if not output and result.stderr:
                output = result.stderr.strip()

            # Extract JSON
            data = self._extract_json_from_output(output)

            # Build response
            has_structure = 'action' in data and 'new_state' in data
            return AgentResponse(
                action=data.get('action', data),
                new_state_data=data.get('new_state', state.state_data),
                reasoning=data.get('reasoning', f"Provider: {provider.value}"),
                format_valid=has_structure,
                token_count=len(output.split()),
                execution_time_ms=0.0
            )

        except subprocess.TimeoutExpired:
            raise Exception(f"{provider.value} timeout after {config.timeout}s")
        except Exception as e:
            raise Exception(f"{provider.value} error: {e}")

    def get_provider_distribution(self, num_queries: int) -> list[AIProvider]:
        """
        Get balanced distribution for voting:
        - 40% Claude Haiku
        - 30% Codex
        - 20% Gemini
        - 10% Ollama
        """
        claude_count = int(num_queries * 0.40)
        codex_count = int(num_queries * 0.30)
        gemini_count = int(num_queries * 0.20)
        ollama_count = num_queries - (claude_count + codex_count + gemini_count)

        distribution = []
        distribution.extend([AIProvider.CLAUDE_HAIKU] * claude_count)
        distribution.extend([AIProvider.CODEX] * codex_count)
        distribution.extend([AIProvider.GEMINI] * gemini_count)
        distribution.extend([AIProvider.OLLAMA] * ollama_count)

        return distribution


async def test_all_providers():
    """Test all providers with a simple counting task"""
    print("🧪 Testing MAKER Headless Multi-Provider System\n")

    # Simple test state
    test_state = AtomicState(
        state_id="test-0",
        step_number=0,
        state_data={"count": 0, "target": 5},
        rules=["Increment count by 1 each step"],
        goal="Reach target value"
    )

    executor = HeadlessMultiProvider()

    # Test each provider
    for provider in AIProvider:
        print(f"Testing {provider.value}...")
        try:
            response = await executor.execute_with_provider(provider, test_state)
            status = "✅" if response.format_valid else "⚠️"
            print(f"  {status} Success!")
            print(f"     Action: {response.action}")
            print(f"     Valid JSON: {response.format_valid}")
            print(f"     Reasoning: {response.reasoning}")
        except Exception as e:
            print(f"  ❌ Failed: {e}")
        print()

    # Test distribution
    print("\n📊 Provider Distribution for 10 queries:")
    distribution = executor.get_provider_distribution(10)
    from collections import Counter
    counts = Counter(distribution)
    for provider, count in counts.items():
        print(f"  {provider.value}: {count} queries ({count*10}%)")


if __name__ == "__main__":
    asyncio.run(test_all_providers())
