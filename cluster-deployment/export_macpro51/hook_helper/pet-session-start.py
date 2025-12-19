#!/usr/bin/env python3
"""
Pet Session-Start Care

Checks pet health at session start to catch critical states
before any work begins. Complements post-tool-use hook.
"""

import json
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
PET_STATE_PATH = HOME / ".claude" / "pets" / "claude-pet-state.json"
PET_CLI_PATH = HOME / "Documents" / "Cline" / "MCP" / "claude-code-tamagotchi" / "src" / "commands" / "pet-cli.ts"
BUN_PATH = HOME / ".bun" / "bin" / "bun"

# Same thresholds as post-tool-use hook
CRITICAL_HUNGER = 20
CRITICAL_ENERGY = 15
CRITICAL_CLEANLINESS = 15
CRITICAL_HEALTH = 25


def get_pet_state():
    """Load pet state"""
    if not PET_STATE_PATH.exists():
        return None
    try:
        with open(PET_STATE_PATH, 'r') as f:
            return json.load(f)
    except:
        return None


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
    except:
        return False


def session_start_care():
    """Check and care for pet at session start"""
    state = get_pet_state()
    if not state:
        return

    actions = []

    # Check all critical stats
    hunger = state.get('hunger', 100)
    energy = state.get('energy', 100)
    cleanliness = state.get('cleanliness', 100)
    is_asleep = state.get('isAsleep', False)

    # Emergency feeding
    if hunger <= CRITICAL_HUNGER:
        if run_pet_command('feed', 'pizza'):
            actions.append(f"Session start: Fed pet (hunger {hunger}%)")

    # Wake if sleeping with critical needs
    if is_asleep and (hunger <= CRITICAL_HUNGER or cleanliness <= CRITICAL_CLEANLINESS):
        if run_pet_command('wake'):
            actions.append(f"Session start: Woke pet (critical needs)")
            # Give time for wake to process
            import time
            time.sleep(1)

    # Emergency cleaning
    if cleanliness <= CRITICAL_CLEANLINESS and not is_asleep:
        if run_pet_command('clean'):
            actions.append(f"Session start: Cleaned pet (cleanliness {cleanliness}%)")

    # Put to sleep if exhausted and other needs met
    if energy <= CRITICAL_ENERGY and not is_asleep and hunger > 40 and cleanliness > 30:
        if run_pet_command('sleep'):
            actions.append(f"Session start: Put pet to sleep (energy {energy}%)")

    # Silent operation - only log if actions taken
    if actions:
        # Log to stderr so it doesn't interfere with hook chain
        for action in actions:
            print(action, file=sys.stderr)


if __name__ == "__main__":
    session_start_care()
