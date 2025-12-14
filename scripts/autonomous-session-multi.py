#!/usr/bin/env python3
"""
Autonomous Session - Multi-Provider Implementation

Supports redundant AI providers with automatic fallback:
1. Claude Code SDK (headless) - Most capable, uses existing Claude Code installation
2. Groq - Fast inference, cheap, good for quick tasks
3. Ollama Cluster - Local inference, no cost, fully autonomous

Provider selection based on:
- Task complexity (complex tasks use Claude Code)
- Availability (automatic fallback on failure)
- Cost considerations (prefer free options for simple tasks)
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List
import httpx

# Configuration
CONFIG = {
    "log_file": "/var/log/autonomous-session.log",
    "cost_log": "/mnt/agentic-system/logs/autonomous-costs.jsonl",
    "identity_path": os.path.expanduser("~/.claude/enhanced_memories/agent_identity.json"),

    # Provider endpoints
    "ollama_endpoints": [
        "http://192.168.1.186:11434",  # completeu-server (primary GPU node)
        "http://192.168.1.79:11434",   # mac-studio
        "http://192.168.1.55:11434",   # macbook-air
    ],
    "groq_api_url": "https://api.groq.com/openai/v1/chat/completions",

    # Model preferences - must match installed models on cluster
    "ollama_models": {
        "complex": "llama3-groq-tool-use:70b-q8_0",  # 70B for complex reasoning
        "standard": "mistral-small3.2:24b-instruct-2506-fp16",  # 24B for standard tasks
        "simple": "mistral:7b-instruct-fp16",  # 7B for quick tasks
        "fast": "mistral:7b-instruct-fp16",  # Alias for simple
    },
    "groq_models": {
        "complex": "openai/gpt-oss-120b",  # Best quality (1183ms benchmark)
        "standard": "meta-llama/llama-4-maverick-17b-128e-instruct",  # Great balance (633ms)
        "simple": "llama-3.1-8b-instant",  # Fastest! (495ms benchmark)
        "fast": "llama-3.1-8b-instant",  # Alias for simple tier
        "agentic": "groq/compound-mini",  # Agentic with tools (979ms)
    },

    # Timeouts
    "ollama_timeout": 300,
    "groq_timeout": 120,
    "claude_timeout": 600,
}

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(CONFIG["log_file"], mode='a')
        if os.access(os.path.dirname(CONFIG["log_file"]) or '.', os.W_OK)
        else logging.StreamHandler()
    ]
)
logger = logging.getLogger("AutonomousSession")


class Provider(Enum):
    CLAUDE_CODE = "claude_code"
    GROQ = "groq"
    OLLAMA = "ollama"


class TaskComplexity(Enum):
    SIMPLE = "simple"       # Quick lookups, simple responses
    STANDARD = "standard"   # Typical tasks, reasoning
    COMPLEX = "complex"     # Multi-step reasoning, code generation


class TaskUrgency(Enum):
    """
    Urgency determines latency requirements:
    - IMMEDIATE: Needs response in seconds (use fast cloud)
    - NORMAL: Minutes are acceptable (can use local)
    - BACKGROUND: Can take as long as needed (prefer free/local)
    """
    IMMEDIATE = "immediate"  # Fast response needed
    NORMAL = "normal"        # Standard timing
    BACKGROUND = "background"  # Async, can wait


@dataclass
class SessionResult:
    success: bool
    provider: str
    model: str
    response: Optional[str] = None
    error: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    cost_usd: float = 0.0


class MultiProviderSession:
    """
    Autonomous session with multiple AI provider support and fallback.
    """

    def __init__(self):
        self.identity = self._load_identity()
        self.groq_api_key = os.environ.get("GROQ_API_KEY", "")

    def _load_identity(self) -> Dict:
        """Load agent identity for context"""
        try:
            path = Path(CONFIG["identity_path"])
            if path.exists():
                return json.loads(path.read_text())
        except Exception as e:
            logger.warning(f"Failed to load identity: {e}")
        return {}

    def _build_system_prompt(self, trigger: str) -> str:
        """Build system prompt with identity context"""
        prompt = f"""You are Pixel, an autonomous AGI agent.

## Current Context
- Trigger Type: {trigger}
- Execution Mode: Autonomous (headless)
- Node: macpro51 (Builder role)

## Your Identity
Agent ID: {self.identity.get('agent_id', 'pixel')}
"""
        if self.identity.get('skills'):
            skills = [f"{k}({int(v*100)}%)" for k, v in self.identity.get('skills', {}).items() if v > 0.5]
            prompt += f"\nSkills: {', '.join(skills)}\n"

        prompt += """
