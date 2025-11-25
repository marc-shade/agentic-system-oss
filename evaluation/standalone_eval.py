#!/usr/bin/env python3
"""
Standalone evaluation runner for enhanced-memory MCP.

This runner evaluates memory operations without requiring a Letta server.
It directly uses the enhanced-memory MCP's tools and database.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import sqlite3

# Add MCP server to path
sys.path.insert(0, str(Path(__file__).parent.parent / "mcp-servers" / "enhanced-memory-mcp"))

from letta_memory_blocks import MemoryBlockManager

# Database path
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"


class MemoryEvaluator:
    """Evaluate memory block operations"""

    def __init__(self, agent_id="test_agent"):
        self.agent_id = agent_id
        self.manager = MemoryBlockManager(DB_PATH)
        self.results = []

    def cleanup_agent(self):
        """Delete existing memory blocks for test agent to ensure clean slate"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM memory_blocks WHERE agent_id = ?', (self.agent_id,))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        if deleted > 0:
            print(f"✓ Cleanup: Deleted {deleted} existing blocks")

    def setup_agent(self):
        """Create default memory blocks for test agent"""
        # Clean up any existing blocks first
        self.cleanup_agent()

        result = self.manager.create_default_blocks(
            agent_id=self.agent_id,
            node_id="test_node"
        )
        print(f"✓ Setup: Created {len(result['blocks_created'])} memory blocks")
        return result

    def run_eval_dataset(self, dataset_path: Path):
        """
        Run evaluation on a JSONL dataset.

        Dataset format:
        {"input": "command", "ground_truth": "expected content"}
        """
        with open(dataset_path) as f:
            for line_num, line in enumerate(f, 1):
                sample = json.loads(line)
                input_text = sample["input"]
                ground_truth = sample["ground_truth"]

                print(f"\n[Sample {line_num}] {input_text[:60]}...")

                # Execute the command
                success, output = self.execute_command(input_text)

                # Grade the result
                score = self.grade_output(output, ground_truth, input_text)

                self.results.append({
                    "sample_num": line_num,
                    "input": input_text,
                    "ground_truth": ground_truth,
                    "output": output,
                    "success": success,
                    "score": score
                })

                status = "✓" if score >= 0.7 else "✗"
                print(f"  {status} Score: {score:.2f}")

    def execute_command(self, input_text: str):
        """
        Execute a memory command based on input text.

        Supports:
        - Append operations
        - Replace operations
        - Updates
        """
        input_lower = input_text.lower()

        try:
            # Determine operation type
            if "append" in input_lower:
                return self.execute_append(input_text)
            elif "replace" in input_lower or "update" in input_lower:
                return self.execute_replace(input_text)
            else:
                return False, "Unknown command type"

        except Exception as e:
            return False, f"Error: {str(e)}"

    def execute_append(self, input_text: str):
        """Execute append operation"""
        # Parse: "Append 'content' to block_label block"
        import re

        # Extract content in quotes
        content_match = re.search(r"'([^']+)'", input_text)
        if not content_match:
            return False, "Could not extract content"

        content = content_match.group(1)

        # Extract block label
        block_label = self.extract_block_label(input_text)

        # Execute append
        result = self.manager.append_to_block(
            agent_id=self.agent_id,
            label=block_label,
            content=content
        )

        if result["success"]:
            return True, f"Appended to {block_label}: {result['chars_current']}/{result['chars_limit']} chars"
        else:
            return False, result.get("error", "Append failed")

    def execute_replace(self, input_text: str):
        """Execute replace operation"""
        import re

        # Parse: "Replace 'old' with 'new' in block"
        # or: "Update block: Replace 'old' with 'new'"

        # Extract old and new content
        replace_match = re.search(r"'([^']+)'.*?(?:with|to)\s+'([^']+)'", input_text, re.IGNORECASE)

        if replace_match:
            old_content = replace_match.group(1)
            new_content = replace_match.group(2)
        else:
            # Try simpler pattern for updates
            content_match = re.search(r"'([^']+)'", input_text)
            if content_match:
                new_content = content_match.group(1)
                old_content = ""  # Will match anything
            else:
                return False, "Could not extract content"

        block_label = self.extract_block_label(input_text)

        # Get current block value from database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT value FROM memory_blocks
            WHERE agent_id = ? AND label = ?
        ''', (self.agent_id, block_label))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return False, f"Block {block_label} not found"

        current_value = row[0]

        # Validate old_content exists in block
        if old_content and old_content not in current_value:
            return False, f"Old content not found in block '{block_label}'"

        # Update block - replace_in_block handles the string replacement internally
        result = self.manager.replace_in_block(
            agent_id=self.agent_id,
            label=block_label,
            old_content=old_content,
            new_content=new_content
        )

        if result["success"]:
            return True, f"Replaced in {block_label}: {result['chars_current']}/{result['chars_limit']} chars"
        else:
            return False, result.get("error", "Replace failed")

    def extract_block_label(self, input_text: str) -> str:
        """Extract block label from input text"""
        input_lower = input_text.lower()

        for label in ["identity", "human", "task", "learnings"]:
            if label in input_lower:
                return label

        # Default to task
        return "task"

    def grade_output(self, output: str, ground_truth: str, input_text: str) -> float:
        """
        Grade the output against ground truth.

        Returns score from 0.0 to 1.0
        """
        block_label = self.extract_block_label(input_text)

        # Get actual block value from database directly
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT value, char_limit FROM memory_blocks
            WHERE agent_id = ? AND label = ?
        ''', (self.agent_id, block_label))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return 0.0

        actual_value, char_limit = row

        # Check if ground truth is in actual value
        if ground_truth in actual_value:
            # Check char limit
            if len(actual_value) > char_limit:
                return 0.8  # Content correct but exceeded limit
            return 1.0  # Perfect

        # Check case-insensitive
        if ground_truth.lower() in actual_value.lower():
            return 0.7  # Case mismatch

        # Partial match
        if any(word in actual_value for word in ground_truth.split()):
            return 0.5  # Partial match

        return 0.0  # No match

    def generate_report(self, output_dir: Path):
        """Generate evaluation report"""
        output_dir.mkdir(parents=True, exist_ok=True)

        # Calculate statistics
        total_samples = len(self.results)
        passed = sum(1 for r in self.results if r["score"] >= 0.7)
        avg_score = sum(r["score"] for r in self.results) / total_samples if total_samples > 0 else 0.0

        gate_passed = avg_score >= 0.7

        summary = {
            "suite_name": "memory_quality_standalone",
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
        print("EVALUATION SUMMARY")
        print(f"{'='*80}")
        print(f"Total Samples: {total_samples}")
        print(f"Passed: {passed} ({passed/total_samples*100:.1f}%)")
        print(f"Failed: {total_samples - passed}")
        print(f"Average Score: {avg_score:.2%}")
        print(f"Gate Status: {'✅ PASSED' if gate_passed else '❌ FAILED'} (threshold: 70%)")
        print(f"\nResults saved to: {output_dir}")

        return summary


def main():
    """Run standalone evaluation"""
    print("="*80)
    print("ENHANCED MEMORY MCP - STANDALONE EVALUATION")
    print("="*80)

    # Initialize evaluator
    evaluator = MemoryEvaluator(agent_id="test_agent")

    # Setup test agent
    print("\nSetting up test agent...")
    evaluator.setup_agent()

    # Run evaluation
    dataset_path = Path(__file__).parent / "datasets" / "memory_ops.jsonl"
    print(f"\nRunning evaluation on: {dataset_path}")
    evaluator.run_eval_dataset(dataset_path)

    # Generate report
    output_dir = Path(__file__).parent / "results" / f"standalone_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    summary = evaluator.generate_report(output_dir)

    # Exit with appropriate code
    sys.exit(0 if summary["gate_passed"] else 1)


if __name__ == "__main__":
    main()
