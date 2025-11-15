#!/usr/bin/env python3
"""
Test TTS Context Filtering System
Validates that TTS commands are properly filtered during context loading
"""

import sys
import json
from pathlib import Path
from context_compression_filter import ContextCompressionFilter

def test_tts_filtering():
    """Test that TTS commands are properly filtered"""
    print("🧪 Testing TTS Context Filtering System")
    print("=" * 50)
    
    filter_system = ContextCompressionFilter()
    
    # Test cases that SHOULD be filtered out
    tts_test_cases = [
        'say -v Moira -r 180 "Orchestrator initialized"',
        'speak_to_marc("System ready for operation")',
        'subprocess.run(["say", "-v", "Moira", message])',
        '"Orchestrator communication protocol now active"',
        '"communication protocol established and operational"',
    ]
    
    # Test cases that SHOULD be preserved
    preserve_test_cases = [
        'mcp__enhanced-memory-mcp__create_entities()',
        'mcp__memory__search_nodes(query="project context")',
        'Loading core memories and system configuration',
        'Task execution completed successfully',
        'Error: Failed to connect to MCP server',
    ]
    
    print("🔍 Testing TTS Command Filtering...")
    all_filtered = True
    for i, test_case in enumerate(tts_test_cases, 1):
        should_filter = filter_system.should_filter_content(test_case)
        status = "✅ FILTERED" if should_filter else "❌ NOT FILTERED"
        print(f"  {i}. {status}: {test_case[:60]}...")
        if not should_filter:
            all_filtered = False
    
    print(f"\n🛡️ Testing Content Preservation...")
    all_preserved = True
    for i, test_case in enumerate(preserve_test_cases, 1):
        should_filter = filter_system.should_filter_content(test_case)
        status = "✅ PRESERVED" if not should_filter else "❌ FILTERED"
        print(f"  {i}. {status}: {test_case[:60]}...")
        if should_filter:
            all_preserved = False
    
    print(f"\n📊 Test Results Summary:")
    print(f"TTS Filtering: {'✅ PASS' if all_filtered else '❌ FAIL'}")
    print(f"Content Preservation: {'✅ PASS' if all_preserved else '❌ FAIL'}")
    
    if all_filtered and all_preserved:
        print("\n🎉 ALL TESTS PASSED - TTS filtering system is working correctly!")
        return True
    else:
        print("\n⚠️ SOME TESTS FAILED - TTS filtering needs adjustment")
        return False

def test_context_compression():
    """Test context compression functionality"""
    print("\n🗜️ Testing Context Compression...")
    
    filter_system = ContextCompressionFilter()
    
    # Sample context with mixed content
    sample_context = [
        "mcp__enhanced-memory-mcp__create_entities() called",
        'say -v Moira -r 180 "System initialized"',
        "Loading project memories from database",
        'speak_to_marc("Ready for orchestration")',
        "Error: Connection timeout to MCP server",
        "Task: Analyze codebase architecture",
        'subprocess.run(["say", "Completion announcement"])',
        "Result: Analysis completed successfully"
    ]
    
    # Filter the content
    filtered_context = []
    for entry in sample_context:
        if not filter_system.should_filter_content(entry):
            filtered_context.append(entry)
    
    print(f"Original entries: {len(sample_context)}")
    print(f"Filtered entries: {len(filtered_context)}")
    compression_ratio = ((len(sample_context) - len(filtered_context)) / len(sample_context)) * 100
    print(f"Compression ratio: {compression_ratio:.1f}%")
    
    print("\nFiltered context:")
    for entry in filtered_context:
        print(f"  ✓ {entry}")
    
    return compression_ratio > 0

if __name__ == "__main__":
    # Run the tests
    filtering_passed = test_tts_filtering()
    compression_passed = test_context_compression()
    
    if filtering_passed and compression_passed:
        print("\n🚀 Context filtering system is fully operational!")
        sys.exit(0)
    else:
        print("\n🔧 Context filtering system needs adjustments")
        sys.exit(1)