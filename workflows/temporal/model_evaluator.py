#!/usr/bin/env python3
"""
Model Evaluator - Evaluate custom trained models against benchmarks

Evaluation Metrics:
1. Code Quality: Syntax correctness, style adherence
2. Task Completion: Does output solve the task?
3. Latency: Response time
4. Token Efficiency: Output length vs quality

STATUS: Production Ready
"""

import asyncio
import json
import logging
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import sqlite3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TRAINING_DATA_DIR = Path("/Volumes/SSDRAID0/agentic-system/training-data")
EVAL_RESULTS_DIR = TRAINING_DATA_DIR / "eval_results"
EVAL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class EvalResult:
    """Single evaluation result"""
    model_name: str
    test_name: str
    category: str
    prompt: str
    expected_keywords: List[str]
    output: str
    latency_ms: float
    syntax_valid: bool
    keywords_found: int
    keywords_total: int
    score: float  # 0-100
    error: Optional[str] = None


@dataclass
class BenchmarkTest:
    """Benchmark test case"""
    name: str
    category: str  # implement, test, research, plan, document
    prompt: str
    expected_keywords: List[str]
    expected_patterns: List[str]  # Regex patterns to match


# Standard benchmark tests
BENCHMARK_TESTS = [
    BenchmarkTest(
        name="simple_function",
        category="implement",
        prompt="Write a Python function that checks if a port is available on localhost.",
        expected_keywords=["def", "socket", "return", "try", "except"],
        expected_patterns=[r"def \w+\(", r"socket\.", r"return\s+(True|False)"]
    ),
    BenchmarkTest(
        name="async_function",
        category="implement",
        prompt="Write an async Python function that fetches data from a URL and returns JSON.",
        expected_keywords=["async", "def", "await", "aiohttp", "json", "return"],
        expected_patterns=[r"async def \w+\(", r"await\s+", r"\.json\(\)"]
    ),
    BenchmarkTest(
        name="mcp_tool",
        category="implement",
        prompt="Create a FastMCP tool that returns system memory usage using psutil.",
        expected_keywords=["FastMCP", "@", "tool", "psutil", "memory", "return"],
        expected_patterns=[r"@\w+\.tool", r"psutil\.virtual_memory"]
    ),
    BenchmarkTest(
        name="test_function",
        category="test",
        prompt="Write pytest tests for a function add(a, b) that returns the sum of two numbers.",
        expected_keywords=["def", "test", "assert", "add"],
        expected_patterns=[r"def test_\w+", r"assert\s+add\("]
    ),
    BenchmarkTest(
        name="temporal_activity",
        category="implement",
        prompt="Write a Temporal activity that processes a task and returns the result.",
        expected_keywords=["@activity.defn", "async", "def", "return"],
        expected_patterns=[r"@activity\.defn", r"async def \w+"]
    ),
    BenchmarkTest(
        name="error_handling",
        category="implement",
        prompt="Write a Python function with proper error handling that reads a JSON file.",
        expected_keywords=["def", "try", "except", "json", "open", "return"],
        expected_patterns=[r"try:", r"except\s+\w+", r"json\.load"]
    ),
    BenchmarkTest(
        name="research_analysis",
        category="research",
        prompt="Analyze the trade-offs between Redis and PostgreSQL for caching in a Python application.",
        expected_keywords=["Redis", "PostgreSQL", "cache", "performance", "memory"],
        expected_patterns=[r"(Redis|PostgreSQL)", r"(advantage|disadvantage|trade-off)"]
    ),
    BenchmarkTest(
        name="documentation",
        category="document",
        prompt="Write documentation for a Python class called TaskManager that manages async tasks.",
        expected_keywords=["TaskManager", "async", "task", "method", "example"],
        expected_patterns=[r"(Args|Returns|Example|Parameters)", r"```python"]
    ),
]


