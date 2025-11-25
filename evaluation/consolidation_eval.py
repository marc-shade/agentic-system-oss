#!/usr/bin/env python3
"""
Consolidation quality evaluation runner.

Tests the sleeptime agent's consolidation capabilities.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add MCP server to path
sys.path.insert(0, str(Path(__file__).parent.parent / "mcp-servers" / "enhanced-memory-mcp"))

from sleeptime_agent import SleetimeAgent


class ConsolidationEvaluator:
    """Evaluate consolidation quality"""

    def __init__(self, agent_id="test_agent"):
        self.agent_id = agent_id
        self.agent = SleetimeAgent(agent_id=agent_id)
        self.results = []

    def run_eval_dataset(self, dataset_path: Path):
        """Run evaluation on consolidation scenarios"""
        with open(dataset_path) as f:
            for line_num, line in enumerate(f, 1):
                sample = json.loads(line)
                input_text = sample["input"]
                ground_truth = sample["ground_truth"]

                print(f"\n[Sample {line_num}] {input_text[:60]}...")

                # Execute consolidation
                result = self.execute_consolidation(input_text)

                # Grade the result
                score = self.grade_consolidation(result, ground_truth)

                self.results.append({
                    "sample_num": line_num,
                    "input": input_text,
                    "ground_truth": ground_truth,
                    "result": result,
                    "score": score
                })

                status = "✓" if score >= 0.7 else "✗"
                print(f"  {status} Score: {score:.2f}")

    def execute_consolidation(self, input_text: str):
        """Execute consolidation command"""
        input_lower = input_text.lower()

        try:
            if "run consolidation" in input_lower:
                # Run full consolidation cycle
                return self.agent.run_consolidation_cycle(time_window_hours=24)

            elif "extract patterns" in input_lower:
                # Get recent memories and extract patterns
                memories = self.agent.get_recent_episodic_memories(time_window_hours=24)
                patterns = self.agent.extract_patterns(memories, min_frequency=2)
                return {"patterns_found": len(patterns), "patterns": patterns}

            elif "create semantic concepts" in input_lower or "create concepts" in input_lower:
                # Extract patterns then create concepts
                memories = self.agent.get_recent_episodic_memories(time_window_hours=24)
                patterns = self.agent.extract_patterns(memories, min_frequency=2)
                concepts = self.agent.create_semantic_concepts(patterns)
                return {"concepts_created": len(concepts), "concepts": concepts}

            elif "discover causal" in input_lower:
                # Discover causal relationships
                memories = self.agent.get_recent_episodic_memories(time_window_hours=24)
                causal_chains = self.agent.discover_causal_relationships(memories)
                return {"causal_chains_discovered": len(causal_chains), "chains": causal_chains}

            elif "update learnings" in input_lower:
                # Update learnings block
                result = self.agent.update_learnings_block([], [], [])
                return {"learnings_updated": result["success"]}

            else:
                return {"error": "Unknown command"}

        except Exception as e:
            return {"error": str(e)}

    def grade_consolidation(self, result: dict, ground_truth: dict) -> float:
        """
        Grade consolidation result.

        Checks if key metrics match expectations.
        """
        if "error" in result:
            return 0.0

        score = 0.0
        checks = 0

        # Check each expected key
        for key, expected_value in ground_truth.items():
            checks += 1

            if key not in result:
                continue  # Missing key, no points

            actual_value = result[key]

            # For numeric values (counts)
            if isinstance(expected_value, int):
                if actual_value >= expected_value:
                    score += 1.0  # Met or exceeded expectation

            # For boolean values
            elif isinstance(expected_value, bool):
                if actual_value == expected_value:
                    score += 1.0  # Exact match

            # For string values
            elif isinstance(expected_value, str):
                if expected_value in str(actual_value):
                    score += 1.0  # Content present

        # Return average score across all checks
        return score / checks if checks > 0 else 0.0

    def generate_report(self, output_dir: Path):
        """Generate evaluation report"""
        output_dir.mkdir(parents=True, exist_ok=True)

        # Calculate statistics
        total_samples = len(self.results)
        passed = sum(1 for r in self.results if r["score"] >= 0.7)
        avg_score = sum(r["score"] for r in self.results) / total_samples if total_samples > 0 else 0.0

        gate_passed = avg_score >= 0.7

        summary = {
            "suite_name": "consolidation_quality",
            "timestamp": datetime.now().isoformat(),
            "total_samples": total_samples,
            "passed_samples": passed,
            "failed_samples": total_samples - passed,
            "avg_score": avg_score,
            "pass_rate": passed / total_samples if total_samples > 0 else 0.0,
            "gate_threshold": 0.7,
            "gate_passed": gate_passed
        }

        # Write summary
        summary_path = output_dir / "summary.json"
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)

        # Write results
        results_path = output_dir / "results.jsonl"
        with open(results_path, "w") as f:
            for result in self.results:
                f.write(json.dumps(result) + "\n")

        print(f"\n{'='*80}")
        print("CONSOLIDATION EVALUATION SUMMARY")
        print(f"{'='*80}")
        print(f"Total Samples: {total_samples}")
        print(f"Passed: {passed} ({passed/total_samples*100:.1f}%)")
        print(f"Failed: {total_samples - passed}")
        print(f"Average Score: {avg_score:.2%}")
        print(f"Gate Status: {'✅ PASSED' if gate_passed else '❌ FAILED'} (threshold: 70%)")
        print(f"\nResults saved to: {output_dir}")

        return summary


def main():
    """Run consolidation evaluation"""
    print("="*80)
    print("SLEEPTIME AGENT - CONSOLIDATION EVALUATION")
    print("="*80)

    # Initialize evaluator
    evaluator = ConsolidationEvaluator(agent_id="test_agent")

    # Run evaluation
    dataset_path = Path(__file__).parent / "datasets" / "consolidation_scenarios.jsonl"
    print(f"\nRunning evaluation on: {dataset_path}")
    evaluator.run_eval_dataset(dataset_path)

    # Generate report
    output_dir = Path(__file__).parent / "results" / f"consolidation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    summary = evaluator.generate_report(output_dir)

    # Exit with appropriate code
    sys.exit(0 if summary["gate_passed"] else 1)


if __name__ == "__main__":
    main()
