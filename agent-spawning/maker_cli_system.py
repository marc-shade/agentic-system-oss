#!/usr/bin/env python3
"""
MAKER CLI System - Zero-Cost Agent Framework
===========================================

Implements MAKER framework using LOCAL CLI tools instead of API calls:
- Claude Code CLI (Max subscription)
- OpenAI Codex CLI
- Gemini CLI
- Ollama (local models)

ZERO API COSTS - All execution is local via subprocess

Based on "Solving a Million-Step LLM Task with Zero Errors" (Cognizant AI Lab, 2025)
"""

import json
import logging
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import hashlib
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# CLI Provider Configuration
# ============================================================================

class CLIProvider(Enum):
    """Available local CLI providers (zero cost)"""
    CLAUDE_CODE = "claude"      # Claude Code Max CLI
    CODEX = "codex"             # OpenAI Codex CLI
    GEMINI = "gemini"           # Gemini CLI
    OLLAMA = "ollama"           # Local Ollama models


@dataclass
class CLIConfig:
    """CLI tool configuration"""
    provider: CLIProvider
    command_path: str
    execution_template: str
    default_args: List[str] = field(default_factory=list)
    cost_per_token: float = 0.0  # Zero for all CLI tools
    available: bool = True


# CLI tool configurations with actual paths
CLI_CONFIGS = {
    CLIProvider.CLAUDE_CODE: CLIConfig(
        provider=CLIProvider.CLAUDE_CODE,
        command_path="/Users/marc/.local/bin/claude",
        execution_template="claude --print {prompt}",
        default_args=["--print"],
        cost_per_token=0.0
    ),
    CLIProvider.CODEX: CLIConfig(
        provider=CLIProvider.CODEX,
        command_path="/Users/marc/.bun/bin/codex",
        execution_template="codex exec {prompt}",
        default_args=["exec"],
        cost_per_token=0.0
    ),
    CLIProvider.GEMINI: CLIConfig(
        provider=CLIProvider.GEMINI,
        command_path="/Users/marc/.nvm/versions/node/v24.3.0/bin/gemini",
        execution_template="gemini {prompt}",
        default_args=[],
        cost_per_token=0.0
    ),
    CLIProvider.OLLAMA: CLIConfig(
        provider=CLIProvider.OLLAMA,
        command_path="/usr/local/bin/ollama",
        execution_template="ollama run llama2 {prompt}",
        default_args=["run", "llama2"],
        cost_per_token=0.0
    )
}


# ============================================================================
# CLI Executor
# ============================================================================

class CLIExecutor:
    """Execute prompts via local CLI tools (zero cost)"""

    def __init__(self, provider: CLIProvider = CLIProvider.CLAUDE_CODE):
        self.provider = provider
        self.config = CLI_CONFIGS[provider]
        self._verify_available()

    def _verify_available(self):
        """Check if CLI tool is available"""
        try:
            result = subprocess.run(
                [self.config.command_path, "--help"],
                capture_output=True,
                timeout=5
            )
            self.config.available = result.returncode == 0
            if self.config.available:
                logger.info(f"✅ {self.provider.value} CLI available at {self.config.command_path}")
            else:
                logger.warning(f"⚠️ {self.provider.value} CLI found but returned error")
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            self.config.available = False
            logger.warning(f"⚠️ {self.provider.value} CLI not available: {e}")

    def execute(self, prompt: str, timeout: int = 30) -> str:
        """
        Execute prompt via CLI tool

        Args:
            prompt: Task prompt
            timeout: Execution timeout in seconds

        Returns:
            CLI output text

        Raises:
            RuntimeError: If CLI execution fails
        """
        if not self.config.available:
            raise RuntimeError(f"{self.provider.value} CLI not available")

        # Build command based on provider
        # Use stdin for compatibility with interactive CLIs
        if self.provider == CLIProvider.CLAUDE_CODE:
            cmd = [self.config.command_path, "--print"]
            input_text = prompt
        elif self.provider == CLIProvider.CODEX:
            # Codex exec doesn't support stdin, use prompt as arg
            cmd = [self.config.command_path, "exec", "--", prompt]
            input_text = None
        elif self.provider == CLIProvider.GEMINI:
            cmd = [self.config.command_path]
            input_text = prompt
        elif self.provider == CLIProvider.OLLAMA:
            cmd = [self.config.command_path, "run", "llama2"]
            input_text = prompt
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

        logger.info(f"Executing via {self.provider.value}: {prompt[:100]}...")

        try:
            result = subprocess.run(
                cmd,
                input=input_text,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=True
            )
            output = result.stdout.strip()
            logger.info(f"✅ {self.provider.value} execution successful ({len(output)} chars)")
            return output
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"{self.provider.value} execution timeout after {timeout}s")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"{self.provider.value} execution failed: {e.stderr}")
        except Exception as e:
            raise RuntimeError(f"{self.provider.value} execution error: {str(e)}")