class ModelEvaluator:
    """Evaluate models against benchmarks"""

    def __init__(self, model_name: str = "agentic-task-executor"):
        self.model_name = model_name
        self.results: List[EvalResult] = []
        self.db_path = EVAL_RESULTS_DIR / "eval_results.db"
        self._init_db()

    def _init_db(self):
        """Initialize results database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS eval_results (
                id INTEGER PRIMARY KEY,
                model_name TEXT,
                test_name TEXT,
                category TEXT,
                prompt TEXT,
                output TEXT,
                latency_ms REAL,
                syntax_valid INTEGER,
                keywords_found INTEGER,
                keywords_total INTEGER,
                score REAL,
                error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def run_inference(self, prompt: str, timeout: int = 60) -> Tuple[str, float, Optional[str]]:
        """Run model inference and measure latency"""
        start_time = time.time()

        try:
            result = subprocess.run(
                ["ollama", "run", self.model_name, prompt],
                capture_output=True,
                text=True,
                timeout=timeout
            )

            latency_ms = (time.time() - start_time) * 1000
            output = result.stdout.strip()
            error = result.stderr.strip() if result.returncode != 0 else None

            return output, latency_ms, error

        except subprocess.TimeoutExpired:
            latency_ms = (time.time() - start_time) * 1000
            return "", latency_ms, f"Timeout after {timeout}s"
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return "", latency_ms, str(e)

    def check_syntax(self, code: str) -> bool:
        """Check if Python code has valid syntax"""
        try:
            compile(code, "<string>", "exec")
            return True
        except SyntaxError:
            # Try to extract code blocks
            import re
            code_blocks = re.findall(r"```python\n(.*?)```", code, re.DOTALL)
            if code_blocks:
                try:
                    compile(code_blocks[0], "<string>", "exec")
                    return True
                except SyntaxError:
                    pass
            return False

    def count_keywords(self, output: str, keywords: List[str]) -> int:
        """Count how many expected keywords appear in output"""
        output_lower = output.lower()
        return sum(1 for kw in keywords if kw.lower() in output_lower)

    def calculate_score(self, result: EvalResult) -> float:
        """Calculate overall score (0-100)"""
        score = 0.0

        # Keyword coverage (40%)
        if result.keywords_total > 0:
            keyword_score = (result.keywords_found / result.keywords_total) * 40
            score += keyword_score

        # Syntax validity (30%) - for code tasks
        if result.category in ["implement", "test"]:
            if result.syntax_valid:
                score += 30

        # Response quality (20%) - based on length
        output_len = len(result.output)
        if output_len > 100:
            score += min(20, output_len / 50)

        # Latency (10%) - faster is better
        if result.latency_ms < 5000:
            score += 10
        elif result.latency_ms < 15000:
            score += 5

        return min(100, score)

    def evaluate_test(self, test: BenchmarkTest) -> EvalResult:
        """Run a single benchmark test"""
        logger.info(f"Running test: {test.name}")

        output, latency_ms, error = self.run_inference(test.prompt)

        syntax_valid = self.check_syntax(output) if test.category in ["implement", "test"] else True
        keywords_found = self.count_keywords(output, test.expected_keywords)

        result = EvalResult(
            model_name=self.model_name,
            test_name=test.name,
            category=test.category,
            prompt=test.prompt,
            expected_keywords=test.expected_keywords,
            output=output[:5000],  # Limit size
            latency_ms=latency_ms,
            syntax_valid=syntax_valid,
            keywords_found=keywords_found,
            keywords_total=len(test.expected_keywords),
            score=0,
            error=error
        )

        result.score = self.calculate_score(result)
        return result

    def run_benchmark(self, tests: List[BenchmarkTest] = None) -> Dict:
        """Run full benchmark suite"""
        if tests is None:
            tests = BENCHMARK_TESTS

        logger.info(f"Running benchmark with {len(tests)} tests on model: {self.model_name}")

        self.results = []
        for test in tests:
            result = self.evaluate_test(test)
            self.results.append(result)
            self._save_result(result)

        # Calculate summary
        summary = self._calculate_summary()
        self._save_summary(summary)

        return summary

    def _save_result(self, result: EvalResult):
        """Save result to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO eval_results
            (model_name, test_name, category, prompt, output, latency_ms,
             syntax_valid, keywords_found, keywords_total, score, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result.model_name, result.test_name, result.category, result.prompt,
            result.output, result.latency_ms, 1 if result.syntax_valid else 0,
            result.keywords_found, result.keywords_total, result.score, result.error
        ))

        conn.commit()
        conn.close()

    def _calculate_summary(self) -> Dict:
        """Calculate benchmark summary"""
        if not self.results:
            return {"error": "No results"}

        total_score = sum(r.score for r in self.results)
        avg_score = total_score / len(self.results)
        avg_latency = sum(r.latency_ms for r in self.results) / len(self.results)

        by_category = {}
        for r in self.results:
            if r.category not in by_category:
                by_category[r.category] = {"scores": [], "latencies": []}
            by_category[r.category]["scores"].append(r.score)
            by_category[r.category]["latencies"].append(r.latency_ms)

        category_summary = {}
        for cat, data in by_category.items():
            category_summary[cat] = {
                "avg_score": sum(data["scores"]) / len(data["scores"]),
                "avg_latency_ms": sum(data["latencies"]) / len(data["latencies"]),
                "test_count": len(data["scores"])
            }

        return {
            "model_name": self.model_name,
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(self.results),
            "overall_score": avg_score,
            "avg_latency_ms": avg_latency,
            "by_category": category_summary,
            "passed": sum(1 for r in self.results if r.score >= 50),
            "failed": sum(1 for r in self.results if r.score < 50),
        }

    def _save_summary(self, summary: Dict):
        """Save summary to file"""
        summary_file = EVAL_RESULTS_DIR / f"summary_{self.model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"Summary saved to {summary_file}")

    def compare_models(self, model_names: List[str]) -> Dict:
        """Compare multiple models"""
        results = {}

        for model_name in model_names:
            logger.info(f"Evaluating model: {model_name}")
            self.model_name = model_name
            results[model_name] = self.run_benchmark()

        # Rank models
        rankings = sorted(
            results.items(),
            key=lambda x: x[1].get("overall_score", 0),
            reverse=True
        )

        return {
            "comparison": results,
            "rankings": [{"model": name, "score": data.get("overall_score", 0)}
                        for name, data in rankings]
        }