## Operational Guidelines
1. Execute tasks efficiently
2. Record action outcomes
3. Stay within capabilities
4. Maintain safety invariants

## Output Format
Return a JSON object with:
{
    "task_completed": boolean,
    "summary": "Brief summary of what was done",
    "actions_taken": ["list", "of", "actions"],
    "findings": "Key findings or results",
    "next_steps": ["optional", "follow-up", "tasks"]
}
"""
        return prompt

    def estimate_complexity(self, prompt: str) -> TaskComplexity:
        """Estimate task complexity from prompt"""
        prompt_lower = prompt.lower()

        # Complex indicators
        complex_indicators = [
            "implement", "create", "build", "design", "architect",
            "analyze deeply", "comprehensive", "multi-step",
            "code generation", "refactor", "debug"
        ]

        # Simple indicators
        simple_indicators = [
            "lookup", "find", "what is", "define", "list",
            "simple", "quick", "basic"
        ]

        # Check for complex indicators
        if any(ind in prompt_lower for ind in complex_indicators):
            return TaskComplexity.COMPLEX

        # Check for simple indicators
        if any(ind in prompt_lower for ind in simple_indicators):
            return TaskComplexity.SIMPLE

        # Default to standard
        return TaskComplexity.STANDARD

    def estimate_urgency(self, trigger: str, priority: float) -> TaskUrgency:
        """
        Estimate task urgency from trigger type and priority.

        Urgency determines provider selection for speed vs cost tradeoff:
        - IMMEDIATE: Use fast cloud providers (Groq)
        - NORMAL: Balance of speed and cost
        - BACKGROUND: Use local/free providers (Ollama)
        """
        # High priority always urgent
        if priority >= 0.8:
            return TaskUrgency.IMMEDIATE

        # Certain triggers are inherently urgent
        urgent_triggers = [
            "user_request", "error", "security", "interactive",
            "emergency", "realtime"
        ]
        if any(t in trigger.lower() for t in urgent_triggers):
            return TaskUrgency.IMMEDIATE

        # Background/scheduled tasks are not urgent
        background_triggers = [
            "scheduled", "cron", "consolidation", "cleanup",
            "research", "learning", "maintenance", "background"
        ]
        if any(t in trigger.lower() for t in background_triggers):
            return TaskUrgency.BACKGROUND

        # Default to normal
        return TaskUrgency.NORMAL

    def select_provider_order(
        self,
        complexity: TaskComplexity,
        urgency: TaskUrgency
    ) -> List[tuple]:
        """
        Select provider order based on 2D routing matrix:

        |              | Needs Smart      | Doesn't Need Smart |
        |--------------|------------------|-------------------|
        | Fast/Urgent  | Claude Code      | Groq (fast cloud) |
        | Slow OK      | Ollama 70B       | Ollama 3B/8B      |

        Returns list of (Provider, model_tier) tuples for fallback chain.
        """
        if urgency == TaskUrgency.IMMEDIATE:
            if complexity == TaskComplexity.COMPLEX:
                # Fast + Smart: Claude Code first, then Groq 70B, then Ollama
                return [
                    (Provider.CLAUDE_CODE, "complex"),
                    (Provider.GROQ, "complex"),
                    (Provider.OLLAMA, "complex"),
                ]
            else:
                # Fast + Simple: Groq first (fastest), then Ollama, then Claude
                return [
                    (Provider.GROQ, "fast" if complexity == TaskComplexity.SIMPLE else "standard"),
                    (Provider.OLLAMA, "fast" if complexity == TaskComplexity.SIMPLE else "standard"),
                    (Provider.CLAUDE_CODE, "standard"),
                ]

        elif urgency == TaskUrgency.BACKGROUND:
            # Background tasks: Always prefer free local inference
            if complexity == TaskComplexity.COMPLEX:
                return [
                    (Provider.OLLAMA, "complex"),  # 70B for complex
                    (Provider.GROQ, "complex"),    # Fallback to cloud
                    (Provider.CLAUDE_CODE, "complex"),
                ]
            else:
                return [
                    (Provider.OLLAMA, "fast" if complexity == TaskComplexity.SIMPLE else "standard"),
                    (Provider.GROQ, "fast" if complexity == TaskComplexity.SIMPLE else "standard"),
                ]

        else:  # NORMAL urgency
            # Balance speed and cost
            if complexity == TaskComplexity.COMPLEX:
                return [
                    (Provider.OLLAMA, "complex"),
                    (Provider.GROQ, "complex"),
                    (Provider.CLAUDE_CODE, "complex"),
                ]
            else:
                return [
                    (Provider.OLLAMA, "standard"),
                    (Provider.GROQ, "standard"),
                ]

    # ═══════════════════════════════════════════════════════════════════
    # PROVIDER: Claude Code SDK (Headless)
    # ═══════════════════════════════════════════════════════════════════

    async def execute_claude_code(self, prompt: str, trigger: str) -> SessionResult:
        """Execute via Claude Code SDK in headless mode"""
        logger.info("Attempting Claude Code SDK execution")
        start_time = datetime.now()

        try:
            # Use claude CLI with --print flag for headless execution
            process = await asyncio.create_subprocess_exec(
                "claude",
                "--print",  # Output response without interactive mode
                "--model", "sonnet",  # Use sonnet for balance
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Send the prompt
            full_prompt = f"{self._build_system_prompt(trigger)}\n\n{prompt}"
            stdout, stderr = await asyncio.wait_for(
                process.communicate(full_prompt.encode()),
                timeout=CONFIG["claude_timeout"]
            )

            latency = int((datetime.now() - start_time).total_seconds() * 1000)

            if process.returncode == 0:
                response = stdout.decode().strip()
                return SessionResult(
                    success=True,
                    provider="claude_code",
                    model="sonnet",
                    response=response,
                    latency_ms=latency,
                    # Cost is handled by Claude Code internally
                )
            else:
                return SessionResult(
                    success=False,
                    provider="claude_code",
                    model="sonnet",
                    error=stderr.decode(),
                    latency_ms=latency,
                )

        except asyncio.TimeoutError:
            return SessionResult(
                success=False,
                provider="claude_code",
                model="sonnet",
                error="Timeout after 600s",
            )
        except Exception as e:
            return SessionResult(
                success=False,
                provider="claude_code",
                model="sonnet",
                error=str(e),
            )

    # ═══════════════════════════════════════════════════════════════════
    # PROVIDER: Groq
    # ═══════════════════════════════════════════════════════════════════

    async def execute_groq(self, prompt: str, trigger: str, complexity: TaskComplexity) -> SessionResult:
        """Execute via Groq API"""
        if not self.groq_api_key:
            return SessionResult(
                success=False,
                provider="groq",
                model="",
                error="GROQ_API_KEY not set",
            )

        model = CONFIG["groq_models"].get(complexity.value, CONFIG["groq_models"]["standard"])
        logger.info(f"Attempting Groq execution with {model}")
        start_time = datetime.now()

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    CONFIG["groq_api_url"],
                    headers={
                        "Authorization": f"Bearer {self.groq_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": self._build_system_prompt(trigger)},
                            {"role": "user", "content": prompt},
                        ],
                        "max_tokens": 4096,
                        "temperature": 0.7,
                    },
                    timeout=CONFIG["groq_timeout"],
                )

                latency = int((datetime.now() - start_time).total_seconds() * 1000)

                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    usage = data.get("usage", {})

                    return SessionResult(
                        success=True,
                        provider="groq",
                        model=model,
                        response=content,
                        input_tokens=usage.get("prompt_tokens", 0),
                        output_tokens=usage.get("completion_tokens", 0),
                        latency_ms=latency,
                        cost_usd=0.0,  # Groq is effectively free for our volume
                    )
                else:
                    return SessionResult(
                        success=False,
                        provider="groq",
                        model=model,
                        error=f"HTTP {response.status_code}: {response.text}",
                        latency_ms=latency,
                    )

        except Exception as e:
            return SessionResult(
                success=False,
                provider="groq",
                model=model,
                error=str(e),
            )

    # ═══════════════════════════════════════════════════════════════════
    # PROVIDER: Ollama Cluster
    # ═══════════════════════════════════════════════════════════════════

    async def find_available_ollama(self) -> Optional[str]:
        """Find an available Ollama endpoint in the cluster"""
        async with httpx.AsyncClient() as client:
            for endpoint in CONFIG["ollama_endpoints"]:
                try:
                    response = await client.get(
                        f"{endpoint}/api/tags",
                        timeout=5.0,
                    )
                    if response.status_code == 200:
                        logger.info(f"Found available Ollama at {endpoint}")
                        return endpoint
                except Exception:
                    continue
        return None

    async def execute_ollama(self, prompt: str, trigger: str, complexity: TaskComplexity) -> SessionResult:
        """Execute via Ollama cluster"""
        endpoint = await self.find_available_ollama()
        if not endpoint:
            return SessionResult(
                success=False,
                provider="ollama",
                model="",
                error="No available Ollama endpoints",
            )

        model = CONFIG["ollama_models"].get(complexity.value, CONFIG["ollama_models"]["standard"])
        logger.info(f"Attempting Ollama execution at {endpoint} with {model}")
        start_time = datetime.now()

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{endpoint}/api/chat",
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": self._build_system_prompt(trigger)},
                            {"role": "user", "content": prompt},
                        ],
                        "stream": False,
                    },
                    timeout=CONFIG["ollama_timeout"],
                )

                latency = int((datetime.now() - start_time).total_seconds() * 1000)

                if response.status_code == 200:
                    data = response.json()
                    content = data["message"]["content"]

                    return SessionResult(
                        success=True,
                        provider="ollama",
                        model=model,
                        response=content,
                        latency_ms=latency,
                        cost_usd=0.0,  # Local inference is free
                    )
                else:
                    return SessionResult(
                        success=False,
                        provider="ollama",
                        model=model,
                        error=f"HTTP {response.status_code}: {response.text}",
                        latency_ms=latency,
                    )

        except Exception as e:
            return SessionResult(
                success=False,
                provider="ollama",
                model=model,
                error=str(e),
            )

    # ═══════════════════════════════════════════════════════════════════
    # MAIN EXECUTION with Fallback
    # ═══════════════════════════════════════════════════════════════════

    async def execute(
        self,
        prompt: str,
        trigger: str = "unknown",
        priority: float = 0.5,
        urgency: Optional[str] = None,  # Override urgency estimation
    ) -> SessionResult:
        """
        Execute autonomous session with intelligent 2D routing.

        Routing matrix (Urgency × Complexity):
        |              | Needs Smart      | Doesn't Need Smart |
        |--------------|------------------|-------------------|
        | Fast/Urgent  | Claude Code      | Groq (fast cloud) |
        | Slow OK      | Ollama 70B       | Ollama 3B/8B      |

        Args:
            prompt: Task to execute
            trigger: What triggered this task (affects urgency estimation)
            priority: Task priority 0.0-1.0 (higher = more urgent)
            urgency: Override urgency ('immediate', 'normal', 'background')
        """
        # Estimate task dimensions
        complexity = self.estimate_complexity(prompt)

        # Allow override of urgency, otherwise estimate from trigger/priority
        if urgency:
            task_urgency = TaskUrgency(urgency)
        else:
            task_urgency = self.estimate_urgency(trigger, priority)

        logger.info(f"Task routing: complexity={complexity.value}, urgency={task_urgency.value}")

        # Get provider order from 2D routing matrix
        provider_order = self.select_provider_order(complexity, task_urgency)
        logger.info(f"Provider order: {[(p.value, t) for p, t in provider_order]}")

        # Build executable provider list
        def make_executor(provider: Provider, model_tier: str):
            if provider == Provider.CLAUDE_CODE:
                return lambda: self.execute_claude_code(prompt, trigger)
            elif provider == Provider.GROQ:
                # Map tier to complexity enum for model selection
                tier_to_complexity = {
                    "fast": TaskComplexity.SIMPLE,
                    "standard": TaskComplexity.STANDARD,
                    "complex": TaskComplexity.COMPLEX,
                }
                c = tier_to_complexity.get(model_tier, TaskComplexity.STANDARD)
                return lambda c=c: self.execute_groq(prompt, trigger, c)
            elif provider == Provider.OLLAMA:
                tier_to_complexity = {
                    "fast": TaskComplexity.SIMPLE,
                    "standard": TaskComplexity.STANDARD,
                    "complex": TaskComplexity.COMPLEX,
                }
                c = tier_to_complexity.get(model_tier, TaskComplexity.STANDARD)
                return lambda c=c: self.execute_ollama(prompt, trigger, c)

        # Try each provider in order
        last_error = None
        for provider, model_tier in provider_order:
            execute_fn = make_executor(provider, model_tier)
            logger.info(f"Trying provider: {provider.value} (tier: {model_tier})")
            result = await execute_fn()

            if result.success:
                logger.info(f"Success with {provider.value} ({result.latency_ms}ms)")

                # Run built-in evaluation on responses
                eval_scores = None
                if result.response:
                    eval_scores = await self.evaluate_response(prompt, result.response)
                    if eval_scores:
                        logger.info(f"Eval scores: overall={eval_scores.get('overall')}/10")
                        if eval_scores.get("overall", 10) < 6:
                            logger.warning(f"Low quality response detected: {eval_scores.get('issues')}")

                self._log_cost(result, trigger, prompt, eval_scores)
                return result
            else:
                logger.warning(f"{provider.value} failed: {result.error}")
                last_error = result.error

        # All providers failed
        return SessionResult(
            success=False,
            provider="all",
            model="",
            error=f"All providers failed. Last error: {last_error}",
        )

    async def evaluate_response(self, prompt: str, response: str) -> Optional[Dict[str, Any]]:
        """
        Evaluate response quality using fast judge model.

        Uses Groq 8B for fast evaluation (~600ms) to score responses on:
        - Correctness: Is the answer technically accurate?
        - Completeness: Does it fully address the question?
        - Usefulness: Would this response actually help?

        Returns eval dict or None if eval fails.
        """
        if not self.groq_api_key:
            return None

        eval_prompt = f"""Score this response 1-10 on each dimension. Be strict but fair.

