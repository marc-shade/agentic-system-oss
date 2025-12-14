#!/usr/bin/env python3
"""
Multi-Provider Peer Review Orchestrator

Coordinates code review and problem-solving across multiple AI providers:
- OpenAI (Codex/GPT-4)
- Google Gemini CLI
- Ollama Cloud (cluster nodes)
- Claude (for synthesis)

Each provider brings unique perspective and capabilities:
- Codex: Strong at code patterns, practical suggestions
- Gemini: Fast inference, 1M context, multimodal
- Ollama: Local models (CodeLlama, DeepSeek), specialized focus
- Claude: Nuanced analysis, ethical considerations, synthesis

Usage:
    orchestrator = PeerReviewOrchestrator()

    # Interactive (user-steered)
    session = await orchestrator.start_review(
        target="path/to/file.py",
        review_type="code_quality"
    )

    # Internal (autonomous)
    results = await orchestrator.run_internal_review(
        target="some code or problem",
        context={"domain": "security"},
        auto_synthesize=True
    )
"""

import asyncio
import json
import logging
import os
import sys
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Add SDK agents path
sys.path.insert(0, str(Path(__file__).parent / "sdk_agents"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReviewType(Enum):
    """Types of peer review"""
    CODE_QUALITY = "code_quality"          # General code review
    SECURITY = "security"                   # Security audit
    PERFORMANCE = "performance"             # Performance optimization
    ARCHITECTURE = "architecture"           # Design review
    PROBLEM_SOLVING = "problem_solving"     # General problem solving
    DEBUGGING = "debugging"                 # Bug analysis


class Provider(Enum):
    """AI Providers available for peer review"""
    CODEX = "codex"           # OpenAI Codex/GPT
    GEMINI = "gemini"         # Google Gemini CLI
    OLLAMA = "ollama"         # Local Ollama models
    CLAUDE = "claude"         # Claude (synthesis role)

    @property
    def emoji(self) -> str:
        return {
            Provider.CODEX: "🟢",    # OpenAI green
            Provider.GEMINI: "🔵",   # Google blue
            Provider.OLLAMA: "🟣",   # Ollama purple
            Provider.CLAUDE: "🟠",   # Anthropic orange
        }[self]

    @property
    def display_name(self) -> str:
        return {
            Provider.CODEX: "OpenAI Codex",
            Provider.GEMINI: "Gemini Pro",
            Provider.OLLAMA: "Ollama (Local)",
            Provider.CLAUDE: "Claude",
        }[self]


@dataclass
class ReviewFeedback:
    """Feedback from a single provider"""
    provider: Provider
    model: str
    findings: List[Dict[str, Any]]
    suggestions: List[str]
    severity_assessment: str  # low, medium, high, critical
    confidence: float
    reasoning: str
    response_time_ms: float
    raw_response: str = ""


@dataclass
class ReviewSession:
    """Active peer review session"""
    session_id: str
    target: str
    target_type: str  # file, code_snippet, problem
    review_type: ReviewType
    started_at: datetime
    providers: List[Provider]
    feedback: Dict[Provider, ReviewFeedback] = field(default_factory=dict)
    synthesis: Optional[str] = None
    status: str = "active"  # active, reviewing, synthesizing, complete


@dataclass
class ReviewResults:
    """Final review results"""
    session_id: str
    target: str
    review_type: ReviewType
    providers_consulted: List[str]
    consensus_findings: List[Dict[str, Any]]
    divergent_opinions: List[Dict[str, Any]]
    top_recommendations: List[str]
    severity: str
    confidence: float
    synthesis: str


class ProviderClient:
    """Base class for provider clients"""

    def __init__(self, provider: Provider):
        self.provider = provider

    async def review(self, content: str, review_type: ReviewType, context: Dict[str, Any]) -> ReviewFeedback:
        raise NotImplementedError


class CodexClient(ProviderClient):
    """OpenAI Codex/GPT client"""

    def __init__(self):
        super().__init__(Provider.CODEX)
        self.api_key = os.environ.get("OPENAI_API_KEY")

    async def review(self, content: str, review_type: ReviewType, context: Dict[str, Any]) -> ReviewFeedback:
        import time
        start = time.time()

        prompt = self._build_prompt(content, review_type, context)

        try:
            # Try using openai library if available
            import openai

            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": f"You are a senior code reviewer specializing in {review_type.value}. Provide thorough analysis."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )

            result_text = response.choices[0].message.content
            elapsed_ms = (time.time() - start) * 1000

            return self._parse_response(result_text, elapsed_ms, "gpt-4o")

        except ImportError:
            # Fallback to codex-exec binary
            try:
                from codex_agent import CodexAgent, AgentPurpose
                agent = CodexAgent(purpose=AgentPurpose.CODE_QUALITY, tools=[])
                result = agent._call_codex(prompt, timeout=60)
                elapsed_ms = (time.time() - start) * 1000
                return self._parse_response(result, elapsed_ms, "codex-exec")
            except Exception as e:
                logger.warning(f"Codex unavailable: {e}")
                return self._error_feedback(str(e))
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return self._error_feedback(str(e))

    def _build_prompt(self, content: str, review_type: ReviewType, context: Dict[str, Any]) -> str:
        return f"""Review this code/content from a {review_type.value} perspective.

CONTENT:
```
{content[:8000]}
```

CONTEXT:
{json.dumps(context, indent=2)}

Provide your review in this JSON format:
{{
  "findings": [
    {{"issue": "description", "severity": "low|medium|high|critical", "line": null, "suggestion": "fix"}}
  ],
  "suggestions": ["improvement 1", "improvement 2"],
  "severity_assessment": "overall severity",
  "reasoning": "explain your analysis",
  "confidence": 0.0-1.0
}}

Be thorough but practical. Focus on actionable insights."""

    def _parse_response(self, text: str, elapsed_ms: float, model: str) -> ReviewFeedback:
        try:
            # Extract JSON from response
            if "```json" in text:
                json_start = text.find("```json") + 7
                json_end = text.find("```", json_start)
                json_str = text[json_start:json_end].strip()
            elif "{" in text:
                json_start = text.find("{")
                json_end = text.rfind("}") + 1
                json_str = text[json_start:json_end]
            else:
                json_str = text

            data = json.loads(json_str)

            return ReviewFeedback(
                provider=self.provider,
                model=model,
                findings=data.get("findings", []),
                suggestions=data.get("suggestions", []),
                severity_assessment=data.get("severity_assessment", "unknown"),
                confidence=float(data.get("confidence", 0.5)),
                reasoning=data.get("reasoning", ""),
                response_time_ms=elapsed_ms,
                raw_response=text
            )
        except Exception as e:
            logger.error(f"Parse error: {e}")
            return ReviewFeedback(
                provider=self.provider,
                model=model,
                findings=[],
                suggestions=[text[:200]] if text else [],
                severity_assessment="unknown",
                confidence=0.3,
                reasoning=f"Parse error: {e}",
                response_time_ms=elapsed_ms,
                raw_response=text
            )

    def _error_feedback(self, error: str) -> ReviewFeedback:
        return ReviewFeedback(
            provider=self.provider,
            model="error",
            findings=[],
            suggestions=[],
            severity_assessment="unknown",
            confidence=0.0,
            reasoning=f"Error: {error}",
            response_time_ms=0
        )


class GeminiClient(ProviderClient):
    """Google Gemini CLI client"""

    def __init__(self):
        super().__init__(Provider.GEMINI)
        self.gemini_bin = self._find_gemini()

    def _find_gemini(self) -> Optional[str]:
        try:
            result = subprocess.run(["which", "gemini"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    async def review(self, content: str, review_type: ReviewType, context: Dict[str, Any]) -> ReviewFeedback:
        import time
        start = time.time()

        if not self.gemini_bin:
            return self._error_feedback("Gemini CLI not found")

        prompt = self._build_prompt(content, review_type, context)

        try:
            result = subprocess.run(
                [self.gemini_bin, prompt],
                capture_output=True,
                text=True,
                timeout=60
            )

            elapsed_ms = (time.time() - start) * 1000

            if result.returncode != 0:
                return self._error_feedback(result.stderr)

            return self._parse_response(result.stdout, elapsed_ms)

        except subprocess.TimeoutExpired:
            return self._error_feedback("Gemini timed out")
        except Exception as e:
            return self._error_feedback(str(e))

    def _build_prompt(self, content: str, review_type: ReviewType, context: Dict[str, Any]) -> str:
        return f"""You are a thorough code reviewer. Review this from a {review_type.value} perspective.

CONTENT:
{content[:50000]}

CONTEXT: {json.dumps(context)}

Return ONLY JSON (no markdown):
{{"findings": [{{"issue": "desc", "severity": "low|medium|high|critical"}}], "suggestions": [], "severity_assessment": "overall", "reasoning": "analysis", "confidence": 0.8}}"""

    def _parse_response(self, text: str, elapsed_ms: float) -> ReviewFeedback:
        try:
            if "{" in text:
                json_start = text.find("{")
                json_end = text.rfind("}") + 1
                data = json.loads(text[json_start:json_end])
            else:
                raise ValueError("No JSON found")

            return ReviewFeedback(
                provider=self.provider,
                model="gemini-2.5-pro",
                findings=data.get("findings", []),
                suggestions=data.get("suggestions", []),
                severity_assessment=data.get("severity_assessment", "unknown"),
                confidence=float(data.get("confidence", 0.7)),
                reasoning=data.get("reasoning", ""),
                response_time_ms=elapsed_ms,
                raw_response=text
            )
        except Exception as e:
            return ReviewFeedback(
                provider=self.provider,
                model="gemini-2.5-pro",
                findings=[],
                suggestions=[text[:200]] if text else [],
                severity_assessment="unknown",
                confidence=0.3,
                reasoning=str(e),
                response_time_ms=elapsed_ms,
                raw_response=text
            )

    def _error_feedback(self, error: str) -> ReviewFeedback:
        return ReviewFeedback(
            provider=self.provider,
            model="error",
            findings=[],
            suggestions=[],
            severity_assessment="unknown",
            confidence=0.0,
            reasoning=f"Error: {error}",
            response_time_ms=0
        )


class OllamaClient(ProviderClient):
    """Ollama client using cluster load balancer"""

    def __init__(self, model: str = "codellama:13b"):
        super().__init__(Provider.OLLAMA)
        self.model = model
        self.endpoints = [
            "http://192.168.1.183:11434",  # macpro51 - primary GPU node
            "http://192.168.1.76:11434",   # macbook-air
        ]

    async def review(self, content: str, review_type: ReviewType, context: Dict[str, Any]) -> ReviewFeedback:
        import time
        import requests

        start = time.time()
        prompt = self._build_prompt(content, review_type, context)

        # Try endpoints in order
        for endpoint in self.endpoints:
            try:
                response = requests.post(
                    f"{endpoint}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.3}
                    },
                    timeout=120
                )

                if response.status_code == 200:
                    elapsed_ms = (time.time() - start) * 1000
                    result = response.json()
                    return self._parse_response(result.get("response", ""), elapsed_ms)

            except Exception as e:
                logger.warning(f"Ollama endpoint {endpoint} failed: {e}")
                continue

        return self._error_feedback("All Ollama endpoints unavailable")

    def _build_prompt(self, content: str, review_type: ReviewType, context: Dict[str, Any]) -> str:
        return f"""<s>[INST] You are a code reviewer. Review this {review_type.value}.

CODE:
{content[:4000]}

Respond in JSON:
{{"findings": [{{"issue": "desc", "severity": "low|medium|high"}}], "suggestions": [], "severity_assessment": "overall", "reasoning": "brief analysis", "confidence": 0.7}}

JSON only, no explanation: [/INST]"""

    def _parse_response(self, text: str, elapsed_ms: float) -> ReviewFeedback:
        try:
            if "{" in text:
                json_start = text.find("{")
                json_end = text.rfind("}") + 1
                data = json.loads(text[json_start:json_end])
            else:
                raise ValueError("No JSON")

            return ReviewFeedback(
                provider=self.provider,
                model=self.model,
                findings=data.get("findings", []),
                suggestions=data.get("suggestions", []),
                severity_assessment=data.get("severity_assessment", "unknown"),
                confidence=float(data.get("confidence", 0.6)),
                reasoning=data.get("reasoning", ""),
                response_time_ms=elapsed_ms,
                raw_response=text
            )
        except Exception:
            return ReviewFeedback(
                provider=self.provider,
                model=self.model,
                findings=[],
                suggestions=[text[:150]] if text else [],
                severity_assessment="unknown",
                confidence=0.3,
                reasoning="Parse failed",
                response_time_ms=elapsed_ms,
                raw_response=text
            )

    def _error_feedback(self, error: str) -> ReviewFeedback:
        return ReviewFeedback(
            provider=self.provider,
            model=self.model,
            findings=[],
            suggestions=[],
            severity_assessment="unknown",
            confidence=0.0,
            reasoning=f"Error: {error}",
            response_time_ms=0
        )


class PeerReviewOrchestrator:
    """
    Orchestrates multi-provider peer review sessions.

    Coordinates multiple AI models to review code/problems,
    collects diverse perspectives, and synthesizes consensus.
    """

    def __init__(self, default_providers: List[Provider] = None):
        """
        Initialize peer review orchestrator.

        Args:
            default_providers: Default providers to use (all if None)
        """
        self.default_providers = default_providers or [
            Provider.CODEX,
            Provider.GEMINI,
            Provider.OLLAMA
        ]

        self.clients = {
            Provider.CODEX: CodexClient(),
            Provider.GEMINI: GeminiClient(),
            Provider.OLLAMA: OllamaClient(),
        }

        self.active_session: Optional[ReviewSession] = None

    async def start_review(
        self,
        target: str,
        review_type: ReviewType = ReviewType.CODE_QUALITY,
        providers: List[Provider] = None,
        context: Dict[str, Any] = None
    ) -> ReviewSession:
        """
        Start an interactive peer review session.

        Args:
            target: File path or code/problem to review
            review_type: Type of review to perform
            providers: Specific providers to use
            context: Additional context

        Returns:
            Active ReviewSession
        """
        session_id = str(uuid.uuid4())[:8]

        # Determine target type and load content
        if os.path.isfile(target):
            target_type = "file"
            content = Path(target).read_text()
        else:
            target_type = "code_snippet" if "\n" in target else "problem"
            content = target

        self.active_session = ReviewSession(
            session_id=session_id,
            target=target,
            target_type=target_type,
            review_type=review_type,
            started_at=datetime.now(),
            providers=providers or self.default_providers
        )

        logger.info(f"Started peer review session: {session_id}")
        logger.info(f"Target type: {target_type}, Review type: {review_type.value}")
        logger.info(f"Providers: {[p.display_name for p in self.active_session.providers]}")

        return self.active_session

    async def collect_reviews(
        self,
        content: str = None,
        context: Dict[str, Any] = None
    ) -> Dict[Provider, ReviewFeedback]:
        """
        Collect reviews from all configured providers in parallel.

        Args:
            content: Content to review (uses session target if None)
            context: Additional context

        Returns:
            Dict of provider feedback
        """
        if not self.active_session:
            raise ValueError("No active session. Call start_review first.")

        self.active_session.status = "reviewing"

        # Load content from file if needed
        if content is None:
            if self.active_session.target_type == "file":
                content = Path(self.active_session.target).read_text()
            else:
                content = self.active_session.target

        context = context or {}

        # Run all providers in parallel
        tasks = []
        for provider in self.active_session.providers:
            if provider in self.clients:
                tasks.append(self._review_with_provider(
                    provider, content,
                    self.active_session.review_type,
                    context
                ))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect feedback
        for i, provider in enumerate(self.active_session.providers):
            if isinstance(results[i], ReviewFeedback):
                self.active_session.feedback[provider] = results[i]
                logger.info(f"{provider.emoji} {provider.display_name}: {len(results[i].findings)} findings")
            else:
                logger.error(f"{provider.display_name} failed: {results[i]}")

        return self.active_session.feedback

    async def _review_with_provider(
        self,
        provider: Provider,
        content: str,
        review_type: ReviewType,
        context: Dict[str, Any]
    ) -> ReviewFeedback:
        """Run review with a specific provider"""
        client = self.clients.get(provider)
        if not client:
            return ReviewFeedback(
                provider=provider,
                model="unavailable",
                findings=[],
                suggestions=[],
                severity_assessment="unknown",
                confidence=0.0,
                reasoning="Provider not configured",
                response_time_ms=0
            )

        return await client.review(content, review_type, context)

    async def synthesize(self) -> str:
        """
        Synthesize all provider feedback into consensus findings.

        Returns:
            Synthesis text
        """
        if not self.active_session or not self.active_session.feedback:
            raise ValueError("No feedback to synthesize")

        self.active_session.status = "synthesizing"

        # Aggregate findings
        all_findings = []
        all_suggestions = []
        severities = []
        confidences = []

        for provider, feedback in self.active_session.feedback.items():
            for finding in feedback.findings:
                finding["source"] = provider.display_name
                all_findings.append(finding)
            all_suggestions.extend(feedback.suggestions)
            severities.append(feedback.severity_assessment)
            confidences.append(feedback.confidence)

        # Find consensus (findings mentioned by multiple providers)
        finding_texts = [f.get("issue", "") for f in all_findings]
        consensus = []
        divergent = []

        for finding in all_findings:
            issue = finding.get("issue", "")
            # Simple similarity check
            similar_count = sum(1 for t in finding_texts if self._similar(issue, t))
            if similar_count > 1:
                if finding not in consensus:
                    consensus.append(finding)
            else:
                divergent.append(finding)

        # Build synthesis
        synthesis = f"""## Peer Review Synthesis

**Providers Consulted**: {', '.join(p.display_name for p in self.active_session.feedback.keys())}
**Review Type**: {self.active_session.review_type.value}

### Consensus Findings ({len(consensus)})
"""
        for i, f in enumerate(consensus[:5], 1):
            synthesis += f"\n{i}. [{f.get('severity', 'medium').upper()}] {f.get('issue', 'N/A')}\n   Source: {f.get('source', 'unknown')}\n"

        synthesis += f"""
### Divergent Opinions ({len(divergent)})
"""
        for i, f in enumerate(divergent[:3], 1):
            synthesis += f"\n{i}. {f.get('issue', 'N/A')} ({f.get('source', 'unknown')})\n"

        synthesis += f"""
### Top Suggestions
"""
        for i, s in enumerate(list(set(all_suggestions))[:5], 1):
            synthesis += f"\n{i}. {s}\n"

        synthesis += f"""
### Overall Assessment
- **Severity**: {max(severities, key=lambda x: ['low', 'medium', 'high', 'critical'].index(x) if x in ['low', 'medium', 'high', 'critical'] else 0)}
- **Average Confidence**: {sum(confidences)/len(confidences):.0%}
"""

        self.active_session.synthesis = synthesis
        self.active_session.status = "complete"

        return synthesis

    def _similar(self, a: str, b: str) -> bool:
        """Check if two strings are similar (simple word overlap)"""
        if a == b:
            return True
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        overlap = len(words_a & words_b)
        return overlap > min(len(words_a), len(words_b)) * 0.5

    async def conclude(self) -> ReviewResults:
        """
        Conclude the review session and return final results.

        Returns:
            ReviewResults with all findings and synthesis
        """
        if not self.active_session:
            raise ValueError("No active session")

        if not self.active_session.synthesis:
            await self.synthesize()

        # Build results
        all_findings = []
        all_suggestions = []
        severities = []

        for feedback in self.active_session.feedback.values():
            all_findings.extend(feedback.findings)
            all_suggestions.extend(feedback.suggestions)
            severities.append(feedback.severity_assessment)

        # Determine consensus vs divergent
        consensus = []
        divergent = []
        seen = set()

        for f in all_findings:
            key = f.get("issue", "")[:50]
            if key in seen:
                if f not in consensus:
                    consensus.append(f)
            else:
                seen.add(key)
                divergent.append(f)

        results = ReviewResults(
            session_id=self.active_session.session_id,
            target=self.active_session.target,
            review_type=self.active_session.review_type,
            providers_consulted=[p.display_name for p in self.active_session.feedback.keys()],
            consensus_findings=consensus[:10],
            divergent_opinions=divergent[:10],
            top_recommendations=list(set(all_suggestions))[:5],
            severity=max(severities, default="unknown"),
            confidence=sum(f.confidence for f in self.active_session.feedback.values()) / max(len(self.active_session.feedback), 1),
            synthesis=self.active_session.synthesis or ""
        )

        logger.info(f"Concluded peer review session: {results.session_id}")
        self.active_session = None

        return results

    async def run_internal_review(
        self,
        target: str,
        review_type: ReviewType = ReviewType.CODE_QUALITY,
        context: Dict[str, Any] = None,
        providers: List[Provider] = None,
        auto_synthesize: bool = True
    ) -> ReviewResults:
        """
        Run a complete internal review (no user interaction).

        Args:
            target: Code/file/problem to review
            review_type: Type of review
            context: Additional context
            providers: Specific providers
            auto_synthesize: Auto-synthesize results

        Returns:
            ReviewResults
        """
        await self.start_review(target, review_type, providers, context)
        await self.collect_reviews(context=context)

        if auto_synthesize:
            await self.synthesize()

        return await self.conclude()


class PeerReviewTrigger:
    """
    Determines when to trigger autonomous peer review.

    Criteria:
    - Code complexity (cyclomatic, LOC)
    - File type (critical files get review)
    - Change size (large changes)
    - Security sensitivity
    """

    CRITICAL_PATTERNS = [
        "auth", "security", "crypto", "password", "token",
        "payment", "billing", "admin", "permission"
    ]

    @staticmethod
    def should_trigger(
        file_path: str = None,
        code: str = None,
        change_size: int = 0,
        is_new_file: bool = False
    ) -> Tuple[bool, str]:
        """
        Determine if peer review should be triggered.

        Returns:
            (should_trigger, reason)
        """
        reasons = []

        # Check file path for critical patterns
        if file_path:
            path_lower = file_path.lower()
            for pattern in PeerReviewTrigger.CRITICAL_PATTERNS:
                if pattern in path_lower:
                    reasons.append(f"Critical path pattern: {pattern}")
                    break

        # Check code content
        if code:
            # Large files
            lines = code.count('\n')
            if lines > 200:
                reasons.append(f"Large file: {lines} lines")

            # Security-sensitive content
            for pattern in PeerReviewTrigger.CRITICAL_PATTERNS:
                if pattern in code.lower():
                    reasons.append(f"Security-sensitive content: {pattern}")
                    break

        # Large changes
        if change_size > 100:
            reasons.append(f"Large change: {change_size} lines")

        # New files in critical paths
        if is_new_file and file_path:
            for pattern in PeerReviewTrigger.CRITICAL_PATTERNS:
                if pattern in file_path.lower():
                    reasons.append(f"New file in critical path")
                    break

        should_trigger = len(reasons) > 0
        reason = "; ".join(reasons) if reasons else "No trigger conditions met"

        return should_trigger, reason


# Convenience functions for internal use
async def quick_review(target: str, review_type: str = "code_quality") -> ReviewResults:
    """Quick internal review for autonomous use"""
    orchestrator = PeerReviewOrchestrator()
    return await orchestrator.run_internal_review(
        target=target,
        review_type=ReviewType(review_type)
    )


if __name__ == "__main__":
    # Test the orchestrator
    async def test():
        orchestrator = PeerReviewOrchestrator(
            default_providers=[Provider.OLLAMA]  # Test with Ollama only
        )

        test_code = '''
def login(username, password):
    if username == "admin" and password == "password123":
        return True
    return False
'''

        print("Starting peer review test...")
        results = await orchestrator.run_internal_review(
            target=test_code,
            review_type=ReviewType.SECURITY,
            context={"language": "python", "domain": "authentication"}
        )

        print(f"\nSession: {results.session_id}")
        print(f"Providers: {results.providers_consulted}")
        print(f"Findings: {len(results.consensus_findings)}")
        print(f"\n{results.synthesis}")

    asyncio.run(test())
