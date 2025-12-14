#!/usr/bin/env python3
"""
Response Quality Evaluator

Scores autonomous session responses on multiple dimensions:
1. Format compliance (follows JSON schema)
2. Actionability (concrete vs vague)
3. System awareness (uses our actual tools/capabilities)
4. Specificity (detailed vs generic)

Uses a judge model (Groq 70B) to evaluate responses from worker models.
"""

import asyncio
import json
import os
import sys
from dataclasses import dataclass
from typing import Optional
import httpx

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Our system's actual capabilities for context
SYSTEM_CAPABILITIES = """
Available tools and capabilities:
- Ollama cluster with models: mistral-small3.2:24b, llama3-groq-tool-use:70b, moondream (vision)
- TPU for embeddings and small model inference
- Enhanced memory MCP with vector search, episodic/semantic memory
- Research paper MCP for arXiv/Semantic Scholar
- Voice mode MCP for speech I/O
- GPU node (completeu-server) with RTX 4090 for heavy inference
- Node chat for inter-agent communication
"""

EVAL_PROMPT = """You are a quality evaluator for an autonomous AGI system.

Score this response on a scale of 1-10 for each dimension:

1. FORMAT_COMPLIANCE: Does it follow the expected JSON schema with task_completed, summary, actions_taken, findings, next_steps?
2. ACTIONABILITY: Are the suggested actions concrete and executable, or vague platitudes?
3. SYSTEM_AWARENESS: Does it reference our actual tools and capabilities, or suggest generic solutions?
4. SPECIFICITY: Are there specific details (file paths, model names, code snippets) or just high-level ideas?
5. CORRECTNESS: Is the information technically accurate?

System capabilities for context:
{capabilities}

Task that was given:
{task}

Response to evaluate:
{response}

Return JSON only:
{{
    "format_compliance": <1-10>,
    "actionability": <1-10>,
    "system_awareness": <1-10>,
    "specificity": <1-10>,
    "correctness": <1-10>,
    "overall_score": <1-10>,
    "issues": ["list", "of", "specific", "issues"],
    "suggestions": ["how", "to", "improve"]
}}
"""


@dataclass
class EvalResult:
    format_compliance: int
    actionability: int
    system_awareness: int
    specificity: int
    correctness: int
    overall_score: int
    issues: list
    suggestions: list


async def evaluate_response(task: str, response: str) -> Optional[EvalResult]:
    """Use Groq 70B as judge to evaluate response quality."""
    if not GROQ_API_KEY:
        print("GROQ_API_KEY not set")
        return None

    prompt = EVAL_PROMPT.format(
        capabilities=SYSTEM_CAPABILITIES,
        task=task,
        response=response
    )

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1024,
                    "temperature": 0.1,  # Low temp for consistent evals
                },
                timeout=60,
            )

            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]

                # Parse JSON from response
                # Handle markdown code blocks
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                eval_data = json.loads(content.strip())
                return EvalResult(**eval_data)
            else:
                print(f"Eval failed: {resp.status_code}")
                return None

    except Exception as e:
        print(f"Eval error: {e}")
        return None


async def main():
    if len(sys.argv) < 3:
        print("Usage: eval-response-quality.py '<task>' '<response>'")
        print("\nExample:")
        print("  eval-response-quality.py 'Fill knowledge gap in visual processing' '{\"task_completed\": true, ...}'")
        sys.exit(1)

    task = sys.argv[1]
    response = sys.argv[2]

    print(f"Evaluating response quality...")
    print(f"Task: {task[:100]}...")
    print()

    result = await evaluate_response(task, response)

    if result:
        print("=" * 50)
        print("QUALITY SCORES")
        print("=" * 50)
        print(f"Format Compliance:  {result.format_compliance}/10")
        print(f"Actionability:      {result.actionability}/10")
        print(f"System Awareness:   {result.system_awareness}/10")
        print(f"Specificity:        {result.specificity}/10")
        print(f"Correctness:        {result.correctness}/10")
        print("-" * 50)
        print(f"OVERALL SCORE:      {result.overall_score}/10")
        print()

        if result.issues:
            print("Issues:")
            for issue in result.issues:
                print(f"  - {issue}")
            print()

        if result.suggestions:
            print("Suggestions:")
            for suggestion in result.suggestions:
                print(f"  - {suggestion}")

        # Return pass/fail based on threshold
        if result.overall_score >= 7:
            print("\n✓ PASS - Response quality acceptable")
            sys.exit(0)
        else:
            print("\n✗ FAIL - Response quality below threshold")
            sys.exit(1)
    else:
        print("Evaluation failed")
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())