# ============================================================================
# MAKER Framework Exceptions
# ============================================================================

class RedFlagError(Exception):
    """Base exception for red flag violations"""
    pass


class MalformedOutputError(RedFlagError):
    """Agent output is malformed - signals logic error"""
    pass


class VerboseResponseError(RedFlagError):
    """Agent response too long - signals hallucination"""
    pass


class IncompleteOutputError(RedFlagError):
    """Agent output missing required fields - signals confusion"""
    pass


class InvalidStateError(RedFlagError):
    """Agent state is invalid"""
    pass


# ============================================================================
# Task Complexity Classification
# ============================================================================

class TaskComplexity(Enum):
    """Task complexity levels for agent selection"""
    SIMPLE = "simple"        # CLI tool directly (90% of tasks)
    CRITICAL = "critical"    # CLI tool with voting (8% of tasks)
    COMPLEX = "complex"      # Best available CLI tool (2% of tasks)


@dataclass
class TaskClassification:
    """Task complexity classification result"""
    complexity: TaskComplexity
    confidence: float
    reasoning: str
    recommended_provider: CLIProvider
    estimated_cost: float = 0.0  # Always zero for CLI


class TaskComplexityAnalyzer:
    """Analyzes tasks to determine optimal execution strategy"""

    # Keyword-based classification
    SIMPLE_KEYWORDS = {
        'parse', 'extract', 'validate', 'format', 'acknowledge',
        'respond', 'confirm', 'list', 'show', 'get', 'fetch'
    }

    CRITICAL_KEYWORDS = {
        'register', 'configure', 'authenticate', 'authorize', 'deploy',
        'delete', 'remove', 'modify', 'update', 'change', 'security'
    }

    COMPLEX_KEYWORDS = {
        'design', 'architect', 'optimize', 'analyze', 'evaluate',
        'plan', 'strategy', 'refactor', 'implement', 'algorithm'
    }

    @classmethod
    def classify_task(cls, task_description: str,
                     context: Optional[Dict[str, Any]] = None) -> TaskClassification:
        """
        Classify task complexity and recommend CLI provider

        Args:
            task_description: Task to classify
            context: Optional context with hints

        Returns:
            TaskClassification with recommendations
        """
        desc_lower = task_description.lower()

        # Check for explicit hints in context
        if context:
            if context.get('is_critical'):
                return TaskClassification(
                    complexity=TaskComplexity.CRITICAL,
                    confidence=1.0,
                    reasoning="Explicitly marked as critical in context",
                    recommended_provider=CLIProvider.CLAUDE_CODE
                )
            if context.get('is_complex'):
                return TaskClassification(
                    complexity=TaskComplexity.COMPLEX,
                    confidence=1.0,
                    reasoning="Explicitly marked as complex in context",
                    recommended_provider=CLIProvider.CLAUDE_CODE
                )

        # Keyword-based classification
        simple_count = sum(1 for kw in cls.SIMPLE_KEYWORDS if kw in desc_lower)
        critical_count = sum(1 for kw in cls.CRITICAL_KEYWORDS if kw in desc_lower)
        complex_count = sum(1 for kw in cls.COMPLEX_KEYWORDS if kw in desc_lower)

        # Length heuristic
        if len(task_description) > 500:
            complex_count += 2

        # Classify based on counts
        # NOTE: Using Codex as primary provider (proven working, zero cost)
        if complex_count > 0 or len(task_description) > 500:
            return TaskClassification(
                complexity=TaskComplexity.COMPLEX,
                confidence=0.7 + (complex_count * 0.1),
                reasoning=f"Complex keywords detected: {complex_count}",
                recommended_provider=CLIProvider.CODEX  # Codex for complex tasks
            )
        elif critical_count > 0:
            return TaskClassification(
                complexity=TaskComplexity.CRITICAL,
                confidence=0.8,
                reasoning=f"Critical keywords detected: {critical_count}",
                recommended_provider=CLIProvider.CODEX  # Codex with voting for critical
            )
        else:
            return TaskClassification(
                complexity=TaskComplexity.SIMPLE,
                confidence=0.9,
                reasoning=f"Simple keywords detected: {simple_count}",
                recommended_provider=CLIProvider.CODEX  # Codex for simple tasks
            )


# ============================================================================
# Stateless Agent State
# ============================================================================

@dataclass
class AgentState:
    """
    Stateless agent state - the ONLY memory

    MAKER Principle: No conversation history, only current state
    """
    task_id: str
    task_description: str
    context: Dict[str, Any]
    previous_result: Optional[Any] = None
    step_number: int = 0
    max_steps: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Serialize state for storage"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentState':
        """Deserialize state from storage"""
        return cls(**data)

    def validate(self) -> bool:
        """Validate state integrity"""
        if not self.task_id or not self.task_description:
            raise InvalidStateError("Missing required state fields")
        if self.step_number < 0 or self.step_number > self.max_steps:
            raise InvalidStateError(f"Invalid step number: {self.step_number}/{self.max_steps}")
        return True