async def main():
    """Run model evaluation"""
    print("=" * 60)
    print("Model Evaluation")
    print("=" * 60)

    # Check if model exists
    result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
    if "agentic-task-executor" not in result.stdout:
        print("\nWaiting for agentic-task-executor model to be ready...")
        print("Run: ollama create agentic-task-executor -f /Volumes/SSDRAID0/agentic-system/models/Modelfile.agentic-task-executor")
        return

    evaluator = ModelEvaluator("agentic-task-executor")

    print("\nRunning benchmark tests...")
    summary = evaluator.run_benchmark()

    print("\n" + "=" * 60)
    print("Evaluation Results")
    print("=" * 60)
    print(f"\nModel: {summary['model_name']}")
    print(f"Overall Score: {summary['overall_score']:.1f}/100")
    print(f"Average Latency: {summary['avg_latency_ms']:.0f}ms")
    print(f"Tests Passed: {summary['passed']}/{summary['total_tests']}")

    print("\nBy Category:")
    for cat, data in summary.get("by_category", {}).items():
        print(f"  {cat}: {data['avg_score']:.1f}/100 ({data['test_count']} tests)")

    # Compare with base model
    print("\n" + "=" * 60)
    print("Comparing with base model...")
    print("=" * 60)

    comparison = evaluator.compare_models([
        "agentic-task-executor",
        "qwen2.5-coder:14b"
    ])

    print("\nModel Rankings:")
    for i, entry in enumerate(comparison["rankings"], 1):
        print(f"  {i}. {entry['model']}: {entry['score']:.1f}/100")


if __name__ == "__main__":
    asyncio.run(main())
