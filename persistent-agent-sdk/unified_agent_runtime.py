#!/usr/bin/env python3
"""
Unified Persistent Agent SDK Runtime
Leverages Claude Code, OpenAI Codex, and Gemini CLI for optimal task execution
"""

import os
import json
import subprocess
import asyncio
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import anthropic
import openai
try:
    import google.generativeai as genai
except ImportError:
    print("⚠️ Google GenerativeAI SDK not installed. Gemini provider will be unavailable.")
    genai = None

class AgentProvider(Enum):
    """Supported AI providers for agent execution"""
    CLAUDE_CODE = "claude_code"
    OPENAI_CODEX = "openai_codex"
    GEMINI_CLI = "gemini_cli"

class TaskType(Enum):
    """Task types for intelligent provider routing"""
    CODE_ANALYSIS = "code_analysis"
    CODE_GENERATION = "code_generation"
    DEBUGGING = "debugging"
    REFACTORING = "refactoring"
    DOCUMENTATION = "documentation"
    RESEARCH = "research"
    TESTING = "testing"
    ARCHITECTURE = "architecture"

@dataclass
class AgentTask:
    """Persistent agent task with provider selection"""
    task_id: str
    task_type: TaskType
    description: str
    context: Dict[str, Any]
    preferred_provider: Optional[AgentProvider] = None
    created_at: str = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "description": self.description,
            "context": self.context,
            "preferred_provider": self.preferred_provider.value if self.preferred_provider else None,
            "created_at": self.created_at
        }

class UnifiedAgentRuntime:
    """
    Unified runtime for persistent agents across multiple AI providers
    Automatically selects best provider based on task type and availability
    """

    def __init__(self, verbose=True):
        self.verbose = verbose
        self.claude_client = None
        self.openai_client = None
        self.gemini_client = None

        # Provider capabilities matrix
        self.provider_strengths = {
            AgentProvider.CLAUDE_CODE: {
                TaskType.CODE_ANALYSIS: 0.95,
                TaskType.REFACTORING: 0.90,
                TaskType.ARCHITECTURE: 0.95,
                TaskType.DEBUGGING: 0.85,
                TaskType.DOCUMENTATION: 0.85,
                TaskType.RESEARCH: 0.80,
                TaskType.CODE_GENERATION: 0.85,
                TaskType.TESTING: 0.80
            },
            AgentProvider.OPENAI_CODEX: {
                TaskType.CODE_GENERATION: 0.95,
                TaskType.CODE_ANALYSIS: 0.85,
                TaskType.DEBUGGING: 0.90,
                TaskType.TESTING: 0.85,
                TaskType.REFACTORING: 0.80,
                TaskType.DOCUMENTATION: 0.75,
                TaskType.RESEARCH: 0.70,
                TaskType.ARCHITECTURE: 0.75
            },
            AgentProvider.GEMINI_CLI: {
                TaskType.RESEARCH: 0.95,
                TaskType.DOCUMENTATION: 0.90,
                TaskType.CODE_ANALYSIS: 0.80,
                TaskType.ARCHITECTURE: 0.85,
                TaskType.DEBUGGING: 0.75,
                TaskType.CODE_GENERATION: 0.75,
                TaskType.REFACTORING: 0.70,
                TaskType.TESTING: 0.70
            }
        }

        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize all available AI provider clients"""

        # Initialize Claude Code (Anthropic SDK)
        try:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                self.claude_client = anthropic.Anthropic(api_key=api_key)
                if self.verbose:
                    print("✅ Claude Code SDK initialized")
            else:
                if self.verbose:
                    print("⚠️ ANTHROPIC_API_KEY not found")
        except Exception as e:
            if self.verbose:
                print(f"❌ Claude Code initialization failed: {e}")

        # Initialize OpenAI Codex
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.openai_client = openai.OpenAI(api_key=api_key)
                if self.verbose:
                    print("✅ OpenAI Codex SDK initialized")
            else:
                if self.verbose:
                    print("⚠️ OPENAI_API_KEY not found")
        except Exception as e:
            if self.verbose:
                print(f"❌ OpenAI Codex initialization failed: {e}")

        # Initialize Gemini CLI (Google GenAI SDK)
        try:
            api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                self.gemini_client = genai.GenerativeModel('gemini-2.0-flash-exp')
                if self.verbose:
                    print("✅ Gemini CLI SDK initialized")
            else:
                if self.verbose:
                    print("⚠️ GEMINI_API_KEY not found")
        except Exception as e:
            if self.verbose:
                print(f"❌ Gemini CLI initialization failed: {e}")

    def select_optimal_provider(self, task: AgentTask) -> AgentProvider:
        """
        Intelligently select the best provider for a given task
        Based on task type, provider availability, and performance scores
        """

        # Honor explicit provider preference if specified
        if task.preferred_provider:
            provider_available = {
                AgentProvider.CLAUDE_CODE: self.claude_client is not None,
                AgentProvider.OPENAI_CODEX: self.openai_client is not None,
                AgentProvider.GEMINI_CLI: self.gemini_client is not None
            }
            if provider_available.get(task.preferred_provider, False):
                return task.preferred_provider

        # Calculate scores for each available provider
        scores = {}
        for provider, strengths in self.provider_strengths.items():
            # Check if provider is available
            if provider == AgentProvider.CLAUDE_CODE and not self.claude_client:
                continue
            if provider == AgentProvider.OPENAI_CODEX and not self.openai_client:
                continue
            if provider == AgentProvider.GEMINI_CLI and not self.gemini_client:
                continue

            # Get strength score for this task type
            score = strengths.get(task.task_type, 0.5)
            scores[provider] = score

        # Select provider with highest score
        if not scores:
            raise RuntimeError("No AI providers available")

        optimal_provider = max(scores.items(), key=lambda x: x[1])[0]
        if self.verbose:
            print(f"📊 Provider selection for {task.task_type.value}:")
            for provider, score in scores.items():
                marker = "✅" if provider == optimal_provider else "  "
                print(f"  {marker} {provider.value}: {score:.2f}")

        return optimal_provider

    async def execute_with_claude_code(self, task: AgentTask) -> Dict[str, Any]:
        """Execute task using Claude Code (Anthropic SDK)"""
        if self.verbose:
            print(f"🤖 Executing with Claude Code: {task.description}")

        try:
            message = self.claude_client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=8000,
                system="You are a persistent agent executing long-running tasks. Provide comprehensive, production-ready solutions.",
                messages=[
                    {
                        "role": "user",
                        "content": f"""
