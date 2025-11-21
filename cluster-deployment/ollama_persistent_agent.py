#!/usr/bin/env python3
"""
Ollama-Powered Persistent Agent

Uses Ollama Cloud models to provide AI reasoning for background
self-X systems (self-improvement, self-optimization, self-healing).

This is designed to run 24/7 as a lightweight always-on agent that
can make intelligent decisions about cluster management without
expensive API costs.

Features:
- Ollama Cloud model integration (cost-effective)
- JSON-structured reasoning for automation
- Context-aware decision making
- Memory of past actions and outcomes
- Integration with node discovery and improvement systems

Usage:
    # Run as decision-making agent
    agent = OllamaPersistentAgent()
    decision = agent.analyze_cluster_state(inventories)
    improvements = agent.recommend_improvements(gaps)

Models:
    - Default: llama3.2:latest (efficient, capable)
    - Alternative: qwen2.5-coder:latest (code-focused)
    - Alternative: phi4:latest (fast, lightweight)
"""

import os
import json
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass
import time


@dataclass
class AgentDecision:
    """Structured decision from the agent"""
    decision_type: str  # improve, wait, alert, escalate
    reasoning: str
    recommended_actions: List[Dict]
    confidence: float  # 0.0-1.0
    requires_approval: bool


class OllamaPersistentAgent:
    """
    AI agent powered by Ollama for persistent background reasoning
    """

    def __init__(
        self,
        model: str = "llama3.2:latest",
        ollama_host: str = "http://localhost:11434",
        temperature: float = 0.7
    ):
        self.model = model
        self.ollama_host = ollama_host
        self.temperature = temperature

        self.memory = []  # Track past decisions
        self.context = {
            "role": "autonomous_cluster_agent",
            "mission": "maintain and improve cluster health through continuous observation and action"
        }

    def _call_ollama(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Call Ollama API with a prompt

        Returns model response text
        """
        messages = []

        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })

        messages.append({
            "role": "user",
            "content": prompt
        })

        try:
            response = requests.post(
                f"{self.ollama_host}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "temperature": self.temperature
                },
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                return result['message']['content']
            else:
                return f"Error: Ollama API returned {response.status_code}"

        except Exception as e:
            return f"Error calling Ollama: {e}"

    def analyze_cluster_state(self, inventories: Dict) -> AgentDecision:
        """
        Analyze cluster state and decide if action is needed

        Args:
            inventories: Dict of node_id -> NodeInventory

        Returns:
            AgentDecision with recommended actions
        """
        system_prompt = """You are an autonomous cluster management agent.
Your role is to analyze cluster state and recommend improvements.
Always respond in valid JSON format with the following structure:
{
  "decision_type": "improve|wait|alert|escalate",
  "reasoning": "explanation of your analysis",
  "recommended_actions": [
    {"action": "action_name", "target": "what to act on", "priority": 1-10, "rationale": "why"}
  ],
  "confidence": 0.0-1.0,
  "requires_approval": true|false
}
"""

        # Build cluster state summary
        state_summary = {
            "nodes": {},
            "timestamp": time.time()
        }

        for node_id, inv in inventories.items():
            state_summary["nodes"][node_id] = {
                "os": inv.os_type,
                "architecture": inv.architecture,
                "mcp_servers": list(inv.mcp_servers.keys()),
                "pip_packages_count": len(inv.pip_packages),
                "agents": list(inv.intelligent_agents.keys()),
                "workflows": list(inv.workflows.keys()),
                "capabilities": inv.capabilities,
                "git_commit": inv.git_commit[:8] if inv.git_commit else None
            }

        prompt = f"""Analyze this cluster state and recommend improvements:

{json.dumps(state_summary, indent=2)}

Consider:
1. Are all nodes at the same git commit? If not, some may need updates.
2. Do all nodes have similar capabilities? Missing MCP servers or agents should be synced.
3. Are there significant package count differences? May indicate missing dependencies.
4. What would provide the most value to improve cluster-wide?

Provide your analysis as JSON."""

        response_text = self._call_ollama(prompt, system_prompt)

        # Parse JSON response
        try:
            # Extract JSON from response (may have markdown)
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            decision_data = json.loads(response_text)

            decision = AgentDecision(
                decision_type=decision_data.get("decision_type", "wait"),
                reasoning=decision_data.get("reasoning", "No reasoning provided"),
                recommended_actions=decision_data.get("recommended_actions", []),
                confidence=decision_data.get("confidence", 0.5),
                requires_approval=decision_data.get("requires_approval", True)
            )

            # Store in memory
            self.memory.append({
                "timestamp": time.time(),
                "type": "cluster_analysis",
                "decision": decision_data
            })

            return decision

        except Exception as e:
            # Fallback decision if parsing fails
            return AgentDecision(
                decision_type="wait",
                reasoning=f"Failed to parse agent response: {e}",
                recommended_actions=[],
                confidence=0.0,
                requires_approval=True
            )

    def recommend_improvements(self, gaps: Dict, inventories: Dict) -> List[Dict]:
        """
        Use AI to prioritize and recommend specific improvements

        Args:
            gaps: Gap analysis from node discovery
            inventories: Current cluster inventories

        Returns:
            List of recommended improvement actions
        """
        system_prompt = """You are an autonomous cluster improvement agent.
Analyze gaps between nodes and recommend the most valuable improvements.
Respond in JSON format:
{
  "recommendations": [
    {
      "action": "install_mcp_server|sync_code|install_package|update_git",
      "target": "what to install/sync",
      "node": "which node needs it",
      "source_node": "where to get it from (if applicable)",
      "priority": 1-10,
      "rationale": "why this is important",
      "estimated_impact": "expected benefit"
    }
  ]
}
"""

        prompt = f"""Analyze these gaps and recommend improvements:

Gaps:
{json.dumps(gaps, indent=2)}

Cluster State:
{json.dumps({k: {"mcp_servers": list(v.mcp_servers.keys()), "agents": list(v.intelligent_agents.keys())} for k, v in inventories.items()}, indent=2)}

Prioritize improvements that:
1. Give nodes missing critical capabilities
2. Sync important MCP servers cluster-wide
3. Ensure all nodes have key intelligent agents
4. Bring all nodes to latest git commit

Provide recommendations as JSON."""

        response_text = self._call_ollama(prompt, system_prompt)

        try:
            # Extract JSON
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            recommendations = json.loads(response_text)
            return recommendations.get("recommendations", [])

        except Exception as e:
            print(f"Failed to parse recommendations: {e}")
            return []

    def analyze_performance_metrics(self, metrics: Dict) -> AgentDecision:
        """
        Analyze performance metrics and decide on optimization actions

        Args:
            metrics: Performance metrics from nodes

        Returns:
            AgentDecision with optimization recommendations
        """
        system_prompt = """You are a performance optimization agent.
Analyze cluster performance metrics and recommend optimizations.
Respond in JSON format with decision_type, reasoning, recommended_actions, confidence, requires_approval."""

        prompt = f"""Analyze these performance metrics:

{json.dumps(metrics, indent=2)}

Consider:
1. Which nodes are overloaded (CPU > 70%, Memory > 80%)?
2. Are tasks being distributed optimally?
3. Should we offload more aggressively?
4. Are there idle nodes that could take more work?

Provide optimization recommendations as JSON."""

        response_text = self._call_ollama(prompt, system_prompt)

        try:
            # Parse JSON
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            decision_data = json.loads(response_text)

            decision = AgentDecision(
                decision_type=decision_data.get("decision_type", "wait"),
                reasoning=decision_data.get("reasoning", ""),
                recommended_actions=decision_data.get("recommended_actions", []),
                confidence=decision_data.get("confidence", 0.5),
                requires_approval=decision_data.get("requires_approval", False)
            )

            self.memory.append({
                "timestamp": time.time(),
                "type": "performance_analysis",
                "decision": decision_data
            })

            return decision

        except Exception as e:
            return AgentDecision(
                decision_type="wait",
                reasoning=f"Parse error: {e}",
                recommended_actions=[],
                confidence=0.0,
                requires_approval=True
            )

    def should_apply_improvement(self, improvement: Dict) -> bool:
        """
        Decide if an improvement should be applied automatically

        Args:
            improvement: Improvement action dict

        Returns:
            True if safe to apply automatically
        """
        system_prompt = """You are a safety-focused agent that evaluates if improvements are safe to apply automatically.
Respond ONLY with valid JSON:
{
  "safe_to_apply": true|false,
  "reasoning": "explanation",
  "risk_level": "low|medium|high"
}
"""

        prompt = f"""Is this improvement safe to apply automatically?

{json.dumps(improvement, indent=2)}

Consider:
1. Will it break existing functionality?
2. Can it be easily reverted if needed?
3. Does it require configuration changes?
4. Is it a standard operation (package install, code sync)?

Provide safety assessment as JSON."""

        response_text = self._call_ollama(prompt, system_prompt)

        try:
            # Parse JSON
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            safety = json.loads(response_text)
            return safety.get("safe_to_apply", False) and safety.get("risk_level", "high") == "low"

        except:
            # Default to safe=False if can't parse
            return False

    def get_memory_summary(self) -> Dict:
        """Get summary of agent's decision history"""
        return {
            "total_decisions": len(self.memory),
            "recent_decisions": self.memory[-10:],
            "context": self.context
        }


# Example usage
if __name__ == "__main__":
    # Test the agent
    agent = OllamaPersistentAgent()

    # Example cluster state
    mock_inventories = {
        "macpro51": {
            "mcp_servers": {"enhanced-memory-mcp", "agent-runtime-mcp"},
            "agents": {"system_health_guardian"},
            "git_commit": "abc123"
        },
        "mac-studio": {
            "mcp_servers": {"enhanced-memory-mcp"},
            "agents": {},
            "git_commit": "abc123"
        }
    }

    print("Testing Ollama Persistent Agent...")
    print("\nAnalyzing cluster state...")

    # This would normally use real NodeInventory objects
    # decision = agent.analyze_cluster_state(mock_inventories)
    # print(f"\nDecision: {decision.decision_type}")
    # print(f"Reasoning: {decision.reasoning}")
    # print(f"Actions: {decision.recommended_actions}")
    # print(f"Confidence: {decision.confidence}")

    print("\n✓ Agent configured and ready")
    print(f"  Model: {agent.model}")
    print(f"  Host: {agent.ollama_host}")
    print("\nUse this agent in your self-improvement and optimization daemons")
