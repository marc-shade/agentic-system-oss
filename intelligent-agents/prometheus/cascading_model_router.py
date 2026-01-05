"""
Cascading Model Router - Fast model routing with intelligent escalation.

Addresses timeout issues identified in GAIA benchmarks:
- PROBLEM: Sequential provider calls (Claude → Codex → Gemini) = 360s worst-case
- SOLUTION: Parallel execution + cascading patterns + Groq fast path

Patterns implemented:
1. Fast Classification (Groq) - Route simple tasks to fast models
2. Parallel Consensus - Query all providers simultaneously
3. Cascading Escalation - Start fast, escalate if needed
4. Timeout Handling - Graceful degradation with partial results

Performance targets:
- Simple tasks: <5s (Groq fast path)
- Medium tasks: <30s (single provider)
- Complex tasks: <60s (parallel consensus)
- Worst-case: <120s (escalated with retries)
"""

import asyncio
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, List, Any, Callable
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

logger = logging.getLogger(__name__)


class TaskComplexity(Enum):
    """Task complexity levels for routing decisions."""
    SIMPLE = "simple"        # Direct answers, factual queries
    MEDIUM = "medium"        # Single-step reasoning, calculations
    COMPLEX = "complex"      # Multi-step reasoning, research required
    EXPERT = "expert"        # Requires consensus, high-stakes


class ModelTier(Enum):
    """Model tiers by speed/capability trade-off."""
    FAST = "fast"            # Groq llama-3.1-8b (~800 tok/s)
    BALANCED = "balanced"    # Groq llama-3.3-70b (~200 tok/s)
    POWERFUL = "powerful"    # Claude/GPT-4 (~50 tok/s)
    CONSENSUS = "consensus"  # Multi-provider agreement


@dataclass
class RoutingResult:
    """Result from model routing."""
    answer: str
    model_used: str
    tier: ModelTier
    execution_time: float
    confidence: float = 0.8
    escalated: bool = False
    providers_queried: List[str] = field(default_factory=list)


@dataclass
class ClassificationResult:
    """Result from fast complexity classification."""
    complexity: TaskComplexity
    recommended_tier: ModelTier
    reasoning: str
    confidence: float


class GroqFastPath:
    """
    Fast inference path using Groq's LPU for initial classification
    and simple task completion.

    Groq speeds:
    - llama-3.1-8b-instant: ~800 tokens/sec
    - llama-3.3-70b-versatile: ~200 tokens/sec
    """

    CLASSIFICATION_PROMPT = """Classify this task's complexity. Respond with ONLY one word:
- SIMPLE: Direct factual answer, no reasoning needed
- MEDIUM: Single-step calculation or lookup
- COMPLEX: Multi-step reasoning or research required
- EXPERT: High-stakes decision requiring verification

Task: {task}

Classification:"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self._client = None

    @property
    def client(self):
        """Lazy-load Groq client."""
        if self._client is None:
            try:
                from groq import Groq
                self._client = Groq(api_key=self.api_key)
            except ImportError:
                logger.warning("Groq SDK not installed. Run: pip install groq")
                return None
        return self._client

    def classify_task(self, task: str, timeout: float = 5.0) -> ClassificationResult:
        """
        Fast task classification using Groq's fastest model.
        Target: <2s response time.
        """
        if not self.client:
            # Fallback to heuristic classification
            return self._heuristic_classification(task)

        try:
            start = time.time()
            response = self.client.chat.completions.create(
                messages=[{
                    "role": "user",
                    "content": self.CLASSIFICATION_PROMPT.format(task=task[:500])
                }],
                model="llama-3.1-8b-instant",  # Fastest model
                max_tokens=10,
                temperature=0,
                timeout=timeout
            )

            elapsed = time.time() - start
            classification = response.choices[0].message.content.strip().upper()

            # Map to complexity
            complexity_map = {
                "SIMPLE": TaskComplexity.SIMPLE,
                "MEDIUM": TaskComplexity.MEDIUM,
                "COMPLEX": TaskComplexity.COMPLEX,
                "EXPERT": TaskComplexity.EXPERT
            }

            complexity = complexity_map.get(classification, TaskComplexity.MEDIUM)
            tier = self._complexity_to_tier(complexity)

            logger.info(f"Groq classified task as {complexity.value} in {elapsed:.2f}s")

            return ClassificationResult(
                complexity=complexity,
                recommended_tier=tier,
                reasoning=f"Groq fast classification: {classification}",
                confidence=0.85 if elapsed < 2.0 else 0.7
            )

        except Exception as e:
            logger.warning(f"Groq classification failed: {e}")
            return self._heuristic_classification(task)

    # System prompt for GAIA-style benchmark tasks
    ANSWER_SYSTEM_PROMPT = """You are a precise answer extraction system for benchmark questions.

