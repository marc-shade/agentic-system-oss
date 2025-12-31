#!/usr/bin/env python3
"""
Multi-Provider Task Executor - Intelligent AI routing with cascading fallback

Providers (in preference order):
1. Claude Code - Complex reasoning, architecture, code review
2. OpenAI Codex - Code generation, implementation
3. Gemini CLI - Research, documentation, analysis
4. Ollama (local) - Always-available fallback

Provider Selection Strategy:
- Research tasks → Gemini (fast, good at synthesis) → Claude → Codex → Ollama
- Implementation tasks → Codex (code specialist) → Claude → Gemini → Ollama
- Testing tasks → Claude (reasoning) → Codex → Gemini → Ollama
- Documentation tasks → Gemini (good prose) → Claude → Codex → Ollama
- Planning/Architecture → Claude (deep reasoning) → Gemini → Codex → Ollama

STATUS: Production Ready
"""

import asyncio
import logging
import os
import subprocess
import json
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class Provider(Enum):
    CLAUDE = "claude"
    CODEX = "codex"
    GEMINI = "gemini"
    OLLAMA = "ollama"


@dataclass
class ProviderConfig:
    name: str
    command: List[str]
    timeout: int
    rate_limit_patterns: List[str]
    success_min_length: int


# Provider configurations
PROVIDERS = {
    Provider.CLAUDE: ProviderConfig(
        name="Claude Code",
        command=["claude", "-p", "{prompt}", "--output-format", "text", "--verbose"],
        timeout=300,
        rate_limit_patterns=["credit balance", "rate limit", "quota exceeded"],
        success_min_length=50
    ),
    Provider.CODEX: ProviderConfig(
        name="OpenAI Codex",
        command=["codex", "{prompt}"],
        timeout=300,
        rate_limit_patterns=["rate limit", "quota", "insufficient_quota"],
        success_min_length=50
    ),
    Provider.GEMINI: ProviderConfig(
        name="Gemini CLI",
        command=["gemini", "{prompt}"],
        timeout=300,
        rate_limit_patterns=["quota", "rate limit", "resource exhausted"],
        success_min_length=50
    ),
}

# Ollama configuration
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:14b")

# Task phase to provider routing
# NOTE: Claude and Ollama work in non-TTY environments
# Codex and Gemini require interactive terminals - placed lower in chain
PHASE_ROUTING = {
    "research": [Provider.CLAUDE, Provider.OLLAMA, Provider.GEMINI, Provider.CODEX],
    "plan": [Provider.CLAUDE, Provider.OLLAMA, Provider.GEMINI, Provider.CODEX],
    "implement": [Provider.CLAUDE, Provider.OLLAMA, Provider.CODEX, Provider.GEMINI],
    "test": [Provider.CLAUDE, Provider.OLLAMA, Provider.CODEX, Provider.GEMINI],
    "document": [Provider.CLAUDE, Provider.OLLAMA, Provider.GEMINI, Provider.CODEX],
    "general": [Provider.CLAUDE, Provider.OLLAMA, Provider.CODEX, Provider.GEMINI],
}


def detect_task_phase(title: str) -> str:
    """Detect task phase from title pattern"""
    title_lower = title.lower()
    if title_lower.startswith("research"):
        return "research"
    elif title_lower.startswith("plan"):
        return "plan"
    elif title_lower.startswith("implement"):
        return "implement"
    elif title_lower.startswith("test"):
        return "test"
    elif title_lower.startswith("document"):
        return "document"
    return "general"


