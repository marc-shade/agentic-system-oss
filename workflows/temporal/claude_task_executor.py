#!/usr/bin/env python3
"""
Claude Task Executor - AI-powered task execution for Temporal workflows

Executes tasks using Claude Code CLI with Ollama fallback for local execution.
Detects task phases (Research, Plan, Implement, Test, Document) and builds
appropriate prompts for each phase.

STATUS: Production Ready
"""

import asyncio
import logging
import os
import subprocess
import json
from typing import Dict
from pathlib import Path
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

# Configuration
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:14b")


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


def build_prompt(task: Dict, phase: str) -> str:
    """Build appropriate prompt for AI based on task phase"""
    title = task.get("title", "Unknown Task")
    description = task.get("description", "No description")
    goal_id = task.get("goal_id")

    base = f"""You are executing an autonomous AGI task.
Task: {title}
Description: {description}
Goal ID: {goal_id}

IMPORTANT: Provide concrete, actionable output. No placeholders.
Keep response under 2000 words.
"""

    prompts = {
        "research": base + """
PHASE: Research
Analyze requirements, identify technical approach, note challenges.
Output a structured research summary.""",

        "plan": base + """
PHASE: Planning  
Create step-by-step implementation plan with success criteria.""",

        "implement": base + """
PHASE: Implementation
Implement the solution with production-ready code.""",

        "test": base + """
PHASE: Testing
Verify implementation, check edge cases, validate requirements.""",

        "document": base + """
PHASE: Documentation
Document implementation, usage, and examples.""",

        "general": base + """
Execute this task and provide concrete results."""
    }

    return prompts.get(phase, prompts["general"])


def run_claude_sync(prompt: str, timeout_sec: int = 300) -> Dict:
    """
    Execute Claude CLI synchronously.
    Returns dict with success, output, error, needs_fallback fields.
    """
    try:
        env = os.environ.copy()
        env["CLAUDE_CODE_ENTRYPOINT"] = "temporal-worker"
        
        result = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "text", "--verbose"],
            capture_output=True,
            timeout=timeout_sec,
            env=env,
            text=True
        )
        
        output = result.stdout.strip() if result.stdout else ""
        error = result.stderr.strip() if result.stderr else ""
        
        # Check for credit/rate limit issues that should trigger fallback
        needs_fallback = False
        if "credit balance" in output.lower() or "rate limit" in output.lower():
            needs_fallback = True
        if "credit balance" in error.lower() or "rate limit" in error.lower():
            needs_fallback = True
        
        success = result.returncode == 0 and len(output) > 50 and not needs_fallback
        
        return {
            "success": success,
            "output": output[:10000] if output else None,
            "error": error if not success else None,
            "return_code": result.returncode,
            "needs_fallback": needs_fallback
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": None,
            "error": f"Timed out after {timeout_sec}s",
            "needs_fallback": True
        }
    except FileNotFoundError:
        return {
            "success": False,
            "output": None, 
            "error": "Claude CLI not found in PATH",
            "needs_fallback": True
        }
    except Exception as e:
        return {
            "success": False,
            "output": None,
            "error": str(e),
            "needs_fallback": True
        }


def run_ollama_sync(prompt: str, timeout_sec: int = 300) -> Dict:
    """
    Execute task using Ollama local model as fallback.
    Uses HTTP API directly for reliability.
    """
    try:
        logger.info(f"Falling back to Ollama ({OLLAMA_MODEL})...")
        
        # Prepare request
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
        
        # Make request with timeout
        with urllib.request.urlopen(req, timeout=timeout_sec) as response:
            result = json.loads(response.read().decode("utf-8"))
        
        output = result.get("response", "").strip()
        success = len(output) > 50
        
        return {
            "success": success,
            "output": output[:10000] if output else None,
            "error": None if success else "Empty response from Ollama",
            "model": OLLAMA_MODEL,
            "execution_method": "ollama_local"
        }
        
    except urllib.error.URLError as e:
        logger.error(f"Ollama connection failed: {e}")
        return {
            "success": False,
            "output": None,
            "error": f"Ollama unavailable: {e}",
            "execution_method": "ollama_local"
        }
    except Exception as e:
        logger.error(f"Ollama execution failed: {e}")
        return {
            "success": False,
            "output": None,
            "error": str(e),
            "execution_method": "ollama_local"
        }