Task Type: {task.task_type.value}
Description: {task.description}
Context: {json.dumps(task.context, indent=2)}

Please execute this task thoroughly and return a structured result.
"""
                    }
                ]
            )

            return {
                "success": True,
                "provider": "claude_code",
                "result": message.content[0].text,
                "model": "claude-sonnet-4.5",
                "usage": {
                    "input_tokens": message.usage.input_tokens,
                    "output_tokens": message.usage.output_tokens
                }
            }
        except Exception as e:
            return {
                "success": False,
                "provider": "claude_code",
                "error": str(e)
            }

    async def execute_with_openai_codex(self, task: AgentTask) -> Dict[str, Any]:
        """Execute task using OpenAI Codex"""
        if self.verbose:
            print(f"🤖 Executing with OpenAI Codex: {task.description}")

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",  # Latest OpenAI model
                messages=[
                    {
                        "role": "system",
                        "content": "You are a persistent agent executing long-running tasks. Provide comprehensive, production-ready solutions."
                    },
                    {
                        "role": "user",
                        "content": f"""
Task Type: {task.task_type.value}
Description: {task.description}
Context: {json.dumps(task.context, indent=2)}

Please execute this task thoroughly and return a structured result.
"""
                    }
                ],
                max_tokens=4000
            )

            return {
                "success": True,
                "provider": "openai_codex",
                "result": response.choices[0].message.content,
                "model": response.model,
                "usage": {
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens
                }
            }
        except Exception as e:
            return {
                "success": False,
                "provider": "openai_codex",
                "error": str(e)
            }

    async def execute_with_gemini_cli(self, task: AgentTask) -> Dict[str, Any]:
        """Execute task using Gemini CLI (Google GenAI SDK)"""
        if self.verbose:
            print(f"🤖 Executing with Gemini CLI: {task.description}")

        try:
            prompt = f"""