def build_prompt(task: Dict, phase: str, provider: Provider) -> str:
    """Build provider-optimized prompt for task"""
    title = task.get("title", "Unknown Task")
    description = task.get("description", "No description")
    goal_id = task.get("goal_id")

    base = f"""Task: {title}
Description: {description}
Goal ID: {goal_id}

Provide concrete, actionable output. No placeholders or TODOs.
Keep response focused and under 2000 words.
"""

    phase_context = {
        "research": "PHASE: Research\nAnalyze requirements, identify technical approaches, note challenges and resources needed.",
        "plan": "PHASE: Planning\nCreate step-by-step implementation plan with clear success criteria.",
        "implement": "PHASE: Implementation\nProvide production-ready code with proper error handling.",
        "test": "PHASE: Testing\nVerify implementation, check edge cases, validate all requirements.",
        "document": "PHASE: Documentation\nDocument implementation, usage instructions, and examples.",
        "general": "Execute this task and provide concrete results."
    }

    # Provider-specific optimizations
    if provider == Provider.CODEX:
        return f"You are an expert programmer.\n\n{base}\n{phase_context.get(phase, '')}\n\nFocus on clean, efficient code."
    elif provider == Provider.GEMINI:
        return f"{base}\n{phase_context.get(phase, '')}\n\nBe thorough but concise."
    else:
        return f"{base}\n{phase_context.get(phase, '')}"


def check_provider_available(provider: Provider) -> bool:
    """Check if a provider CLI is available"""
    if provider == Provider.OLLAMA:
        return check_ollama_available()
    
    config = PROVIDERS.get(provider)
    if not config:
        return False
    
    try:
        cmd = config.command[0]
        result = subprocess.run(
            ["which", cmd],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def check_ollama_available() -> bool:
    """Check if Ollama is available with a suitable model"""
    try:
        url = f"{OLLAMA_HOST}/api/tags"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            models = [m.get("name", "") for m in data.get("models", [])]
            model_base = OLLAMA_MODEL.split(":")[0]
            return any(model_base in m for m in models)
    except Exception:
        return False


# Track last update check time
_last_update_check = 0
_UPDATE_CHECK_INTERVAL = 3600 * 24  # 24 hours


def check_and_update_providers() -> Dict[str, str]:
    """
    Check for updates to Codex and Gemini CLI.
    Runs at most once per day to avoid slowing down task execution.

    Returns dict with update status for each provider.
    """
    import time
    global _last_update_check

    current_time = time.time()
    if current_time - _last_update_check < _UPDATE_CHECK_INTERVAL:
        return {"status": "skipped", "reason": "checked recently"}

    _last_update_check = current_time
    results = {}

    try:
        # Update Codex CLI
        logger.info("Checking for Codex CLI updates...")
        codex_result = subprocess.run(
            ["npm", "update", "-g", "@openai/codex"],
            capture_output=True,
            timeout=60,
            text=True
        )
        results["codex"] = "updated" if codex_result.returncode == 0 else "failed"
    except Exception as e:
        results["codex"] = f"error: {e}"

    try:
        # Update Gemini CLI
        logger.info("Checking for Gemini CLI updates...")
        gemini_result = subprocess.run(
            ["npm", "update", "-g", "@google/gemini-cli"],
            capture_output=True,
            timeout=60,
            text=True
        )
        results["gemini"] = "updated" if gemini_result.returncode == 0 else "failed"
    except Exception as e:
        results["gemini"] = f"error: {e}"

    logger.info(f"Provider update check complete: {results}")
    return results


def run_cli_provider(provider: Provider, prompt: str) -> Dict:
    """Execute task using CLI provider (Claude, Codex, Gemini)"""
    config = PROVIDERS.get(provider)
    if not config:
        return {"success": False, "error": f"Unknown provider: {provider}"}

    try:
        # Build command with prompt
        cmd = []
        for part in config.command:
            if "{prompt}" in part:
                cmd.append(prompt)
            else:
                cmd.append(part)

        env = os.environ.copy()
        env["CLAUDE_CODE_ENTRYPOINT"] = "temporal-worker"

        logger.info(f"Executing with {config.name}...")

        # Use script wrapper for TTY-requiring tools (Codex, Gemini)
        if provider in [Provider.CODEX, Provider.GEMINI]:
            # Wrap with script to provide pseudo-terminal
            cmd = ["script", "-q", "/dev/null"] + cmd

        result = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,  # Prevent stdin issues
            capture_output=True,
            timeout=config.timeout,
            env=env,
            text=True
        )
        
        output = result.stdout.strip() if result.stdout else ""
        error = result.stderr.strip() if result.stderr else ""
        combined = (output + " " + error).lower()
        
        # Check for rate limit / credit issues
        needs_fallback = any(pattern in combined for pattern in config.rate_limit_patterns)
        
        success = (
            result.returncode == 0 and 
            len(output) >= config.success_min_length and 
            not needs_fallback
        )
        
        return {
            "success": success,
            "output": output[:10000] if output else None,
            "error": error if not success else None,
            "needs_fallback": needs_fallback,
            "provider": config.name
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"Timeout after {config.timeout}s",
            "needs_fallback": True,
            "provider": config.name
        }
    except FileNotFoundError:
        return {
            "success": False,
            "error": f"{config.name} CLI not found",
            "needs_fallback": True,
            "provider": config.name
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "needs_fallback": True,
            "provider": config.name
        }


