#!/usr/bin/env python3
"""
Ollama Cloud Model Configuration - Single Source of Truth

This module provides centralized model selection for all background agents
based on comprehensive benchmarking results from 2025-11-12.

Benchmark Results Summary:
- 7 models tested across 7 task types (49 total tests)
- Success rate: 87.8% (43/49 passed)
- Best overall: gpt-oss:120b (4.2s avg, 100% success)
- Fastest: gpt-oss:120b (4.2s)
- Highest quality: All top 5 models tied at 8.14/10

Reference: /mnt/agentic-system/mcp-servers/enhanced-memory-mcp/OLLAMA_MODEL_RECOMMENDATIONS.md
"""

from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class ModelConfig:
    """Configuration for a specific Ollama Cloud model"""
    model_id: str
    display_name: str
    parameters: str
    avg_speed_ms: float
    success_rate: float
    avg_quality: float
    best_for: list[str]
    avoid_for: list[str] = None

    @property
    def cli_tool_string(self) -> str:
        """Return the CLI tool string for agent initialization"""
        return f"ollama:{self.model_id}"


# Model definitions from benchmark results
MODELS = {
    "gpt-oss:120b": ModelConfig(
        model_id="gpt-oss:120b-cloud",
        display_name="GPT-OSS 120B",
        parameters="120B",
        avg_speed_ms=4200,
        success_rate=100.0,
        avg_quality=8.14,
        best_for=[
            "Complex reasoning",
            "Multi-step remediation planning",
            "General purpose tasks",
            "Production systems requiring reliability"
        ],
        avoid_for=[]
    ),

    "gpt-oss:20b": ModelConfig(
        model_id="gpt-oss:20b-cloud",
        display_name="GPT-OSS 20B",
        parameters="20B",
        avg_speed_ms=5200,
        success_rate=100.0,
        avg_quality=8.14,
        best_for=[
            "Real-time monitoring (System Health Guardian)",
            "Quick decisions with good accuracy",
            "High-frequency tasks (cost optimization)",
            "Memory extraction (2.8s, 9/10 quality)",
            "System health reasoning (4.0s, 10/10 quality)",
            "Fast remediation (4.5s, 7/10 quality)"
        ],
        avoid_for=[]
    ),

    "kimi-k2:1t": ModelConfig(
        model_id="kimi-k2:1t-cloud",
        display_name="Kimi K2 1T",
        parameters="1T",
        avg_speed_ms=6000,
        success_rate=100.0,
        avg_quality=8.14,
        best_for=[
            "Code analysis & debugging (3.4s - FASTEST)",
            "Mathematical reasoning",
            "Large context understanding",
            "Code Evolution Protector (33% faster than gpt-oss:120b)"
        ],
        avoid_for=[]
    ),

    "qwen3-coder:480b": ModelConfig(
        model_id="qwen3-coder:480b-cloud",
        display_name="Qwen3 Coder 480B",
        parameters="480B",
        avg_speed_ms=6000,
        success_rate=100.0,
        avg_quality=8.14,
        best_for=[
            "Mathematical reasoning (3.2s - FASTEST)",
            "Query perspective generation (1.2s - FASTEST)",
            "Code-related tasks"
        ],
        avoid_for=[]
    ),

    "deepseek-v3.1:671b": ModelConfig(
        model_id="deepseek-v3.1:671b-cloud",
        display_name="DeepSeek V3.1 671B",
        parameters="671B",
        avg_speed_ms=7900,
        success_rate=100.0,
        avg_quality=8.14,
        best_for=[
            "Creative text generation (1.5s)",
            "Maximum accuracy requirements",
            "Complex multi-step reasoning"
        ],
        avoid_for=[
            "Real-time/speed-critical tasks",
            "Simple quick decisions"
        ]
    ),

    "minimax-m2": ModelConfig(
        model_id="minimax-m2:cloud",
        display_name="MiniMax M2",
        parameters="Unknown",
        avg_speed_ms=11300,
        success_rate=71.4,
        avg_quality=8.0,
        best_for=[],
        avoid_for=[
            "Production use - 71.4% success rate",
            "JSON parsing - multiple failures",
            "Speed-critical tasks - 11.3s avg"
        ]
    ),

    "glm-4.6": ModelConfig(
        model_id="glm-4.6:cloud",
        display_name="GLM 4.6",
        parameters="Unknown",
        avg_speed_ms=21700,
        success_rate=57.1,
        avg_quality=8.0,
        best_for=[],
        avoid_for=[
            "Production use - 57.1% success rate",
            "JSON parsing - multiple failures",
            "Any use case - 5x slower than fastest model"
        ]
    )
}


