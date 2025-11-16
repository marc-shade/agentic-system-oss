#!/usr/bin/env python3
"""
Claude Agent - Intelligent agent powered by Anthropic Claude SDK
Replaces dumb polling scripts with AI-powered reasoning

Integrated with Comprehensive Cluster State for full cluster awareness.
Can query all nodes, services, software, network topology in real-time.
"""

import os
import json
import asyncio
import sys
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from anthropic import Anthropic, AsyncAnthropic

# Add cluster-deployment to path for comprehensive state access
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "cluster-deployment"))

try:
    from comprehensive_cluster_state import ComprehensiveClusterState, get_complete_state
    from cluster_state_aggregator import ClusterStateAggregator
    CLUSTER_STATE_AVAILABLE = True
except ImportError:
    CLUSTER_STATE_AVAILABLE = False


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


class ClaudeAgent:
    """
    Production-ready intelligent agent using Anthropic Claude SDK

    This agent REASONS about what to do, when to do it, and how to use its tools.
    It does NOT just poll and trigger tools on a schedule.
    """

    def __init__(
        self,
        purpose: AgentPurpose,
        tools: List[Dict[str, Any]],
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        use_cluster_state: bool = True
    ):
        self.purpose = purpose
        self.tools = tools
        self.model = model
        self.client = AsyncAnthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        self.context_window = []
        self.decision_history = []
        self.running = False
        self.iteration_count = 0

        # Initialize cluster state access
        self.cluster_state = None
        self.cluster_aggregator = None
        if use_cluster_state and CLUSTER_STATE_AVAILABLE:
            try:
                self.cluster_state = ComprehensiveClusterState()
                self.cluster_aggregator = ClusterStateAggregator()
                print("✅ Cluster state access enabled (local + aggregated)")
            except Exception as e:
                print(f"⚠️  Could not initialize cluster state: {e}")

    async def reason(self, observations: Dict[str, Any]) -> AgentDecision:
        """
        Use Claude to reason about current observations and decide what to do

        This is the KEY difference from dumb scripts:
        - Script: if time % 60 == 0: check_status()
        - Agent: Look at situation, reason about what's important, decide what to do
        """
        system_prompt = self.get_system_prompt()
        user_message = self._format_observations_prompt(observations)

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ],
                tools=self.tools if self.tools else None
            )

            # Extract decision from Claude's response
            decision_text = ""
            reasoning_text = ""
            tool_used = None
            confidence = 0.7  # Default confidence

            for block in response.content:
                if hasattr(block, 'text'):
                    decision_text += block.text
                elif block.type == 'tool_use':
                    tool_used = block.name
                    reasoning_text = f"Using tool: {block.name}"

            # Parse decision and reasoning from response
            lines = decision_text.strip().split('\n')
            if len(lines) > 0:
                decision = lines[0]
                reasoning = ' '.join(lines[1:]) if len(lines) > 1 else decision_text
            else:
                decision = "No action needed"
                reasoning = "System appears stable"

            # Estimate confidence from response
            if "critical" in decision.lower() or "urgent" in decision.lower():
                confidence = 0.95
            elif "warning" in decision.lower():
                confidence = 0.85
            elif "monitor" in decision.lower():
                confidence = 0.75
            else:
                confidence = 0.6

            return AgentDecision(
                timestamp=datetime.now().isoformat(),
                decision=decision,
                reasoning=reasoning if reasoning else reasoning_text,
                confidence=confidence,
                action_taken=decision if tool_used else None,
                tool_used=tool_used
            )

        except Exception as e:
            print(f"Error in reasoning: {e}")
            return AgentDecision(
                timestamp=datetime.now().isoformat(),
                decision="Error occurred, monitoring",
                reasoning=f"Failed to reason: {str(e)}",
                confidence=0.3,
                action_taken=None,
                tool_used=None
            )

    def get_system_prompt(self) -> str:
        """Generate system prompt for Claude"""
        criteria_str = '\n'.join([f"- {c}" for c in self.purpose.decision_criteria])

        return f"""You are {self.purpose.name}, an intelligent monitoring agent.

Purpose: {self.purpose.description}
Primary Goal: {self.purpose.primary_goal}

Your Decision Criteria:
{criteria_str}

You are NOT a dumb script that just checks things on a schedule.
You REASON about what's important RIGHT NOW based on observations.

For each observation set, decide:
1. What is the current priority? (critical/warning/monitor/stable)
2. What action should be taken? (specific action or "continue monitoring")
3. Why is this the right decision? (your reasoning)

Respond with your decision on the first line, followed by your reasoning."""

    def _format_observations_prompt(self, observations: Dict[str, Any]) -> str:
        """Format observations into a prompt for Claude"""
        obs_lines = []
        for key, value in observations.items():
            if isinstance(value, dict):
                obs_lines.append(f"{key}:")
                for k, v in value.items():
                    obs_lines.append(f"  {k}: {v}")
            else:
                obs_lines.append(f"{key}: {value}")

        obs_str = '\n'.join(obs_lines)
        return f"""Current Observations (Iteration #{self.iteration_count}):

{obs_str}

Based on these observations, what should I do right now? Consider:
- Is anything critical that needs immediate attention?
- Are there warnings that should be monitored?
- Is the system stable and healthy?
- What is the most important thing to focus on?

Decide what action to take (if any) and explain your reasoning."""

    async def execute_decision(self, decision: AgentDecision) -> Dict[str, Any]:
        """Execute the action decided upon"""
        print(f"\n⚡ Decision: {decision.decision}")
        print(f"   Reasoning: {decision.reasoning}")
        print(f"   Confidence: {decision.confidence:.2f}")

        if decision.tool_used:
            print(f"   Tool: {decision.tool_used}")
            return {"status": "tool_executed", "tool": decision.tool_used}
        else:
            return {"status": "monitoring", "action": decision.action_taken}

    async def gather_observations(self) -> Dict[str, Any]:
        """
        Gather observations - subclasses override this
        Default implementation provides basic system info
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "iteration": self.iteration_count,
            "decision_history_size": len(self.decision_history),
            "context_window_size": len(self.context_window)
        }

    def add_to_context(self, event: Dict[str, Any]):
        """Add an event to the agent's context window"""
        self.context_window.append({
            "timestamp": datetime.now().isoformat(),
            "event": event
        })

        if len(self.context_window) > 100:
            self.context_window = self.context_window[-100:]

    def log_decision(self, decision: AgentDecision):
        """Log a decision for learning and debugging"""
        self.decision_history.append(decision)

        if len(self.decision_history) > 1000:
            self._persist_old_decisions()
            self.decision_history = self.decision_history[-100:]

    def _persist_old_decisions(self):
        """Persist old decisions to disk for analysis"""
        filename = f"/tmp/{self.purpose.name}_decisions.jsonl"
        try:
            with open(filename, 'a') as f:
                for decision in self.decision_history[:-100]:
                    f.write(json.dumps({
                        "timestamp": decision.timestamp,
                        "decision": decision.decision,
                        "reasoning": decision.reasoning,
                        "confidence": decision.confidence,
                        "action_taken": decision.action_taken,
                        "tool_used": decision.tool_used
                    }) + "\n")
        except Exception as e:
            print(f"Warning: Failed to persist decisions: {e}")

    def calculate_next_interval(
        self,
        decision: AgentDecision,
        default_interval: int
    ) -> int:
        """
        Intelligently adjust check interval based on decision

        High urgency = check more frequently
        Low urgency = check less frequently
        """
        if "critical" in decision.decision.lower() or "urgent" in decision.decision.lower():
            return max(5, default_interval // 4)
        elif "warning" in decision.decision.lower():
            return max(15, default_interval // 2)
        elif "healthy" in decision.decision.lower() or "stable" in decision.decision.lower():
            return min(300, default_interval * 2)
        else:
            return default_interval

    async def run_loop(self, interval_seconds: int = 60):
        """
        Main agent loop with intelligent decision-making
        """
        self.running = True
        print(f"🤖 {self.purpose.name} starting...")
        print(f"   Purpose: {self.purpose.description}")
        print(f"   Model: {self.model}")
        print(f"   Tools: {len(self.tools)} available")
        print()

        while self.running:
            try:
                self.iteration_count += 1

                # Gather observations
                observations = await self.gather_observations()

                # REASON about what to do (this is the key difference!)
                decision = await self.reason(observations)
                self.log_decision(decision)

                # Execute decision
                if decision.action_taken:
                    result = await self.execute_decision(decision)
                    self.add_to_context({
                        "type": "action_result",
                        "decision": decision.decision,
                        "result": result
                    })

                # Intelligent interval adjustment
                next_interval = self.calculate_next_interval(decision, interval_seconds)
                await asyncio.sleep(next_interval)

            except KeyboardInterrupt:
                print(f"\n🛑 {self.purpose.name} shutting down gracefully...")
                self.running = False
                break
            except Exception as e:
                print(f"❌ Error in {self.purpose.name}: {e}")
                self.add_to_context({
                    "type": "error",
                    "error": str(e)
                })
                await asyncio.sleep(interval_seconds * 2)

    def stop(self):
        """Stop the agent gracefully"""
        self.running = False

    # === Cluster State Query Methods ===

    def get_cluster_state(self) -> Dict[str, Any]:
        """
        Get complete cluster state from all nodes

        Uses cluster state aggregator to query all reachable nodes
        and merge into unified view.
        """
        if not self.cluster_aggregator:
            return {"error": "Cluster state aggregator not available"}

        try:
            return self.cluster_aggregator.get_unified_cluster_state()
        except Exception as e:
            print(f"❌ Failed to get aggregated cluster state: {e}")
            return {"error": str(e)}

    def query_services(self, service_name: str = None, port: int = None,
                       node_id: str = None) -> List[Dict]:
        """Query services across cluster"""
        if not self.cluster_state:
            return []

        try:
            return self.cluster_state.query_services(
                service_name=service_name,
                port=port,
                node_id=node_id
            )
        except Exception as e:
            print(f"❌ Failed to query services: {e}")
            return []

    def query_software(self, package_name: str = None,
                       package_type: str = None,
                       node_id: str = None) -> List[Dict]:
        """Query installed software across cluster"""
        if not self.cluster_state:
            return []

        try:
            return self.cluster_state.query_software(
                package_name=package_name,
                package_type=package_type,
                node_id=node_id
            )
        except Exception as e:
            print(f"❌ Failed to query software: {e}")
            return []

    def get_network_topology(self) -> Dict[str, Any]:
        """Get complete network topology"""
        if not self.cluster_state:
            return {}

        try:
            return self.cluster_state.get_network_map()
        except Exception as e:
            print(f"❌ Failed to get network topology: {e}")
            return {}

    async def orchestrate_cluster_task(self, task_description: str) -> Dict[str, Any]:
        """
        Orchestrate a task across the cluster

        Uses Claude's reasoning to decide:
        - Which nodes should execute the task
        - In what order
        - With what parameters

        This is what Claude Code sessions will use for cluster-aware decisions
        """
        if not self.cluster_state:
            return {"error": "Cluster state not available"}

        try:
            # Get complete cluster state
            cluster = self.cluster_state.get_complete_cluster_state()

            # Build orchestration prompt
            prompt = f"""You are orchestrating a distributed task across a cluster.

Task: {task_description}

Available nodes and their capabilities:
{json.dumps(cluster, indent=2)}

Decide:
1. Which node(s) should execute this task?
2. In what order?
3. What are the parameters for each?
4. What could go wrong and how to mitigate?

Respond in JSON format with your orchestration plan.
"""

            response = await self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )

            # Extract orchestration plan
            plan_text = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    plan_text += block.text

            return {
                "task": task_description,
                "plan": plan_text,
                "cluster_state": cluster
            }

        except Exception as e:
            print(f"❌ Cluster orchestration failed: {e}")
            return {"error": str(e)}
