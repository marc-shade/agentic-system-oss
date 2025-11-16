#!/usr/bin/env python3
"""
Ollama Agent - Intelligent agent using local Ollama models
Free AI inference with no API keys required
"""

import os
import subprocess
import json
import requests
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


class OllamaAgent:
    """
    Production-ready intelligent agent using local Ollama models

    Benefits:
    - Free - runs locally
    - No API keys needed
    - Fast inference on Apple Silicon / GPU
    - Privacy - all data stays local
    """

    def __init__(
        self,
        purpose: AgentPurpose,
        tools: List[Dict[str, Any]],
        ollama_url: str = None,
        model: str = "llama3.2:latest"
    ):
        self.purpose = purpose
        self.tools = tools
        # Use cloud if no URL specified, or use env variable
        # Default to local Ollama for now (cloud endpoint TBD)
        self.ollama_url = ollama_url or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self.model = model
        self.context_window = []
        self.decision_history = []
        self.running = False
        self.iteration_count = 0

    def reason(self, observations: Dict[str, Any]) -> AgentDecision:
        """
        Use Ollama to reason about current observations
        """
        system_prompt = self.get_system_prompt()
        user_message = self._format_observations_prompt(observations)

        try:
            # Call Ollama API
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": f"{system_prompt}\n\n{user_message}",
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Lower for more deterministic decisions
                        "top_p": 0.9
                    }
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                decision_text = result.get("response", "")

                # Parse the decision
                decision = AgentDecision(
                    timestamp=datetime.now().isoformat(),
                    decision=self._extract_decision(decision_text),
                    reasoning=self._extract_reasoning(decision_text),
                    confidence=self._extract_confidence(decision_text),
                    action_taken=None,
                    tool_used="ollama"
                )

                # Add to history
                self.decision_history.append(decision)
                return decision
            else:
                return self._fallback_decision(f"Ollama API error: {response.status_code}")

        except requests.RequestException as e:
            return self._fallback_decision(f"Ollama connection error: {e}")
        except Exception as e:
            return self._fallback_decision(f"Unexpected error: {e}")

    def get_system_prompt(self) -> str:
        """Generate system prompt for the agent"""
        tools_str = "\n".join([
            f"- {tool['name']}: {tool['description']}"
            for tool in self.tools
        ])

        criteria_str = "\n".join([
            f"- {criterion}"
            for criterion in self.purpose.decision_criteria
        ])

        return f"""You are {self.purpose.name}.

Purpose: {self.purpose.description}
Primary Goal: {self.purpose.primary_goal}

Available Tools:
{tools_str}

Decision Criteria:
{criteria_str}

You must respond in JSON format with:
{{
    "decision": "brief decision statement",
    "reasoning": "why you made this decision",
    "confidence": 0.0-1.0,
    "action": "specific action to take or null"
}}

Be concise, decisive, and action-oriented. Focus on what matters most RIGHT NOW."""

    def _format_observations_prompt(self, observations: Dict[str, Any]) -> str:
        """Format observations into a prompt"""
        obs_str = json.dumps(observations, indent=2)
        return f"""Current Observations:
{obs_str}

Based on these observations and your purpose, what should you do?
Respond in JSON format as specified in your system prompt."""

    def _extract_decision(self, text: str) -> str:
        """Extract decision from response"""
        try:
            # Try to parse as JSON
            data = json.loads(text)
            return data.get("decision", "continue monitoring")
        except json.JSONDecodeError:
            # Fallback: extract first sentence
            lines = text.strip().split('\n')
            for line in lines:
                if line.strip() and not line.strip().startswith('{'):
                    return line.strip()[:100]
            return "continue monitoring"

    def _extract_reasoning(self, text: str) -> str:
        """Extract reasoning from response"""
        try:
            data = json.loads(text)
            return data.get("reasoning", text[:200])
        except json.JSONDecodeError:
            return text[:200]

    def _extract_confidence(self, text: str) -> float:
        """Extract confidence from response"""
        try:
            data = json.loads(text)
            return float(data.get("confidence", 0.5))
        except (json.JSONDecodeError, ValueError):
            return 0.5

    def _fallback_decision(self, error_msg: str) -> AgentDecision:
        """Create a fallback decision when reasoning fails"""
        return AgentDecision(
            timestamp=datetime.now().isoformat(),
            decision="continue monitoring",
            reasoning=f"Using fallback due to: {error_msg}",
            confidence=0.3,
            action_taken=None,
            tool_used="fallback"
        )

    def gather_observations(self) -> Dict[str, Any]:
        """
        Override this in subclasses to gather relevant observations
        """
        raise NotImplementedError("Subclass must implement gather_observations()")

    def execute_decision(self, decision: AgentDecision) -> bool:
        """
        Override this in subclasses to execute the decision
        Returns True if action was successful
        """
        raise NotImplementedError("Subclass must implement execute_decision()")

    def run_iteration(self) -> bool:
        """
        Run one iteration of the agent loop
        Returns True if should continue running
        """
        try:
            self.iteration_count += 1

            # 1. Gather observations
            observations = self.gather_observations()

            # 2. Reason about them
            decision = self.reason(observations)

            # 3. Execute the decision
            success = self.execute_decision(decision)

            # Update decision with action result
            decision.action_taken = "executed" if success else "failed"

            return True

        except Exception as e:
            print(f"Error in agent iteration: {e}")
            return True  # Continue even on errors

    def start(self):
        """Start the agent loop"""
        self.running = True

    def stop(self):
        """Stop the agent loop"""
        self.running = False
