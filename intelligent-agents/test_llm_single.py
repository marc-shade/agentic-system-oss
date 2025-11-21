#!/usr/bin/env python3
"""Quick test of LLM analyzer on a single function."""

import logging
from llm_code_analyzer import create_llm_detector

logging.basicConfig(level=logging.INFO)

# Test code
code = """
def process_items(items):
    result = []
    for item in items:
        if item > 0:
            result.append(item * 2)
    return result
"""

print("Testing LLM on single function...")
print("="*60)

detector = create_llm_detector(use_ollama=True)
proposals = detector.detect_improvements(code, "test.py")

print(f"\nDetected {len(proposals)} improvements")
for p in proposals:
    print(f"\nFunction: {p.function_name}")
    print(f"Type: {p.optimization_type.value}")
    print(f"Confidence: {p.confidence_score:.2f}")
    print(f"Code after:\n{p.code_after}")
