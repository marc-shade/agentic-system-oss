#!/usr/bin/env python3
"""
Run GAIA benchmark with improved executor.

Usage:
    python3 run_improved_gaia.py --level 1 --limit 5  # Test run
    python3 run_improved_gaia.py --level 1            # Full Level 1
"""

import asyncio
import argparse
import json
from datetime import datetime
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import from local modules
from gaia_official_benchmark import GAIADatasetLoader, GAIAAnswerValidator, RESULTS_DIR
from gaia_improved_executor import ImprovedGAIAExecutor


async def run_improved_benchmark(level: int = 1, limit: int = None):
    """Run GAIA benchmark with improved executor."""

    print("=" * 70)
    print("IMPROVED GAIA BENCHMARK EVALUATION")
    print("=" * 70)

    # Load dataset
    loader = GAIADatasetLoader()
    has_access, msg = loader.check_access()
    if not has_access:
        print(f"ERROR: {msg}")
        return

    loader.download_dataset()
    tasks = loader.load_tasks(level=level, split="validation")

    if limit:
        tasks = tasks[:limit]

    print(f"\nLevel: {level}")
    print(f"Tasks: {len(tasks)}")
    print("=" * 70)

    # Initialize improved executor
    executor = ImprovedGAIAExecutor(timeout=300, max_retries=2)
    validator = GAIAAnswerValidator()

    # Track results
    results = []
    correct = 0
    skipped = 0
    total_time = 0

    for i, task in enumerate(tasks):
        print(f"\n[{i+1}/{len(tasks)}] Task: {task.task_id[:8]}...")
        print(f"Q: {task.question[:100]}...")

        start = asyncio.get_event_loop().time()

        # Execute with improved strategy
        answer, confidence = await executor.execute(task.question, task.task_id)

        elapsed = asyncio.get_event_loop().time() - start
        total_time += elapsed

        # Check if skipped (file required)
        if not answer and confidence == 0.0:
            is_correct = False
            skipped += 1
            status = "SKIP"
        else:
            # Validate answer
            is_correct = validator.check_answer(answer, task.final_answer)
            if is_correct:
                correct += 1
                status = "✓"
            else:
                status = "✗"

        print(f"Expected: {task.final_answer}")
        print(f"Got: {answer[:100] if answer else '(no answer)'}")
        print(f"Result: {status} | Time: {elapsed:.1f}s")

        results.append({
            "task_id": task.task_id,
            "level": task.level,
            "question": task.question[:200],
            "expected_answer": task.final_answer,
            "agent_answer": answer,
            "is_correct": is_correct,
            "confidence": confidence,
            "execution_time_seconds": elapsed,
            "skipped": not answer and confidence == 0.0
        })

        # Running stats
        attempted = len(results) - skipped
        accuracy = (correct / attempted * 100) if attempted > 0 else 0
        print(f"Running: {correct}/{attempted} ({accuracy:.1f}%)")

    # Final summary
    attempted = len(results) - skipped
    accuracy = (correct / attempted * 100) if attempted > 0 else 0

    summary = {
        "timestamp": datetime.now().isoformat(),
        "benchmark": "GAIA",
        "level": level,
        "executor": "improved",
        "total_tasks": len(tasks),
        "attempted": attempted,
        "skipped": skipped,
        "correct": correct,
        "accuracy": accuracy,
        "total_time_seconds": total_time,
        "avg_time_per_task": total_time / len(tasks) if tasks else 0,
        "comparison": {
            "human": 92.0,
            "gpt4_plugins": 15.0,
            "h2o_agent_sota": 75.0,
            "previous_run": 41.5,  # Level 1 baseline
            "improved_run": accuracy
        },
        "results": results
    }

    print("\n" + "=" * 70)
    print("IMPROVED GAIA BENCHMARK RESULTS")
    print("=" * 70)
    print(f"Total tasks: {len(tasks)}")
    print(f"Skipped (file required): {skipped}")
    print(f"Attempted: {attempted}")
    print(f"Correct: {correct}")
    print(f"Accuracy: {accuracy:.1f}%")
    print(f"Total time: {total_time:.1f}s")
    print(f"Avg time/task: {total_time/len(tasks):.1f}s")

    print("\n--- Comparison ---")
    print(f"  Human:          92.0%")
    print(f"  GPT-4+plugins:  15.0%")
    print(f"  H2O Agent:      75.0%")
    print(f"  Previous run:   {summary['comparison']['previous_run']:.1f}%")
    print(f"  Improved run:   {accuracy:.1f}%")

    if accuracy > summary['comparison']['previous_run']:
        improvement = accuracy - summary['comparison']['previous_run']
        print(f"\n  IMPROVEMENT: +{improvement:.1f}%")
    print("=" * 70)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"gaia_improved_level{level}_{timestamp}.json"
    output_path = RESULTS_DIR / filename

    with open(output_path, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\nResults saved to: {output_path}")

    return summary


async def main():
    parser = argparse.ArgumentParser(description="Improved GAIA Benchmark")
    parser.add_argument("--level", type=int, default=1, choices=[1, 2, 3],
                        help="GAIA difficulty level")
    parser.add_argument("--limit", type=int, default=None,
                        help="Max tasks to run (for testing)")
    args = parser.parse_args()

    await run_improved_benchmark(level=args.level, limit=args.limit)


if __name__ == "__main__":
    asyncio.run(main())
