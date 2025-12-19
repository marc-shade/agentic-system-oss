#!/usr/bin/env python3
"""
Test hooks integration - Validate all hooks are properly configured.
"""
import json
import os
import subprocess
import sys
from datetime import datetime

def test_hooks_integration():
    """Test that all hooks are properly integrated and functional."""
    
    test_results = {
        'timestamp': datetime.now().isoformat(),
        'total_tests': 0,
        'passed_tests': 0,
        'failed_tests': 0,
        'results': []
    }
    
    # Load settings
    settings_file = '/home/marc/.claude/settings.json'
    with open(settings_file, 'r') as f:
        settings = json.load(f)
    
    hooks = settings.get('hooks', {})
    
    print("🧪 Testing Claude Code Hooks Integration")
    print("=" * 50)
    
    # Test 1: Verify all hook scripts exist
    print("\n📁 Testing hook script existence...")
    for event, matchers in hooks.items():
        for matcher in matchers:
            for hook in matcher['hooks']:
                command = hook['command']
                if command.startswith('python3 '):
                    script_path = command.split()[1]
                    test_results['total_tests'] += 1
                    
                    if os.path.exists(script_path):
                        print(f"  ✅ {os.path.basename(script_path)}")
                        test_results['passed_tests'] += 1
                        test_results['results'].append({
                            'test': 'script_exists',
                            'script': script_path,
                            'status': 'PASS'
                        })
                    else:
                        print(f"  ❌ {script_path} - FILE NOT FOUND")
                        test_results['failed_tests'] += 1
                        test_results['results'].append({
                            'test': 'script_exists',
                            'script': script_path,
                            'status': 'FAIL',
                            'error': 'File not found'
                        })
    
    # Test 2: Verify scripts are executable
    print("\n🔧 Testing script permissions...")
    for event, matchers in hooks.items():
        for matcher in matchers:
            for hook in matcher['hooks']:
                command = hook['command']
                if command.startswith('python3 '):
                    script_path = command.split()[1]
                    test_results['total_tests'] += 1
                    
                    if os.path.exists(script_path):
                        if os.access(script_path, os.X_OK):
                            print(f"  ✅ {os.path.basename(script_path)} - executable")
                            test_results['passed_tests'] += 1
                            test_results['results'].append({
                                'test': 'script_executable',
                                'script': script_path,
                                'status': 'PASS'
                            })
                        else:
                            print(f"  ⚠️  {os.path.basename(script_path)} - not executable")
                            test_results['failed_tests'] += 1
                            test_results['results'].append({
                                'test': 'script_executable',
                                'script': script_path,
                                'status': 'FAIL',
                                'error': 'Not executable'
                            })
    
    # Test 3: Test basic hook functionality
    print("\n⚡ Testing basic hook functionality...")
    test_hooks = [
        '/home/marc/.claude/hooks/tool_name_validator.py',
        '/home/marc/.claude/hooks/startup_sequence.py',
        '/home/marc/.claude/hooks/voice_usage_checker.py'
    ]
    
    for script in test_hooks:
        if os.path.exists(script):
            test_results['total_tests'] += 1
            
            try:
                # Test with basic arguments
                result = subprocess.run(
                    ['python3', script, 'test_arg'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode in [0, 1, 2]:  # Valid exit codes
                    print(f"  ✅ {os.path.basename(script)} - functional")
                    test_results['passed_tests'] += 1
                    test_results['results'].append({
                        'test': 'hook_functional',
                        'script': script,
                        'status': 'PASS',
                        'exit_code': result.returncode
                    })
                else:
                    print(f"  ❌ {os.path.basename(script)} - unexpected exit code: {result.returncode}")
                    test_results['failed_tests'] += 1
                    test_results['results'].append({
                        'test': 'hook_functional',
                        'script': script,
                        'status': 'FAIL',
                        'error': f'Unexpected exit code: {result.returncode}',
                        'stderr': result.stderr
                    })
                    
            except subprocess.TimeoutExpired:
                print(f"  ⚠️  {os.path.basename(script)} - timeout")
                test_results['failed_tests'] += 1
                test_results['results'].append({
                    'test': 'hook_functional',
                    'script': script,
                    'status': 'FAIL',
                    'error': 'Timeout'
                })
            except Exception as e:
                print(f"  ❌ {os.path.basename(script)} - error: {e}")
                test_results['failed_tests'] += 1
                test_results['results'].append({
                    'test': 'hook_functional',
                    'script': script,
                    'status': 'FAIL',
                    'error': str(e)
                })
    
    # Test 4: Validate hook configuration structure
    print("\n📋 Testing hook configuration structure...")
    required_events = ['SessionStart', 'UserPromptSubmit', 'PreToolUse', 'PostToolUse', 'Stop']
    
    for event in required_events:
        test_results['total_tests'] += 1
        
        if event in hooks:
            print(f"  ✅ {event} - configured")
            test_results['passed_tests'] += 1
            test_results['results'].append({
                'test': 'event_configured',
                'event': event,
                'status': 'PASS'
            })
        else:
            print(f"  ❌ {event} - missing")
            test_results['failed_tests'] += 1
            test_results['results'].append({
                'test': 'event_configured',
                'event': event,
                'status': 'FAIL',
                'error': 'Event not configured'
            })
    
    # Generate summary
    print("\n📊 Test Summary")
    print("=" * 50)
    print(f"Total Tests: {test_results['total_tests']}")
    print(f"Passed: {test_results['passed_tests']}")
    print(f"Failed: {test_results['failed_tests']}")
    
    success_rate = (test_results['passed_tests'] / test_results['total_tests']) * 100 if test_results['total_tests'] > 0 else 0
    print(f"Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 90:
        print("🎉 EXCELLENT - Hooks integration successful!")
        status = "EXCELLENT"
    elif success_rate >= 80:
        print("✅ GOOD - Hooks integration mostly successful")
        status = "GOOD"
    elif success_rate >= 70:
        print("⚠️  WARNING - Some issues found")
        status = "WARNING"
    else:
        print("❌ CRITICAL - Major issues found")
        status = "CRITICAL"
    
    # Save test results
    test_results['status'] = status
    test_results['success_rate'] = success_rate
    
    with open('/home/marc/.claude/hooks/.integration_test_results.json', 'w') as f:
        json.dump(test_results, f, indent=2)
    
    return test_results

if __name__ == "__main__":
    results = test_hooks_integration()
    sys.exit(0 if results['success_rate'] >= 80 else 1)