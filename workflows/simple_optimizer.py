#!/usr/bin/env python3
"""
Simple Performance Optimizer - Standalone Script
Demonstrates agentic marker system without requiring Temporal or AutoKitteh

USAGE: python3 simple_optimizer.py [--dry-run]
STATUS: Production Ready
"""

import json
import os
import platform
import sys
import argparse
from pathlib import Path
from datetime import datetime


def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path("/Volumes/SSDRAID0/agentic-system").exists():
            return Path("/Volumes/SSDRAID0/agentic-system")
        elif Path("/Volumes/FILES/agentic-system").exists():
            return Path("/Volumes/FILES/agentic-system")
    elif system == "Linux":
        if Path("/home/marc/agentic-system").exists():
            return Path("/home/marc/agentic-system")
        elif Path("/mnt/agentic-system").exists():
            return Path("/mnt/agentic-system")
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()

# Add intelligent healing system to path
sys.path.insert(0, str(_STORAGE_BASE / "intelligent-self-healing"))
from intelligent_config_agent import IntelligentConfigAgent


def analyze_system() -> dict:
    """Quick system analysis"""
    try:
        import psutil

        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=1)

        return {
            "memory_percent": memory.percent,
            "memory_available_gb": memory.available / (1024**3),
            "cpu_percent": cpu,
            "needs_optimization": memory.percent > 75 or cpu > 80
        }
    except ImportError:
        print("⚠️  psutil not available - using mock data")
        return {
            "memory_percent": 80,
            "memory_available_gb": 4.5,
            "cpu_percent": 65,
            "needs_optimization": True
        }