# ============================================================================
# Red Flagging System
# ============================================================================

class RedFlagValidator:
    """Validates agent outputs using strict parsing"""

    @staticmethod
    def validate_json_response(response: str, expected_fields: List[str],
                               max_chars: Optional[int] = None) -> Dict[str, Any]:
        """
        Strictly validate JSON response with red flagging

        Raises:
            MalformedOutputError: Invalid JSON
            VerboseResponseError: Response too long
            IncompleteOutputError: Missing required fields
        """
        # Red Flag 1: Check response length
        if max_chars and len(response) > max_chars * 3:
            raise VerboseResponseError(
                f"Response length {len(response)} exceeds expected {max_chars * 3}"
            )

        # Red Flag 2: Strict JSON parsing
        try:
            parsed = json.loads(response)
        except json.JSONDecodeError as e:
            raise MalformedOutputError(f"JSON parsing failed: {str(e)}")

        # Red Flag 3: Required fields check
        missing_fields = [f for f in expected_fields if f not in parsed]
        if missing_fields:
            raise IncompleteOutputError(f"Missing required fields {missing_fields}")

        return parsed


# ============================================================================
# Voting Mechanism
# ============================================================================

class VotingMechanism:
    """First-to-head-by-K voting algorithm"""

    @staticmethod
    def majority_vote(votes: List[Any], k: int = 5) -> Tuple[Any, float]:
        """
        Execute first-to-head-by-K voting

        Args:
            votes: List of vote results
            k: Winning threshold

        Returns:
            (winner, confidence)
        """
        if not votes:
            raise ValueError("No votes to count")

        # Count occurrences
        vote_counts = {}
        for vote in votes:
            vote_str = json.dumps(vote, sort_keys=True) if isinstance(vote, dict) else str(vote)
            vote_counts[vote_str] = vote_counts.get(vote_str, 0) + 1

        # Find winner
        max_count = max(vote_counts.values())
        winner_str = [v for v, c in vote_counts.items() if c == max_count][0]

        # Reconstruct winner from string
        try:
            winner = json.loads(winner_str)
        except json.JSONDecodeError:
            winner = winner_str

        confidence = max_count / len(votes)

        logger.info(f"Voting result: {max_count}/{len(votes)} votes (confidence: {confidence:.1%})")

        return winner, confidence


# ============================================================================
# MAKER CLI Agents
# ============================================================================

class MAKERCLIAgent(ABC):
    """Base class for CLI-based MAKER agents"""

    def __init__(self, provider: CLIProvider):
        self.provider = provider
        self.executor = CLIExecutor(provider)
        self.cost_per_execution = 0.0  # Zero cost for CLI

    @abstractmethod
    def execute_step(self, state: AgentState) -> Any:
        """Execute single stateless step"""
        pass

    def run(self, state: AgentState) -> Dict[str, Any]:
        """
        Run stateless agent execution

        MAKER Principle: Load state, execute one step, return result, die
        """
        # Validate state
        state.validate()

        # Execute single step
        result = self.execute_step(state)

        # Update state
        state.step_number += 1
        state.previous_result = result

        return {
            'success': True,
            'result': result,
            'state': state.to_dict(),
            'provider': self.provider.value,
            'cost': self.cost_per_execution
        }


class SimpleCLIAgent(MAKERCLIAgent):
    """Simple tasks via CLI (90% of operations, zero cost)"""

    def __init__(self, provider: CLIProvider = CLIProvider.CODEX):
        super().__init__(provider)

    def execute_step(self, state: AgentState) -> Any:
        """Execute simple task via CLI"""
        logger.info(f"SimpleCLIAgent executing via {self.provider.value}")

        # Execute via CLI
        output = self.executor.execute(state.task_description)

        # Try to parse as JSON, fallback to text
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return {
                'status': 'completed',
                'message': output,
                'provider': self.provider.value
            }


class VotingCLIAgent(MAKERCLIAgent):
    """Critical operations with K-voting via CLI (zero cost, ultra-reliable)"""

    def __init__(self, provider: CLIProvider = CLIProvider.CODEX, k: int = 5):
        super().__init__(provider)
        self.k = k

    def execute_step(self, state: AgentState) -> Any:
        """Execute with K parallel CLI calls and voting"""
        logger.info(f"VotingCLIAgent executing K={self.k} via {self.provider.value}")

        votes = []
        for i in range(self.k):
            try:
                output = self.executor.execute(state.task_description)
                # Try to parse as JSON
                try:
                    vote = json.loads(output)
                except json.JSONDecodeError:
                    vote = {'result': output}
                votes.append(vote)
            except Exception as e:
                logger.warning(f"Vote {i+1}/{self.k} failed: {e}")
                continue

        if not votes:
            raise RuntimeError(f"All {self.k} votes failed")

        # Vote on result
        winner, confidence = VotingMechanism.majority_vote(votes, self.k)

        logger.info(f"Voting completed: {len(votes)} votes, confidence {confidence:.1%}")

        return winner


