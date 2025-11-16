#!/usr/bin/env python3
"""
Codex Agent - OpenAI Codex-powered intelligent agent
Uses local Codex binary for AI-powered decision making

Integrated with Comprehensive Cluster State for full cluster awareness.
Can query all nodes, services, software, network topology in real-time.

Similar to OllamaAgent but uses Codex instead of Ollama
Provides multi-provider support for intelligent agents
"""

import json
import logging
import subprocess
import sys
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# Add cluster-deployment to path for comprehensive state access
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "cluster-deployment"))

try:
    from comprehensive_cluster_state import ComprehensiveClusterState, get_complete_state
    CLUSTER_STATE_AVAILABLE = True
except ImportError:
    logger.warning("Comprehensive cluster state not available")
    CLUSTER_STATE_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentPurpose(Enum):
    """Agent purpose types"""
    SYSTEM_HEALTH = "system_health"
    MEMORY_OPTIMIZATION = "memory_optimization"
    CODE_QUALITY = "code_quality"
    PERFORMANCE_TUNING = "performance_tuning"


@dataclass
class AgentDecision:
    """Agent decision with reasoning"""
    action: str
    reasoning: str
    confidence: float
    alternatives: List[str]


class CodexAgent:
    """
    Intelligent agent powered by local Codex
    
    Provides autonomous decision-making using OpenAI Codex
    for system monitoring, optimization, and self-improvement
    """
    
    def __init__(
        self,
        purpose: AgentPurpose,
        tools: List[Dict[str, Any]],
        codex_bin: str = None,
        use_cluster_state: bool = True
    ):
        """
        Initialize Codex-powered agent

        Args:
            purpose: Agent's primary purpose
            tools: Available tools the agent can use
            codex_bin: Path to codex-exec binary
            use_cluster_state: Enable comprehensive cluster state access
        """
        self.purpose = purpose
        self.tools = tools
        self.codex_bin = codex_bin or self._find_codex_binary()

        # Initialize cluster state access
        self.cluster_state = None
        if use_cluster_state and CLUSTER_STATE_AVAILABLE:
            try:
                self.cluster_state = ComprehensiveClusterState()
                logger.info("Cluster state access enabled")
            except Exception as e:
                logger.warning(f"Could not initialize cluster state: {e}")

        if not self.codex_bin:
            raise RuntimeError("Codex binary not found. Install from https://github.com/openai/codex")

        logger.info(f"Initialized {purpose.value} agent with Codex at {self.codex_bin}")
    
    def _find_codex_binary(self) -> Optional[str]:
        """Find codex-exec binary"""
        # Check common locations
        locations = [
            Path.home() / ".local/bin/codex-exec",
            Path("/usr/local/bin/codex-exec"),
            Path("/usr/bin/codex-exec")
        ]
        
        for loc in locations:
            if loc.exists() and loc.is_file():
                return str(loc)
        
        # Try which command
        try:
            result = subprocess.run(
                ["which", "codex-exec"],
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
        Use Codex to reason about observations and decide action
        
        Args:
            observations: Current state observations
            
        Returns:
            AgentDecision with action, reasoning, confidence
        """
        # Build prompt for Codex
        prompt = self._build_reasoning_prompt(observations)
        
        # Call Codex for reasoning
        try:
            response = self._call_codex(prompt)
            decision = self._parse_decision(response)
            
            logger.info(f"Agent decision: {decision.action} (confidence: {decision.confidence})")
            logger.debug(f"Reasoning: {decision.reasoning}")
            
            return decision
            
        except Exception as e:
            logger.error(f"Codex reasoning failed: {e}")
            # Fallback to conservative decision
            return AgentDecision(
                action="no_action",
                reasoning=f"Error during reasoning: {e}",
                confidence=0.0,
                alternatives=[]
            )
    
    def _build_reasoning_prompt(self, observations: Dict[str, Any]) -> str:
        """Build reasoning prompt for Codex"""
        tool_desc = "\n".join([f"- {t['name']}: {t['description']}" for t in self.tools])
        
        prompt = f"""You are an autonomous {self.purpose.value} agent.

Your available tools:
{tool_desc}

Current observations:
{json.dumps(observations, indent=2)}

Analyze the observations and decide what action to take.
Respond in JSON format:
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
"""
        return prompt
    
    def _call_codex(self, prompt: str, timeout: int = 30) -> str:
        """
        Call Codex binary for inference
        
        Args:
            prompt: Input prompt
            timeout: Timeout in seconds
            
        Returns:
            Codex response text
        """
        try:
            # Call codex-exec with prompt
            # Note: Actual API/usage may vary - this is a placeholder
            # You may need to configure API keys or use codex-tui instead
            
            result = subprocess.run(
                [self.codex_bin, "--prompt", prompt],
                capture_output=True,
                text=True,
                timeout=timeout,
                env={"OPENAI_API_KEY": self._get_api_key()}
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Codex failed: {result.stderr}")
            
            return result.stdout.strip()
            
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Codex timed out after {timeout}s")
        except Exception as e:
            raise RuntimeError(f"Codex execution failed: {e}")
    
    def _get_api_key(self) -> Optional[str]:
        """Get OpenAI API key from environment or config"""
        import os
        
        # Check environment
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            return api_key
        
        # Check config file
        config_file = Path.home() / ".config/openai/api_key"
        if config_file.exists():
            return config_file.read_text().strip()
        
        logger.warning("No OpenAI API key found. Codex may not work.")
        return None
    
    def _parse_decision(self, response: str) -> AgentDecision:
        """Parse Codex response into AgentDecision"""
        try:
            # Try to extract JSON from response
            # Codex might wrap JSON in markdown code blocks
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
            # Try to extract action from text
            if "no action" in response.lower() or "no_action" in response.lower():
                action = "no_action"
            else:
                action = "unknown"
            
            return AgentDecision(
                action=action,
                reasoning=response[:200],
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

    # === Cluster State Query Methods ===

    def get_cluster_state(self) -> Dict[str, Any]:
        """Get complete cluster state"""
        if not self.cluster_state:
            return {"error": "Cluster state not available"}

        try:
            return self.cluster_state.get_complete_cluster_state()
        except Exception as e:
            logger.error(f"Failed to get cluster state: {e}")
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
            logger.error(f"Failed to query services: {e}")
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
            logger.error(f"Failed to query software: {e}")
            return []

    def get_network_topology(self) -> Dict[str, Any]:
        """Get complete network topology"""
        if not self.cluster_state:
            return {}

        try:
            return self.cluster_state.get_network_map()
        except Exception as e:
            logger.error(f"Failed to get network topology: {e}")
            return {}

    def audit_cluster_packages(self) -> Dict[str, Any]:
        """
        Audit all packages across cluster for vulnerabilities

        Returns summary of security concerns by node
        """
        if not self.cluster_state:
            return {"error": "Cluster state not available"}

        try:
            cluster = self.cluster_state.get_complete_cluster_state()
            audit_results = {}

            for node_id, node_info in cluster["nodes"].items():
                packages = node_info.get("software", [])

                # Build audit prompt for Codex
                package_list = "\n".join([
                    f"- {pkg['package_name']} {pkg['version']} ({pkg['package_type']})"
                    for pkg in packages[:100]  # Limit to avoid token overflow
                ])

                prompt = f"""Security audit for node {node_id}:

Installed packages:
{package_list}

Identify any packages with known vulnerabilities or security concerns.
Respond in JSON format:
{{
  "vulnerable_packages": ["package names"],
  "security_concerns": ["descriptions"],
  "recommendations": ["actions to take"]
}}
"""

                # Use Codex to audit
                response = self._call_codex(prompt)
                audit_results[node_id] = self._parse_decision(response)

            return audit_results

        except Exception as e:
            logger.error(f"Cluster package audit failed: {e}")
            return {"error": str(e)}


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
    agent = CodexAgent(
        purpose=AgentPurpose.SYSTEM_HEALTH,
        tools=tools
    )
    
    # Gather observations
    observations = {
        "memory_percent": 85,
        "cpu_percent": 45,
        "services_down": ["temporal-workers"]
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


if __name__ == "__main__":
    main()