def run_ollama(prompt: str, timeout_sec: int = 300) -> Dict:
    """Execute task using Ollama local model"""
    try:
        logger.info(f"Executing with Ollama ({OLLAMA_MODEL})...")
        
        url = f"{OLLAMA_HOST}/api/generate"
        data = json.dumps({
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 2000
            }
        }).encode("utf-8")
        
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=timeout_sec) as response:
            result = json.loads(response.read().decode("utf-8"))
        
        output = result.get("response", "").strip()
        success = len(output) > 50
        
        return {
            "success": success,
            "output": output[:10000] if output else None,
            "error": None if success else "Empty response",
            "needs_fallback": False,
            "provider": f"Ollama ({OLLAMA_MODEL})"
        }
        
    except Exception as e:
        logger.error(f"Ollama failed: {e}")
        return {
            "success": False,
            "output": None,
            "error": str(e),
            "needs_fallback": False,
            "provider": "Ollama"
        }


def execute_with_provider(provider: Provider, prompt: str) -> Dict:
    """Execute task with specified provider"""
    if provider == Provider.OLLAMA:
        return run_ollama(prompt)
    else:
        return run_cli_provider(provider, prompt)


async def execute_task_with_ai(task: Dict) -> Dict:
    """
    Main entry point: Execute task with intelligent provider selection and fallback.
    
    Routing strategy:
    1. Select optimal provider chain based on task phase
    2. Try providers in order until one succeeds
    3. Use Ollama as final fallback (always available)
    
    Returns:
        Result dict with success, output, error, phase, execution_method, providers_tried
    """
    task_id = task.get("id", "unknown")
    task_title = task.get("title", "Unknown")
    
    logger.info(f"Multi-provider executing task {task_id}: {task_title}")
    
    # Detect phase and get provider chain
    phase = detect_task_phase(task_title)
    provider_chain = PHASE_ROUTING.get(phase, PHASE_ROUTING["general"])
    
    logger.info(f"Task {task_id} phase: {phase}, provider chain: {[p.value for p in provider_chain]}")
    
    # Track attempts
    providers_tried = []
    errors = []
    
    # Run in thread pool
    loop = asyncio.get_event_loop()
    
    for provider in provider_chain:
        # Check availability first
        available = await loop.run_in_executor(None, lambda p=provider: check_provider_available(p))
        
        if not available:
            logger.info(f"Provider {provider.value} not available, skipping...")
            continue
        
        # Build provider-optimized prompt
        prompt = build_prompt(task, phase, provider)
        
        # Execute
        providers_tried.append(provider.value)
        result = await loop.run_in_executor(
            None,
            lambda p=provider, pr=prompt: execute_with_provider(p, pr)
        )
        
        if result["success"]:
            logger.info(f"Task {task_id} succeeded with {result['provider']}")
            return {
                "success": True,
                "output": result.get("output"),
                "error": None,
                "phase": phase,
                "execution_method": result["provider"],
                "providers_tried": providers_tried,
                "task_id": task_id
            }
        
        # Log failure and continue to next provider
        error_msg = result.get("error", "Unknown error")
        errors.append(f"{provider.value}: {error_msg}")
        logger.warning(f"Provider {provider.value} failed: {error_msg}")
        
        if not result.get("needs_fallback", True):
            # Hard failure, don't try more providers
            break
    
    # All providers failed
    logger.error(f"Task {task_id} failed with all providers: {errors}")
    return {
        "success": False,
        "output": None,
        "error": f"All providers failed: {'; '.join(errors)}",
        "phase": phase,
        "execution_method": "all_failed",
        "providers_tried": providers_tried,
        "task_id": task_id
    }


