#!/usr/bin/env python3
"""
Gemini Agent - Intelligent agent powered by Google Gemini CLI
Specialized for multi-modal analysis (text, images, video)
Uses local Gemini CLI binary for headless operation

Updated: 2025-11-13 - Now uses Gemini CLI v0.15.0
"""

import os
import json
import asyncio
import subprocess
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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


class GeminiAgent:
    """
    Production-ready intelligent agent using Google Gemini

    Specialized for:
    - Multi-modal analysis (text + images)
    - Visual system monitoring
    - Screenshot analysis
    - Fast inference tasks
    - Headless CLI operations
    """

    def __init__(
        self,
        purpose: AgentPurpose,
        tools: List[Dict[str, Any]],
        api_key: Optional[str] = None,
        model: str = "gemini-2.0-flash-exp"
    ):
        self.purpose = purpose
        self.tools = tools
        self.model = model

        # Configure Gemini
        genai.configure(api_key=api_key or os.environ.get("GOOGLE_API_KEY"))
        self.client = genai.GenerativeModel(model)

        self.context_window = []
        self.decision_history = []
        self.running = False
        self.iteration_count = 0

    async def reason(self, observations: Dict[str, Any]) -> AgentDecision:
        """
        Use Gemini to reason about observations (including visual data)
        """
        system_prompt = self.get_system_prompt()
        user_message = self._format_observations_prompt(observations)

        try:
            # Prepare content (text + images if present)
            content_parts = [user_message]

            # Add images if present in observations
            if "images" in observations:
                for img_path in observations["images"]:
                    if os.path.exists(img_path):
                        with open(img_path, 'rb') as img_file:
                            img_data = img_file.read()
                            content_parts.append({"mime_type": "image/jpeg", "data": img_data})

            response = await asyncio.to_thread(
                self.client.generate_content,
                content_parts
            )

            # Extract decision from response
            decision_text = response.text
            lines = decision_text.strip().split('\n')
            decision = lines[0] if lines else "Continue monitoring"
            reasoning = ' '.join(lines[1:]) if len(lines) > 1 else decision_text

            # Estimate confidence
            confidence = 0.85  # Gemini is strong with multi-modal
            if "critical" in decision.lower() or "urgent" in decision.lower():
                confidence = 0.95
            elif "warning" in decision.lower() or "concern" in decision.lower():
                confidence = 0.88

            return AgentDecision(
                timestamp=datetime.now().isoformat(),
                decision=decision,
                reasoning=reasoning,
                confidence=confidence,
                action_taken=decision,
                tool_used=None
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

    async def run_headless_gemini(
        self,
        command: str,
        image_path: Optional[str] = None,
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        Run Gemini CLI programmatically (formerly "headless mode")

        Uses the Gemini CLI for non-interactive execution.
        Note: Method name kept for backwards compatibility.

        Example: gemini "analyze screenshot.png"
        """
        try:
            cmd = ['gemini', '--headless', '--format', format]

            if image_path:
                cmd.extend(['analyze', image_path])
            else:
                cmd.append(command)

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                if format == "json":
                    return json.loads(stdout.decode())
                else:
                    return {"output": stdout.decode(), "status": "success"}
            else:
                return {
                    "error": stderr.decode(),
                    "status": "error",
                    "exit_code": process.returncode
                }

        except Exception as e:
            return {
                "error": str(e),
                "status": "error"
            }

    def get_system_prompt(self) -> str:
        """Generate system prompt for Gemini"""
        criteria_str = '\n'.join([f"- {c}" for c in self.purpose.decision_criteria])

        return f"""You are {self.purpose.name}, a multi-modal analysis agent.

Purpose: {self.purpose.description}
Primary Goal: {self.purpose.primary_goal}

Your Decision Criteria:
{criteria_str}

You analyze both text and visual information to:
- Understand system state from screenshots
- Detect visual anomalies
- Assess UI/UX issues
- Provide comprehensive multi-modal insights

For each observation set, decide:
1. What does the visual/text data show?
2. Are there any concerns or issues?
3. What action should be taken?

Respond with your decision on the first line, followed by detailed analysis."""

    def _format_observations_prompt(self, observations: Dict[str, Any]) -> str:
        """Format observations into a prompt for Gemini"""
        obs_lines = []
        for key, value in observations.items():
            if key == "images":
                obs_lines.append(f"Images to analyze: {len(value)} screenshot(s)")
            elif isinstance(value, dict):
                obs_lines.append(f"{key}:")
                for k, v in value.items():
                    obs_lines.append(f"  {k}: {v}")
            else:
                obs_lines.append(f"{key}: {value}")

        obs_str = '\n'.join(obs_lines)
        return f"""Multi-Modal Analysis Request (Iteration #{self.iteration_count}):

{obs_str}

Analyze the provided text and visual information. What do you observe? Are there any concerns?

Provide your analysis and recommendations."""

    async def execute_decision(self, decision: AgentDecision) -> Dict[str, Any]:
        """Execute the action decided upon"""
        print(f"\n⚡ Gemini Decision: {decision.decision}")
        print(f"   Reasoning: {decision.reasoning}")
        print(f"   Confidence: {decision.confidence:.2f}")

        if decision.tool_used:
            print(f"   Tool: {decision.tool_used}")
            return {"status": "tool_executed", "tool": decision.tool_used}
        else:
            return {"status": "analysis_complete", "action": decision.action_taken}

    async def gather_observations(self) -> Dict[str, Any]:
        """
        Gather observations for multi-modal analysis
        Subclasses override this to provide specific observations
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
        """Intelligently adjust check interval based on decision"""
        if "critical" in decision.decision.lower() or "urgent" in decision.decision.lower():
            return max(5, default_interval // 4)
        elif "warning" in decision.decision.lower() or "concern" in decision.decision.lower():
            return max(15, default_interval // 2)
        elif "normal" in decision.decision.lower() or "stable" in decision.decision.lower():
            return min(300, default_interval * 2)
        else:
            return default_interval

    async def run_loop(self, interval_seconds: int = 60):
        """Main agent loop with intelligent decision-making"""
        self.running = True
        print(f"🤖 {self.purpose.name} starting...")
        print(f"   Purpose: {self.purpose.description}")
        print(f"   Model: {self.model}")
        print(f"   Multi-modal: Text + Images")
        print()

        while self.running:
            try:
                self.iteration_count += 1

                # Gather observations
                observations = await self.gather_observations()

                # REASON about what to do
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
