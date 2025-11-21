#!/usr/bin/env python3
"""
CLI Agent - Intelligent agent using CLI tools (codex, claude, gemini)
No API keys required - uses installed CLI tools
"""

import subprocess
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class AgentPurpose:
    """Defines what an agent is for"""
    name: str
    description: str
    primary_goal: str
    decision_criteria: List[str]
    tools_needed: List[str]


@dataclass
class AgentDecision:
    """A decision made by an agent"""
    timestamp: str
    decision: str
    reasoning: str
    confidence: float
    action_taken: Optional[str]
    tool_used: Optional[str]


class CLIAgent:
    """
    Production-ready intelligent agent using CLI tools (codex/claude/gemini)

    Benefits:
    - No API keys needed
    - Uses installed CLI tools
    - Simpler deployment
    - Same reasoning capabilities
    """

    def __init__(
        self,
        purpose: AgentPurpose,
        tools: List[Dict[str, Any]],
        cli_tool: str = "codex"  # codex, claude, or gemini
    ):
        self.purpose = purpose
        self.tools = tools
        self.cli_tool = cli_tool
        self.context_window = []
        self.decision_history = []
        self.running = False
        self.iteration_count = 0

    def reason(self, observations: Dict[str, Any]) -> AgentDecision:
        """
        Use CLI tool to reason about current observations

        This shells out to codex/claude/gemini instead of using SDK
        """
        system_prompt = self.get_system_prompt()
        user_message = self._format_observations_prompt(observations)

        try:
            # Build CLI command
            full_prompt = f"{system_prompt}\n\n{user_message}"

            # Execute CLI tool
            result = subprocess.run(
                [self.cli_tool, "exec", "--skip-git-repo-check", "--json", full_prompt],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                decision_text = result.stdout.strip()

                # Parse JSON output from codex CLI
                try:
                    agent_message = None
                    reasoning_text = None

                    for line in decision_text.split('\n'):
                        if not line.strip():
                            continue
                        event = json.loads(line)
                        if event.get("type") == "item.completed":
                            item = event.get("item", {})
                            if item.get("type") == "agent_message":
                                agent_message = item.get("text", "")
                            elif item.get("type") == "reasoning":
                                reasoning_text = item.get("text", "")

                    if agent_message:
                        decision = agent_message
                        reasoning = reasoning_text or agent_message
                    else:
                        # Fallback to plain text parsing
                        lines = decision_text.split('\n')
                        decision = lines[0] if lines else "Continue monitoring"
                        reasoning = ' '.join(lines[1:]) if len(lines) > 1 else decision_text
                except json.JSONDecodeError:
                    # Fallback to plain text parsing
                    lines = decision_text.split('\n')
                    decision = lines[0] if lines else "Continue monitoring"
                    reasoning = ' '.join(lines[1:]) if len(lines) > 1 else decision_text

                # Parse tool usage from decision text
                tool_used = None
                for tool in self.tools:
                    tool_name = tool['name']
                    if tool_name in decision.lower():
                        tool_used = tool_name
                        break

                agent_decision = AgentDecision(
                    timestamp=datetime.now().isoformat(),
                    decision=decision,
                    reasoning=reasoning,
                    confidence=0.7,
                    action_taken=None,
                    tool_used=tool_used
                )

                self.decision_history.append(agent_decision)
                return agent_decision
            else:
                # CLI tool failed, return safe default
                return AgentDecision(
                    timestamp=datetime.now().isoformat(),
                    decision="Continue monitoring (CLI error)",
                    reasoning=f"CLI tool error: {result.stderr}",
                    confidence=0.3,
                    action_taken=None,
                    tool_used=None
                )

        except subprocess.TimeoutExpired:
            return AgentDecision(
                timestamp=datetime.now().isoformat(),
                decision="Continue monitoring (timeout)",
                reasoning="CLI tool timed out after 30 seconds",
                confidence=0.3,
                action_taken=None,
                tool_used=None
            )
        except Exception as e:
            return AgentDecision(
                timestamp=datetime.now().isoformat(),
                decision="Continue monitoring (error)",
                reasoning=f"Error: {str(e)}",
                confidence=0.3,
                action_taken=None,
                tool_used=None
            )

    def get_system_prompt(self) -> str:
        """Generate system prompt defining agent's role"""
        criteria_text = "\n".join(f"  - {c}" for c in self.purpose.decision_criteria)

        # Include tool definitions so CLI knows what actions it can take
        tools_text = ""
        if self.tools:
            tools_text = "\n\nAvailable Tools (you can use these to take action):\n"
            for tool in self.tools:
                tools_text += f"\n  • {tool['name']}: {tool['description']}"
                if 'input_schema' in tool:
                    props = tool['input_schema'].get('properties', {})
                    if props:
                        tools_text += f"\n    Parameters: {', '.join(props.keys())}"

        return f"""You are {self.purpose.name}.

Purpose: {self.purpose.description}
Primary Goal: {self.purpose.primary_goal}

Decision Criteria:
{criteria_text}{tools_text}

IMPORTANT: When you detect a problem that can be fixed with one of the available tools,
use that tool by stating the tool name and parameters in your decision.

For example:
- If a service is down: "restart_service: temporal - Service detected as down"
- If a service is crash-looping: "investigate_root_cause: temporal - Too many crashes"

Respond with a brief decision (one line) followed by your reasoning.
Be concise and actionable."""

    def _format_observations_prompt(self, observations: Dict[str, Any]) -> str:
        """Format observations into a prompt"""
        obs_text = json.dumps(observations, indent=2)

        return f"""Current System Observations:
{obs_text}

Based on these observations, what should be done? Provide:
1. A brief decision (one line)
2. Your reasoning

Keep response concise and actionable."""

    def run_loop(self, interval_seconds: int = 30):
        """Run agent reasoning loop (synchronous version)"""
        import time

        self.running = True
        print(f"🤖 {self.purpose.name} starting...")
        print(f"   Using CLI tool: {self.cli_tool}")

        while self.running:
            try:
                # Gather observations (implemented by subclass)
                if hasattr(self, 'gather_observations'):
                    observations = self.gather_observations()
                else:
                    observations = {"iteration": self.iteration_count}

                # Reason about observations
                decision = self.reason(observations)

                print(f"\n🧠 Decision: {decision.decision}")
                print(f"   Reasoning: {decision.reasoning[:100]}...")

                # Execute decision (implemented by subclass)
                if hasattr(self, 'execute_decision'):
                    self.execute_decision(decision, observations)

                self.iteration_count += 1
                time.sleep(interval_seconds)

            except KeyboardInterrupt:
                print(f"\n⏹️  {self.purpose.name} stopping...")
                self.running = False
                break
            except Exception as e:
                print(f"❌ Error in agent loop: {e}")
                time.sleep(interval_seconds)
