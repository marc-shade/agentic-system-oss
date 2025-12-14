#!/usr/bin/env python3
"""
Model Benchmark Suite

Comprehensive evaluation of available models for optimal task routing.
Tests each model on standardized prompts and scores using Groq 70B as judge.

Available models discovered:
- Ollama (Mac Studio): mistral-small3.2:24b, mistral:7b, llama3-groq-tool-use:70b,
                       qwen3:32b, gemma3:27b, deepseek-r1:32b, qwen3-coder:30b, etc.
- Groq Cloud: llama-3.3-70b-versatile, llama-3.1-8b-instant, qwen/qwen3-32b,
              meta-llama/llama-4-maverick-17b-128e-instruct, kimi-k2-instruct, etc.
"""

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any
import httpx

# API Keys
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://192.168.1.186:11434")

# Judge model for evaluations
JUDGE_MODEL = "llama-3.3-70b-versatile"

# System capabilities context for evaluation
SYSTEM_CONTEXT = """
Available system capabilities:
- Ollama cluster with 70B/32B/24B/7B models
- TPU for embeddings
- Enhanced memory MCP with vector search
- Research paper MCP for arXiv/Semantic Scholar
- Voice mode MCP for speech I/O
- GPU node (RTX 4090) for heavy inference
- Node chat for inter-agent communication
- RAID10 storage at /mnt/agentic-system
"""

# Test prompts for different task types
TEST_PROMPTS = {
    "coding_simple": {
        "prompt": "Write a Python function that reverses a string without using slicing.",
        "expected_traits": ["function definition", "implementation", "return statement"],
        "complexity": "simple",
    },
    "coding_complex": {
        "prompt": "Implement a LRU cache in Python with O(1) get and put operations. Include type hints and docstrings.",
        "expected_traits": ["OrderedDict or doubly-linked list", "O(1) operations", "type hints", "docstrings"],
        "complexity": "complex",
    },
    "reasoning": {
        "prompt": "A farmer has 17 sheep. All but 9 die. How many sheep does the farmer have left? Explain your reasoning step by step.",
        "expected_traits": ["9 sheep", "step by step", "explanation of 'all but'"],
        "complexity": "simple",
    },
    "system_task": {
        "prompt": f"""Given our system capabilities, suggest how to implement a visual memory system that stores screenshots with semantic search.

{SYSTEM_CONTEXT}

Provide a concrete implementation plan using our actual tools.""",
        "expected_traits": ["TPU for embeddings", "enhanced memory", "specific file paths", "concrete steps"],
        "complexity": "complex",
    },
    "analysis": {
        "prompt": "Analyze the trade-offs between using Groq API (fast, cloud) vs Ollama (local, slower) for an autonomous agent system. Consider latency, cost, privacy, and reliability.",
        "expected_traits": ["latency comparison", "cost analysis", "privacy", "reliability", "recommendation"],
        "complexity": "standard",
    },
}

# Models to benchmark
MODELS_TO_TEST = {
    "groq": [
        # Production models
        ("openai/gpt-oss-120b", "OpenAI 120B"),  # Best quality (947ms)
        ("openai/gpt-oss-20b", "OpenAI 20B"),  # Fastest (283ms)
        ("llama-3.3-70b-versatile", "Llama 70B"),  # Meta flagship (1059ms)
        ("llama-3.1-8b-instant", "Llama 8B fast"),  # Fast cheap (636ms)
        ("moonshotai/kimi-k2-instruct", "Kimi K2"),  # Moonshot (673ms)
        # Llama 4 family
        ("meta-llama/llama-4-maverick-17b-128e-instruct", "Llama4 Maverick"),  # (628ms)
        ("meta-llama/llama-4-scout-17b-16e-instruct", "Llama4 Scout"),  # (465ms)
        # Agentic compound models
        ("groq/compound-mini", "Compound Mini"),  # Agentic with tools (1504ms)
        ("qwen/qwen3-32b", "Qwen3 32B"),  # Alibaba (6407ms - slow)
    ],
    "ollama": [
        ("mistral-small3.2:24b-instruct-2506-fp16", "Mistral Small 24B"),
        ("mistral:7b-instruct-fp16", "Mistral 7B"),
        ("llama3-groq-tool-use:70b-q8_0", "Llama3 70B Tool"),
        ("qwen3:32b-fp16", "Qwen3 32B"),
        ("qwen3-coder:30b", "Qwen3 Coder 30B"),
    ],
}


@dataclass
class BenchmarkResult:
    provider: str
    model: str
    model_desc: str
    test_name: str
    latency_ms: int
    success: bool
    response_length: int
    quality_scores: Optional[Dict[str, int]] = None
    overall_score: Optional[int] = None
    error: Optional[str] = None


