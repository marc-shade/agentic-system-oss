#!/usr/bin/env python3
"""
Intelligent service integration - only install what's missing
"""

import json
from pathlib import Path

def get_services_to_install():
    """Determine which services need installation"""

    awareness_file = Path.home() / ".claude" / "environmental-awareness.json"

    if not awareness_file.exists():
        print("❌ Environmental awareness not found. Run environmental-awareness.py first!")
        return None

    with open(awareness_file) as f:
        awareness = json.load(f)

    services = awareness.get("services", {})

    install_plan = {
        "Qdrant": not services.get("Qdrant", {}).get("running", False),
        "Temporal": not services.get("Temporal gRPC", {}).get("running", False),
        "AutoKitteh": not services.get("AutoKitteh", {}).get("running", False),
        "Ollama": not services.get("Ollama", {}).get("running", False),
        "Prometheus": not services.get("Prometheus", {}).get("running", False),
        "Loki": not services.get("Loki", {}).get("running", False),
        "Grafana": not services.get("Grafana", {}).get("running", False)
    }

    return install_plan

def main():
    plan = get_services_to_install()

    if plan is None:
        return 1

    print("📦 Service Installation Plan")
    print("=" * 60)
    print()

    to_install = [name for name, needed in plan.items() if needed]
    already_running = [name for name, needed in plan.items() if not needed]

    if already_running:
        print("✅ Already Running (will reuse):")
        for service in already_running:
            print(f"   - {service}")
        print()

    if to_install:
        print("📥 Will Install:")
        for service in to_install:
            print(f"   - {service}")
        print()
    else:
        print("✅ All required services are already running!")
        print()

    # Save installation plan
    plan_file = Path.home() / ".claude" / "installation-plan.json"
    plan_file.parent.mkdir(parents=True, exist_ok=True)

    with open(plan_file, 'w') as f:
        json.dump(plan, f, indent=2)

    print(f"💾 Installation plan saved to: {plan_file}")

    return 0

if __name__ == "__main__":
    exit(main())
