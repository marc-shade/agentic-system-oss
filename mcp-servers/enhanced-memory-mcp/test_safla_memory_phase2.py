#!/usr/bin/env python3
"""
SAFLA Phase 2 Enhanced Memory Test Suite
Comprehensive testing of autonomous memory learning patterns and enhanced operations
"""

import asyncio
import json
import time
import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path

# Add the server directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def speak_to_marc(message):
    """Voice communication"""
    try:
        voice_script = Path(__file__).parent.parent / "voice-cloning-mcp" / "production_comprehensive_voice.py"
        subprocess.run([
            "python", str(voice_script), message, "foghorn_friendly"
        ], check=False, capture_output=True, timeout=5)
        print(f"🗣️ {message}")
    except:
        print(f"🗣️ {message}")

class SAFLAMemoryPhase2Tester:
    """Test suite for SAFLA Phase 2 enhanced memory implementation"""
    
    def __init__(self):
        self.test_results = {
            "safla_tools": {"passed": 0, "failed": 0, "tests": []},
            "enhanced_operations": {"passed": 0, "failed": 0, "tests": []},
            "autonomous_learning": {"passed": 0, "failed": 0, "tests": []},
            "safety_validation": {"passed": 0, "failed": 0, "tests": []},
            "performance_tracking": {"passed": 0, "failed": 0, "tests": []}
        }
        
    def record_test_result(self, category, test_name, passed, details=""):
        """Record individual test results"""
        self.test_results[category]["tests"].append({
            "name": test_name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        
        if passed:
            self.test_results[category]["passed"] += 1
        else:
            self.test_results[category]["failed"] += 1
    
    async def test_safla_tools_integration(self):
        """Test SAFLA-specific MCP tools"""
        print("\n🛠️ TESTING SAFLA TOOLS INTEGRATION")
        print("=" * 40)
        
        try:
            from server import safla_orchestrator, SAFLA_MEMORY_CONFIG
            
            # Test 1: Memory pattern analysis
            try:
                analysis_result = await safla_orchestrator.analyze_memory_usage_patterns()
                
                required_fields = ["tier_distribution", "compression_efficiency", "optimization_candidates"]
                if all(field in analysis_result for field in required_fields):
                    self.record_test_result("safla_tools", "memory_pattern_analysis", True,
                                          f"Analysis completed with {len(analysis_result.get('optimization_candidates', []))} optimization suggestions")
                    print("✅ Memory pattern analysis: PASSED")
                else:
                    self.record_test_result("safla_tools", "memory_pattern_analysis", False,
                                          f"Missing required fields: {analysis_result}")
                    print("❌ Memory pattern analysis: FAILED")
                    
            except Exception as e:
                self.record_test_result("safla_tools", "memory_pattern_analysis", False, str(e))
                print(f"❌ Memory pattern analysis: ERROR - {e}")
            
            # Test 2: Autonomous curation
            try:
                curation_result = await safla_orchestrator.autonomous_memory_curation()
                
                if "entities_processed" in curation_result and "actions_taken" in curation_result:
                    actions_taken = len(curation_result.get("actions_taken", []))
                    self.record_test_result("safla_tools", "autonomous_curation", True,
                                          f"Processed entities with {actions_taken} actions taken")
                    print(f"✅ Autonomous curation: PASSED ({actions_taken} actions)")
                else:
                    self.record_test_result("safla_tools", "autonomous_curation", False,
                                          f"Invalid curation result: {curation_result}")
                    print("❌ Autonomous curation: FAILED")
                    
            except Exception as e:
                self.record_test_result("safla_tools", "autonomous_curation", False, str(e))
                print(f"❌ Autonomous curation: ERROR - {e}")
            
            # Test 3: Performance evaluation
            try:
                perf_result = await safla_orchestrator.evaluate_memory_performance()
                
                performance_metrics = ["operation_efficiency", "compression_effectiveness", "search_speed"]
                if any(metric in perf_result for metric in performance_metrics):
                    self.record_test_result("safla_tools", "performance_evaluation", True,
                                          f"Performance evaluation completed: {perf_result.get('overall_score', 'N/A')}")
                    print("✅ Performance evaluation: PASSED")
                else:
                    self.record_test_result("safla_tools", "performance_evaluation", False,
                                          f"No performance metrics found: {perf_result}")
                    print("❌ Performance evaluation: FAILED")
                    
            except Exception as e:
                self.record_test_result("safla_tools", "performance_evaluation", False, str(e))
                print(f"❌ Performance evaluation: ERROR - {e}")
            
            # Test 4: Safety validation
            try:
                safe_operation = {"operation": "create_entity", "entity_type": "test"}
                safety_result = await safla_orchestrator.validate_memory_safety("test_operation", safe_operation)
                
                if "safe" in safety_result and safety_result["safe"]:
                    self.record_test_result("safla_tools", "safety_validation_safe", True,
                                          "Safe operation correctly validated")
                    print("✅ Safety validation (safe): PASSED")
                else:
                    self.record_test_result("safla_tools", "safety_validation_safe", False,
                                          f"Safe operation incorrectly flagged: {safety_result}")
                    print("❌ Safety validation (safe): FAILED")
                    
            except Exception as e:
                self.record_test_result("safla_tools", "safety_validation_safe", False, str(e))
                print(f"❌ Safety validation (safe): ERROR - {e}")
            
            # Test 5: Dangerous operation detection
            try:
                dangerous_operation = {"operation": "delete_all", "entity_type": "core_system"}
                safety_result = await safla_orchestrator.validate_memory_safety("dangerous_operation", dangerous_operation)
                
                if not safety_result.get("safe", True) and "violations" in safety_result:
                    self.record_test_result("safla_tools", "safety_validation_dangerous", True,
                                          f"Dangerous operation correctly blocked: {safety_result['violations']}")
                    print("✅ Safety validation (dangerous): PASSED")
                else:
                    self.record_test_result("safla_tools", "safety_validation_dangerous", False,
                                          f"Dangerous operation not detected: {safety_result}")
                    print("❌ Safety validation (dangerous): FAILED")
                    
            except Exception as e:
                self.record_test_result("safla_tools", "safety_validation_dangerous", False, str(e))
                print(f"❌ Safety validation (dangerous): ERROR - {e}")
                
        except Exception as e:
            print(f"❌ SAFLA tools integration: CRITICAL ERROR - {e}")
    
    async def test_enhanced_operations(self):
        """Test enhanced create_entities and search_nodes operations"""
        print("\n🔧 TESTING ENHANCED OPERATIONS")
        print("=" * 40)
        
        try:
            from server import create_entities, search_nodes
            
            # Test 1: Enhanced entity creation with SAFLA tracking
            try:
                test_entities = [
                    {
                        "name": "SAFLA_Test_Entity_1",
                        "entityType": "test_entity",
                        "observations": ["SAFLA Phase 2 testing", "Enhanced memory operations", "Autonomous learning patterns"]
                    },
                    {
                        "name": "SAFLA_Test_Entity_2", 
                        "entityType": "test_performance",
                        "observations": ["Performance tracking validation", "Memory optimization testing"]
                    }
                ]
                
                create_result = create_entities({"entities": test_entities})
                
                if create_result.get("success") and create_result.get("safla_enhanced"):
                    entities_created = create_result.get("entities_created", 0)
                    compression_ratio = create_result.get("overall_compression_ratio", 1.0)
                    self.record_test_result("enhanced_operations", "enhanced_entity_creation", True,
                                          f"Created {entities_created} entities with {(1-compression_ratio)*100:.1f}% compression")
                    print(f"✅ Enhanced entity creation: PASSED ({entities_created} entities)")
                else:
                    self.record_test_result("enhanced_operations", "enhanced_entity_creation", False,
                                          f"SAFLA enhancement not detected: {create_result}")
                    print("❌ Enhanced entity creation: FAILED")
                    
            except Exception as e:
                self.record_test_result("enhanced_operations", "enhanced_entity_creation", False, str(e))
                print(f"❌ Enhanced entity creation: ERROR - {e}")
            
            # Test 2: Enhanced search with SAFLA tracking
            try:
                search_result = search_nodes({"query": "SAFLA", "max_results": 10})
                
                if search_result.get("success") and search_result.get("safla_enhanced"):
                    results_found = search_result.get("results_found", 0)
                    self.record_test_result("enhanced_operations", "enhanced_search", True,
                                          f"SAFLA search found {results_found} results")
                    print(f"✅ Enhanced search: PASSED ({results_found} results)")
                else:
                    self.record_test_result("enhanced_operations", "enhanced_search", False,
                                          f"SAFLA enhancement not detected: {search_result}")
                    print("❌ Enhanced search: FAILED")
                    
            except Exception as e:
                self.record_test_result("enhanced_operations", "enhanced_search", False, str(e))
                print(f"❌ Enhanced search: ERROR - {e}")
                
        except Exception as e:
            print(f"❌ Enhanced operations: CRITICAL ERROR - {e}")
    
    async def test_autonomous_learning_patterns(self):
        """Test autonomous learning and continuous enhancement"""
        print("\n🧠 TESTING AUTONOMOUS LEARNING PATTERNS")
        print("=" * 44)
        
        try:
            from server import safla_orchestrator
            
            # Test 1: Continuous memory enhancement
            try:
                enhancement_result = await safla_orchestrator.continuous_memory_enhancement()
                
                if "optimizations_applied" in enhancement_result:
                    optimizations = len(enhancement_result.get("optimizations_applied", []))
                    self.record_test_result("autonomous_learning", "continuous_enhancement", True,
                                          f"Applied {optimizations} memory optimizations")
                    print(f"✅ Continuous enhancement: PASSED ({optimizations} optimizations)")
                else:
                    self.record_test_result("autonomous_learning", "continuous_enhancement", False,
                                          f"No optimizations found: {enhancement_result}")
                    print("❌ Continuous enhancement: FAILED")
                    
            except Exception as e:
                self.record_test_result("autonomous_learning", "continuous_enhancement", False, str(e))
                print(f"❌ Continuous enhancement: ERROR - {e}")
            
            # Test 2: Learning pattern detection
            try:
                learning_patterns = await safla_orchestrator.detect_learning_patterns()
                
                if "patterns_detected" in learning_patterns:
                    patterns_count = len(learning_patterns.get("patterns_detected", []))
                    self.record_test_result("autonomous_learning", "pattern_detection", True,
                                          f"Detected {patterns_count} learning patterns")
                    print(f"✅ Pattern detection: PASSED ({patterns_count} patterns)")
                else:
                    self.record_test_result("autonomous_learning", "pattern_detection", False,
                                          f"No patterns detected: {learning_patterns}")
                    print("❌ Pattern detection: FAILED")
                    
            except Exception as e:
                self.record_test_result("autonomous_learning", "pattern_detection", False, str(e))
                print(f"❌ Pattern detection: ERROR - {e}")
                
        except Exception as e:
            print(f"❌ Autonomous learning: CRITICAL ERROR - {e}")
    
    async def test_safla_configuration(self):
        """Test SAFLA configuration and component integration"""
        print("\n⚙️ TESTING SAFLA CONFIGURATION")
        print("=" * 32)
        
        try:
            from server import SAFLA_MEMORY_CONFIG, safla_orchestrator
            
            # Test configuration completeness
            required_config = [
                "autonomous_curation_enabled",
                "performance_tracking_enabled", 
                "safety_validation_enabled",
                "meta_cognitive_analysis_enabled",
                "continuous_optimization_enabled"
            ]
            
            config_score = 0
            for config_key in required_config:
                if SAFLA_MEMORY_CONFIG.get(config_key, False):
                    config_score += 1
            
            if config_score >= 4:
                self.record_test_result("safla_tools", "configuration_completeness", True,
                                      f"SAFLA configuration: {config_score}/{len(required_config)} features enabled")
                print(f"✅ SAFLA configuration: PASSED ({config_score}/{len(required_config)})")
            else:
                self.record_test_result("safla_tools", "configuration_completeness", False,
                                      f"Insufficient SAFLA features enabled: {config_score}/{len(required_config)}")
                print(f"❌ SAFLA configuration: FAILED ({config_score}/{len(required_config)})")
            
            # Test thresholds configuration
            thresholds = SAFLA_MEMORY_CONFIG.get("curation_thresholds", {})
            if len(thresholds) >= 3:
                self.record_test_result("safla_tools", "thresholds_configuration", True,
                                      f"Curation thresholds configured: {len(thresholds)} parameters")
                print(f"✅ Thresholds configuration: PASSED ({len(thresholds)} parameters)")
            else:
                self.record_test_result("safla_tools", "thresholds_configuration", False,
                                      f"Insufficient thresholds: {len(thresholds)}")
                print(f"❌ Thresholds configuration: FAILED ({len(thresholds)})")
                
        except Exception as e:
            self.record_test_result("safla_tools", "configuration_test", False, str(e))
            print(f"❌ SAFLA configuration: ERROR - {e}")
    
    async def run_comprehensive_test(self):
        """Run complete SAFLA Phase 2 test suite"""
        print("🧠 SAFLA PHASE 2 ENHANCED MEMORY TEST SUITE")
        print("=" * 48)
        print(f"Test Start Time: {datetime.now().isoformat()}")
        speak_to_marc("Starting SAFLA Phase 2 enhanced memory testing!")
        
        # Initialize database
        try:
            from server import init_database
            init_database()
            print("✅ Database initialized successfully")
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
        
        # Run all test categories
        await self.test_safla_tools_integration()
        await self.test_enhanced_operations()
        await self.test_autonomous_learning_patterns()
        await self.test_safla_configuration()
        
        # Generate comprehensive report
        self.generate_test_report()
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        print("\n" + "=" * 48)
        print("🎯 SAFLA PHASE 2 MEMORY TEST RESULTS")
        print("=" * 48)
        
        total_passed = 0
        total_failed = 0
        
        for category, results in self.test_results.items():
            passed = results["passed"]
            failed = results["failed"]
            total = passed + failed
            
            total_passed += passed
            total_failed += failed
            
            if total > 0:
                success_rate = (passed / total) * 100
                status_emoji = "✅" if success_rate >= 80 else "⚠️" if success_rate >= 60 else "❌"
                
                print(f"{status_emoji} {category.upper().replace('_', ' ')}: {passed}/{total} ({success_rate:.1f}%)")
                
                # Show individual test details
                for test in results["tests"]:
                    test_emoji = "✅" if test["passed"] else "❌"
                    print(f"   {test_emoji} {test['name']}: {test['details']}")
        
        print("\n" + "=" * 48)
        
        # Overall assessment
        overall_total = total_passed + total_failed
        if overall_total > 0:
            overall_success_rate = (total_passed / overall_total) * 100
            
            if overall_success_rate >= 90:
                status = "🎉 EXCELLENT"
                message = "SAFLA Phase 2 enhanced memory system performing excellently!"
            elif overall_success_rate >= 80:
                status = "✅ GOOD"
                message = "SAFLA Phase 2 enhanced memory system performing well!"
            elif overall_success_rate >= 70:
                status = "⚠️ NEEDS IMPROVEMENT"
                message = "SAFLA Phase 2 enhanced memory system needs optimization."
            else:
                status = "❌ CRITICAL ISSUES"
                message = "SAFLA Phase 2 enhanced memory system requires immediate attention."
            
            print(f"OVERALL RESULT: {status}")
            print(f"Success Rate: {total_passed}/{overall_total} ({overall_success_rate:.1f}%)")
            print(f"Assessment: {message}")
            
            # Phase completion assessment
            if overall_success_rate >= 80:
                phase_status = "🎉 PHASE 2 COMPLETE"
                phase_message = "SAFLA Phase 2 implementation successful! Enhanced memory with autonomous learning is operational!"
                next_steps = "• Ready for Phase 3: Cross-component coordination\n• Integrate with other AGI components\n• Deploy distributed autonomous agents"
            elif overall_success_rate >= 70:
                phase_status = "⚠️ PHASE 2 MOSTLY COMPLETE"
                phase_message = "SAFLA Phase 2 mostly successful with minor issues."
                next_steps = "• Address failing tests\n• Optimize autonomous learning patterns\n• Validate safety protocols"
            else:
                phase_status = "❌ PHASE 2 NEEDS WORK"
                phase_message = "SAFLA Phase 2 requires additional work before completion."
                next_steps = "• Fix critical issues\n• Validate SAFLA integration\n• Test autonomous learning patterns"
            
            print(f"\nPHASE STATUS: {phase_status}")
            print(f"Phase Assessment: {phase_message}")
            print(f"\nNext Steps:\n{next_steps}")
            
            speak_to_marc(f"SAFLA Phase 2 testing complete! Overall success rate: {overall_success_rate:.1f} percent. {phase_message}")
        else:
            print("❌ NO TESTS EXECUTED")
            speak_to_marc("SAFLA Phase 2 testing failed - no tests were executed!")
        
        print(f"\nTest Completion Time: {datetime.now().isoformat()}")
        print("=" * 48)
        
        # Save detailed results
        with open("safla_phase2_test_results.json", "w") as f:
            json.dump({
                "test_results": self.test_results,
                "summary": {
                    "total_passed": total_passed,
                    "total_failed": total_failed,
                    "overall_success_rate": overall_success_rate if overall_total > 0 else 0,
                    "test_timestamp": datetime.now().isoformat(),
                    "phase": "SAFLA Phase 2",
                    "component": "Enhanced Memory MCP"
                }
            }, f, indent=2)
        
        print("📋 Detailed results saved to: safla_phase2_test_results.json")

async def main():
    """Main test execution"""
    tester = SAFLAMemoryPhase2Tester()
    await tester.run_comprehensive_test()

if __name__ == "__main__":
    asyncio.run(main())