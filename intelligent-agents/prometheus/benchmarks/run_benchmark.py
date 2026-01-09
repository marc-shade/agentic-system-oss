#!/usr/bin/env python3
"""GAIA Benchmark Runner Script"""
import asyncio
import os
import json
from datetime import datetime

# Ensure GROQ key is set
if not os.environ.get("GROQ_API_KEY"):
    raise ValueError("GROQ_API_KEY environment variable required")

from gaia_official_benchmark import GAIABenchmarkRunner


async def run_full():
    benchmark = GAIABenchmarkRunner()
    results = await benchmark.run_benchmark(level="1")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"gaia_results/gaia_eval_{timestamp}.json"
    with open(filename, "w") as f:
        json.dump(results, f, indent=2)

    correct = results["correct"]
    total = results["total_tasks"]
    accuracy = results["accuracy"] / 100 if results["accuracy"] > 1 else results["accuracy"]

    print(f"\n{'='*50}")
    print(f"FINAL RESULTS: {correct}/{total} ({accuracy:.1%})")
    print(f"{'='*50}")
    print(f"Saved to: {filename}")

    # Show failures
    failures = [r for r in results["results"] if not r.get("is_correct", r.get("correct", False))]
    print(f"\nFailures ({len(failures)}):")
    for i, f in enumerate(failures[:15], 1):
        exp = str(f.get("expected_answer", "N/A"))
        got = str(f.get("agent_answer", "N/A"))[:60]
        print(f"  {i}. Exp: {repr(exp)}, Got: {repr(got)}")


if __name__ == "__main__":
    asyncio.run(run_full())
