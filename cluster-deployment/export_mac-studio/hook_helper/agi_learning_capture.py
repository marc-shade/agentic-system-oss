#!/usr/bin/env python3
"""
AGI Learning Capture Hook - Post-Tool-Use
Captures outcomes for continuous learning

Part of minimal AGI system
"""

import os
import json
import sys
from datetime import datetime
from pathlib import Path

MEMORY_ROOT = Path("/Users/marc/.claude/memory")
EPISODIC = MEMORY_ROOT / "episodic"
SEMANTIC = MEMORY_ROOT / "semantic"

class LearningCapture:
    def __init__(self):
        self.ensure_dirs()

    def ensure_dirs(self):
        """Ensure memory directories exist"""
        EPISODIC.mkdir(parents=True, exist_ok=True)
        SEMANTIC.mkdir(parents=True, exist_ok=True)

    def capture_learning(self, tool_name, params, outcome):
        """Capture learning from tool execution"""

        today = datetime.now().strftime("%Y-%m-%d")
        learning_log = EPISODIC / f"learnings_{today}.jsonl"

        # Extract outcome details
        success = outcome.get("success", True)
        duration_ms = outcome.get("duration_ms", 0)
        errors = outcome.get("error") or outcome.get("errors")

        # Create learning entry
        entry = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "params_hash": hash(str(sorted(params.items()))),
            "success": success,
            "duration_ms": duration_ms,
            "learnings": self.extract_learnings(outcome),
            "errors": errors
        }

        # Append to daily log
        try:
            with open(learning_log, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            print(f"Warning: Could not write learning log: {e}", file=sys.stderr)

        # If significant learning or failure, also update semantic memory immediately
        if not success or self.is_significant(entry):
            self.update_semantic_immediate(entry)

        return entry

    def extract_learnings(self, outcome):
        """Extract key learnings from outcome"""
        learnings = []

        # Check for specific outcome patterns
        if "output" in outcome:
            output = str(outcome["output"])
            if "error" in output.lower():
                learnings.append("encountered_error")
            if "success" in output.lower():
                learnings.append("successful_operation")
            if len(output) > 1000:
                learnings.append("large_output")

        if outcome.get("duration_ms", 0) > 5000:
            learnings.append("slow_operation")

        return learnings

    def is_significant(self, entry):
        """Determine if this learning is significant enough for immediate semantic update"""

        # Failures are significant
        if not entry["success"]:
            return True

        # Very slow operations are significant
        if entry["duration_ms"] > 10000:
            return True

        # Operations with specific learnings
        if len(entry["learnings"]) > 2:
            return True

        return False

    def update_semantic_immediate(self, entry):
        """Immediately update semantic memory for significant learnings"""

        # Load current tool success rates
        success_file = SEMANTIC / "tool_success_rates.json"
        rates = {}

        if success_file.exists():
            try:
                with open(success_file) as f:
                    rates = json.load(f)
            except:
                pass

        tool = entry["tool"]

        # Initialize if new tool
        if tool not in rates:
            rates[tool] = {"successes": 0, "total": 0}

        # Update counts
        rates[tool]["total"] += 1
        if entry["success"]:
            rates[tool]["successes"] += 1

        # Save updated rates
        try:
            with open(success_file, "w") as f:
                json.dump(rates, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not update success rates: {e}", file=sys.stderr)

def main():
    """Entry point for hook"""

    if len(sys.argv) < 4:
        print(json.dumps({"error": "Insufficient arguments"}))
        sys.exit(1)

    tool_name = sys.argv[1]

    try:
        params = json.loads(sys.argv[2])
    except:
        params = {}

    try:
        outcome = json.loads(sys.argv[3])
    except:
        outcome = {"success": True}

    # Capture learning
    capture = LearningCapture()
    result = capture.capture_learning(tool_name, params, outcome)

    # Output result
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
