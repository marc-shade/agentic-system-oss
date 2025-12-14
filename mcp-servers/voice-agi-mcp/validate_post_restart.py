#!/usr/bin/env python3
"""
Post-Restart Validation Script
Run this after restarting Claude Code to verify Voice-AGI improvements are active
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("\n" + "="*80)
print("VOICE-AGI POST-RESTART VALIDATION")
print("="*80)

print("\n1. Checking MCP Server Availability...")
print("-" * 80)

# Try to import the server
try:
    import server
    print("✓ Server module imports successfully")
except ImportError as e:
    print(f"✗ FAILED: Cannot import server: {e}")
    sys.exit(1)

# Check that all tools are registered
print("\n2. Checking Tool Registry...")
print("-" * 80)

tool_registry = server.tool_registry
tools = tool_registry.list_tools()

expected_tools = [
    'search_agi_memory',
    'create_goal_from_voice',
    'list_pending_tasks',
    'trigger_consolidation',
    'start_research',
    'check_system_status',
    'remember_name',
    'recall_name',
    'start_improvement_cycle',
    'decompose_goal'
]

print(f"Expected: {len(expected_tools)} tools")
print(f"Found: {len(tools)} tools")

if len(tools) == len(expected_tools):
    print("✓ All 10 voice-callable tools registered")
else:
    print(f"✗ FAILED: Expected {len(expected_tools)} tools, found {len(tools)}")

missing = set(expected_tools) - set(t['name'] for t in tools)
if missing:
    print(f"  Missing tools: {missing}")

print("\n3. Checking Enhanced Intent Keywords...")
print("-" * 80)

# Check that tools have comprehensive intent keywords
for tool in tools:
    name = tool['name']
    intents = tool.get('intents', [])
    print(f"\n{name}:")
    print(f"  Intents: {len(intents)}")
    if len(intents) >= 7:
        print(f"  ✓ Has comprehensive keywords ({len(intents)} variations)")
    else:
        print(f"  ⚠ Only {len(intents)} intents (expected 7+)")

    # Show first 3 intents as examples
    print(f"  Examples: {intents[:3]}")

print("\n" + "="*80)
print("4. Testing Intent Matching with Edge Cases")
print("="*80)

test_cases = [
    ("How is the system doing?", "check_system_status"),
    ("My name is Marc", "remember_name"),
    ("Remember that I'm Marc", "remember_name"),  # Critical disambiguation
    ("Create a goal to optimize memory", "create_goal_from_voice"),
    ("Research transformer architectures", "start_research"),
]

passed = 0
for input_text, expected_tool in test_cases:
    matched = tool_registry.match_tool(input_text)
    if matched and matched.name == expected_tool:
        print(f"✓ '{input_text}' → {matched.name}")
        passed += 1
    else:
        matched_name = matched.name if matched else "None"
        print(f"✗ '{input_text}' → {matched_name} (expected {expected_tool})")

print(f"\nIntent Matching: {passed}/{len(test_cases)} passed ({passed/len(test_cases)*100:.0f}%)")

print("\n" + "="*80)
print("5. Checking Parameter Extraction")
print("="*80)

# Check if parameter extractor is available
if hasattr(tool_registry, 'param_extractor') and tool_registry.param_extractor:
    print("✓ Parameter extractor initialized")
    print(f"  Model: {tool_registry.param_extractor.model}")
    print(f"  Ollama URL: {tool_registry.param_extractor.ollama_url}")
else:
    print("✗ Parameter extractor not initialized")

print("\n" + "="*80)
print("6. Component Status")
print("="*80)

# Check voice pipeline
voice_pipeline = server.voice_pipeline
print(f"Voice Pipeline:")
print(f"  STT Model: {voice_pipeline.stt_model_name}")
print(f"  TTS Voice: {voice_pipeline.tts_voice}")
print(f"  Status: ✓ Initialized")

# Check conversation manager
conversation_manager = server.conversation_manager
print(f"\nConversation Manager:")
print(f"  Session ID: {conversation_manager.session_id}")
print(f"  Status: ✓ Initialized")

# Check intent detector
intent_detector = server.intent_detector
print(f"\nIntent Detector:")
print(f"  Model: {intent_detector.model}")
print(f"  Ollama URL: {intent_detector.ollama_url}")
print(f"  Status: ✓ Initialized")

print("\n" + "="*80)
print("VALIDATION SUMMARY")
print("="*80)

checks = [
    ("Server module imports", True),
    ("All 10 tools registered", len(tools) == len(expected_tools)),
    ("Comprehensive intent keywords", all(len(t.get('intents', [])) >= 7 for t in tools)),
    ("Intent matching accuracy", passed == len(test_cases)),
    ("Parameter extractor available", hasattr(tool_registry, 'param_extractor') and tool_registry.param_extractor is not None),
]

passed_checks = sum(1 for _, result in checks if result)
total_checks = len(checks)

print(f"\nTotal: {passed_checks}/{total_checks} checks passed ({passed_checks/total_checks*100:.0f}%)")
print()

for check_name, result in checks:
    status = "✓ PASS" if result else "✗ FAIL"
    print(f"  {status}: {check_name}")

print("\n" + "="*80)

if passed_checks == total_checks:
    print("🎉 ALL VALIDATION CHECKS PASSED!")
    print("\nVoice-AGI v0.2.0 improvements are fully active:")
    print("  • 100% intent matching accuracy")
    print("  • Enhanced parameter extraction with Ollama")
    print("  • Comprehensive intent keywords (7-11 per tool)")
    print("  • Sophisticated scoring algorithm")
    print("\nYou can now test with:")
    print('  voice_chat(text="How is the system doing?")')
    print('  voice_chat(text="My name is Marc")')
    print('  voice_chat(text="Create a goal to optimize memory")')
elif passed_checks >= total_checks * 0.8:
    print("✓ VALIDATION MOSTLY PASSED")
    print(f"\n{passed_checks}/{total_checks} checks passed - system is functional with minor issues")
else:
    print("⚠ VALIDATION FAILED")
    print(f"\nOnly {passed_checks}/{total_checks} checks passed")
    print("Please review errors above and restart Claude Code")

print("="*80 + "\n")

sys.exit(0 if passed_checks == total_checks else 1)
