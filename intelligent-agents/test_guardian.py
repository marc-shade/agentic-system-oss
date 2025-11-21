#!/usr/bin/env python3
import sys
from pathlib import Path

print("1. Starting test")

sys.path.insert(0, "sdk_agents")
sys.path.insert(0, str(Path(__file__).parent.parent / "arduino-surface" / "bridge"))
sys.path.insert(0, str(Path(__file__).parent.parent / "arduino-surface" / "ember_integration"))

print("2. Paths added")

from specialized.system_health_guardian import SystemHealthGuardian

print("3. SystemHealthGuardian imported")

guardian = SystemHealthGuardian("/dev/tty.usbmodem8344401")

print("4. Guardian instantiated")

print("5. Starting guardian...")
guardian.start(check_interval=30)

print("6. Guardian started")