QUESTION: {prompt[:500]}

RESPONSE: {response[:2000]}

Return JSON only:
{{"correctness": <1-10>, "completeness": <1-10>, "usefulness": <1-10>, "overall": <1-10>, "issues": "<brief issues or 'none'>"}}"""

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    CONFIG["groq_api_url"],
                    headers={
                        "Authorization": f"Bearer {self.groq_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "llama-3.1-8b-instant",  # Fast judge model
                        "messages": [{"role": "user", "content": eval_prompt}],
                        "max_tokens": 200,
                        "temperature": 0.1,  # Low temp for consistent evals
                    },
                    timeout=30,
                )

                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"]
                    # Parse JSON from response
                    if "```" in content:
                        content = content.split("```")[1].split("```")[0]
                        if content.startswith("json"):
                            content = content[4:]
                    return json.loads(content.strip())
                else:
                    logger.debug(f"Eval request failed: {resp.status_code}")
                    return None
        except Exception as e:
            logger.debug(f"Eval failed: {e}")
            return None

    def _log_cost(self, result: SessionResult, trigger: str, prompt: str, eval_scores: Optional[Dict] = None):
        """Log session cost, metrics, and evaluation scores"""
        try:
            Path(CONFIG["cost_log"]).parent.mkdir(parents=True, exist_ok=True)

            entry = {
                "timestamp": datetime.now().isoformat(),
                "trigger": trigger,
                "provider": result.provider,
                "model": result.model,
                "success": result.success,
                "latency_ms": result.latency_ms,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "cost_usd": result.cost_usd,
                "prompt_length": len(prompt),
            }

            # Add evaluation scores if available
            if eval_scores:
                entry["eval_correctness"] = eval_scores.get("correctness")
                entry["eval_completeness"] = eval_scores.get("completeness")
                entry["eval_usefulness"] = eval_scores.get("usefulness")
                entry["eval_overall"] = eval_scores.get("overall")
                entry["eval_issues"] = eval_scores.get("issues")

            with open(CONFIG["cost_log"], "a") as f:
                f.write(json.dumps(entry) + "\n")

        except Exception as e:
            logger.warning(f"Failed to log cost: {e}")


def parse_args():
    """Parse command line arguments"""
    import argparse
    parser = argparse.ArgumentParser(description="Autonomous Session - Multi-Provider")
    parser.add_argument("--prompt", required=True, help="Task prompt")
    parser.add_argument("--trigger", default="unknown", help="Trigger type")
    parser.add_argument("--priority", type=float, default=0.5, help="Task priority (0.0-1.0)")
    parser.add_argument("--urgency", choices=["immediate", "normal", "background"],
                        help="Override urgency estimation")
    # Legacy flags for backwards compatibility
    parser.add_argument("--prefer-local", action="store_true", default=False,
                        help="[DEPRECATED] Use --urgency=background instead")
    parser.add_argument("--prefer-quality", action="store_true",
                        help="[DEPRECATED] Use --urgency=immediate with high priority")
    return parser.parse_args()


async def main():
    args = parse_args()

    # Handle legacy flags
    urgency = args.urgency
    if not urgency:
        if args.prefer_quality:
            urgency = "immediate"
        elif args.prefer_local:
            urgency = "background"

    session = MultiProviderSession()
    result = await session.execute(
        prompt=args.prompt,
        trigger=args.trigger,
        priority=args.priority,
        urgency=urgency,
    )

    # Output result as JSON for the daemon
    output = {
        "success": result.success,
        "provider": result.provider,
        "model": result.model,
        "latency_ms": result.latency_ms,
    }

    if result.success:
        output["result"] = result.response
    else:
        output["error"] = result.error

    print(json.dumps(output))

    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    asyncio.run(main())