EVAL_PROMPT = """You are a response quality evaluator.

Score this response on a scale of 1-10 for each dimension:

1. CORRECTNESS: Is the answer technically accurate?
2. COMPLETENESS: Does it fully address the question?
3. CLARITY: Is it well-structured and easy to understand?
4. SPECIFICITY: Are there concrete details, code, examples?
5. USEFULNESS: Would this response actually help the user?

Test prompt: {prompt}

Expected traits: {traits}

Response to evaluate:
{response}

Return JSON only:
{{
    "correctness": <1-10>,
    "completeness": <1-10>,
    "clarity": <1-10>,
    "specificity": <1-10>,
    "usefulness": <1-10>,
    "overall_score": <1-10>,
    "brief_assessment": "<one sentence assessment>"
}}"""


async def call_groq(model: str, prompt: str, timeout: int = 120) -> tuple[str, int]:
    """Call Groq API and return response + latency_ms"""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set")

    start = time.time()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2048,
                "temperature": 0.7,
            },
            timeout=timeout,
        )
        latency_ms = int((time.time() - start) * 1000)

        if resp.status_code == 200:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return content, latency_ms
        else:
            raise Exception(f"HTTP {resp.status_code}: {resp.text}")


async def call_ollama(model: str, prompt: str, timeout: int = 300) -> tuple[str, int]:
    """Call Ollama and return response + latency_ms"""
    start = time.time()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 2048,
                },
            },
            timeout=timeout,
        )
        latency_ms = int((time.time() - start) * 1000)

        if resp.status_code == 200:
            data = resp.json()
            return data.get("response", ""), latency_ms
        else:
            raise Exception(f"HTTP {resp.status_code}: {resp.text}")


async def evaluate_response(prompt: str, traits: List[str], response: str) -> Optional[Dict]:
    """Use judge model to evaluate response quality"""
    if not GROQ_API_KEY:
        return None

    eval_prompt = EVAL_PROMPT.format(
        prompt=prompt,
        traits=", ".join(traits),
        response=response[:4000]  # Limit response length
    )

    try:
        content, _ = await call_groq(JUDGE_MODEL, eval_prompt, timeout=60)

        # Parse JSON from response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        return json.loads(content.strip())
    except Exception as e:
        print(f"  Eval error: {e}")
        return None


async def benchmark_model(
    provider: str, model: str, model_desc: str, test_name: str, test_config: Dict
) -> BenchmarkResult:
    """Benchmark a single model on a single test"""
    prompt = test_config["prompt"]
    traits = test_config["expected_traits"]

    print(f"  Testing {model_desc} on '{test_name}'...")

    try:
        if provider == "groq":
            response, latency_ms = await call_groq(model, prompt)
        else:  # ollama
            response, latency_ms = await call_ollama(model, prompt)

        # Evaluate response
        eval_result = await evaluate_response(prompt, traits, response)

        return BenchmarkResult(
            provider=provider,
            model=model,
            model_desc=model_desc,
            test_name=test_name,
            latency_ms=latency_ms,
            success=True,
            response_length=len(response),
            quality_scores=eval_result,
            overall_score=eval_result.get("overall_score") if eval_result else None,
        )

    except Exception as e:
        return BenchmarkResult(
            provider=provider,
            model=model,
            model_desc=model_desc,
            test_name=test_name,
            latency_ms=0,
            success=False,
            response_length=0,
            error=str(e),
        )


async def run_benchmarks(
    providers: List[str] = None,
    tests: List[str] = None,
    models: Dict[str, List[tuple]] = None,
) -> List[BenchmarkResult]:
    """Run benchmarks across specified models and tests"""
    providers = providers or ["groq", "ollama"]
    tests = tests or list(TEST_PROMPTS.keys())
    models = models or MODELS_TO_TEST

    results = []

    for provider in providers:
        if provider not in models:
            continue

        print(f"\n{'='*60}")
        print(f"Benchmarking {provider.upper()} models")
        print(f"{'='*60}")

        for model, desc in models[provider]:
            print(f"\nModel: {desc} ({model})")

            for test_name in tests:
                if test_name not in TEST_PROMPTS:
                    continue

                result = await benchmark_model(
                    provider, model, desc, test_name, TEST_PROMPTS[test_name]
                )
                results.append(result)

                if result.success:
                    score = result.overall_score or "N/A"
                    print(f"    {test_name}: {result.latency_ms}ms, score={score}/10")
                else:
                    print(f"    {test_name}: FAILED - {result.error}")

    return results