def get_provider_status() -> Dict:
    """Get availability status of all providers"""
    status = {}
    for provider in Provider:
        status[provider.value] = check_provider_available(provider)
    return status


if __name__ == "__main__":
    print("Multi-Provider Task Executor")
    print("=" * 60)
    
    print("\nProvider Status:")
    status = get_provider_status()
    for provider, available in status.items():
        icon = "✅" if available else "❌"
        print(f"  {icon} {provider}")
    
    print("\nPhase Routing:")
    for phase, chain in PHASE_ROUTING.items():
        print(f"  {phase}: {' → '.join(p.value for p in chain)}")
    
    print("\nModule ready!")


# ============================================================================
# CUSTOM TRAINED MODEL SUPPORT
# ============================================================================

# Custom model configuration - for models trained on system-specific data
CUSTOM_MODEL_CONFIG = {
    "enabled": os.environ.get("CUSTOM_MODEL_ENABLED", "true").lower() == "true",
    "host": os.environ.get("CUSTOM_MODEL_HOST", "http://localhost:11434"),  # Default to Ollama
    "model": os.environ.get("CUSTOM_MODEL_NAME", "agentic-task-executor"),  # Custom fine-tuned model
    "fallback_model": os.environ.get("CUSTOM_MODEL_FALLBACK", "qwen2.5-coder:14b"),
    "priority_phases": ["implement", "test"],  # Phases where custom model is preferred
}


def check_custom_model_available() -> bool:
    """Check if custom trained model is available"""
    if not CUSTOM_MODEL_CONFIG["enabled"]:
        return False
    
    try:
        url = f"{CUSTOM_MODEL_CONFIG['host']}/api/tags"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            models = [m.get("name", "") for m in data.get("models", [])]
            return CUSTOM_MODEL_CONFIG["model"] in models
    except Exception:
        return False


def run_custom_model(prompt: str, timeout_sec: int = 300) -> Dict:
    """Execute task using custom trained model"""
    try:
        model = CUSTOM_MODEL_CONFIG["model"]
        host = CUSTOM_MODEL_CONFIG["host"]
        
        logger.info(f"Executing with custom model ({model})...")
        
        url = f"{host}/api/generate"
        data = json.dumps({
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.5,  # Lower temp for trained model
                "num_predict": 2000
            }
        }).encode("utf-8")
        
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=timeout_sec) as response:
            result = json.loads(response.read().decode("utf-8"))
        
        output = result.get("response", "").strip()
        success = len(output) > 50
        
        return {
            "success": success,
            "output": output[:10000] if output else None,
            "error": None if success else "Empty response",
            "needs_fallback": not success,
            "provider": f"Custom Model ({model})"
        }
        
    except Exception as e:
        logger.warning(f"Custom model failed: {e}")
        return {
            "success": False,
            "output": None,
            "error": str(e),
            "needs_fallback": True,
            "provider": "Custom Model"
        }


# Extended provider enum with custom model
class ExtendedProvider(Enum):
    CUSTOM = "custom"
    CLAUDE = "claude"
    CODEX = "codex"
    GEMINI = "gemini"
    OLLAMA = "ollama"


# Enhanced phase routing with custom model for specific tasks
# NOTE: Claude and Ollama work in non-TTY environments (background workers)
# Codex and Gemini require interactive terminals - placed lower in chain
ENHANCED_PHASE_ROUTING = {
    # Implementation: Custom (codebase patterns) -> Claude -> Ollama -> TTY providers
    "implement": [ExtendedProvider.CUSTOM, ExtendedProvider.CLAUDE, ExtendedProvider.OLLAMA,
                  ExtendedProvider.CODEX, ExtendedProvider.GEMINI],

    # Testing: Custom (test patterns) -> Claude -> Ollama -> TTY providers
    "test": [ExtendedProvider.CUSTOM, ExtendedProvider.CLAUDE, ExtendedProvider.OLLAMA,
             ExtendedProvider.CODEX, ExtendedProvider.GEMINI],

    # Research: Claude (reasoning) -> Ollama -> TTY providers
    "research": [ExtendedProvider.CLAUDE, ExtendedProvider.OLLAMA, ExtendedProvider.CUSTOM,
                 ExtendedProvider.GEMINI, ExtendedProvider.CODEX],

    # Planning: Claude (reasoning) -> Ollama -> TTY providers
    "plan": [ExtendedProvider.CLAUDE, ExtendedProvider.OLLAMA, ExtendedProvider.CUSTOM,
             ExtendedProvider.GEMINI, ExtendedProvider.CODEX],

    # Documentation: Claude -> Ollama -> TTY providers
    "document": [ExtendedProvider.CLAUDE, ExtendedProvider.OLLAMA, ExtendedProvider.CUSTOM,
                 ExtendedProvider.GEMINI, ExtendedProvider.CODEX],

    # General: Claude -> Ollama -> Custom -> TTY providers
    "general": [ExtendedProvider.CLAUDE, ExtendedProvider.OLLAMA, ExtendedProvider.CUSTOM,
                ExtendedProvider.CODEX, ExtendedProvider.GEMINI],
}