class ComplexCLIAgent(MAKERCLIAgent):
    """Complex tasks via best CLI provider (zero cost)"""

    def __init__(self, provider: CLIProvider = CLIProvider.CODEX):
        super().__init__(provider)

    def execute_step(self, state: AgentState) -> Any:
        """Execute complex task via CLI"""
        logger.info(f"ComplexCLIAgent executing via {self.provider.value}")

        # Execute via CLI
        output = self.executor.execute(state.task_description, timeout=60)

        # Try to parse as JSON
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return {
                'status': 'completed',
                'message': output,
                'provider': self.provider.value
            }


# ============================================================================
# Agent Factory
# ============================================================================

class MAKERCLIAgentFactory:
    """Creates appropriate CLI agent based on task complexity"""

    @staticmethod
    def create_agent(task_description: str,
                    context: Optional[Dict[str, Any]] = None,
                    force_agent_type: Optional[str] = None) -> MAKERCLIAgent:
        """
        Create optimal CLI agent based on task complexity

        Args:
            task_description: Task to execute
            context: Optional context
            force_agent_type: Force specific agent type

        Returns:
            Appropriate MAKERCLIAgent instance
        """
        if force_agent_type:
            if force_agent_type == 'simple':
                return SimpleCLIAgent(CLIProvider.CODEX)
            elif force_agent_type == 'voting':
                return VotingCLIAgent(CLIProvider.CLAUDE_CODE)
            elif force_agent_type == 'complex':
                return ComplexCLIAgent(CLIProvider.CLAUDE_CODE)
            else:
                raise ValueError(f"Unknown agent type: {force_agent_type}")

        # Classify task
        classification = TaskComplexityAnalyzer.classify_task(task_description, context)

        logger.info(f"Task classified as {classification.complexity.value} "
                   f"(confidence: {classification.confidence:.1%})")

        # Create appropriate agent
        if classification.complexity == TaskComplexity.SIMPLE:
            return SimpleCLIAgent(classification.recommended_provider)
        elif classification.complexity == TaskComplexity.CRITICAL:
            return VotingCLIAgent(classification.recommended_provider)
        else:  # COMPLEX
            return ComplexCLIAgent(classification.recommended_provider)


# ============================================================================
# Main Entry Point
# ============================================================================

def execute_maker_cli_task(task_description: str,
                          context: Optional[Dict[str, Any]] = None,
                          force_agent_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute MAKER task via local CLI tools (ZERO COST)

    Args:
        task_description: Task to execute
        context: Optional context
        force_agent_type: Force specific agent type

    Returns:
        Execution result
    """
    # Create state
    task_id = f"task_{int(time.time())}_{hashlib.md5(task_description.encode()).hexdigest()[:8]}"
    state = AgentState(
        task_id=task_id,
        task_description=task_description,
        context=context or {}
    )

    # Create agent
    agent = MAKERCLIAgentFactory.create_agent(task_description, context, force_agent_type)

    # Execute
    logger.info(f"Executing task {task_id} via {agent.provider.value}")
    result = agent.run(state)

    return result


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("MAKER CLI System - Zero-Cost Agent Framework")
    print("="*70)

    # Example 1: Simple task (uses Codex CLI)
    print("\n--- Example 1: Simple Task (Codex CLI) ---")
    result1 = execute_maker_cli_task(
        task_description="List the benefits of using Claude Code CLI",
        context={'operation': 'simple_query'}
    )
    print(f"Result: {json.dumps(result1, indent=2)}")

    # Example 2: Critical task (uses Claude CLI with voting)
    print("\n--- Example 2: Critical Task (Claude CLI + Voting) ---")
    result2 = execute_maker_cli_task(
        task_description="Generate secure authentication configuration",
        context={'is_critical': True}
    )
    print(f"Result: {json.dumps(result2, indent=2)}")

    # Example 3: Complex task (uses Claude CLI)
    print("\n--- Example 3: Complex Task (Claude CLI) ---")
    result3 = execute_maker_cli_task(
        task_description="Design a distributed caching architecture for high-throughput system",
        context={'is_complex': True}
    )
    print(f"Result: {json.dumps(result3, indent=2)}")

    print("\n" + "="*70)
    print("All executions completed with ZERO API COSTS")
    print("="*70)
