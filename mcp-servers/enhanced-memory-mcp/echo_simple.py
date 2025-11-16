#!/usr/bin/env python3
import sys
import json

print("Echo server starting", file=sys.stderr)
sys.stdin.reconfigure(encoding='utf-8', newline='')
sys.stdout.reconfigure(encoding='utf-8', newline='')
print("Echo server ready", file=sys.stderr)

for line in sys.stdin:
    print(f"Echo: {line.strip()}")
    sys.stdout.flush()