async def execute_task_with_smart_routing(task: Dict) -> Dict:
    """
    Enhanced task execution with custom model support.

    Routing strategy:
    1. For implementation/testing: Try custom model first (knows codebase patterns)
    2. For research/docs: Use external models (broader knowledge)
    3. Always fallback through chain to Ollama
    """
    task_id = task.get("id", "unknown")
    task_title = task.get("title", "Unknown")

    # Check for provider updates (runs at most once per day)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, check_and_update_providers)

    logger.info(f"Smart routing task {task_id}: {task_title}")
    
    phase = detect_task_phase(task_title)
    provider_chain = ENHANCED_PHASE_ROUTING.get(phase, ENHANCED_PHASE_ROUTING["general"])
    
    logger.info(f"Task {task_id} phase: {phase}, chain: {[p.value for p in provider_chain]}")
    
    providers_tried = []
    errors = []
    loop = asyncio.get_event_loop()
    
    for provider in provider_chain:
        # Check availability
        if provider == ExtendedProvider.CUSTOM:
            available = await loop.run_in_executor(None, check_custom_model_available)
        elif provider == ExtendedProvider.OLLAMA:
            available = await loop.run_in_executor(None, check_ollama_available)
        else:
            available = await loop.run_in_executor(
                None, 
                lambda p=Provider(provider.value): check_provider_available(p)
            )
        
        if not available:
            logger.info(f"Provider {provider.value} not available, skipping...")
            continue
        
        # Build prompt
        if provider in [ExtendedProvider.CUSTOM, ExtendedProvider.OLLAMA]:
            prompt = build_prompt(task, phase, Provider.CLAUDE)  # Use standard prompt
        else:
            prompt = build_prompt(task, phase, Provider(provider.value))
        
        # Execute
        providers_tried.append(provider.value)
        
        if provider == ExtendedProvider.CUSTOM:
            result = await loop.run_in_executor(None, lambda pr=prompt: run_custom_model(pr))
        elif provider == ExtendedProvider.OLLAMA:
            result = await loop.run_in_executor(None, lambda pr=prompt: run_ollama(pr))
        else:
            result = await loop.run_in_executor(
                None,
                lambda p=Provider(provider.value), pr=prompt: execute_with_provider(p, pr)
            )
        
        if result["success"]:
            logger.info(f"Task {task_id} succeeded with {result['provider']}")
            return {
                "success": True,
                "output": result.get("output"),
                "error": None,
                "phase": phase,
                "execution_method": result["provider"],
                "providers_tried": providers_tried,
                "task_id": task_id
            }
        
        error_msg = result.get("error", "Unknown error")
        errors.append(f"{provider.value}: {error_msg}")
        logger.warning(f"Provider {provider.value} failed: {error_msg}")
        
        if not result.get("needs_fallback", True):
            break
    
    logger.error(f"Task {task_id} failed: {errors}")
    return {
        "success": False,
        "output": None,
        "error": f"All providers failed: {'; '.join(errors)}",
        "phase": phase,
        "execution_method": "all_failed",
        "providers_tried": providers_tried,
        "task_id": task_id
    }


# Export the smart routing function as the main entry point
execute_task_with_ai = execute_task_with_smart_routing