def generate_report(results: List[BenchmarkResult]) -> str:
    """Generate summary report from benchmark results"""
    report = []
    report.append("\n" + "=" * 70)
    report.append("MODEL BENCHMARK REPORT")
    report.append(f"Generated: {datetime.now().isoformat()}")
    report.append("=" * 70)

    # Group by model
    by_model = {}
    for r in results:
        key = f"{r.provider}/{r.model_desc}"
        if key not in by_model:
            by_model[key] = {"results": [], "total_latency": 0, "scores": [], "successes": 0}
        by_model[key]["results"].append(r)
        if r.success:
            by_model[key]["total_latency"] += r.latency_ms
            by_model[key]["successes"] += 1
            if r.overall_score:
                by_model[key]["scores"].append(r.overall_score)

    # Summary table
    report.append("\n" + "-" * 70)
    report.append(f"{'Model':<35} {'Avg Latency':<12} {'Avg Score':<10} {'Success':<10}")
    report.append("-" * 70)

    model_rankings = []
    for model, data in by_model.items():
        success_rate = data["successes"] / len(data["results"]) if data["results"] else 0
        avg_latency = data["total_latency"] / data["successes"] if data["successes"] > 0 else 0
        avg_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0

        report.append(
            f"{model:<35} {avg_latency:>8.0f}ms   {avg_score:>6.1f}/10   {success_rate*100:>6.0f}%"
        )
        model_rankings.append((model, avg_score, avg_latency, success_rate))

    # Recommendations
    report.append("\n" + "=" * 70)
    report.append("RECOMMENDATIONS")
    report.append("=" * 70)

    # Best overall (score * success_rate)
    model_rankings.sort(key=lambda x: x[1] * x[3], reverse=True)
    if model_rankings:
        best = model_rankings[0]
        report.append(f"\nBest Overall: {best[0]} (score={best[1]:.1f}, latency={best[2]:.0f}ms)")

    # Fastest (with score > 6)
    fast_models = [(m, s, l, r) for m, s, l, r in model_rankings if s >= 6 and r > 0.5]
    fast_models.sort(key=lambda x: x[2])
    if fast_models:
        fastest = fast_models[0]
        report.append(f"Fastest (quality ≥6): {fastest[0]} ({fastest[2]:.0f}ms, score={fastest[1]:.1f})")

    # Best for complex tasks
    complex_results = [r for r in results if "complex" in TEST_PROMPTS.get(r.test_name, {}).get("complexity", "")]
    if complex_results:
        complex_by_model = {}
        for r in complex_results:
            key = f"{r.provider}/{r.model_desc}"
            if key not in complex_by_model:
                complex_by_model[key] = []
            if r.overall_score:
                complex_by_model[key].append(r.overall_score)

        best_complex = max(
            complex_by_model.items(),
            key=lambda x: sum(x[1]) / len(x[1]) if x[1] else 0
        )
        if best_complex[1]:
            avg = sum(best_complex[1]) / len(best_complex[1])
            report.append(f"Best for Complex Tasks: {best_complex[0]} (avg score={avg:.1f})")

    return "\n".join(report)


async def main():
    """Run benchmark suite"""
    print("=" * 60)
    print("MODEL BENCHMARK SUITE")
    print("=" * 60)

    # Parse arguments
    providers = None
    tests = None

    if len(sys.argv) > 1:
        if "--quick" in sys.argv:
            # Quick mode: just test one prompt per model
            tests = ["coding_simple"]
            print("Running QUICK benchmark (coding_simple only)")
        elif "--groq-only" in sys.argv:
            providers = ["groq"]
            print("Running Groq models only")
        elif "--ollama-only" in sys.argv:
            providers = ["ollama"]
            print("Running Ollama models only")
        elif "--help" in sys.argv:
            print("""
Usage: benchmark-models.py [options]

Options:
  --quick       Quick test (one prompt only)
  --groq-only   Test only Groq models
  --ollama-only Test only Ollama models
  --help        Show this help

Environment:
  GROQ_API_KEY  Required for Groq models
  OLLAMA_HOST   Ollama server (default: http://192.168.1.186:11434)
""")
            sys.exit(0)

    if not GROQ_API_KEY:
        print("WARNING: GROQ_API_KEY not set - Groq models will fail")

    # Run benchmarks
    results = await run_benchmarks(providers=providers, tests=tests)

    # Generate report
    report = generate_report(results)
    print(report)

    # Save results
    output_dir = "/mnt/agentic-system/logs"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    results_file = f"{output_dir}/benchmark_results_{timestamp}.json"
    with open(results_file, "w") as f:
        json.dump([asdict(r) for r in results], f, indent=2)
    print(f"\nResults saved to: {results_file}")

    report_file = f"{output_dir}/benchmark_report_{timestamp}.txt"
    with open(report_file, "w") as f:
        f.write(report)
    print(f"Report saved to: {report_file}")


if __name__ == "__main__":
    asyncio.run(main())
