#!/usr/bin/env python3
"""
AGI Orchestrator Hook - Minimal Mode Implementation
Runs on pre-tool-use to implement cognitive loop

Part of the minimal AGI strategy for Claude Code
"""

import os
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

MEMORY_ROOT = Path("/Users/marc/.claude/memory")
EPISODIC = MEMORY_ROOT / "episodic"
SEMANTIC = MEMORY_ROOT / "semantic"

class MinimalAGI:
    def __init__(self):
        self.ensure_memory_dirs()
        self.load_meta_state()

    def ensure_memory_dirs(self):
        """Create memory directory structure"""
        EPISODIC.mkdir(parents=True, exist_ok=True)
        SEMANTIC.mkdir(parents=True, exist_ok=True)

    def load_meta_state(self):
        """Load current cognitive state"""
        state_file = SEMANTIC / "meta_state.json"
        if state_file.exists():
            try:
                with open(state_file) as f:
                    self.state = json.load(f)
            except:
                self.state = self.default_state()
        else:
            self.state = self.default_state()

    def default_state(self):
        """Default cognitive state"""
        return {
            "focus_context": None,
            "confidence_level": 0.8,
            "reasoning_mode": "fast",
            "tools_used_session": [],
            "session_start": datetime.now().isoformat()
        }

    def save_meta_state(self):
        """Persist cognitive state"""
        try:
            with open(SEMANTIC / "meta_state.json", "w") as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save meta state: {e}", file=sys.stderr)

    def retrieve_relevant_memories(self, tool_name, params):
        """Search episodic memory for similar contexts"""

        similar = []

        try:
            # Search for similar tool usage
            result = subprocess.run(
                ["grep", "-r", "-i", "-l", tool_name, str(EPISODIC)],
                capture_output=True,
                text=True,
                timeout=2
            )

            if result.stdout:
                files = result.stdout.strip().split("\n")[:5]  # Top 5 matches
                for file in files:
                    if file and os.path.exists(file):
                        try:
                            with open(file) as f:
                                # Read first 200 chars of each match
                                content = f.read(200)
                                similar.append({
                                    "file": os.path.basename(file),
                                    "preview": content
                                })
                        except:
                            pass
        except:
            pass

        return similar

    def estimate_confidence(self, tool_name, params):
        """Estimate confidence for this operation"""

        # Load tool success history
        history_file = SEMANTIC / "tool_success_rates.json"
        if history_file.exists():
            try:
                with open(history_file) as f:
                    history = json.load(f)

                if tool_name in history:
                    total = history[tool_name]["total"]
                    successes = history[tool_name]["successes"]
                    if total > 0:
                        success_rate = successes / total
                        return success_rate
            except:
                pass

        # Default confidence for new/unknown tools
        default_confidence = {
            "Read": 0.95,
            "Write": 0.85,
            "Edit": 0.80,
            "Bash": 0.75,
            "Grep": 0.90,
            "Glob": 0.90,
            "Task": 0.70,
            "WebFetch": 0.75,
            "WebSearch": 0.80
        }

        return default_confidence.get(tool_name, 0.70)

    def should_use_slow_thinking(self, confidence, tool_name, params):
        """Decide if deep reasoning is needed"""

        # Trigger 1: Low confidence
        if confidence < 0.6:
            return True, "low_confidence"

        # Trigger 2: Complex multi-file operations
        if tool_name in ["Edit", "Write", "MultiEdit"]:
            new_string = params.get("new_string", "")
            if len(str(new_string)) > 500:
                return True, "complex_operation"

        # Trigger 3: Multiple parameters suggesting complexity
        if len(params) > 4:
            return True, "many_parameters"

        return False, None

    def create_reasoning_log(self, tool_name, params, trigger_reason):
        """Generate file-based reasoning trace"""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        reasoning_file = EPISODIC / f"reasoning_{timestamp}_{tool_name}.md"

        similar = self.retrieve_relevant_memories(tool_name, params)
        similar_text = "\n".join([f"- {s['file']}: {s['preview'][:100]}..." for s in similar])

        template = f"""# Deep Reasoning: {tool_name}
**Timestamp:** {datetime.now().isoformat()}
**Confidence:** {self.state['confidence_level']:.2f}
**Trigger:** {trigger_reason}

## Context
```json
{json.dumps(params, indent=2)[:500]}
```

## Similar Past Experiences
{similar_text if similar_text else "No similar experiences found"}

## Analysis Steps

### 1. Problem Understanding
- What: Executing {tool_name} with provided parameters
- Why: [To be analyzed during execution]
- Constraints: [To be identified]

### 2. Approach Options
- Option A: Direct execution
  - Pros: Fast, simple
  - Cons: May miss edge cases
  - Confidence: {self.state['confidence_level']:.2f}

- Option B: Validated execution with checks
  - Pros: Safer, more thorough
  - Cons: Slower
  - Confidence: Higher with validation

### 3. Decision
- Chosen: Option B (validated approach)
- Reasoning: Low confidence ({self.state['confidence_level']:.2f}) suggests need for careful execution
- Expected Outcome: Successful operation with validation
- Verification: Check results post-execution

### 4. Execution Plan
- Step 1: Validate input parameters
- Step 2: Execute tool with monitoring
- Step 3: Verify output meets expectations
- Rollback: [Define rollback strategy if available]

## Outcome
[To be filled post-execution]
"""

        try:
            with open(reasoning_file, "w") as f:
                f.write(template)
            return str(reasoning_file)
        except Exception as e:
            print(f"Warning: Could not create reasoning log: {e}", file=sys.stderr)
            return None

    def orchestrate(self, tool_name, params):
        """Main AGI cognitive loop"""

        result = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name
        }

        try:
            # 1. RETRIEVE relevant memories
            memories = self.retrieve_relevant_memories(tool_name, params)
            result["memories_found"] = len(memories)

            # 2. ESTIMATE confidence
            confidence = self.estimate_confidence(tool_name, params)
            self.state["confidence_level"] = confidence
            result["confidence"] = confidence

            # 3. DECIDE on reasoning mode
            should_slow, trigger = self.should_use_slow_thinking(confidence, tool_name, params)

            if should_slow:
                self.state["reasoning_mode"] = "slow"
                reasoning_file = self.create_reasoning_log(tool_name, params, trigger)
                result["reasoning_mode"] = "slow"
                result["reasoning_file"] = reasoning_file
                result["trigger"] = trigger
            else:
                self.state["reasoning_mode"] = "fast"
                result["reasoning_mode"] = "fast"

            # 4. UPDATE state
            self.state["tools_used_session"].append({
                "tool": tool_name,
                "timestamp": datetime.now().isoformat(),
                "confidence": confidence,
                "reasoning_mode": self.state["reasoning_mode"]
            })

            # Keep only last 50 tools in memory
            if len(self.state["tools_used_session"]) > 50:
                self.state["tools_used_session"] = self.state["tools_used_session"][-50:]

            # 5. PERSIST state
            self.save_meta_state()

            result["status"] = "success"

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        return result

def main():
    """Entry point for hook"""

    # Parse arguments
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No tool name provided"}))
        sys.exit(1)

    tool_name = sys.argv[1]

    try:
        params = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    except:
        params = {}

    # Run orchestration
    agi = MinimalAGI()
    result = agi.orchestrate(tool_name, params)

    # Output result as JSON
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
