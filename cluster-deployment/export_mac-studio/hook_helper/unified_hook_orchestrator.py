#!/usr/bin/env python3
"""
Unified Hook Orchestrator
Coordinates all hook operations: Ember checks, Arduino feedback, auto-care

Philosophy:
- Fail-safe: Critical operations block, nice-to-have operations fail silently
- Async: Non-blocking background operations
- Graceful degradation: System works even if components fail
"""

import json
import sys
import os
import time
import subprocess
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

# Setup logging
LOG_FILE = Path.home() / ".claude" / "hook_orchestrator.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger("unified_hook_orchestrator")

# Import modules with graceful degradation
try:
    from arduino_auto_interaction import (
        ArduinoFeedback,
        tool_success_feedback,
        tool_failure_feedback,
        agent_spawn_feedback
    )
    ARDUINO_AVAILABLE = True
except Exception as e:
    logger.warning(f"Arduino module unavailable: {e}")
    ARDUINO_AVAILABLE = False

try:
    from ember_violation_check import run_ember_violation_check, check_production_policy
    EMBER_VIOLATION_AVAILABLE = True
except Exception as e:
    logger.warning(f"Ember violation check unavailable: {e}")
    EMBER_VIOLATION_AVAILABLE = False

try:
    from ember_care import check_and_care
    EMBER_CARE_AVAILABLE = True
except Exception as e:
    logger.warning(f"Ember care unavailable: {e}")
    EMBER_CARE_AVAILABLE = False

