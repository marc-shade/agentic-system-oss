#!/usr/bin/env python3
"""
Code Evolution Protector - Evolution-aware protection agent
Understands when changes are intentional improvements vs bugs

KEY INNOVATION: This agent prevents protection systems from reverting
progress when the system is intentionally evolving.

Example: When migrating from dumb scripts to AI agents, traditional
protection would see "new AI SDK imports" and revert them as "unexpected changes".
This agent understands that's EVOLUTION, not a bug.
"""

import os
import sys
import json
import datetime
from datetime import datetime as dt_now
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "sdk_agents"))
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))

from cli_agent import CLIAgent, AgentPurpose
from agent_memory import AgentMemory


class CodeEvolutionProtector(CLIAgent):
    """
    Intelligent protection agent that understands intentional evolution

    Traditional Protection Agent Says:
    "New import detected! Reverting to last known good state!"

    Evolution-Aware Protection Agent Says:
    "New import detected. Checking if this is part of Script→AI Agent migration...
    Yes, it matches expected evolution pattern. ALLOWING change."
    """

    def __init__(self, evolution_config_path: str):
        # Define what this agent is for
        purpose = AgentPurpose(
            name="Code Evolution Protector",
            description="Protects system while understanding intentional evolution",
            primary_goal="Distinguish bugs from evolution, prevent regressive changes",
            decision_criteria=[
                "Check if change matches known evolution phase",
                "Detect actual bugs vs intentional improvements",
                "Allow progress, block regressions",
                "Learn from evolution history",
                "Provide context-aware protection"
            ],
            tools_needed=["codex_cli", "enhanced_memory", "git"]
        )

        # Initialize CLI agent (uses codex CLI - no API key needed)
        super().__init__(
            purpose=purpose,
            tools=self._get_tool_definitions(),
            cli_tool="codex"
        )

        # Load evolution context
        self.evolution_config_path = evolution_config_path
        self.evolution_phases = self._load_evolution_phases()
        self.current_phase = self._detect_current_phase()

        # Memory integration - Remember code changes and evolution patterns
        self.memory = AgentMemory("code_evolution_protector")
        print(f"Memory enabled: {self.memory.is_enabled()}")

    def _get_tool_definitions(self) -> list:
        """Define tools this agent can use"""
        return [
            {
                "name": "analyze_code_change",
                "description": "Analyze a code change to determine if it's evolution or bug",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "change_description": {"type": "string"},
                        "change_type": {"type": "string", "enum": ["addition", "deletion", "modification"]}
                    },
                    "required": ["file_path", "change_description"]
                }
            },
            {
                "name": "check_evolution_context",
                "description": "Check if a change matches current evolution phase",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "change_patterns": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "required": ["change_patterns"]
                }
            },
            {
                "name": "run_security_check",
                "description": "Run security analysis on code change",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"}
                    },
                    "required": ["file_path"]
                }
            }
        ]

    def _load_evolution_phases(self) -> List[Dict[str, Any]]:
        """Load evolution phases from configuration"""
        if os.path.exists(self.evolution_config_path):
            try:
                with open(self.evolution_config_path, 'r') as f:
                    config = json.load(f)
                    return config.get("phases", [])
            except Exception as e:
                print(f"Warning: Failed to load evolution phases: {e}")

        # Return default current phase if config doesn't exist
        return [{
            "name": "Script to AI Agent Migration",
            "start_date": datetime.datetime.now().isoformat(),
            "status": "active",
            "description": "Converting dumb polling scripts to intelligent AI agents",
            "expected_changes": [
                "New intelligent-agents directory structure",
                "Import anthropic SDK",
                "Import openai SDK",
                "Import google.generativeai SDK",
                "New async def reason() methods",
                "New AgentPurpose classes",
                "New AgentDecision dataclasses",
                "Replacement of polling loops with reasoning loops"
            ],
            "allow_patterns": [
                "from anthropic import",
                "from openai import",
                "import google.generativeai",
                "async def reason(",
                "class.*Agent.*:",
                "@dataclass",
                "AgentPurpose",
                "AgentDecision",
                "await.*reason(",
                "intelligent-agents/"
            ],
            "block_patterns": [
                "eval(",
                "exec(",
                "os.system(",
                "subprocess.call.*shell=True",
                "__import__",
                "pickle.loads"
            ]
        }]

    def _detect_current_phase(self) -> Optional[Dict[str, Any]]:
        """Detect which evolution phase we're currently in"""
        now = datetime.datetime.now()

        for phase in self.evolution_phases:
            start_date = datetime.datetime.fromisoformat(phase.get("start_date", "2025-01-01"))
            end_date = phase.get("end_date")

            if end_date:
                end_date = datetime.datetime.fromisoformat(end_date)
                if start_date <= now <= end_date:
                    return phase
            else:
                # Phase with no end date is considered active if started
                if start_date <= now and phase.get("status") == "active":
                    return phase

        return None

    def gather_observations(self) -> Dict[str, Any]:
        """
        Gather observations about code changes

        This agent monitors:
        - New files created
        - Imports added/changed
        - Function signatures changed
        - Security-critical changes
        """
        observations = {
            "timestamp": datetime.datetime.now().isoformat(),
            "iteration": self.iteration_count,
            "current_phase": self.current_phase.get("name") if self.current_phase else None,
            "phase_status": self.current_phase.get("status") if self.current_phase else None
        }

        # Check for recent code changes
        try:
            # Use git to detect changes (last commit)
            import subprocess
            result = subprocess.run(
                ['git', 'diff', '--name-status', 'HEAD~1', 'HEAD'],
                capture_output=True,
                text=True,
                cwd="/mnt/agentic-system"
            )

            if result.returncode == 0:
                changes = result.stdout.strip().split('\n')
                observations["recent_changes"] = {
                    "count": len([c for c in changes if c]),
                    "files": changes[:10]  # First 10 changes
                }
        except Exception as e:
            observations["git_error"] = str(e)

        # Check memory for similar code evolution patterns
        if self.memory.is_enabled():
            try:
                query_parts = []
                if self.current_phase:
                    query_parts.append(f"phase:{self.current_phase.get('name')}")
                if observations.get("recent_changes", {}).get("count", 0) > 0:
                    query_parts.append("code changes")

                if query_parts:
                    query = " ".join(query_parts)
                    similar_evolutions = self.memory.recall(query, limit=3)
                    if similar_evolutions:
                        observations["similar_past_evolutions"] = len(similar_evolutions)
                        print(f"Found {len(similar_evolutions)} similar past evolutions")
            except Exception as e:
                print(f"Memory recall failed: {e}")

        return observations

    def is_change_allowed(
        self,
        file_path: str,
        change_description: str
    ) -> tuple[bool, str]:
        """
        Determine if a code change should be allowed

        Returns: (allowed, reasoning)

        This is the KEY METHOD that distinguishes this agent from dumb protection
        """
        if not self.current_phase:
            # No active evolution phase - use strict protection
            return self._strict_protection_check(file_path, change_description)

        # Check if change matches evolution phase
        phase_name = self.current_phase.get("name", "Unknown")
        allow_patterns = self.current_phase.get("allow_patterns", [])
        block_patterns = self.current_phase.get("block_patterns", [])

        # Check block patterns first (security-critical)
        for pattern in block_patterns:
            if pattern in change_description:
                return (
                    False,
                    f"BLOCKED: Security concern - matches block pattern '{pattern}'"
                )

        # Check allow patterns (evolution-related)
        for pattern in allow_patterns:
            if pattern in change_description:
                return (
                    True,
                    f"ALLOWED: Matches evolution phase '{phase_name}' - pattern '{pattern}'"
                )

        # Use Codex to make intelligent decision
        prompt = f"""Analyze this code change:

File: {file_path}
Change: {change_description}

Current Evolution Phase: {phase_name}
Phase Description: {self.current_phase.get('description')}

Expected Changes for this Phase:
{json.dumps(self.current_phase.get('expected_changes'), indent=2)}

Question: Is this change part of the intentional evolution, or is it a bug/problem?

Consider:
1. Does it match the expected changes for this phase?
2. Does it improve the system architecture?
3. Is it adding AI capabilities as intended?
4. Or is it a mistake/bug/security issue?

Respond with ALLOW or BLOCK followed by your reasoning."""

        try:
            # Use Codex CLI for analysis
            result = self.run_headless_codex(prompt, format="text")

            if result.get("status") == "success":
                response = result.get("output", "")
                if "ALLOW" in response.upper():
                    return (True, response)
                else:
                    return (False, response)

        except Exception as e:
            print(f"Warning: Codex analysis failed: {e}")

        # Default to cautious approval if analysis fails but matches patterns
        return (False, "Uncertain - requires manual review")

    def _strict_protection_check(
        self,
        file_path: str,
        change_description: str
    ) -> tuple[bool, str]:
        """
        Strict protection when no evolution phase is active

        This is traditional protection behavior
        """
        # Run security checks
        dangerous_patterns = [
            "eval(",
            "exec(",
            "os.system(",
            "subprocess.*shell=True",
            "__import__",
            "pickle.loads"
        ]

        for pattern in dangerous_patterns:
            if pattern in change_description:
                return (
                    False,
                    f"BLOCKED: Security concern - dangerous pattern '{pattern}'"
                )

        # Allow safe changes
        return (True, "No active evolution phase, but change appears safe")

    def execute_decision(self, decision: Any, observations: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute protection decision"""
        print(f"\n🛡️  Protection Decision: {decision.decision}")
        print(f"   Reasoning: {decision.reasoning}")
        print(f"   Confidence: {decision.confidence:.2f}")

        result = {}
        if "BLOCKED" in decision.decision.upper():
            print(f"   ❌ CHANGE BLOCKED")
            result = {"status": "blocked", "reason": decision.reasoning}
        elif "ALLOWED" in decision.decision.upper():
            print(f"   ✅ CHANGE ALLOWED (Evolution-aware)")
            result = {"status": "allowed", "reason": decision.reasoning}
        else:
            print(f"   ⚠️  REQUIRES REVIEW")
            result = {"status": "review_required", "reason": decision.reasoning}

        # Store decision and outcome in memory for learning
        if self.memory.is_enabled() and observations:
            try:
                self.memory.remember({
                    "type": "code_protection",
                    "decision": decision.decision,
                    "confidence": decision.confidence,
                    "status": result["status"],
                    "current_phase": observations.get("current_phase", "none"),
                    "changes_count": observations.get("recent_changes", {}).get("count", 0),
                    "phase_status": observations.get("phase_status", "none")
                })
            except Exception as mem_error:
                print(f"Memory storage failed: {mem_error}")

        return result

    def start(self, check_interval: int = 120):
        """
        Start the evolution-aware protection agent

        Default: Check every 2 minutes for code changes
        """
        print("=" * 60)
        print("🛡️  Code Evolution Protector Starting 🛡️")
        print("=" * 60)
        print(f"CLI Tool: {self.cli_tool}")
        print(f"Current Phase: {self.current_phase.get('name') if self.current_phase else 'None'}")
        print(f"Check interval: {check_interval}s")
        print()
        print("Key Capability: Distinguishes evolution from bugs")
        print("  ✅ Allows: AI SDK imports, agent reasoning loops")
        print("  ❌ Blocks: Security issues, actual bugs")
        print()

        # Run the intelligent protection loop
        self.run_loop(interval_seconds=check_interval)

        return 0


def main():
    """Main entry point"""
    # NOTE: Codex CLI manages its own API keys, no OPENAI_API_KEY needed here

    # Evolution configuration
    evolution_config = "/mnt/agentic-system/config/evolution_phases.json"

    # Create and start the protection agent
    protector = CodeEvolutionProtector(evolution_config)
    protector.start(check_interval=120)


if __name__ == "__main__":
    main()
