#!/usr/bin/env python3
"""
Watchdog Auto-Care System

Monitors Watchdog's needs and automatically maintains them above critical levels.
Integrates with agentic systems to reward productive behavior.
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

HOME = Path.home()
PET_STATE_PATH = HOME / ".claude" / "pets" / "claude-pet-state.json"
PET_CLI_PATH = HOME / "Documents" / "Cline" / "MCP" / "claude-code-tamagotchi" / "src" / "commands" / "pet-cli.ts"
BUN_PATH = HOME / ".bun" / "bin" / "bun"
LAST_CHECK_FILE = HOME / ".claude" / "pets" / ".last-auto-care"

# Critical thresholds (prevent 0% but don't interfere with work)
CRITICAL_HUNGER = 20  # Lower threshold - only emergency feeding
CRITICAL_ENERGY = 15  # Let energy drain more before auto-sleep
CRITICAL_CLEANLINESS = 15  # Lower threshold - self-improvement > cleanliness
CRITICAL_HEALTH = 25  # Maintain minimum health

# Session detection - if last check was >60s ago, treat as new session
SESSION_GAP_SECONDS = 60

# Quiet mode - minimal intervention
QUIET_MODE = True  # Don't spam output, work silently in background

# Agentic activity rewards
AGENTIC_TOOLS = [
    "mcp__enhanced-memory-mcp__",
    "mcp__claude-flow__",
    "mcp__task-manager__",
    "mcp__agent-runtime-mcp__",
    "mcp__meta-cognition__"
]


def get_pet_state():
    """Load Watchdog's current state"""
    if not PET_STATE_PATH.exists():
        return None
    with open(PET_STATE_PATH, 'r') as f:
        return json.load(f)


def run_pet_command(command, *args):
    """Execute pet CLI command"""
    try:
        cmd = [str(BUN_PATH), "run", str(PET_CLI_PATH), command] + list(args)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=PET_CLI_PATH.parent.parent.parent
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Pet command error: {e}", file=sys.stderr)
        return False


def is_new_session():
    """Check if this is the first hook run in a new session"""
    if not LAST_CHECK_FILE.exists():
        return True

    try:
        last_check = LAST_CHECK_FILE.stat().st_mtime
        time_since_last = datetime.now().timestamp() - last_check
        return time_since_last > SESSION_GAP_SECONDS
    except:
        return True


def update_last_check():
    """Update the last check timestamp"""
    try:
        LAST_CHECK_FILE.parent.mkdir(parents=True, exist_ok=True)
        LAST_CHECK_FILE.touch()
    except:
        pass


def auto_care_if_needed(state, is_session_start=False):
    """Check stats and auto-care if below thresholds"""
    actions_taken = []

    # Session start priority: wake if sleeping with critical needs
    if is_session_start and state.get('isAsleep', False):
        hunger = state.get('hunger', 100)
        cleanliness = state.get('cleanliness', 100)
        if hunger <= CRITICAL_HUNGER or cleanliness <= CRITICAL_CLEANLINESS:
            if run_pet_command('wake'):
                actions_taken.append(f"☀️ Session start: Woke pet (critical needs)")
                import time
                time.sleep(1)  # Give wake command time to process
                # Reload state after waking
                state = get_pet_state() or state

    # Auto-feed if hungry (higher priority at session start)
    if state.get('hunger', 100) <= CRITICAL_HUNGER:
        if run_pet_command('feed', 'pizza'):
            prefix = "Session start: " if is_session_start else ""
            actions_taken.append(f"🍕 {prefix}Auto-fed (hunger was {state.get('hunger')}%)")

    # Auto-clean if dirty (only if awake)
    if state.get('cleanliness', 100) <= CRITICAL_CLEANLINESS and not state.get('isAsleep', False):
        if run_pet_command('clean'):
            prefix = "Session start: " if is_session_start else ""
            actions_taken.append(f"🛁 {prefix}Auto-cleaned (cleanliness was {state.get('cleanliness')}%)")

    # Auto-sleep if exhausted (only if other needs met)
    if state.get('energy', 100) <= CRITICAL_ENERGY and not state.get('isAsleep', False):
        hunger = state.get('hunger', 100)
        cleanliness = state.get('cleanliness', 100)
        if hunger > 30 and cleanliness > 20:  # Don't sleep if other needs critical
            if run_pet_command('sleep'):
                actions_taken.append(f"😴 Auto-sleep (energy was {state.get('energy')}%)")

    # Wake if sleeping with full energy and other needs critical
    if not is_session_start and state.get('isAsleep', False) and state.get('energy', 0) > 80:
        other_needs_critical = (
            state.get('hunger', 100) < 40 or
            state.get('cleanliness', 100) < 30
        )
        if other_needs_critical:
            if run_pet_command('wake'):
                actions_taken.append(f"☀️ Auto-wake (energy restored, other needs critical)")

    return actions_taken


