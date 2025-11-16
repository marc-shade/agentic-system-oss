#!/usr/bin/env python3
"""
Comprehensive Ollama Cloud Model Benchmarking
Tests all 7 available models across different task types to find optimal model-task pairings
"""

import os
import json
import time
from typing import Dict, List, Any
from datetime import datetime
from ollama import Client

# All available Ollama Cloud models
MODELS = [
    "deepseek-v3.1:671b",      # 671B - Advanced reasoning
    "gpt-oss:120b",             # 120B - Complex tasks (current default)
    "kimi-k2:1t",               # 1T - Maximum capability
    "qwen3-coder:480b",         # 480B - Code-focused
    "gpt-oss:20b",              # 20B - Quick decisions
    "glm-4.6",                  # General purpose
    "minimax-m2",               # Multimodal
]

# Test cases for different task types
TEST_CASES = {
    "memory_extraction": {
        "name": "Memory Extraction",
        "description": "Extract structured facts from conversation",
        "prompt": """You are a memory extraction specialist. Extract key facts from this conversation.

Return ONLY valid JSON (no markdown):
{
    "entities": [
        {
            "name": "descriptive-name",
            "entityType": "preference|fact|requirement",
            "observations": ["fact 1", "fact 2"],
            "confidence": 0.0-1.0
        }
    ]
}

Conversation:
User: I prefer Python for backend development, especially FastAPI for APIs.
Assistant: Got it, FastAPI is great for async performance.
User: Yes, and I always use PostgreSQL with SQLAlchemy ORM.
""",
        "expected_entities": 3,
        "scoring": ["accuracy", "structure", "detail"]
    },

    "query_perspectives": {
        "name": "Query Perspective Generation",
        "description": "Generate alternative search query phrasings",
        "prompt": """Generate 2 alternative phrasings of this search query with the same intent but different wording.

Original query: distributed system monitoring

Return ONLY a JSON array:
["alternative 1", "alternative 2"]
""",
        "expected_count": 2,
        "scoring": ["diversity", "relevance", "creativity"]
    },

    "code_analysis": {
        "name": "Code Analysis & Debugging",
        "description": "Analyze code and identify issues",
        "prompt": """Analyze this code and identify issues:

```python
def process_data(items):
    result = []
    for i in range(len(items)):
        if items[i] > 0:
            result.append(items[i] * 2)
    return result
```

Return JSON with issues found:
{
    "issues": [
        {"type": "performance|style|bug", "description": "...", "severity": "low|medium|high"}
    ],
    "suggestions": ["improvement 1", "improvement 2"]
}
""",
        "expected_issues": 2,
        "scoring": ["accuracy", "depth", "actionability"]
    },

    "system_reasoning": {
        "name": "System Health Reasoning",
        "description": "Reason about system state and prioritize actions",
        "prompt": """Given this system state, what should be prioritized?

System Status:
- CPU: 85% usage (high)
- Memory: 60% usage (normal)
- Disk: 95% full (critical)
- Network: 10 Mbps (normal)
- 3 services failing to start
- 1 security alert (unauthorized access attempt)

Return JSON with prioritized actions:
{
    "priority_actions": [
        {"action": "...", "urgency": "critical|high|medium|low", "reasoning": "..."}
    ]
}
""",
        "expected_actions": 3,
        "scoring": ["prioritization", "reasoning", "completeness"]
    },

    "remediation_planning": {
        "name": "Complex Remediation Planning",
        "description": "Create detailed multi-step remediation plan",
        "prompt": """Create a remediation plan for this issue:

Issue: Database connection pool exhausted, causing 500 errors for users.
Context:
- Max pool size: 20 connections
- Average request time: 2s
- Peak traffic: 100 req/s
- Connection leak suspected in user-session endpoint

Return JSON remediation plan:
{
    "immediate_actions": ["action 1", "action 2"],
    "investigation_steps": ["step 1", "step 2"],
    "long_term_fixes": ["fix 1", "fix 2"],
    "monitoring": ["metric 1", "metric 2"]
}
""",
        "expected_steps": 4,
        "scoring": ["thoroughness", "practicality", "prioritization"]
    },

    "creative_generation": {
        "name": "Creative Text Generation",
        "description": "Generate creative but structured content",
        "prompt": """Generate a system status message for display on Arduino LCD (16x2 chars).

System info:
- All services healthy
- CPU: 45%
- Uptime: 3d 12h

Return JSON with 2 lines:
{
    "line1": "...",
    "line2": "..."
}

Constraints:
- Each line max 16 characters
- Clear and informative
- Use abbreviations if needed
""",
        "expected_format": "lcd_display",
        "scoring": ["clarity", "brevity", "informativeness"]
    },

    "math_reasoning": {
        "name": "Mathematical Reasoning",
        "description": "Solve problems requiring mathematical logic",
        "prompt": """Calculate the optimal check interval for system monitoring:

Given:
- Normal state: check every 60 seconds
- Warning state: check every 30 seconds
- Critical state: check every 10 seconds
- Current state: Warning (CPU at 75%)
- State transition threshold: CPU > 80% = Critical, CPU < 60% = Normal
- Current CPU trend: increasing 2% per minute

What should the next 5 check intervals be? Return JSON:
{
    "intervals": [30, 30, 10, 10, 10],
    "reasoning": "..."
}
""",
        "expected_logic": "adaptive_intervals",
        "scoring": ["correctness", "reasoning", "adaptiveness"]
    }
}


