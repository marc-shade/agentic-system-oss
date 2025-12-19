#!/usr/bin/env python3
"""
Complete Hook System Integration Test
=====================================

This script validates that all hook system components are working correctly
and integrated properly with Claude Code.

Author: Backend Engineer
Purpose: Comprehensive hook system validation
"""

import sys
import os
import json
import subprocess
from datetime import datetime
from pathlib import Path

sys.path.append('/home/marc/.claude')

def run_test(test_name, command, expected_condition=None):
    """Run a test and return results"""
    print(f"\n{'='*60}")
    print(f"TEST: {test_name}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        output = result.stdout.strip()
        error_output = result.stderr.strip()
        
        print(f"Command: {command}")
        print(f"Return Code: {result.returncode}")
        print(f"Output: {output}")
        if error_output:
            print(f"Error: {error_output}")
        
        # Evaluate test condition
        if expected_condition:
            success = expected_condition(result, output)
        else:
            success = result.returncode == 0
            
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"Result: {status}")
        
        return {
            "test_name": test_name,
            "command": command,
            "return_code": result.returncode,
            "output": output,
            "error": error_output,
            "success": success,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"Exception: {e}")
        return {
            "test_name": test_name,
            "command": command,
            "return_code": -1,
            "output": "",
            "error": str(e),
            "success": False,
            "timestamp": datetime.now().isoformat()
        }

