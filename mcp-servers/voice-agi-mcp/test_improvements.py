#!/usr/bin/env python3
"""
Test script for voice-agi improvements
Tests parameter extraction and enhanced intent matching
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from tool_registry import ToolRegistry
from parameter_extractor import ParameterExtractor
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("test")


async def test_parameter_extraction():
    """Test parameter extraction from natural language"""
    print("\n" + "="*60)
    print("TESTING PARAMETER EXTRACTION")
    print("="*60)

    from parameter_extractor import ToolDefinition as ExtractorToolDef

    extractor = ParameterExtractor()

    # Check if Ollama is available
    available = await extractor.check_availability()
    print(f"\n✓ Ollama available: {available}")

    # Test cases
    test_cases = [
        {
            'input': 'Create a goal to optimize memory consolidation',
            'tool': ExtractorToolDef(
                name='create_goal_from_voice',
                description='Create a new AGI goal',
                parameters={
                    'description': {'type': 'str', 'required': True, 'default': None}
                }
            ),
            'expected': {'description': 'optimize memory consolidation'}
        },
        {
            'input': 'Research transformer architectures',
            'tool': ExtractorToolDef(
                name='start_research',
                description='Start autonomous research',
                parameters={
                    'topic': {'type': 'str', 'required': True, 'default': None}
                }
            ),
            'expected': {'topic': 'transformer architectures'}
        },
        {
            'input': "My name is Marc",
            'tool': ExtractorToolDef(
                name='remember_name',
                description="Remember user's name",
                parameters={
                    'name': {'type': 'str', 'required': True, 'default': None}
                }
            ),
            'expected': {'name': 'Marc'}
        },
        {
            'input': "Optimize memory performance",
            'tool': ExtractorToolDef(
                name='start_improvement_cycle',
                description="Start self-improvement cycle",
                parameters={
                    'target_metric': {'type': 'str', 'required': False, 'default': 'overall_performance'}
                }
            ),
            'expected': {'target_metric': 'memory performance'}
        }
    ]

    results = []
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['input']}")
        print(f"Tool: {test['tool'].name}")

        extracted = await extractor.extract_parameters(
            test['input'],
            test['tool'],
            context=None
        )

        print(f"Expected: {test['expected']}")
        print(f"Extracted: {extracted}")

        # Check if key parameters match
        success = all(
            extracted.get(key) == value or (key in extracted and value in str(extracted.get(key)))
            for key, value in test['expected'].items()
        )

        status = "✓ PASS" if success else "✗ FAIL"
        print(f"Status: {status}")
        results.append(success)

    passed = sum(results)
    total = len(results)
    print(f"\n{'='*60}")
    print(f"Parameter Extraction: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    print(f"{'='*60}")

    return passed, total


async def test_intent_matching():
    """Test enhanced intent matching"""
    print("\n" + "="*60)
    print("TESTING ENHANCED INTENT MATCHING")
    print("="*60)

    # Import server to get registered tools
    import server
    registry = server.tool_registry

    # Test cases with expected tools
    test_cases = [
        ("Create a goal to optimize memory", "create_goal_from_voice"),
        ("Research transformer architectures", "start_research"),
        ("How is the system doing?", "check_system_status"),
        ("My name is Marc", "remember_name"),
        ("What is my name?", "recall_name"),
        ("Remember that I'm Marc", "remember_name"),  # Previously matched wrong tool
        ("List my tasks", "list_pending_tasks"),
        ("Run consolidation", "trigger_consolidation"),
        ("Improve performance", "start_improvement_cycle"),
        ("Break down this goal", "decompose_goal"),
    ]

    results = []
    for i, (input_text, expected_tool) in enumerate(test_cases, 1):
        print(f"\nTest {i}: '{input_text}'")

        matched_tool = registry.match_tool(input_text)

        if matched_tool:
            tool_name = matched_tool.name
            success = tool_name == expected_tool

            status = "✓ PASS" if success else "✗ FAIL"
            print(f"Expected: {expected_tool}")
            print(f"Matched:  {tool_name}")
            print(f"Status:   {status}")

            results.append(success)
        else:
            print(f"Expected: {expected_tool}")
            print(f"Matched:  None")
            print(f"Status:   ✗ FAIL (no match)")
            results.append(False)

    passed = sum(results)
    total = len(results)
    print(f"\n{'='*60}")
    print(f"Intent Matching: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    print(f"{'='*60}")

    return passed, total


async def test_disambiguation():
    """Test disambiguation between similar intents"""
    print("\n" + "="*60)
    print("TESTING INTENT DISAMBIGUATION")
    print("="*60)

    import server
    registry = server.tool_registry

    # Test cases where disambiguation is critical
    test_cases = [
        {
            'input': "Remember that I'm Marc",
            'expected': 'remember_name',
            'not_expected': 'search_agi_memory',
            'reason': 'Should match remember_name, not search (contains "remember")'
        },
        {
            'input': "Create a new goal to optimize",
            'expected': 'create_goal_from_voice',
            'not_expected': 'start_improvement_cycle',
            'reason': 'Should match create_goal, not improve (contains "optimize")'
        },
        {
            'input': "Search memory for my name",
            'expected': 'search_agi_memory',
            'not_expected': 'remember_name',
            'reason': 'Should match search, not remember_name'
        }
    ]

    results = []
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: '{test['input']}'")
        print(f"Reason: {test['reason']}")

        matched_tool = registry.match_tool(test['input'])

        if matched_tool:
            tool_name = matched_tool.name
            success = tool_name == test['expected'] and tool_name != test['not_expected']

            status = "✓ PASS" if success else "✗ FAIL"
            print(f"Expected: {test['expected']}")
            print(f"Not expected: {test['not_expected']}")
            print(f"Matched:  {tool_name}")
            print(f"Status:   {status}")

            results.append(success)
        else:
            print(f"Matched:  None")
            print(f"Status:   ✗ FAIL (no match)")
            results.append(False)

    passed = sum(results)
    total = len(results)
    print(f"\n{'='*60}")
    print(f"Disambiguation: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    print(f"{'='*60}")

    return passed, total


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("VOICE-AGI IMPROVEMENTS TEST SUITE")
    print("="*80)

    total_passed = 0
    total_tests = 0

    # Test 1: Parameter extraction
    passed, total = await test_parameter_extraction()
    total_passed += passed
    total_tests += total

    # Test 2: Intent matching
    passed, total = await test_intent_matching()
    total_passed += passed
    total_tests += total

    # Test 3: Disambiguation
    passed, total = await test_disambiguation()
    total_passed += passed
    total_tests += total

    # Final summary
    print("\n" + "="*80)
    print("FINAL TEST SUMMARY")
    print("="*80)
    print(f"Total: {total_passed}/{total_tests} tests passed ({total_passed/total_tests*100:.0f}%)")

    if total_passed == total_tests:
        print("\n🎉 ALL TESTS PASSED!")
    elif total_passed / total_tests >= 0.9:
        print(f"\n✓ EXCELLENT: {total_passed/total_tests*100:.0f}% success rate")
    elif total_passed / total_tests >= 0.8:
        print(f"\n✓ GOOD: {total_passed/total_tests*100:.0f}% success rate")
    else:
        print(f"\n⚠ NEEDS IMPROVEMENT: {total_passed/total_tests*100:.0f}% success rate")

    print("="*80)


if __name__ == '__main__':
    asyncio.run(main())