Task Type: {task.task_type.value}
Description: {task.description}
Context: {json.dumps(task.context, indent=2)}

Please execute this task thoroughly and return a structured result.
"""

            response = self.gemini_client.generate_content(prompt)

            return {
                "success": True,
                "provider": "gemini_cli",
                "result": response.text,
                "model": "gemini-2.0-flash-exp",
                "usage": {
                    "input_tokens": response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else 0,
                    "output_tokens": response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else 0
                }
            }
        except Exception as e:
            return {
                "success": False,
                "provider": "gemini_cli",
                "error": str(e)
            }

    async def execute_task(self, task: AgentTask) -> Dict[str, Any]:
        """
        Execute a persistent agent task using the optimal provider
        Returns execution result with provider metadata
        """

        # Select optimal provider
        provider = self.select_optimal_provider(task)

        # Route to appropriate execution method
        if provider == AgentProvider.CLAUDE_CODE:
            result = await self.execute_with_claude_code(task)
        elif provider == AgentProvider.OPENAI_CODEX:
            result = await self.execute_with_openai_codex(task)
        elif provider == AgentProvider.GEMINI_CLI:
            result = await self.execute_with_gemini_cli(task)
        else:
            return {
                "success": False,
                "error": f"Unknown provider: {provider}"
            }

        # Add task metadata to result
        result["task_id"] = task.task_id
        result["task_type"] = task.task_type.value
        result["selected_provider"] = provider.value
        result["executed_at"] = datetime.now().isoformat()

        return result

    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all AI provider connections"""
        return {
            "claude_code": {
                "available": self.claude_client is not None,
                "provider": "Anthropic",
                "model": "claude-sonnet-4.5"
            },
            "openai_codex": {
                "available": self.openai_client is not None,
                "provider": "OpenAI",
                "model": "gpt-4o"
            },
            "gemini_cli": {
                "available": self.gemini_client is not None,
                "provider": "Google",
                "model": "gemini-2.0-flash-exp"
            }
        }

# Example usage and testing
async def main():
    """Test the unified agent runtime"""

    runtime = UnifiedAgentRuntime()

    print("\n" + "="*60)
    print("UNIFIED PERSISTENT AGENT SDK RUNTIME")
    print("="*60)

    # Show provider status
    print("\nProvider Status:")
    status = runtime.get_provider_status()
    for provider, info in status.items():
        status_icon = "✅" if info["available"] else "❌"
        print(f"{status_icon} {provider}: {info['provider']} ({info['model']})")

    # Test tasks for different providers
    test_tasks = [
        AgentTask(
            task_id="task_001",
            task_type=TaskType.CODE_ANALYSIS,
            description="Analyze the KutiraAI dashboard codebase for potential improvements",
            context={"files": ["/Volumes/FILES/code/kutiraai/src/pages/dashboard/index.jsx"]}
        ),
        AgentTask(
            task_id="task_002",
            task_type=TaskType.CODE_GENERATION,
            description="Generate a React component for displaying agent metrics",
            context={"component_name": "AgentMetricsCard", "framework": "React + Material-UI"}
        ),
        AgentTask(
            task_id="task_003",
            task_type=TaskType.RESEARCH,
            description="Research best practices for persistent agent architectures",
            context={"focus_areas": ["multi-provider", "SDK integration", "failure handling"]}
        )
    ]

    # Execute each task with optimal provider
    for task in test_tasks:
        print(f"\n{'='*60}")
        print(f"Task: {task.description}")
        print(f"Type: {task.task_type.value}")

        result = await runtime.execute_task(task)

        if result["success"]:
            print(f"\n✅ Success!")
            print(f"Provider: {result['provider']}")
            print(f"Model: {result['model']}")
            print(f"Tokens: {result['usage']['input_tokens']} input / {result['usage']['output_tokens']} output")
            print(f"\nResult Preview:")
            print(result['result'][:200] + "..." if len(result['result']) > 200 else result['result'])
        else:
            print(f"\n❌ Failed: {result['error']}")

if __name__ == "__main__":
    asyncio.run(main())