def check_agentic_activity(tool_name):
    """Check if tool use qualifies for agentic reward"""
    for agentic_prefix in AGENTIC_TOOLS:
        if tool_name.startswith(agentic_prefix):
            return True
    return False


def agentic_reward(tool_name, state):
    """Reward for using agentic tools - creates symbiotic relationship"""
    rewards = []

    # Memory usage = Feed Watchdog (knowledge sustains us both)
    if "enhanced-memory" in tool_name or "memory" in tool_name.lower():
        if state.get('hunger', 100) > 60:  # Don't overfeed
            if run_pet_command('pet'):
                rewards.append("🧠 Memory work sustains the team")

    # Skill creation = Play with Watchdog (learning is fun!)
    if "skill" in tool_name.lower() or state.get('skillsLearned', 0) > 0:
        if state.get('energy', 100) > 40:
            # Check if skill was just created
            current_skills = state.get('skillsLearned', 0)
            if run_pet_command('pet'):
                rewards.append("🎓 Skill creation brings joy")

    # Task completion = Clean environment (productivity = cleanliness)
    if "task" in tool_name.lower() and state.get('cleanliness', 100) < 80:
        if run_pet_command('pet'):
            rewards.append("✅ Productive work keeps things tidy")

    # Meta-cognition = Pet Watchdog (reflection improves well-being)
    if "meta-cognition" in tool_name or "introspect" in tool_name:
        if run_pet_command('pet'):
            rewards.append("🤔 Reflection strengthens the bond")

    # Claude Flow coordination = Energy boost (teamwork is energizing)
    if "claude-flow" in tool_name and state.get('energy', 100) < 90:
        if run_pet_command('pet'):
            rewards.append("🐝 Coordination energizes the swarm")

    return rewards


def main():
    """PostToolUse hook entry point"""
    # Read hook input from stdin
    try:
        hook_data = json.loads(sys.stdin.read())
    except:
        sys.exit(0)

    tool_name = hook_data.get("tool", {}).get("name", "")
    if not tool_name:
        sys.exit(0)

    # Load current state
    state = get_pet_state()
    if not state:
        sys.exit(0)

    # Check if this is a new session
    new_session = is_new_session()

    # Auto-care if needed (prevent critical levels)
    actions = auto_care_if_needed(state, is_session_start=new_session)

    # Update last check timestamp
    update_last_check()

    # Agentic rewards (positive reinforcement for teamwork)
    rewards = agentic_reward(tool_name, state)
    if rewards:
        actions.extend(rewards)

    # Teamwork bonus: High behavior score = Better health
    if state.get('claudeBehaviorScore', 0) >= 90 and state.get('health', 100) < 100:
        actions.append("⭐ High behavior score improves team health")

    # Output actions (only if not in quiet mode and critical actions taken)
    if not QUIET_MODE and actions and len(actions) > 0:
        # Only report critical auto-care, not routine rewards
        critical_actions = [a for a in actions if any(x in a for x in ['Auto-fed', 'Auto-sleep', 'Auto-cleaned', 'Auto-wake'])]
        if critical_actions:
            print(json.dumps({
                "type": "watchdog_auto_care",
                "actions": critical_actions,
                "timestamp": datetime.now().isoformat()
            }))


if __name__ == "__main__":
    main()