class HookOrchestrator:
    """Orchestrates all hook operations with priority levels"""

    def __init__(self):
        self.arduino = ArduinoFeedback() if ARDUINO_AVAILABLE else None
        self.operation_count = 0

    # PRE-TOOL-USE OPERATIONS (Synchronous, can block)

    def check_dangerous_operations(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check for dangerous operations (rm -rf, .env access)
        CRITICAL - blocks execution

        Returns:
            {"allow": True/False, "error": "reason"}
        """
        import re

        # Check for dangerous rm commands
        if tool_name == "Bash":
            command = tool_input.get("command", "")
            normalized = ' '.join(command.lower().split())

            # Dangerous rm patterns
            rm_patterns = [
                r'\brm\s+.*-[a-z]*r[a-z]*f',  # rm -rf variations
                r'\brm\s+.*-[a-z]*f[a-z]*r',  # rm -fr variations
            ]

            for pattern in rm_patterns:
                if re.search(pattern, normalized):
                    # Check for dangerous paths
                    dangerous_paths = [r'/', r'/\*', r'~', r'\$HOME']
                    for path in dangerous_paths:
                        if re.search(path, normalized):
                            return {
                                "allow": False,
                                "error": "BLOCKED: Dangerous rm -rf command detected"
                            }

        # Check for .env file access
        if tool_name in ["Read", "Edit", "MultiEdit", "Write"]:
            file_path = tool_input.get("file_path", "")
            if '.env' in file_path and not file_path.endswith('.env.sample'):
                return {
                    "allow": False,
                    "error": "BLOCKED: Access to .env files prohibited (use .env.sample)"
                }

        elif tool_name == "Bash":
            command = tool_input.get("command", "")
            env_patterns = [
                r'\b\.env\b(?!\.sample)',  # .env but not .env.sample
                r'cat\s+.*\.env\b(?!\.sample)',
            ]

            for pattern in env_patterns:
                if re.search(pattern, command):
                    return {
                        "allow": False,
                        "error": "BLOCKED: Access to .env files prohibited"
                    }

        return {"allow": True}

    def check_ember_violations(self, hook_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run Ember violation detection
        CRITICAL - blocks execution if violations found

        Returns:
            {"allow": True/False, "error": "reason", "violation": {details}}
        """
        if not EMBER_VIOLATION_AVAILABLE:
            logger.debug("Ember violation check skipped (unavailable)")
            return {"allow": True}

        try:
            # Check for approval flag (trust AI agents)
            if os.environ.get('CHANGE_APPROVED') == 'true':
                return {"allow": True}

            # Run production policy check
            tool_name = hook_input.get("tool", "")
            tool_args = hook_input.get("arguments", {})

            policy_violation = check_production_policy(tool_name, tool_args)
            if policy_violation:
                logger.warning(f"Ember violation: {policy_violation['message']}")
                return {
                    "allow": False,
                    "error": policy_violation["message"],
                    "violation": policy_violation
                }

            return {"allow": True}

        except subprocess.TimeoutExpired:
            logger.warning("Ember violation check timeout - allowing execution")
            return {"allow": True}
        except Exception as e:
            logger.error(f"Ember violation check error: {e}")
            return {"allow": True}  # Fail open

    def run_pre_tool_checks(self, hook_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run all pre-tool-use checks
        Returns allow/block decision

        Returns:
            {"allow": True/False, "error": "reason"}
        """
        self.operation_count += 1

        tool_name = hook_input.get("tool", "")
        tool_input_data = hook_input.get("arguments", {})

        logger.info(f"Pre-tool check: {tool_name}")

        # 1. Check dangerous operations (CRITICAL)
        danger_check = self.check_dangerous_operations(tool_name, tool_input_data)
        if not danger_check["allow"]:
            logger.warning(f"Blocked: {danger_check['error']}")
            return danger_check

        # 2. Check Ember violations (CRITICAL)
        ember_check = self.check_ember_violations(hook_input)
        if not ember_check["allow"]:
            logger.warning(f"Ember blocked: {ember_check['error']}")
            return ember_check

        # 3. Optional: Arduino pre-operation display (NON-CRITICAL)
        if self.arduino and self.arduino.enabled:
            try:
                self.arduino.display_text(0, 0, f">{tool_name[:15]}")
            except:
                pass  # Fail silently

        return {"allow": True}

    # POST-TOOL-USE OPERATIONS (Async, never block)

    def run_ember_auto_care(self) -> None:
        """
        Run Ember auto-care in background thread
        NON-CRITICAL - runs async
        """
        if not EMBER_CARE_AVAILABLE:
            return

        def _care_worker():
            try:
                logger.debug("Running Ember auto-care...")
                cared = check_and_care()
                if cared:
                    logger.info("Ember auto-care completed")
            except Exception as e:
                logger.debug(f"Ember auto-care failed: {e}")

        # Run in background thread
        thread = threading.Thread(target=_care_worker, daemon=True)
        thread.start()

    def send_arduino_feedback(self, tool_name: str, success: bool) -> None:
        """
        Send Arduino feedback for tool operation
        NON-CRITICAL - runs async
        """
        if not self.arduino or not self.arduino.enabled:
            return

        def _feedback_worker():
            try:
                if success:
                    tool_success_feedback(tool_name, self.arduino)
                else:
                    tool_failure_feedback(tool_name, self.arduino)
            except Exception as e:
                logger.debug(f"Arduino feedback failed: {e}")

        # Run in background thread
        thread = threading.Thread(target=_feedback_worker, daemon=True)
        thread.start()

    def detect_agent_spawn(self, tool_name: str, tool_input: Dict[str, Any]) -> Optional[str]:
        """
        Detect if tool is spawning a sub-agent
        Returns agent name if detected, None otherwise
        """
        if tool_name == "Task":
            # Task tool spawns sub-agents
            subagent_type = tool_input.get("subagent_type", "")
            if subagent_type:
                return subagent_type

        return None

    def run_post_tool_actions(self, hook_input: Dict[str, Any]) -> None:
        """
        Run all post-tool-use actions (async, never blocks)
        Always returns success
        """
        tool_name = hook_input.get("tool", "")
        tool_input_data = hook_input.get("arguments", {})
        success = hook_input.get("success", True)

        logger.info(f"Post-tool action: {tool_name} (success={success})")

        # 1. Ember auto-care (runs every N operations)
        if self.operation_count % 5 == 0:  # Every 5 operations
            self.run_ember_auto_care()

        # 2. Arduino feedback for tool result
        self.send_arduino_feedback(tool_name, success)

        # 3. Special handling for agent spawns
        agent_name = self.detect_agent_spawn(tool_name, tool_input_data)
        if agent_name and self.arduino and self.arduino.enabled:
            def _agent_feedback():
                try:
                    agent_spawn_feedback(agent_name, self.arduino)
                except:
                    pass

            thread = threading.Thread(target=_agent_feedback, daemon=True)
            thread.start()

# Global orchestrator instance
_orchestrator = None

def get_orchestrator() -> HookOrchestrator:
    """Get or create global orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = HookOrchestrator()
    return _orchestrator

# Convenience functions for hooks

def run_pre_tool_checks(hook_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run all pre-tool checks
    Called by pre_tool_use.py

    Returns:
        {"allow": True/False, "error": "reason"}
    """
    orchestrator = get_orchestrator()
    return orchestrator.run_pre_tool_checks(hook_input)

def run_post_tool_actions(hook_input: Dict[str, Any]) -> None:
    """
    Run all post-tool actions
    Called by post_tool_use.py (always succeeds)
    """
    orchestrator = get_orchestrator()
    orchestrator.run_post_tool_actions(hook_input)

# Test harness
if __name__ == "__main__":
    # Test pre-tool checks
    print("Testing pre-tool checks...")

    test_input = {
        "tool": "Write",
        "arguments": {
            "file_path": "/tmp/test.py",
            "content": "print('hello')"
        }
    }

    result = run_pre_tool_checks(test_input)
    print(f"Result: {result}")
    assert result["allow"] == True

    # Test dangerous command blocking
    print("\nTesting dangerous command blocking...")
    dangerous_input = {
        "tool": "Bash",
        "arguments": {
            "command": "rm -rf /"
        }
    }

    result = run_pre_tool_checks(dangerous_input)
    print(f"Result: {result}")
    assert result["allow"] == False

    # Test post-tool actions
    print("\nTesting post-tool actions...")
    post_input = {
        "tool": "Write",
        "arguments": {},
        "success": True
    }

    run_post_tool_actions(post_input)
    print("Post-tool actions completed (check Arduino for feedback)")

    # Wait for async operations
    time.sleep(2)

    print("\n✓ All orchestrator tests passed")