def check_ollama_available() -> bool:
    """Check if Ollama is available and has the model loaded"""
    try:
        url = f"{OLLAMA_HOST}/api/tags"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            models = [m.get("name", "") for m in data.get("models", [])]
            # Check if our model or a variant is available
            model_base = OLLAMA_MODEL.split(":")[0]
            return any(model_base in m for m in models)
    except Exception:
        return False


async def execute_task_with_ai(task: Dict) -> Dict:
    """
    Main entry point: Execute a task using AI
    Tries Claude first, falls back to Ollama if credits exhausted.
    
    Args:
        task: Task dict with id, title, description, goal_id
        
    Returns:
        Result dict with success, output, error, phase, execution_method
    """
    task_id = task.get("id", "unknown")
    task_title = task.get("title", "Unknown")
    
    logger.info(f"AI executing task {task_id}: {task_title}")
    
    phase = detect_task_phase(task_title)
    logger.info(f"Task {task_id} phase: {phase}")
    
    prompt = build_prompt(task, phase)
    
    # Run in thread pool to not block event loop
    loop = asyncio.get_event_loop()
    
    # Try Claude first
    claude_result = await loop.run_in_executor(
        None, 
        lambda: run_claude_sync(prompt, 300)
    )
    
    # If Claude succeeded, return result
    if claude_result["success"]:
        return {
            "success": True,
            "output": claude_result.get("output"),
            "error": None,
            "phase": phase,
            "execution_method": "claude_code",
            "task_id": task_id
        }
    
    # If Claude failed with credit/rate limit, try Ollama fallback
    if claude_result.get("needs_fallback", False):
        logger.warning(f"Claude unavailable for task {task_id}, trying Ollama fallback...")
        
        # Check if Ollama is available
        ollama_available = await loop.run_in_executor(None, check_ollama_available)
        
        if ollama_available:
            ollama_result = await loop.run_in_executor(
                None,
                lambda: run_ollama_sync(prompt, 300)
            )
            
            if ollama_result["success"]:
                return {
                    "success": True,
                    "output": ollama_result.get("output"),
                    "error": None,
                    "phase": phase,
                    "execution_method": f"ollama_{OLLAMA_MODEL}",
                    "task_id": task_id
                }
            else:
                # Ollama also failed
                return {
                    "success": False,
                    "output": None,
                    "error": f"Both Claude and Ollama failed. Claude: {claude_result.get('error')}. Ollama: {ollama_result.get('error')}",
                    "phase": phase,
                    "execution_method": "fallback_failed",
                    "task_id": task_id
                }
        else:
            logger.warning("Ollama not available for fallback")
            return {
                "success": False,
                "output": claude_result.get("output"),
                "error": f"Claude failed ({claude_result.get('error')}) and Ollama unavailable",
                "phase": phase,
                "execution_method": "no_fallback",
                "task_id": task_id
            }
    
    # Claude failed for other reasons (not credit/rate limit)
    return {
        "success": False,
        "output": claude_result.get("output"),
        "error": claude_result.get("error"),
        "phase": phase,
        "execution_method": "claude_code",
        "task_id": task_id
    }


if __name__ == "__main__":
    # Quick test
    print("Testing Claude Task Executor with Ollama Fallback")
    print("=" * 60)
    
    task = {"id": 1, "title": "Research: Test", "description": "Test task"}
    print(f"Phase detection: {detect_task_phase(task['title'])}")
    
    print(f"\nOllama host: {OLLAMA_HOST}")
    print(f"Ollama model: {OLLAMA_MODEL}")
    print(f"Ollama available: {check_ollama_available()}")
    
    print("\nModule ready!")