# Agent-specific model assignments (based on benchmark recommendations)
AGENT_MODELS = {
    "system_health_guardian": {
        "model": "gpt-oss:20b",
        "rationale": "Perfect 10/10 score for system health reasoning, 4.0s response time, ideal for real-time monitoring",
        "benchmark_results": {
            "task": "System Health Reasoning",
            "speed": "4.0s",
            "quality": "10/10",
            "alternatives": "gpt-oss:120b (4.3s, 10/10)"
        }
    },

    "code_evolution_protector": {
        "model": "kimi-k2:1t",
        "rationale": "Fastest code analysis (3.4s), 1T model optimized for code understanding, 33% faster than gpt-oss:120b",
        "benchmark_results": {
            "task": "Code Analysis & Debugging",
            "speed": "3.4s",
            "quality": "9/10",
            "alternatives": "gpt-oss:120b (5.1s, 9/10)"
        }
    },

    "system_remediation_agent": {
        "model": "gpt-oss:20b",
        "rationale": "Fast response (4.5s) for quick remediation, 7/10 quality sufficient for standard fixes",
        "benchmark_results": {
            "task": "Complex Remediation Planning",
            "speed": "4.5s",
            "quality": "7/10",
            "alternatives": "gpt-oss:120b (6.1s, 7/10 - 27% slower)"
        }
    },

    "system_remediation_agent_expanded": {
        "model": "gpt-oss:120b",
        "rationale": "Larger model for complex remediation reasoning across 34 services, accepts slightly slower response (6.1s) for better reasoning",
        "benchmark_results": {
            "task": "Complex Remediation Planning",
            "speed": "6.1s",
            "quality": "7/10",
            "note": "Uses 120b for expanded reasoning despite 20b being faster"
        }
    },

    "enhanced_memory_auto_extract": {
        "model": "gpt-oss:20b",
        "rationale": "12% faster than 120b (2.8s vs 3.7s) with same 9/10 quality for memory extraction",
        "benchmark_results": {
            "task": "Memory Extraction",
            "speed": "2.8s",
            "quality": "9/10",
            "alternatives": "gpt-oss:120b (3.7s, 9/10)"
        }
    },

    "enhanced_memory_multi_query": {
        "model": "qwen3-coder:480b",
        "rationale": "21% faster than 120b (1.2s vs 1.6s) for query perspective generation",
        "benchmark_results": {
            "task": "Query Perspective Generation",
            "speed": "1.2s",
            "quality": "8/10",
            "alternatives": "deepseek-v3.1:671b (1.5s, 8/10)"
        }
    }
}


def get_model_for_agent(agent_name: str) -> str:
    """
    Get the optimal model CLI tool string for a specific agent

    Args:
        agent_name: Name of the agent (e.g., "system_health_guardian")

    Returns:
        CLI tool string (e.g., "ollama:gpt-oss:20b-cloud")

    Raises:
        ValueError: If agent_name is not configured
    """
    if agent_name not in AGENT_MODELS:
        raise ValueError(
            f"Unknown agent: {agent_name}. "
            f"Available agents: {', '.join(AGENT_MODELS.keys())}"
        )

    model_key = AGENT_MODELS[agent_name]["model"]
    model_config = MODELS[model_key]
    return model_config.cli_tool_string


def get_agent_config(agent_name: str) -> Dict[str, Any]:
    """
    Get the complete configuration for a specific agent

    Args:
        agent_name: Name of the agent

    Returns:
        Dictionary with model, rationale, and benchmark results
    """
    if agent_name not in AGENT_MODELS:
        raise ValueError(
            f"Unknown agent: {agent_name}. "
            f"Available agents: {', '.join(AGENT_MODELS.keys())}"
        )

    return AGENT_MODELS[agent_name]


def get_model_info(model_key: str) -> ModelConfig:
    """
    Get detailed information about a specific model

    Args:
        model_key: Model key (e.g., "gpt-oss:20b")

    Returns:
        ModelConfig object with full model details
    """
    if model_key not in MODELS:
        raise ValueError(
            f"Unknown model: {model_key}. "
            f"Available models: {', '.join(MODELS.keys())}"
        )

    return MODELS[model_key]


def print_agent_summary():
    """Print a summary of all agent model assignments"""
    print("=" * 80)
    print("Ollama Cloud Model Assignments (Benchmark-Optimized)")
    print("=" * 80)
    print()

    for agent_name, config in AGENT_MODELS.items():
        model_key = config["model"]
        model = MODELS[model_key]

        print(f"Agent: {agent_name}")
        print(f"  Model: {model.display_name} ({model.parameters})")
        print(f"  CLI: {model.cli_tool_string}")
        print(f"  Performance: {model.avg_speed_ms/1000:.1f}s avg, {model.success_rate:.0f}% success")
        print(f"  Rationale: {config['rationale']}")
        print()


def print_model_details():
    """Print detailed information about all available models"""
    print("=" * 80)
    print("Available Ollama Cloud Models")
    print("=" * 80)
    print()

    for model_key, model in MODELS.items():
        print(f"{model.display_name} ({model.parameters})")
        print(f"  Model ID: {model.model_id}")
        print(f"  Performance: {model.avg_speed_ms/1000:.1f}s avg, {model.success_rate:.0f}% success, {model.avg_quality:.2f}/10 quality")
        print(f"  Best for: {', '.join(model.best_for)}")
        if model.avoid_for:
            print(f"  Avoid for: {', '.join(model.avoid_for)}")
        print()


if __name__ == "__main__":
    # Print configuration summary when run directly
    print_agent_summary()
    print()
    print_model_details()