class ModelBenchmark:
    """Benchmark Ollama Cloud models across different tasks"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = Client(
            host="https://ollama.com",
            headers={'Authorization': f'Bearer {api_key}'}
        )
        self.results = []

    def test_model(self, model: str, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Test a single model on a single test case"""

        print(f"\n  Testing {model} on {test_case['name']}...", end=" ", flush=True)

        start_time = time.time()

        try:
            response = self.client.chat(
                model=model,
                messages=[{"role": "user", "content": test_case["prompt"]}],
                stream=False,
                options={
                    "temperature": 0.3,
                    "num_predict": 2000
                }
            )

            elapsed_ms = (time.time() - start_time) * 1000
            response_text = response['message']['content']

            # Parse JSON from response
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            parsed = json.loads(response_text.strip())

            # Score the response
            quality_score = self._score_response(test_case, parsed, response_text)

            result = {
                "model": model,
                "test": test_case["name"],
                "success": True,
                "response_time_ms": round(elapsed_ms, 2),
                "response": parsed,
                "quality_score": quality_score,
                "timestamp": datetime.now().isoformat()
            }

            print(f"✅ {elapsed_ms:.0f}ms | Quality: {quality_score}/10")
            return result

        except json.JSONDecodeError as e:
            elapsed_ms = (time.time() - start_time) * 1000
            print(f"❌ JSON parse error")
            return {
                "model": model,
                "test": test_case["name"],
                "success": False,
                "error": f"JSON parse error: {str(e)}",
                "response_time_ms": round(elapsed_ms, 2),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            print(f"❌ Error: {str(e)[:50]}")
            return {
                "model": model,
                "test": test_case["name"],
                "success": False,
                "error": str(e),
                "response_time_ms": round(elapsed_ms, 2),
                "timestamp": datetime.now().isoformat()
            }

    def _score_response(self, test_case: Dict[str, Any], parsed: Any, raw: str) -> float:
        """Score response quality (0-10)"""
        score = 5.0  # Base score

        # Check structure completeness
        if isinstance(parsed, dict):
            # Check for expected entities field
            if test_case.get("expected_entities"):
                if "entities" in parsed and len(parsed.get("entities", [])) > 0:
                    score += 2

            # Check for issues field (code analysis)
            if "issues" in str(test_case.get("prompt", "")):
                if "issues" in parsed and len(parsed.get("issues", [])) > 0:
                    score += 2

            # Check for priority actions (system reasoning)
            if "priority_actions" in str(test_case.get("prompt", "")):
                if "priority_actions" in parsed and len(parsed.get("priority_actions", [])) > 0:
                    score += 2

        # Check if it's a valid array (for perspectives)
        elif isinstance(parsed, list):
            if len(parsed) > 0:
                score += 2

        # Check JSON is valid and well-formed
        if parsed:
            score += 1

        # Check response length (detail level)
        if len(raw) > 200:
            score += 1

        # Check for reasoning field (shows depth)
        if isinstance(parsed, dict) and "reasoning" in str(parsed):
            score += 1

        return min(10.0, score)

    def run_all_benchmarks(self) -> Dict[str, Any]:
        """Run all tests across all models"""

        print("=" * 70)
        print("Ollama Cloud Model Benchmarking")
        print("=" * 70)
        print(f"\nTesting {len(MODELS)} models across {len(TEST_CASES)} task types")
        print(f"Total tests: {len(MODELS) * len(TEST_CASES)}")

        for test_name, test_case in TEST_CASES.items():
            print(f"\n{'=' * 70}")
            print(f"Task: {test_case['name']}")
            print(f"{'=' * 70}")

            for model in MODELS:
                result = self.test_model(model, test_case)
                self.results.append(result)

        return self._generate_report()

    def _generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive benchmark report"""

        # Aggregate results
        model_stats = {}
        task_stats = {}

        for result in self.results:
            model = result["model"]
            task = result["test"]

            # Model stats
            if model not in model_stats:
                model_stats[model] = {
                    "total_tests": 0,
                    "success_count": 0,
                    "avg_response_time": 0,
                    "avg_quality": 0,
                    "response_times": [],
                    "quality_scores": []
                }

            model_stats[model]["total_tests"] += 1
            if result["success"]:
                model_stats[model]["success_count"] += 1
                model_stats[model]["response_times"].append(result["response_time_ms"])
                model_stats[model]["quality_scores"].append(result.get("quality_score", 0))

            # Task stats
            if task not in task_stats:
                task_stats[task] = {
                    "best_model": None,
                    "best_score": 0,
                    "fastest_model": None,
                    "fastest_time": float('inf')
                }

            if result["success"]:
                quality = result.get("quality_score", 0)
                if quality > task_stats[task]["best_score"]:
                    task_stats[task]["best_model"] = model
                    task_stats[task]["best_score"] = quality

                if result["response_time_ms"] < task_stats[task]["fastest_time"]:
                    task_stats[task]["fastest_model"] = model
                    task_stats[task]["fastest_time"] = result["response_time_ms"]

        # Calculate averages
        for model, stats in model_stats.items():
            if stats["response_times"]:
                stats["avg_response_time"] = sum(stats["response_times"]) / len(stats["response_times"])
            if stats["quality_scores"]:
                stats["avg_quality"] = sum(stats["quality_scores"]) / len(stats["quality_scores"])
            stats["success_rate"] = stats["success_count"] / stats["total_tests"] * 100

        return {
            "summary": {
                "total_tests": len(self.results),
                "total_models": len(MODELS),
                "total_tasks": len(TEST_CASES)
            },
            "model_stats": model_stats,
            "task_stats": task_stats,
            "recommendations": self._generate_recommendations(model_stats, task_stats),
            "all_results": self.results
        }

    def _generate_recommendations(self, model_stats: Dict, task_stats: Dict) -> Dict[str, str]:
        """Generate model-task recommendations"""

        recommendations = {}

        # Find best overall model
        best_overall = max(
            model_stats.items(),
            key=lambda x: (x[1]["avg_quality"], -x[1]["avg_response_time"])
        )
        recommendations["best_overall"] = best_overall[0]

        # Find fastest model
        fastest = min(
            [(m, s["avg_response_time"]) for m, s in model_stats.items() if s["response_times"]],
            key=lambda x: x[1]
        )
        recommendations["fastest"] = fastest[0]

        # Find most accurate model
        most_accurate = max(
            [(m, s["avg_quality"]) for m, s in model_stats.items() if s["quality_scores"]],
            key=lambda x: x[1]
        )
        recommendations["most_accurate"] = most_accurate[0]

        # Task-specific recommendations
        for task, stats in task_stats.items():
            task_key = task.lower().replace(" ", "_")
            recommendations[f"best_for_{task_key}"] = stats["best_model"]

        return recommendations

    def print_report(self, report: Dict[str, Any]):
        """Print formatted benchmark report"""

        print("\n" + "=" * 70)
        print("BENCHMARK RESULTS")
        print("=" * 70)

        # Summary
        summary = report["summary"]
        print(f"\nTotal Tests: {summary['total_tests']}")
        print(f"Models Tested: {summary['total_models']}")
        print(f"Task Types: {summary['total_tasks']}")

        # Model Rankings
        print("\n" + "-" * 70)
        print("MODEL RANKINGS")
        print("-" * 70)

        model_stats = report["model_stats"]
        sorted_models = sorted(
            model_stats.items(),
            key=lambda x: (x[1]["avg_quality"], -x[1]["avg_response_time"]),
            reverse=True
        )

        print(f"\n{'Model':<25} {'Success%':<12} {'Avg Time':<12} {'Avg Quality':<12}")
        print("-" * 70)
        for model, stats in sorted_models:
            print(f"{model:<25} {stats['success_rate']:>6.1f}%     "
                  f"{stats['avg_response_time']:>7.0f}ms     "
                  f"{stats['avg_quality']:>6.1f}/10")

        # Recommendations
        print("\n" + "-" * 70)
        print("RECOMMENDATIONS")
        print("-" * 70)

        recs = report["recommendations"]
        print(f"\n🏆 Best Overall: {recs['best_overall']}")
        print(f"⚡ Fastest: {recs['fastest']}")
        print(f"🎯 Most Accurate: {recs['most_accurate']}")

        print("\n📋 Task-Specific Recommendations:")
        for task, stats in report["task_stats"].items():
            print(f"  • {task}: {stats['best_model']} "
                  f"(Quality: {stats['best_score']:.1f}/10, "
                  f"Speed: {stats['fastest_time']:.0f}ms)")

        print("\n" + "=" * 70)

    def save_report(self, report: Dict[str, Any], filename: str = "ollama_benchmark_results.json"):
        """Save detailed results to JSON file"""
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n💾 Detailed results saved to: {filename}")


if __name__ == "__main__":
    # Check for API key
    api_key = os.environ.get("OLLAMA_API_KEY")
    if not api_key:
        print("❌ OLLAMA_API_KEY not set")
        print("Set it with: export OLLAMA_API_KEY=your_api_key")
        exit(1)

    print(f"✅ OLLAMA_API_KEY is set")

    # Run benchmark
    benchmark = ModelBenchmark(api_key)
    report = benchmark.run_all_benchmarks()

    # Display results
    benchmark.print_report(report)

    # Save results
    benchmark.save_report(report)

    print("\n✅ Benchmark complete!")
