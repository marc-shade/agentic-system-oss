#!/usr/bin/env python3
"""
Gemini CLI Agent - Google Gemini-powered intelligent agent
Uses local Gemini CLI binary (v0.15.0) for AI-powered decision making

Provides autonomous decision-making using Google Gemini 2.5 Pro
with 1M token context window via the official Gemini CLI
"""

import json
import logging
import subprocess
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentPurpose(Enum):
    """Agent purpose types"""
    SYSTEM_HEALTH = "system_health"
    MEMORY_OPTIMIZATION = "memory_optimization"
    CODE_QUALITY = "code_quality"
    PERFORMANCE_TUNING = "performance_tuning"
    MULTIMODAL_ANALYSIS = "multimodal_analysis"


@dataclass
class AgentDecision:
    """Agent decision with reasoning"""
    action: str
    reasoning: str
    confidence: float
    alternatives: List[str]


class GeminiCLIAgent:
    """
    Intelligent agent powered by Gemini CLI
    
    Provides autonomous decision-making using Google Gemini 2.5 Pro
    for system monitoring, optimization, and self-improvement
    
    Features:
    - 1 million token context window
    - Multimodal support (text, images, code)
    - Built-in tools (search, file ops, shell)
    - Free tier: 60 req/min, 1000/day
    """
    
    def __init__(
        self,
        purpose: AgentPurpose,
        tools: List[Dict[str, Any]],
        gemini_bin: str = None
    ):
        """
        Initialize Gemini CLI-powered agent
        
        Args:
            purpose: Agent's primary purpose
            tools: Available tools the agent can use
            gemini_bin: Path to gemini binary
        """
        self.purpose = purpose
        self.tools = tools
        self.gemini_bin = gemini_bin or self._find_gemini_binary()
        
        if not self.gemini_bin:
            raise RuntimeError("Gemini CLI not found. Install: npm install -g @google/gemini-cli")
        
        logger.info(f"Initialized {purpose.value} agent with Gemini CLI at {self.gemini_bin}")
    
    def _find_gemini_binary(self) -> Optional[str]:
        """Find gemini binary"""
        # Check common locations
        locations = [
            Path.home() / ".local/bin/gemini",
            Path("/usr/local/bin/gemini"),
            Path("/usr/bin/gemini")
        ]
        
        for loc in locations:
            if loc.exists() and loc.is_file():
                return str(loc)
        
        # Try which command
        try:
            result = subprocess.run(
                ["which", "gemini"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        
        return None
    
    def reason(self, observations: Dict[str, Any]) -> AgentDecision:
        """
        Use Gemini to reason about observations and decide action
        
        Args:
            observations: Current state observations
            
        Returns:
            AgentDecision with action, reasoning, confidence
        """
        # Build prompt for Gemini
        prompt = self._build_reasoning_prompt(observations)
        
        # Call Gemini CLI for reasoning
        try:
            response = self._call_gemini(prompt)
            decision = self._parse_decision(response)
            
            logger.info(f"Agent decision: {decision.action} (confidence: {decision.confidence})")
            logger.debug(f"Reasoning: {decision.reasoning}")
            
            return decision
            
        except Exception as e:
            logger.error(f"Gemini reasoning failed: {e}")
            # Fallback to conservative decision
            return AgentDecision(
                action="no_action",
                reasoning=f"Error during reasoning: {e}",
                confidence=0.0,
                alternatives=[]
            )
    
    def _build_reasoning_prompt(self, observations: Dict[str, Any]) -> str:
        """Build reasoning prompt for Gemini"""
        tool_desc = "\n".join([f"- {t['name']}: {t['description']}" for t in self.tools])
        
        prompt = f"""You are an autonomous {self.purpose.value} agent.

Your available tools:
{tool_desc}

Current observations:
{json.dumps(observations, indent=2)}

Analyze the observations and decide what action to take.
Respond in JSON format ONLY (no markdown, no code blocks):
{{
  "action": "tool_name or no_action",
  "reasoning": "explain your decision",
  "confidence": 0.0-1.0,
  "alternatives": ["other possible actions"]
}}

Think step by step:
1. What is the current state?
2. What needs attention?
3. What is the best action?
4. What could go wrong?

Output ONLY the JSON, nothing else.
"""
        return prompt
    
    def _call_gemini(self, prompt: str, timeout: int = 30) -> str:
        """
        Call Gemini CLI for inference
        
        Args:
            prompt: Input prompt
            timeout: Timeout in seconds
            
        Returns:
            Gemini response text
        """
        try:
            # Call gemini CLI with one-shot prompt
            result = subprocess.run(
                [self.gemini_bin, prompt],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode != 0:
                # Check if auth error
                if "not logged in" in result.stderr.lower() or "authenticate" in result.stderr.lower():
                    raise RuntimeError("Gemini CLI not authenticated. Run: gemini (and log in)")
                raise RuntimeError(f"Gemini CLI failed: {result.stderr}")
            
            return result.stdout.strip()
            
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Gemini timed out after {timeout}s")
        except Exception as e:
            raise RuntimeError(f"Gemini execution failed: {e}")
    
    def _parse_decision(self, response: str) -> AgentDecision:
        """Parse Gemini response into AgentDecision"""
        try:
            # Gemini CLI sometimes wraps JSON in text
            # Try to extract JSON from response
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif "{" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
            else:
                json_str = response
            
            data = json.loads(json_str)
            
            return AgentDecision(
                action=data.get("action", "no_action"),
                reasoning=data.get("reasoning", "No reasoning provided"),
                confidence=float(data.get("confidence", 0.5)),
                alternatives=data.get("alternatives", [])
            )
            
        except Exception as e:
            logger.error(f"Failed to parse decision: {e}")
            logger.debug(f"Raw response: {response}")
            
            # Try to extract action from text
            if "no action" in response.lower() or "no_action" in response.lower():
                action = "no_action"
            else:
                action = "unknown"
            
            return AgentDecision(
                action=action,
                reasoning=response[:200] if len(response) > 0 else "No response",
                confidence=0.3,
                alternatives=[]
            )
    
    def execute_decision(self, decision: AgentDecision) -> Dict[str, Any]:
        """
        Execute the decided action
        
        Args:
            decision: AgentDecision to execute
            
        Returns:
            Execution result
        """
        if decision.action == "no_action":
            logger.info("No action needed")
            return {"status": "no_action", "message": "System is healthy"}
        
        # Find matching tool
        tool = next((t for t in self.tools if t["name"] == decision.action), None)
        
        if not tool:
            logger.error(f"Unknown action: {decision.action}")
            return {"status": "error", "message": f"Unknown action: {decision.action}"}
        
        # Execute tool
        try:
            logger.info(f"Executing: {decision.action}")
            result = tool["function"]()
            
            logger.info(f"Execution result: {result}")
            return {
                "status": "success",
                "action": decision.action,
                "result": result,
                "reasoning": decision.reasoning
            }
            
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            return {
                "status": "error",
                "action": decision.action,
                "error": str(e)
            }


def main():
    """Example usage"""
    # Define tools
    def check_memory():
        import psutil
        mem = psutil.virtual_memory()
        return {"percent": mem.percent, "available_gb": mem.available / (1024**3)}
    
    def restart_service():
        return {"restarted": True}
    
    tools = [
        {
            "name": "check_memory",
            "description": "Check system memory usage",
            "function": check_memory
        },
        {
            "name": "restart_service",
            "description": "Restart a failed service",
            "function": restart_service
        }
    ]
    
    # Create agent
    try:
        agent = GeminiCLIAgent(
            purpose=AgentPurpose.SYSTEM_HEALTH,
            tools=tools
        )
        
        # Gather observations
        observations = {
            "memory_percent": 45,
            "cpu_percent": 35,
            "services_down": []
        }
        
        # Reason and decide
        decision = agent.reason(observations)
        
        print(f"Decision: {decision.action}")
        print(f"Reasoning: {decision.reasoning}")
        print(f"Confidence: {decision.confidence}")
        
        # Execute decision
        if decision.confidence > 0.7:
            result = agent.execute_decision(decision)
            print(f"Result: {result}")
            
    except RuntimeError as e:
        print(f"Error: {e}")
        print("\nTo use Gemini CLI agent:")
        print("1. Install: npm install -g @google/gemini-cli")
        print("2. Authenticate: gemini (and log in with Google account)")
        print("3. Test: gemini 'hello world'")


if __name__ == "__main__":
    main()