def optimize_settings(dry_run: bool = False) -> dict:
    """
    Optimize Claude Code settings based on system state

    Args:
        dry_run: If True, only show what would be done

    Returns:
        Optimization summary
    """
    print("=" * 60)
    print("🔧 Claude Code Performance Optimizer")
    print("=" * 60)
    print()

    # Analyze system
    print("📊 Analyzing system...")
    system = analyze_system()
    print(f"  Memory: {system['memory_percent']:.1f}% ({system['memory_available_gb']:.1f}GB available)")
    print(f"  CPU: {system['cpu_percent']:.1f}%")
    print()

    if not system['needs_optimization']:
        print("✓ System performing well - no optimizations needed")
        return {"status": "ok", "optimizations": []}

    # Initialize agent
    agent = IntelligentConfigAgent()
    settings_file = Path.home() / ".claude" / "settings.json"

    # Load current settings
    try:
        with open(settings_file, 'r') as f:
            settings = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load settings: {e}")
        return {"status": "error", "message": str(e)}

    # Generate optimizations
    optimizations = []
    session_id = f"simple_optimizer_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Optimization 1: Memory pressure
    if system['memory_percent'] > 85:
        key = "cachingStrategy"
        is_modifiable, reason = agent.is_key_modifiable(key)

        if is_modifiable:
            current = settings.get(key, 'aggressive')
            if current != 'conservative':
                optimizations.append({
                    "key": key,
                    "old": current,
                    "new": "conservative",
                    "reason": f"High memory at {system['memory_percent']:.1f}%, reducing cache",
                    "confidence": 0.92
                })
        else:
            print(f"⚠️  Skipping {key}: {reason}")

    # Optimization 2: Token limit
    if system['memory_available_gb'] > 8:
        # Plenty of memory - can increase token limit
        key = "maxTokens"
        is_modifiable, reason = agent.is_key_modifiable(key)

        if is_modifiable:
            current = settings.get(key, 200000)
            if current < 250000:
                optimizations.append({
                    "key": key,
                    "old": current,
                    "new": 250000,
                    "reason": f"{system['memory_available_gb']:.1f}GB available, increasing context window",
                    "confidence": 0.88
                })
        else:
            print(f"⚠️  Skipping {key}: {reason}")

    elif system['memory_available_gb'] < 4:
        # Low memory - reduce token limit
        key = "maxTokens"
        is_modifiable, reason = agent.is_key_modifiable(key)

        if is_modifiable:
            current = settings.get(key, 200000)
            if current > 150000:
                optimizations.append({
                    "key": key,
                    "old": current,
                    "new": 150000,
                    "reason": f"Only {system['memory_available_gb']:.1f}GB available, reducing context",
                    "confidence": 0.90
                })
        else:
            print(f"⚠️  Skipping {key}: {reason}")

    # Optimization 3: Parallel tools (if high CPU)
    if system['cpu_percent'] > 90:
        key = "maxParallelTools"
        is_modifiable, reason = agent.is_key_modifiable(key)

        if is_modifiable:
            current = settings.get(key, 10)
            if current > 4:
                new_value = max(4, current - 2)
                optimizations.append({
                    "key": key,
                    "old": current,
                    "new": new_value,
                    "reason": f"High CPU at {system['cpu_percent']:.1f}%, reducing parallel execution",
                    "confidence": 0.89
                })
        else:
            print(f"⚠️  Skipping {key}: {reason}")

    # Show optimizations
    if not optimizations:
        print("✓ No optimizations needed - all settings appropriate")
        return {"status": "ok", "optimizations": []}

    print(f"💡 Found {len(optimizations)} optimization opportunities:")
    print()

    for opt in optimizations:
        print(f"  • {opt['key']}: {opt['old']} → {opt['new']}")
        print(f"    Reason: {opt['reason']}")
        print(f"    Confidence: {opt['confidence']:.1%}")
        print()

    if dry_run:
        print("🔍 DRY RUN MODE - No changes applied")
        return {"status": "dry_run", "optimizations": optimizations}

    # Apply optimizations
    print("🔧 Applying optimizations...")
    applied = []

    for opt in optimizations:
        # Update setting
        settings[opt['key']] = opt['new']

        # Mark as intentional change
        agent.mark_agentic_change(
            file="settings.json",
            key=opt['key'],
            reason=opt['reason'],
            change_type="agentic_optimization",
            confidence=opt['confidence'],
            session_id=session_id
        )

        applied.append(opt)
        print(f"  ✓ {opt['key']}")

    # Save settings
    try:
        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)

        print()
        print(f"✅ Applied {len(applied)} optimizations")
        print()

        # Notify
        agent.notify_change(
            change_info={
                "session": session_id,
                "optimizations": len(applied),
                "keys": [opt['key'] for opt in applied]
            },
            severity="info",
            use_voice=False
        )

        # Verify with watchdog
        print("🛡️  Verifying with intelligent watchdog...")
        import subprocess
        result = subprocess.run(
            ["python3", str(_STORAGE_BASE / "intelligent-self-healing" / "intelligent_statusline_watchdog.py")],
            capture_output=True,
            text=True,
            timeout=30
        )

        if "healed: 0" in result.stdout or "Configs healed: 0" in result.stdout:
            print("✅ Watchdog verified - optimizations recognized as intentional")
        else:
            print("⚠️  Watchdog response:")
            print(result.stdout[-500:])  # Last 500 chars

    except Exception as e:
        print(f"❌ Failed to apply optimizations: {e}")
        return {"status": "error", "message": str(e)}

    print()
    print("=" * 60)
    print("✅ Optimization Complete")
    print("=" * 60)
    print()
    print(f"Session: {session_id}")
    print(f"Applied: {len(applied)} optimizations")
    print()
    print("Logs:")
    print(f"  Markers: ~/.claude/.config_modifications.jsonl")
    print(f"  Notifications: ~/.claude/.config_notifications.jsonl")
    print()

    return {
        "status": "success",
        "session_id": session_id,
        "optimizations": applied,
        "system": system
    }


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Simple Claude Code Performance Optimizer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze and apply optimizations
  python3 simple_optimizer.py

  # Show what would be done without applying
  python3 simple_optimizer.py --dry-run

  # Check recent optimizations
  tail ~/.claude/.config_modifications.jsonl | jq .
        """
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Show optimizations without applying them"
    )

    args = parser.parse_args()

    try:
        result = optimize_settings(dry_run=args.dry_run)
        sys.exit(0 if result['status'] in ['ok', 'success', 'dry_run'] else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