RULES:
1. Read the question carefully and identify exactly what is being asked
2. Think step-by-step if needed, but keep your final answer precise
3. Your FINAL ANSWER must be on the last line, starting with "ANSWER: "
4. The answer should be the exact value asked for (number, name, word, etc.)
5. Do NOT include units, explanations, or qualifiers in the final answer unless explicitly asked
6. If the question asks for a specific format, follow it exactly

Examples:
- "How many albums?" → ANSWER: 3
- "What is the capital?" → ANSWER: Paris
- "Who wrote it?" → ANSWER: William Shakespeare
- "What word?" → ANSWER: research"""

    def answer_simple(self, task: str, timeout: float = 10.0) -> Optional[str]:
        """
        Fast answer for simple tasks using Groq.
        Uses structured prompting for better GAIA benchmark performance.
        """
        if not self.client:
            return None

        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": self.ANSWER_SYSTEM_PROMPT},
                    {"role": "user", "content": task}
                ],
                model="llama-3.3-70b-versatile",
                max_tokens=500,  # More tokens for reasoning
                temperature=0.1,
                timeout=timeout
            )
            answer = response.choices[0].message.content.strip()

            # Extract answer from ANSWER: prefix if present
            if "ANSWER:" in answer:
                lines = answer.split("\n")
                for line in reversed(lines):
                    if line.strip().startswith("ANSWER:"):
                        return line.split("ANSWER:", 1)[1].strip()

            return answer
        except Exception as e:
            logger.warning(f"Groq fast answer failed: {e}")
            return None

    def _heuristic_classification(self, task: str) -> ClassificationResult:
        """Fallback heuristic-based classification."""
        task_lower = task.lower()

        # Simple indicators
        simple_patterns = [
            "what is", "who is", "when did", "where is",
            "define", "spell", "capital of", "opposite of"
        ]

        # Complex indicators
        complex_patterns = [
            "explain", "analyze", "compare", "design",
            "steps", "plan", "strategy", "evaluate",
            "research", "investigate", "develop"
        ]

        # Expert indicators
        expert_patterns = [
            "verify", "confirm", "ensure", "critical",
            "safety", "security", "legal", "financial"
        ]

        if any(p in task_lower for p in expert_patterns):
            complexity = TaskComplexity.EXPERT
        elif any(p in task_lower for p in complex_patterns):
            complexity = TaskComplexity.COMPLEX
        elif any(p in task_lower for p in simple_patterns) and len(task) < 100:
            complexity = TaskComplexity.SIMPLE
        else:
            complexity = TaskComplexity.MEDIUM

        return ClassificationResult(
            complexity=complexity,
            recommended_tier=self._complexity_to_tier(complexity),
            reasoning="Heuristic classification (Groq unavailable)",
            confidence=0.6
        )

    def _complexity_to_tier(self, complexity: TaskComplexity) -> ModelTier:
        """Map complexity to recommended model tier."""
        return {
            TaskComplexity.SIMPLE: ModelTier.FAST,
            TaskComplexity.MEDIUM: ModelTier.BALANCED,
            TaskComplexity.COMPLEX: ModelTier.POWERFUL,
            TaskComplexity.EXPERT: ModelTier.CONSENSUS
        }[complexity]


class OllamaClient:
    """
    Ollama client with cloud/cluster preference.

    STRATEGY:
    1. Cloud models (balanced/powerful) → Mac Studio (has Ollama Cloud auth)
    2. Local models (fast) → Local GPU (RTX 3060 12GB)
    3. Fallback to local models if Mac Studio unreachable

    NO external API keys needed - Mac Studio handles cloud auth.
    """

    # Mac Studio for cloud models (has Ollama Cloud auth configured)
    MAC_STUDIO_URL = "http://mac-studio.local:11434"
    # Local Ollama for GPU models
    LOCAL_URL = "http://localhost:11434"

    # Model tiers - cloud via Mac Studio, local on GPU
    MODELS = {
        "fast": "deepseek-r1:14b",         # Local 14B reasoning
        "balanced": "gpt-oss:120b-cloud",   # Cloud 120B via Mac Studio
        "powerful": "gpt-oss:120b-cloud",   # Cloud 120B via Mac Studio
    }

    # Fallback models if cloud unavailable
    FALLBACK_MODELS = {
        "fast": "qwen3:14b",
        "balanced": "qwen3:32b",  # Mac Studio local 32B
        "powerful": "deepseek-r1:14b",
    }

    # Max tokens per tier - CRITICAL: Cloud reasoning models need 4096+ to complete answers
    MAX_TOKENS = {
        "fast": 500,
        "balanced": 4096,     # Cloud models need space for thinking + answer
        "powerful": 8192,     # Reasoning models need even more
    }

    # Cloud models need longer timeout (120B model over network)
    CLOUD_TIMEOUT = 180.0
    LOCAL_TIMEOUT = 60.0
    MAX_RETRIES = 2

    def __init__(self):
        self.local_available = self._check_availability(self.LOCAL_URL)
        self.mac_studio_available = self._check_availability(self.MAC_STUDIO_URL)
        self.available = self.local_available or self.mac_studio_available
        self._cloud_failures = 0  # Track consecutive failures

    def _check_availability(self, url: str) -> bool:
        """Check if Ollama is running at URL."""
        try:
            import requests
            resp = requests.get(f"{url}/api/tags", timeout=5)
            return resp.status_code == 200
        except:
            return False

    def _refresh_availability(self):
        """Refresh availability status (call after failures)."""
        self.local_available = self._check_availability(self.LOCAL_URL)
        self.mac_studio_available = self._check_availability(self.MAC_STUDIO_URL)
        self.available = self.local_available or self.mac_studio_available

    def query(self, prompt: str, tier: str = "balanced", timeout: float = None) -> Optional[str]:
        """Query Ollama - routes to appropriate node based on tier.

        STRATEGY:
        - fast: Local GPU (deepseek-r1:14b)
        - balanced/powerful: Mac Studio cloud (gpt-oss:120b-cloud)
        - Fallback to local/Mac Studio local models if cloud fails
        - Retry on failures with availability refresh
        """
        if not self.available:
            self._refresh_availability()
            if not self.available:
                return None

        # Select model based on tier
        model = self.MODELS.get(tier, self.MODELS["balanced"])
        max_tokens = self.MAX_TOKENS.get(tier, 500)

        # Cloud models → Mac Studio, local models → local GPU
        is_cloud_model = "cloud" in model

        # Use appropriate timeout
        if timeout is None:
            timeout = self.CLOUD_TIMEOUT if is_cloud_model else self.LOCAL_TIMEOUT

        base_url = self.MAC_STUDIO_URL if is_cloud_model else self.LOCAL_URL
        logger.info(f"OllamaClient.query: tier={tier}, model={model}, cloud={is_cloud_model}, url={base_url}")

        # Check if target is available (with refresh if too many failures)
        if self._cloud_failures >= 3:
            self._refresh_availability()
            self._cloud_failures = 0

        target_available = self.mac_studio_available if is_cloud_model else self.local_available
        logger.info(f"OllamaClient target_available={target_available}, mac_studio={self.mac_studio_available}, local={self.local_available}")
        if not target_available:
            # Try fallback
            model = self.FALLBACK_MODELS.get(tier, "qwen3:14b")
            is_cloud_model = "cloud" in model
            base_url = self.MAC_STUDIO_URL if is_cloud_model else self.LOCAL_URL
            timeout = self.CLOUD_TIMEOUT if is_cloud_model else self.LOCAL_TIMEOUT
            logger.debug(f"Falling back to model: {model}")

        try:
            import requests

            if is_cloud_model:
                # Cloud models use /api/chat endpoint
                response = requests.post(
                    f"{base_url}/api/chat",
                    json={
                        "model": model,
                        "messages": [{
                            "role": "user",
                            "content": f"Answer precisely: {prompt}"
                        }],
                        "stream": False,
                        "options": {
                            "temperature": 0.1,
                            "num_predict": max_tokens,
                        }
                    },
                    timeout=timeout
                )
                if response.status_code == 200:
                    result = response.json()
                    message = result.get("message", {})
                    answer = message.get("content", "").strip()
                    thinking = message.get("thinking", "")
                    done_reason = result.get("done_reason", "")

                    logger.info(f"Cloud model raw response: done={result.get('done')}, done_reason={done_reason}, answer_len={len(answer) if answer else 0}, thinking_len={len(thinking) if thinking else 0}")

                    # If content is empty but we have thinking, extract answer from thinking
                    if not answer and thinking:
                        logger.info("Cloud model has empty content but has thinking - extracting answer")
                        answer = self._extract_answer_from_thinking(thinking)
                        if answer:
                            logger.info(f"Extracted answer from thinking: {answer[:100]}...")
                        else:
                            logger.warning(f"Could not extract answer from thinking (len={len(thinking)})")
                else:
                    logger.warning(f"Cloud model error: {response.status_code} - {response.text[:500]}")
                    return None
            else:
                # Local models use /api/generate endpoint
                full_prompt = f"Answer precisely: {prompt}"
                response = requests.post(
                    f"{base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": full_prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,
                            "num_predict": max_tokens,
                        }
                    },
                    timeout=timeout
                )
                if response.status_code == 200:
                    result = response.json()
                    answer = result.get("response", "").strip()
                else:
                    logger.warning(f"Local model error: {response.status_code} - {response.text[:500]}")
                    return None

            # For deepseek-r1, extract answer after thinking (if present)
            if answer and "<think>" in answer and "</think>" in answer:
                after_think = answer.split("</think>")[-1].strip()
                if after_think:
                    answer = after_think

            # Clean up common prefixes (with null check)
            if answer:
                for prefix in ["The answer is ", "Answer: ", "The result is "]:
                    if answer.lower().startswith(prefix.lower()):
                        answer = answer[len(prefix):].strip()
                        break

            # IMPROVEMENT 35: Strip reasoning artifacts from LLM output
            if answer:
                answer = self._clean_reasoning_artifacts(answer)

            return answer if answer else None

        except Exception as e:
            if is_cloud_model:
                self._cloud_failures += 1
            logger.warning(f"Ollama query exception ({model}): {type(e).__name__}: {e}")

            # Retry with fallback model if cloud failed
            if is_cloud_model and self._cloud_failures < self.MAX_RETRIES:
                fallback = self.FALLBACK_MODELS.get(tier, "qwen3:14b")
                logger.debug(f"Retrying with fallback: {fallback}")
                return self._query_fallback(prompt, fallback, max_tokens)

        return None

    def _query_fallback(self, prompt: str, model: str, max_tokens: int) -> Optional[str]:
        """Query fallback model on Mac Studio."""
        try:
            import requests
            response = requests.post(
                f"{self.MAC_STUDIO_URL}/api/generate",
                json={
                    "model": model,
                    "prompt": f"Answer precisely: {prompt}",
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": max_tokens}
                },
                timeout=self.LOCAL_TIMEOUT
            )
            if response.status_code == 200:
                answer = response.json().get("response", "").strip()
                if "<think>" in answer and "</think>" in answer:
                    answer = answer.split("</think>")[-1].strip()
                # IMPROVEMENT 35: Apply cleaning to fallback too
                if answer:
                    answer = self._clean_reasoning_artifacts(answer)
                return answer if answer else None
        except Exception as e:
            logger.debug(f"Fallback query failed ({model}): {e}")
        return None

    def _extract_answer_from_thinking(self, thinking: str) -> Optional[str]:
        """
        Extract a final answer from the thinking/reasoning output.

        Reasoning models like gpt-oss put their CoT in 'thinking' field.
        We look for patterns like:
        - "FINAL ANSWER: X"
        - "The answer is X"
        - "Therefore, X"
        - Last numerical/short answer after reasoning
        """
        import re

        if not thinking:
            return None

        # Pattern 1: Explicit final answer markers
        final_patterns = [
            r'FINAL[\s_-]?ANSWER[:\s]+([^\n]+)',
            r'(?:^|\n)Answer[:\s]+([^\n]+)',
            r'(?:^|\n)The answer is[:\s]*([^\n]+)',
            r'(?:^|\n)Therefore,?\s*(?:the answer is\s*)?([^\n]+)',
            r'(?:^|\n)So,?\s*(?:the answer is\s*)?([^\n]+)',
            r'(?:^|\n)Result[:\s]+([^\n]+)',
            r'(?:^|\n)=\s*(\d+(?:\.\d+)?)',  # Math result
        ]

        for pattern in final_patterns:
            match = re.search(pattern, thinking, re.IGNORECASE)
            if match:
                answer = match.group(1).strip()
                # Clean up common artifacts
                answer = re.sub(r'[\.,:;!\?]+$', '', answer).strip()
                if answer and len(answer) < 200:  # Sanity check
                    return answer

        # Pattern 2: Look for last line that looks like an answer
        lines = thinking.strip().split('\n')
        for line in reversed(lines[-10:]):  # Check last 10 lines
            line = line.strip()
            # Skip empty or thinking-like lines
            if not line or line.startswith(('I ', 'Let ', 'We ', 'First', 'So ', 'Now ')):
                continue
            # Check if it's a short potential answer
            if len(line) < 100:
                # Look for number patterns
                num_match = re.search(r'^(\d+(?:\.\d+)?)\s*$', line)
                if num_match:
                    return num_match.group(1)
                # Short definitive statements
                if ':' in line:
                    parts = line.split(':')
                    if len(parts) == 2 and len(parts[1].strip()) < 50:
                        return parts[1].strip()

        # Pattern 3: Extract any boxed answers (LaTeX style)
        boxed_match = re.search(r'\\boxed\{([^}]+)\}', thinking)
        if boxed_match:
            return boxed_match.group(1).strip()

        # Pattern 4: Last number in the thinking (common for math)
        numbers = re.findall(r'\b(\d+(?:\.\d+)?)\b', thinking[-500:])
        if numbers:
            # Return the last substantive number
            for num in reversed(numbers):
                if len(num) >= 1:  # At least 1 digit
                    return num

        return None

    def _clean_reasoning_artifacts(self, answer: str) -> Optional[str]:
        """
        IMPROVEMENT 35: Remove reasoning artifacts and extract clean answer.

        Handles patterns like:
        - "Let's search for X" -> None (needs retry)
        - "Thus final answer: X.X" -> X
        - "Search.Search.Open.X" -> X (extract last part)
        - Full URL/snippet text -> None
        """
        import re

        if not answer:
            return None

        original = answer

        # Pattern 1: Reasoning prefixes that indicate no real answer (IMPROVEMENT 35+36+37+39)
        reasoning_starts = [
            r"^let['']?s\s+(search|look|find|check|directly|view|browse|do|try)",  # Added try
            r"^i('ll| will| can| should)\s+(search|look|find|answer|provide)",  # Added answer, provide
            r"^search(ing)?\s+for",
            r"^to find",
            r"^we (need|should|can)\s+(to\s+)?(search|look|browse)",  # Added browse
            r"^first,?\s+(let|i|we)",
            r"^after\s+\d+\s+(year|month|day)",  # "After 10 years..." snippets
            r"^query:",  # IMPROVEMENT 36: Direct query pattern
            r"^probably\s+need",  # IMPROVEMENT 36
            # IMPROVEMENT 37: More reasoning patterns from thinking extraction
            r"^first\s+move\s+(likely|would|should)",  # "first move likely down to A3"
            r"^(the|this|it)\s+(answer|move|result)\s+(would|should|could)\s+be",  # "the answer would be"
            r"^likely\s+(down|up|to|the|a)",  # "likely down to..."
            r"^(based|given|considering)\s+on",  # "based on the analysis..."
            r"^(so|thus|therefore|hence),?\s+(the|it|this)",  # "so the answer is..."
            r"^looking\s+at",  # "looking at the board..."
            r"^analyzing",  # "analyzing the position..."
            # IMPROVEMENT 39: More I'll patterns
            r"^i('ll| need to)\s+(provide|give|show|answer)",  # "I'll provide that"
            r"^(again|however|but|also)\.",  # "again.30" garbage prefix
            # IMPROVEMENT 42: More reasoning patterns
            r"^turn\s*\d+:",  # "turn1:" or "turn 1:"
            r"^alternatively",  # "Alternatively, maybe the other..."
            r"^for\s+[a-z]\s*=\s*\d+\s+",  # "for a=2 allowed triples..."
            r"^allowed\s+(triples|pairs|values)",  # "allowed triples: (2,8,20)..."
            r"^the\s+shared",  # "the shared first letter of the authors..."
        ]

        for pattern in reasoning_starts:
            if re.match(pattern, answer.lower()):
                logger.debug(f"IMPROVEMENT 35: Detected reasoning prefix, answer rejected: {answer[:50]}")
                return None

        # Pattern 2: "Thus final answer: X" or "final answer: X" - extract X
        final_match = re.search(r'(?:thus\s+)?final\s+answer[:\s]+([^\.]+)', answer, re.IGNORECASE)
        if final_match:
            extracted = final_match.group(1).strip()
            # Remove duplicated word patterns like "Kuba.Kuba" -> "Kuba"
            if '.' in extracted:
                parts = extracted.split('.')
                if len(parts) >= 2 and parts[0].strip().lower() == parts[1].strip().lower():
                    extracted = parts[0].strip()
            if extracted and len(extracted) < 100:
                logger.debug(f"IMPROVEMENT 35: Extracted from 'final answer': {extracted}")
                return extracted

        # Pattern 3: "Search.Search.X" or "Open.Scrolling.X" - extract meaningful part
        if re.search(r'\.Search\.|\.Open\.|\.Scrolling\.', answer):
            # Split and find last substantive part
            parts = re.split(r'(?:\.Search|\.Open|\.Scrolling|\.Results?)+\.?', answer)
            for part in reversed(parts):
                part = part.strip()
                if part and len(part) > 2 and not part.lower().startswith(('let', 'search', 'open', 'scroll')):
                    # Check if it's a real answer not another instruction
                    if not re.match(r"^(search|let|i|we|to|first)", part.lower()):
                        logger.debug(f"IMPROVEMENT 35: Extracted from Search chain: {part[:50]}")
                        return part
            return None

        # Pattern 4: Full web snippets (long text with " - Yahoo:", " - Wikipedia:", etc.)
        if ' - Yahoo:' in answer or ' - Wikipedia:' in answer:
            # This is a search result snippet, not an answer
            logger.debug(f"IMPROVEMENT 35: Detected search snippet, rejected")
            return None

        # Pattern 5: Answer contains URL
        if re.search(r'https?://', answer):
            # Try to extract text before URL
            before_url = re.split(r'https?://', answer)[0].strip()
            if before_url and len(before_url) > 2:
                return before_url
            return None

        # Pattern 6: Very long answers (> 200 chars) are likely snippets not answers
        if len(answer) > 200:
            # Try to find a short answer within
            lines = answer.split('\n')
            for line in lines[:5]:
                line = line.strip()
                if line and len(line) < 100 and not line.lower().startswith(('let', 'search', 'i ', 'we ')):
                    return line
            logger.debug(f"IMPROVEMENT 35: Answer too long ({len(answer)} chars), rejected")
            return None

        # IMPROVEMENT 36: Detect news headline patterns
        news_patterns = ["has one condition", "reveals why", "here's what", "breaking:", "exclusive:"]
        for pattern in news_patterns:
            if pattern in answer.lower():
                logger.debug(f"IMPROVEMENT 36: Detected news headline pattern, rejected: {answer[:50]}")
                return None

        # IMPROVEMENT 38: Detect mathematical reasoning/formula patterns
        math_reasoning_patterns = [
            r"possible\s+(triples|pairs|tuples|values|solutions)",  # "possible triples (t, t+6, 24-2t)"
            r"for\s+[a-z]\s*=\s*\d+\.\.\d+",  # "for t=0..6"
            r"\([a-z],\s*[a-z]\s*[+\-*/]\s*\d+",  # "(t, t+6, ..." mathematical expressions
            r"where\s+[a-z]\s*(is|=|represents)",  # "where t is..."
            r"let\s+[a-z]\s*=",  # "let t ="
            r"if\s+[a-z]\s*[<>=]",  # "if t < 5"
            r"^\d+\s*[+\-*/]\s*\d+\s*=",  # "5 + 3 = 8" style arithmetic
        ]
        for pattern in math_reasoning_patterns:
            if re.search(pattern, answer.lower()):
                logger.debug(f"IMPROVEMENT 38: Detected math reasoning pattern, rejected: {answer[:50]}")
                return None

        return answer


class ParallelProviderExecutor:
    """
    Execute provider queries in PARALLEL using LOCAL models.

    Uses:
    - Local Ollama (qwen3:14b, deepseek-r1:14b, gemma3:12b) on GPU
    - NO external API calls (no credits needed)

    Original problem: Sequential queries = 3 × 120s = 360s worst-case
    Solution: Parallel queries = max(120s) = 120s worst-case
    """

    def __init__(self, max_workers: int = 3):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        # Local Ollama client (GPU inference, no API keys needed)
        self._ollama_client = None

    @property
    def ollama_client(self):
        """Lazy-load Ollama client."""
        if self._ollama_client is None:
            self._ollama_client = OllamaClient()
        return self._ollama_client

    def query_all_parallel(
        self,
        prompt: str,
        timeout_per_provider: int = 60,
        providers: Optional[List[str]] = None
    ) -> Dict[str, Optional[str]]:
        """
        Query multiple LOCAL models in parallel via Ollama.

        Args:
            prompt: The query prompt
            timeout_per_provider: Timeout for each model
            providers: List of tiers to query (default: all)

        Returns:
            Dict mapping provider name to response (None if failed)
        """
        # Map old provider names to Ollama tiers
        providers = providers or ["fast", "balanced", "powerful"]

        provider_funcs = {
            "claude": lambda: self._query_ollama(prompt, "powerful", timeout_per_provider),
            "codex": lambda: self._query_ollama(prompt, "balanced", timeout_per_provider),
            "gemini": lambda: self._query_ollama(prompt, "fast", timeout_per_provider),
            "fast": lambda: self._query_ollama(prompt, "fast", timeout_per_provider),
            "balanced": lambda: self._query_ollama(prompt, "balanced", timeout_per_provider),
            "powerful": lambda: self._query_ollama(prompt, "powerful", timeout_per_provider),
        }

        # Submit all queries in parallel
        futures = {}
        for provider in providers:
            if provider in provider_funcs:
                futures[provider] = self.executor.submit(provider_funcs[provider])

        # Collect results with overall timeout
        results = {}
        overall_timeout = timeout_per_provider + 10  # Small buffer

        for provider, future in futures.items():
            try:
                result = future.result(timeout=overall_timeout)
                results[provider] = result
                if result and result.strip():
                    logger.info(f"[PARALLEL] {provider} responded successfully ({len(result)} chars)")
                else:
                    logger.warning(f"[PARALLEL] {provider} returned empty/None response")
            except FuturesTimeout:
                results[provider] = None
                logger.warning(f"[PARALLEL] {provider} timed out")
            except Exception as e:
                results[provider] = None
                logger.warning(f"[PARALLEL] {provider} failed: {e}")

        return results

    def _query_ollama(self, prompt: str, tier: str, timeout: int) -> Optional[str]:
        """Query Ollama model - routes to Mac Studio for cloud, local for GPU."""
        if not self.ollama_client.available:
            logger.warning(f"Ollama not available (local={self.ollama_client.local_available}, mac_studio={self.ollama_client.mac_studio_available})")
            return None

        try:
            result = self.ollama_client.query(prompt, tier=tier, timeout=float(timeout))
            if result:
                logger.debug(f"Ollama query succeeded (tier={tier}): {len(result)} chars")
            else:
                logger.warning(f"Ollama query returned None (tier={tier})")
            return result
        except Exception as e:
            logger.warning(f"Ollama query failed (tier={tier}): {e}")
        return None

    # Keep legacy method names for backward compatibility
    def _query_claude(self, prompt: str, timeout: int) -> Optional[str]:
        """Query via local Ollama powerful model (deepseek-r1:14b)."""
        return self._query_ollama(prompt, "powerful", timeout)

    def _query_codex(self, prompt: str, timeout: int) -> Optional[str]:
        """Query via local Ollama balanced model (qwen3:14b)."""
        return self._query_ollama(prompt, "balanced", timeout)

    def _query_gemini(self, prompt: str, timeout: int) -> Optional[str]:
        """Query via local Ollama fast model (gemma3:12b)."""
        return self._query_ollama(prompt, "fast", timeout)

    def shutdown(self):
        """Cleanup executor."""
        self.executor.shutdown(wait=False)


class CascadingModelRouter:
    """
    Main router implementing cascading pattern:

    1. Fast Classification (Groq, <2s)
       ↓
    2. Route by Complexity:
       - SIMPLE → Groq fast path (<5s)
       - MEDIUM → Single provider (<30s)
       - COMPLEX → Powerful model (<60s)
       - EXPERT → Parallel consensus (<120s)
       ↓
    3. Escalate on Failure:
       - Fast → Balanced → Powerful → Consensus
       ↓
    4. Return Best Answer
    """

    def __init__(
        self,
        groq_api_key: Optional[str] = None,
        enable_groq_fast_path: bool = True,
        default_timeout: int = 60
    ):
        self.groq = GroqFastPath(api_key=groq_api_key) if enable_groq_fast_path else None
        self.parallel_executor = ParallelProviderExecutor()
        self.default_timeout = default_timeout

        # Escalation chain
        self.escalation_chain = [
            ModelTier.FAST,
            ModelTier.BALANCED,
            ModelTier.POWERFUL,
            ModelTier.CONSENSUS
        ]

    async def route(
        self,
        task: str,
        force_tier: Optional[ModelTier] = None,
        max_escalations: int = 2
    ) -> RoutingResult:
        """
        Route task to appropriate model(s) with automatic escalation.

        Args:
            task: The task/question to answer
            force_tier: Override automatic classification
            max_escalations: Max times to escalate on failure

        Returns:
            RoutingResult with answer and metadata
        """
        start_time = time.time()

        # Step 1: Classify task complexity
        if force_tier:
            tier = force_tier
            logger.info(f"Forced tier: {tier.value}")
        elif self.groq:
            classification = self.groq.classify_task(task)
            tier = classification.recommended_tier
            logger.info(f"Classified as {classification.complexity.value} → {tier.value}")
        else:
            tier = ModelTier.BALANCED  # Default without Groq

        # Step 2: Execute with escalation
        current_tier = tier
        escalations = 0
        result = None
        best_intermediate_result = None  # Preserve best result across escalations
        providers_queried = []

        while escalations <= max_escalations:
            try:
                tier_result = await self._execute_tier(task, current_tier, providers_queried)
                if tier_result and tier_result.strip():
                    result = tier_result
                    # Also preserve as best intermediate in case next tier fails
                    if not best_intermediate_result:
                        best_intermediate_result = tier_result
                        logger.debug(f"Preserved intermediate result from {current_tier.value}")
                    break
                else:
                    logger.debug(f"Tier {current_tier.value} returned empty/None response")
            except Exception as e:
                logger.warning(f"Tier {current_tier.value} failed: {e}")

            # Escalate to next tier
            escalations += 1
            tier_index = self.escalation_chain.index(current_tier)
            if tier_index < len(self.escalation_chain) - 1:
                current_tier = self.escalation_chain[tier_index + 1]
                logger.info(f"Escalating to {current_tier.value} (attempt {escalations})")
            else:
                break  # Can't escalate further

        # Use best intermediate result if final result is empty
        final_result = result or best_intermediate_result
        if not result and best_intermediate_result:
            logger.info(f"Using preserved intermediate result as final answer")

        execution_time = time.time() - start_time

        return RoutingResult(
            answer=final_result or "",
            model_used=current_tier.value,
            tier=current_tier,
            execution_time=execution_time,
            confidence=0.9 if current_tier == ModelTier.CONSENSUS else 0.7,
            escalated=escalations > 0,
            providers_queried=providers_queried
        )

    async def _execute_tier(
        self,
        task: str,
        tier: ModelTier,
        providers_queried: List[str]
    ) -> Optional[str]:
        """Execute task at specific model tier.

        STRATEGY: Use local Ollama models on GPU (no API keys needed).
        - FAST: gemma3:12b (quick general model)
        - BALANCED: qwen3:14b (good reasoning)
        - POWERFUL: deepseek-r1:14b (strong reasoning)
        - CONSENSUS: parallel query all three models

        Groq is used ONLY for fast classification, not task execution.
        """

        if tier == ModelTier.FAST:
            # Use local Ollama fast model (deepseek-r1:14b on local GPU)
            providers_queried.append("ollama-local-deepseek-r1-14b")
            result = self.parallel_executor._query_ollama(task, "fast", timeout=30)
            if result and result.strip():
                return result
            # Fallback to Groq if Ollama unavailable
            if self.groq:
                providers_queried.append("groq-8b-fallback")
                return self.groq.answer_simple(task, timeout=5)
            return None

        elif tier == ModelTier.BALANCED:
            # Use cloud model via Mac Studio (gpt-oss:120b-cloud)
            providers_queried.append("mac-studio-gpt-oss-120b-cloud")
            result = self.parallel_executor._query_ollama(task, "balanced", timeout=180)
            if result and result.strip():
                return result
            # Fallback to Groq if Ollama/Mac Studio unavailable
            if self.groq:
                providers_queried.append("groq-70b-fallback")
                return self.groq.answer_simple(task, timeout=30)
            return None

        elif tier == ModelTier.POWERFUL:
            # Use cloud model via Mac Studio (gpt-oss:120b-cloud)
            providers_queried.append("mac-studio-gpt-oss-120b-cloud")
            result = self.parallel_executor._query_ollama(task, "powerful", timeout=180)
            if result and result.strip():
                return result
            # Fallback to Groq 70b if Mac Studio unavailable
            if self.groq:
                logger.info("Mac Studio cloud unavailable, falling back to Groq 70b")
                providers_queried.append("groq-70b-fallback")
                return self.groq.answer_simple(task, timeout=45)
            return None

        elif tier == ModelTier.CONSENSUS:
            # Parallel consensus across all local Ollama models
            providers_queried.extend(["ollama-fast", "ollama-balanced", "ollama-powerful"])
            responses = self.parallel_executor.query_all_parallel(
                task,
                timeout_per_provider=180,
                providers=["fast", "balanced", "powerful"]
            )
            result = self._find_consensus(responses)
            if result and result.strip():
                return result

            # Fallback to Groq 70b with longer timeout if all models fail
            if self.groq:
                logger.info("All Ollama models failed, falling back to Groq 70b")
                providers_queried.append("groq-70b-consensus-fallback")
                return self.groq.answer_simple(task, timeout=45)
            return None

        return None

    def _find_consensus(self, responses: Dict[str, Optional[str]]) -> Optional[str]:
        """Find consensus answer from multiple provider responses."""
        valid_responses = {k: v for k, v in responses.items() if v}

        if not valid_responses:
            return None

        if len(valid_responses) == 1:
            return list(valid_responses.values())[0]

        # Normalize and vote
        def normalize(answer: str) -> str:
            """Extract and normalize final answer."""
            lines = answer.strip().split('\n')
            for line in reversed(lines):
                clean = line.strip()
                if clean and len(clean) < 500:
                    for prefix in ["Answer:", "ANSWER:", "Final Answer:", "The answer is"]:
                        if clean.lower().startswith(prefix.lower()):
                            clean = clean[len(prefix):].strip()
                    return clean.lower().strip()
            return answer.lower().strip()[:200]

        normalized = {k: normalize(v) for k, v in valid_responses.items()}

        # Count votes
        vote_counts: Dict[str, List[str]] = {}
        for provider, norm_answer in normalized.items():
            if norm_answer not in vote_counts:
                vote_counts[norm_answer] = []
            vote_counts[norm_answer].append(provider)

        # Find majority
        max_votes = max(len(voters) for voters in vote_counts.values())
        majority_answers = [ans for ans, voters in vote_counts.items() if len(voters) == max_votes]

        if len(majority_answers) == 1 and max_votes >= 2:
            consensus = majority_answers[0]
            # Return original answer from consensus provider
            for provider, norm_ans in normalized.items():
                if norm_ans == consensus:
                    return valid_responses[provider]

        # No consensus - prefer Claude
        return valid_responses.get("claude") or list(valid_responses.values())[0]

    def shutdown(self):
        """Cleanup resources."""
        self.parallel_executor.shutdown()


# Convenience function for direct use
async def route_task(task: str, **kwargs) -> RoutingResult:
    """
    Quick function to route a task through the cascading system.

    Usage:
        result = await route_task("What is 2 + 2?")
        print(result.answer)  # "4"
        print(result.tier)    # ModelTier.FAST
    """
    router = CascadingModelRouter(**kwargs)
    try:
        return await router.route(task)
    finally:
        router.shutdown()


if __name__ == "__main__":
    # Demo
    import asyncio

    async def demo():
        print("=== Cascading Model Router Demo ===\n")

        test_tasks = [
            "What is 2 + 2?",  # SIMPLE
            "Explain quantum entanglement briefly",  # MEDIUM
            "Design a 5-step plan to launch a SaaS product",  # COMPLEX
            "Verify this financial calculation is correct: ROI = 15%",  # EXPERT
        ]

        router = CascadingModelRouter()

        for task in test_tasks:
            print(f"Task: {task[:60]}...")
            result = await router.route(task)
            print(f"  Tier: {result.tier.value}")
            print(f"  Time: {result.execution_time:.2f}s")
            print(f"  Escalated: {result.escalated}")
            print(f"  Answer: {result.answer[:100]}..." if result.answer else "  Answer: [None]")
            print()

        router.shutdown()

    asyncio.run(demo())
