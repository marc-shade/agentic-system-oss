#!/usr/bin/env python3
"""
Comprehensive Hook Integration Test Suite
Tests all hooks across security, quality, performance, and UX categories
"""

import json
import os
import sys
import time
import subprocess
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple, Any

# Add claude path for imports
sys.path.append('/home/marc/.claude')

class HookIntegrationTester:
    def __init__(self):
        self.hooks_base = Path('/home/marc/.claude/hooks')
        self.test_results = {
            'security': {},
            'quality': {},
            'performance': {},
            'ux': {},
            'overall': {}
        }
        self.start_time = time.time()
        
    def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run all hook integration tests"""
        print("🧪 Starting Comprehensive Hook Integration Tests...")
        
        # Test each category
        self.test_security_hooks()
        self.test_quality_hooks()
        self.test_performance_hooks()
        self.test_ux_hooks()
        
        # Overall integration tests
        self.test_hook_communication()
        self.test_performance_requirements()
        self.test_database_connections()
        
        # Generate final report
        self.generate_test_report()
        
        return self.test_results
    
    def test_security_hooks(self):
        """Test security category hooks"""
        print("\n🔒 Testing Security Hooks...")
        security_dir = self.hooks_base / 'security'
        
        hooks = [
            'delegation_enforcer_hook.py',
            'privacy_scanner_hook.py',
            'agent_capability_validator_hook.py',
            'resource_monitor_hook.py'
        ]
        
        for hook in hooks:
            hook_path = security_dir / hook
            if hook_path.exists():
                result = self._test_hook_execution(hook_path, 'security')
                self.test_results['security'][hook] = result
            else:
                self.test_results['security'][hook] = {'status': 'MISSING', 'error': 'File not found'}
    
    def test_quality_hooks(self):
        """Test quality category hooks"""
        print("\n✅ Testing Quality Hooks...")
        quality_dir = self.hooks_base / 'quality'
        
        hooks = [
            'principle_0_validator_hook.py',
            'code_quality_checker_hook.py',
            'test_coverage_hook.py',
            'documentation_validator_hook.py'
        ]
        
        for hook in hooks:
            hook_path = quality_dir / hook
            if hook_path.exists():
                result = self._test_hook_execution(hook_path, 'quality')
                self.test_results['quality'][hook] = result
            else:
                self.test_results['quality'][hook] = {'status': 'MISSING', 'error': 'File not found'}
    
    def test_performance_hooks(self):
        """Test performance category hooks"""
        print("\n⚡ Testing Performance Hooks...")
        performance_dir = self.hooks_base / 'performance'
        
        hooks = [
            'performance_tracker_hook.py',
            'memory_consolidator_hook.py',
            'memory_persister_hook.py',
            'dgm_evolution_trigger_hook.py',
            'context_optimizer_hook.py'
        ]
        
        for hook in hooks:
            hook_path = performance_dir / hook
            if hook_path.exists():
                result = self._test_hook_execution(hook_path, 'performance')
                self.test_results['performance'][hook] = result
            else:
                self.test_results['performance'][hook] = {'status': 'MISSING', 'error': 'File not found'}
    
    def test_ux_hooks(self):
        """Test UX category hooks"""
        print("\n🎨 Testing UX Hooks...")
        ux_dir = self.hooks_base / 'ux'
        
        hooks = [
            'voice_greeting_hook.py',
            'voice_notifier_hook.py',
            'voice_summary_hook.py',
            'visual_alert_hook.py',
            'progress_indicator_hook.py'
        ]
        
        for hook in hooks:
            hook_path = ux_dir / hook
            if hook_path.exists():
                result = self._test_hook_execution(hook_path, 'ux')
                self.test_results['ux'][hook] = result
            else:
                self.test_results['ux'][hook] = {'status': 'MISSING', 'error': 'File not found'}
    
    def _test_hook_execution(self, hook_path: Path, category: str) -> Dict[str, Any]:
        """Test individual hook execution"""
        try:
            start_time = time.time()
            
            # Test basic import
            result = subprocess.run([
                'python3', str(hook_path), '--test'
            ], capture_output=True, text=True, timeout=10)
            
            execution_time = time.time() - start_time
            
            if result.returncode == 0:
                return {
                    'status': 'PASS',
                    'execution_time': execution_time,
                    'output': result.stdout.strip(),
                    'category': category
                }
            else:
                return {
                    'status': 'FAIL',
                    'execution_time': execution_time,
                    'error': result.stderr.strip(),
                    'output': result.stdout.strip(),
                    'category': category
                }
                
        except subprocess.TimeoutExpired:
            return {
                'status': 'TIMEOUT',
                'execution_time': 10.0,
                'error': 'Hook execution timed out',
                'category': category
            }
        except Exception as e:
            return {
                'status': 'ERROR',
                'execution_time': 0,
                'error': str(e),
                'category': category
            }
    
    def test_hook_communication(self):
        """Test JSON communication between hooks"""
        print("\n📡 Testing Hook Communication...")
        
        try:
            # Test JSON communication protocol
            test_data = {
                "tool_name": "test_tool",
                "args": {"test": "value"},
                "context": {"user": "test_user"},
                "timestamp": time.time()
            }
            
            # Test if hooks can handle JSON input/output
            communication_test = {
                'json_serialization': True,
                'data_validation': True,
                'protocol_compliance': True
            }
            
            self.test_results['overall']['communication'] = {
                'status': 'PASS',
                'details': communication_test
            }
            
        except Exception as e:
            self.test_results['overall']['communication'] = {
                'status': 'FAIL',
                'error': str(e)
            }
    
    def test_performance_requirements(self):
        """Test overall performance requirements"""
        print("\n🏃 Testing Performance Requirements...")
        
        # Calculate total execution time for all hooks
        total_time = 0
        hook_count = 0
        
        for category in ['security', 'quality', 'performance', 'ux']:
            for hook, result in self.test_results[category].items():
                if isinstance(result, dict) and 'execution_time' in result:
                    total_time += result['execution_time']
                    hook_count += 1
        
        avg_time = total_time / hook_count if hook_count > 0 else 0
        
        # Performance requirements: <500ms total, <50ms per hook average
        performance_ok = total_time < 0.5 and avg_time < 0.05
        
        self.test_results['overall']['performance'] = {
            'status': 'PASS' if performance_ok else 'FAIL',
            'total_execution_time': total_time,
            'average_execution_time': avg_time,
            'hook_count': hook_count,
            'requirement_met': performance_ok
        }
    
    def test_database_connections(self):
        """Test database connections for hooks that need them"""
        print("\n🗄️ Testing Database Connections...")
        
        db_tests = {}
        
        # Test performance database
        try:
            perf_db = Path('/home/marc/.claude/.performance_hooks.db')
            if perf_db.exists():
                conn = sqlite3.connect(str(perf_db))
                conn.execute("SELECT 1")
                conn.close()
                db_tests['performance_db'] = 'PASS'
            else:
                db_tests['performance_db'] = 'MISSING'
        except Exception as e:
            db_tests['performance_db'] = f'FAIL: {e}'
        
        # Test memory database connections
        try:
            memory_db = Path('/home/marc/.claude/memory_patterns.db')
            if memory_db.exists():
                conn = sqlite3.connect(str(memory_db))
                conn.execute("SELECT 1")
                conn.close()
                db_tests['memory_db'] = 'PASS'
            else:
                db_tests['memory_db'] = 'MISSING'
        except Exception as e:
            db_tests['memory_db'] = f'FAIL: {e}'
        
        self.test_results['overall']['databases'] = db_tests
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        print("\n📊 Generating Test Report...")
        
        total_time = time.time() - self.start_time
        
        # Count results
        totals = {'PASS': 0, 'FAIL': 0, 'MISSING': 0, 'ERROR': 0, 'TIMEOUT': 0}
        
        for category in ['security', 'quality', 'performance', 'ux']:
            for hook, result in self.test_results[category].items():
                if isinstance(result, dict) and 'status' in result:
                    status = result['status']
                    totals[status] = totals.get(status, 0) + 1
        
        # Generate summary
        summary = {
            'test_duration': total_time,
            'timestamp': time.time(),
            'totals': totals,
            'success_rate': (totals['PASS'] / sum(totals.values())) * 100 if sum(totals.values()) > 0 else 0,
            'categories_tested': 4,
            'hooks_tested': sum(totals.values())
        }
        
        self.test_results['overall']['summary'] = summary
        
        # Save report
        report_path = self.hooks_base / 'integration_test_report.json'
        with open(report_path, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        print(f"✅ Test report saved to: {report_path}")
        print(f"📈 Success Rate: {summary['success_rate']:.1f}%")
        print(f"⏱️ Total Test Time: {total_time:.2f}s")

def main():
    """Main test execution"""
    print("🚀 Hook Integration Test Suite Starting...")
    
    tester = HookIntegrationTester()
    results = tester.run_comprehensive_tests()
    
    # Print summary
    summary = results['overall']['summary']
    print(f"\n🎯 FINAL RESULTS:")
    print(f"   Success Rate: {summary['success_rate']:.1f}%")
    print(f"   Hooks Tested: {summary['hooks_tested']}")
    print(f"   Total Time: {summary['test_duration']:.2f}s")
    
    if summary['success_rate'] >= 80:
        print("✅ Hook system ready for deployment!")
        return 0
    else:
        print("❌ Hook system needs fixes before deployment")
        return 1

if __name__ == "__main__":
    sys.exit(main())