def main():
    """Run comprehensive hook system tests"""
    
    print("🔗 CLAUDE CODE HOOK SYSTEM INTEGRATION TEST")
    print("=" * 80)
    print(f"Test Start Time: {datetime.now().isoformat()}")
    print(f"Test Environment: {os.uname().nodename}")
    
    test_results = []
    
    # Test 1: Startup Sequence Hook
    test_results.append(run_test(
        "Startup Sequence Hook",
        "python3 /home/marc/.claude/hooks/startup_sequence.py",
        lambda r, o: "7/7 systems active" in o and '"allow": true' in o
    ))
    
    # Test 2: Voice Usage Checker
    test_results.append(run_test(
        "Voice Usage Checker",
        "python3 /home/marc/.claude/hooks/voice_usage_checker.py",
        lambda r, o: r.returncode in [0, 1]  # 0 for good compliance, 1 for warnings
    ))
    
    # Test 3: Delegation Enforcement - Write (Should Block)
    test_results.append(run_test(
        "Delegation Enforcement - Write Tool (Should Block)",
        'python3 /home/marc/.claude/hooks/enforce_delegation.py Write \'{"file_path": "/tmp/test.txt", "content": "test"}\'',
        lambda r, o: '"allow": false' in o and "DELEGATION REQUIRED" in o
    ))
    
    # Test 4: Delegation Enforcement - Read (Should Allow)
    test_results.append(run_test(
        "Delegation Enforcement - Read Tool (Should Allow)",
        'python3 /home/marc/.claude/hooks/enforce_delegation.py Read \'{"file_path": "/tmp/test.txt"}\'',
        lambda r, o: '"allow": true' in o
    ))
    
    # Test 5: Enhanced Delegation System
    test_results.append(run_test(
        "Enhanced Delegation System Setup",
        "python3 -c \"import sys; sys.path.append('/home/marc/.claude'); from enhanced_delegation_hooks import setup_enhanced_delegation_system; result = setup_enhanced_delegation_system(); print('SUCCESS' if result.get('test_results', {}).get('system_functional', False) else 'FAILED')\"",
        lambda r, o: "SUCCESS" in o
    ))
    
    # Test 6: Voice Usage Enforcer
    test_results.append(run_test(
        "Voice Usage Enforcer",
        "python3 -c \"import sys; sys.path.append('/home/marc/.claude'); from voice_usage_enforcer import voice_startup_check; result = voice_startup_check(enable_greeting=False); print('SUCCESS' if result else 'FAILED')\"",
        lambda r, o: "SUCCESS" in o
    ))
    
    # Test 7: Principle 0 Orchestrator
    test_results.append(run_test(
        "Principle 0 Orchestrator",
        "python3 -c \"import sys; sys.path.append('/home/marc/.claude'); from principle_0_orchestrator_hook import p0_stats; stats = p0_stats(); print('SUCCESS' if stats.get('score', 0) >= 90 else 'FAILED')\"",
        lambda r, o: "SUCCESS" in o
    ))
    
    # Test 8: Privacy Detection
    test_results.append(run_test(
        "Privacy Detection Hook",
        "python3 -c \"import sys; sys.path.append('/home/marc/.claude'); from privacy_detection_hook import check_privacy_requirement; result = check_privacy_requirement('Process employee SSN data'); print('SUCCESS' if result else 'FAILED')\"",
        lambda r, o: "SUCCESS" in o
    ))
    
    # Test 9: Darwin Gödel Machine Startup
    test_results.append(run_test(
        "Darwin Gödel Machine Startup",
        "python3 -c \"import sys; sys.path.append('/home/marc/.claude'); from start_autonomous_dgm import dgm_startup_check; result = dgm_startup_check(); print('SUCCESS' if result else 'FAILED')\"",
        lambda r, o: "SUCCESS" in o
    ))
    
    # Test 10: Health Monitor
    test_results.append(run_test(
        "Health Monitor",
        "python3 /home/marc/.claude/health-monitor-simple.py 2>/dev/null | grep -c 'HEALTHY'",
        lambda r, o: "1" in o or "HEALTHY" in str(r.stdout)
    ))
    
    # Calculate results
    total_tests = len(test_results)
    passed_tests = sum(1 for test in test_results if test["success"])
    pass_rate = (passed_tests / total_tests) * 100
    
    # Summary
    print("\n" + "="*80)
    print("🔗 HOOK SYSTEM INTEGRATION TEST SUMMARY")
    print("="*80)
    print(f"Total Tests: {total_tests}")
    print(f"Passed Tests: {passed_tests}")
    print(f"Failed Tests: {total_tests - passed_tests}")
    print(f"Pass Rate: {pass_rate:.1f}%")
    print(f"Overall Status: {'✅ HEALTHY' if pass_rate >= 80 else '❌ NEEDS ATTENTION'}")
    
    # Failed tests details
    failed_tests = [test for test in test_results if not test["success"]]
    if failed_tests:
        print(f"\n❌ FAILED TESTS ({len(failed_tests)}):")
        for test in failed_tests:
            print(f"  • {test['test_name']}")
            print(f"    Command: {test['command']}")
            print(f"    Error: {test['error']}")
    
    # Passed tests summary
    passed_test_names = [test['test_name'] for test in test_results if test["success"]]
    if passed_test_names:
        print(f"\n✅ PASSED TESTS ({len(passed_test_names)}):")
        for name in passed_test_names:
            print(f"  • {name}")
    
    # Save detailed results
    report_file = "/home/marc/.claude/hook_system_test_report.json"
    try:
        with open(report_file, "w") as f:
            json.dump({
                "test_summary": {
                    "total_tests": total_tests,
                    "passed_tests": passed_tests,
                    "failed_tests": total_tests - passed_tests,
                    "pass_rate": pass_rate,
                    "status": "HEALTHY" if pass_rate >= 80 else "NEEDS_ATTENTION",
                    "test_timestamp": datetime.now().isoformat()
                },
                "detailed_results": test_results
            }, f, indent=2)
        print(f"\n📊 Detailed report saved to: {report_file}")
    except Exception as e:
        print(f"\n⚠️ Could not save report: {e}")
    
    # Final verdict
    print(f"\n{'='*80}")
    if pass_rate >= 90:
        print("🎉 HOOK SYSTEM STATUS: EXCELLENT")
        print("   All critical systems operational")
    elif pass_rate >= 80:
        print("✅ HOOK SYSTEM STATUS: GOOD")
        print("   Minor issues detected but system functional")
    elif pass_rate >= 60:
        print("⚠️ HOOK SYSTEM STATUS: NEEDS ATTENTION")
        print("   Several issues require fixing")
    else:
        print("🚨 HOOK SYSTEM STATUS: CRITICAL")
        print("   Major issues require immediate attention")
    print("="*80)
    
    return 0 if pass_rate >= 80 else 1

if __name__ == "__main__":
    sys.exit(main())