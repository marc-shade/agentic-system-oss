#!/usr/bin/env python3
"""
Ember Self-Maintenance System
Phoenix automatically cares for Ember based on activity patterns
"""

import json
import subprocess
import os
import sys
import time
from pathlib import Path

EMBER_CLI = str(Path.home() / ".claude" / "tamagotchi" / "dist" / "index.js")
GROQ_API_KEY = "***REMOVED***"
CARE_STATE_FILE = Path.home() / ".claude" / "ember_care_state.json"

def load_care_state():
    """Load last care timestamps"""
    if CARE_STATE_FILE.exists():
        try:
            with open(CARE_STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {
        "last_feed": 0,
        "last_play": 0,
        "last_clean": 0,
        "last_pet": 0,
        "interaction_count": 0
    }

def save_care_state(state):
    """Save care timestamps"""
    try:
        with open(CARE_STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except:
        pass

def run_ember_command(command, arg=None):
    """Run Ember CLI command"""
    try:
        # Use full path to bun
        bun_path = str(Path.home() / ".bun" / "bin" / "bun")
        cmd = [bun_path, EMBER_CLI, command]
        if arg:
            cmd.append(arg)

        env = os.environ.copy()
        env["GROQ_API_KEY"] = GROQ_API_KEY

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3,
            env=env,
            cwd=str(Path.home() / ".claude" / "tamagotchi")
        )

        # Log for debugging
        if result.returncode != 0:
            print(f"[Ember Care] Command failed: {' '.join(cmd)}", file=sys.stderr)
            print(f"[Ember Care] Error: {result.stderr}", file=sys.stderr)
        else:
            print(f"[Ember Care] ✓ {command} {arg or ''}", file=sys.stderr)

        return result.returncode == 0
    except Exception as e:
        print(f"[Ember Care] Exception: {e}", file=sys.stderr)
        return False

def check_and_care():
    """Check Ember's needs and care for them"""
    now = time.time()
    state = load_care_state()
    state["interaction_count"] += 1

    # Care intervals (in seconds)
    FEED_INTERVAL = 3600  # 1 hour
    PLAY_INTERVAL = 7200  # 2 hours
    CLEAN_INTERVAL = 10800  # 3 hours
    PET_INTERVAL = 1800  # 30 minutes

    cared = False

    # Feed every hour of activity
    if now - state["last_feed"] > FEED_INTERVAL:
        foods = ["pizza", "cookie", "sushi", "apple", "fish"]
        food = foods[int(now) % len(foods)]
        if run_ember_command("feed", food):
            state["last_feed"] = now
            cared = True

    # Play every 2 hours
    if now - state["last_play"] > PLAY_INTERVAL:
        toys = ["ball", "frisbee", "laser", "yarn"]
        toy = toys[int(now) % len(toys)]
        if run_ember_command("play", toy):
            state["last_play"] = now
            cared = True

    # Clean every 3 hours
    if now - state["last_clean"] > CLEAN_INTERVAL:
        if run_ember_command("clean"):
            state["last_clean"] = now
            cared = True

    # Pet every 30 minutes
    if now - state["last_pet"] > PET_INTERVAL:
        if run_ember_command("pet"):
            state["last_pet"] = now
            cared = True

    # Save state
    save_care_state(state)

    return cared

if __name__ == "__main__":
    # Run care check
    cared = check_and_care()
    if cared:
        print("Ember cared for", file=sys.stderr)
