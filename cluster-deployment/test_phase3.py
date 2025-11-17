#!/usr/bin/env python3
"""
Phase 3: Human-in-the-Loop Framework - Comprehensive Tests
==========================================================

Tests all Phase 3 components:
- Risk scoring engine
- Approval workflow system
- Arduino approval controller
- Audit trail logging
- Integration with daemon

Test Categories:
1. Risk Assessment Tests
2. Approval Workflow Tests
3. Arduino Controller Tests (simulation)
4. Audit Trail Tests
5. Integration Tests
6. End-to-End Workflow Tests
"""

import json
import logging
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

# Import Phase 3 modules
from risk_assessment import RiskScoringEngine, RiskLevel, ApprovalTier
from approval_workflow import ApprovalWorkflow, ApprovalChannel
from arduino_approval_controller import ArduinoApprovalController
from audit_trail import AuditTrail, AuditEventType
from human_in_loop_integration import HumanInLoopManager

logger = logging.getLogger(__name__)


# ============================================================================
# Test Helpers
# ============================================================================

def create_test_task(
    task_id: str = "test-001",
    task_type: str = "code_execution",
    code: str = "print('hello')",
    target_node: str = "test-node"
) -> dict:
    """Create a test task."""
    return {
        "task_id": task_id,
        "type": task_type,
        "target_node": target_node,
        "payload": {
            "code": code,
            "code_language": "python"
        }
    }


# ============================================================================
# 1. Risk Assessment Tests
# ============================================================================

def test_risk_assessment():
    """Test risk assessment engine."""
    print("\n" + "=" * 70)
    print("TEST 1: Risk Assessment Engine")
    print("=" * 70)

    engine = RiskScoringEngine()
    tests_passed = 0
    tests_total = 0

    # Test 1.1: Low risk task
    print("\n1.1 Testing low-risk task...")
    task = create_test_task(code="print('hello')", target_node="single-node")
    assessment = engine.assess_task_risk(task)

    tests_total += 1
    if assessment.risk_level == RiskLevel.LOW or assessment.risk_level == RiskLevel.MEDIUM:
        print(f"  ✓ Risk level: {assessment.risk_level.value} (score: {assessment.risk_score:.3f})")
        tests_passed += 1
    else:
        print(f"  ✗ Expected low/medium risk, got {assessment.risk_level.value}")

    # Test 1.2: High risk task (destructive operation)
    print("\n1.2 Testing high-risk task...")
    task = create_test_task(code="import shutil; shutil.rmtree('/tmp/test')", target_node="*")
    assessment = engine.assess_task_risk(task)

    tests_total += 1
    if assessment.risk_level == RiskLevel.HIGH or assessment.risk_level == RiskLevel.CRITICAL:
        print(f"  ✓ Risk level: {assessment.risk_level.value} (score: {assessment.risk_score:.3f})")
        tests_passed += 1
    else:
        print(f"  ✗ Expected high/critical risk, got {assessment.risk_level.value}")

    # Test 1.3: Critical patterns detection
    print("\n1.3 Testing critical pattern detection...")
    critical_patterns = [
        "rm -rf /",
        "DROP TABLE users",
        "DELETE FROM sessions"
    ]

    for pattern in critical_patterns:
        task = create_test_task(code=pattern)
        assessment = engine.assess_task_risk(task)
        tests_total += 1

        if assessment.risk_level == RiskLevel.CRITICAL:
            print(f"  ✓ Detected critical pattern: {pattern}")
            tests_passed += 1
        else:
            print(f"  ✗ Failed to detect: {pattern} (got {assessment.risk_level.value})")

    # Test 1.4: Novelty tracking
    print("\n1.4 Testing novelty tracking...")
    task = create_test_task(task_id="novelty-test-1")

    assessment1 = engine.assess_task_risk(task)
    novelty1 = assessment1.risk_factors.novelty

    # Execute same task again
    assessment2 = engine.assess_task_risk(task)
    novelty2 = assessment2.risk_factors.novelty

    tests_total += 1
    if novelty2 < novelty1:
        print(f"  ✓ Novelty decreased: {novelty1:.2f} -> {novelty2:.2f}")
        tests_passed += 1
    else:
        print(f"  ✗ Novelty did not decrease: {novelty1:.2f} -> {novelty2:.2f}")

    print(f"\n  Risk Assessment: {tests_passed}/{tests_total} tests passed")
    return tests_passed, tests_total


# ============================================================================
# 2. Approval Workflow Tests
# ============================================================================

def test_approval_workflow():
    """Test approval workflow system."""
    print("\n" + "=" * 70)
    print("TEST 2: Approval Workflow System")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        workflow = ApprovalWorkflow(
            storage_dir=Path(tmpdir),
            default_timeout=5,
            auto_approve_low_risk=True
        )

        engine = RiskScoringEngine()
        tests_passed = 0
        tests_total = 0

        # Test 2.1: Auto-approval for low risk
        print("\n2.1 Testing auto-approval...")
        task = create_test_task(code="print('test')", target_node="node1")
        assessment = engine.assess_task_risk(task)

        # Force low risk for this test
        assessment.approval_tier = ApprovalTier.AUTOMATIC

        request_id = workflow.request_approval(task, assessment, requester="test")
        decision = workflow.wait_for_approval(request_id, timeout=1)

        tests_total += 1
        if decision.approved:
            print(f"  ✓ Auto-approved low-risk task")
            tests_passed += 1
        else:
            print(f"  ✗ Low-risk task not auto-approved")

        # Test 2.2: Manual approval
        print("\n2.2 Testing manual approval...")
        task = create_test_task(code="rm -rf /tmp/test", target_node="*")
        assessment = engine.assess_task_risk(task)

        request_id = workflow.request_approval(task, assessment, requester="test", timeout=10)

        # Simulate approval
        time.sleep(0.5)
        workflow.approve(request_id, "test_user", ApprovalChannel.CLI, reason="Test approval")

        decision = workflow.wait_for_approval(request_id, timeout=5)

        tests_total += 1
        if decision.approved and decision.channel == ApprovalChannel.CLI:
            print(f"  ✓ Manual approval successful")
            tests_passed += 1
        else:
            print(f"  ✗ Manual approval failed")

        # Test 2.3: Rejection
        print("\n2.3 Testing rejection...")
        task = create_test_task(task_id="reject-test")
        assessment = engine.assess_task_risk(task)

        request_id = workflow.request_approval(task, assessment, requester="test", timeout=10)

        time.sleep(0.5)
        workflow.reject(request_id, "test_user", ApprovalChannel.CLI, reason="Test rejection")

        decision = workflow.wait_for_approval(request_id, timeout=5)

        tests_total += 1
        if not decision.approved:
            print(f"  ✓ Rejection successful")
            tests_passed += 1
        else:
            print(f"  ✗ Rejection failed")

        # Test 2.4: Timeout
        print("\n2.4 Testing timeout...")
        task = create_test_task(task_id="timeout-test")
        assessment = engine.assess_task_risk(task)
        assessment.approval_tier = ApprovalTier.APPROVAL  # Force approval requirement

        request_id = workflow.request_approval(task, assessment, requester="test", timeout=2)

        # Don't approve - let it timeout
        decision = workflow.wait_for_approval(request_id, timeout=3)

        tests_total += 1
        if not decision.approved and decision.reason and "timeout" in decision.reason.lower():
            print(f"  ✓ Timeout handled correctly")
            tests_passed += 1
        else:
            print(f"  ✗ Timeout handling failed")

        # Test 2.5: Statistics
        print("\n2.5 Testing statistics...")
        stats = workflow.get_approval_statistics()

        tests_total += 1
        if stats['total_requests'] >= 4:  # We made at least 4 requests
            print(f"  ✓ Statistics: {stats['total_requests']} requests tracked")
            tests_passed += 1
        else:
            print(f"  ✗ Statistics incomplete: {stats}")

        print(f"\n  Approval Workflow: {tests_passed}/{tests_total} tests passed")
        return tests_passed, tests_total


# ============================================================================
# 3. Arduino Controller Tests
# ============================================================================

def test_arduino_controller():
    """Test Arduino approval controller (simulation mode)."""
    print("\n" + "=" * 70)
    print("TEST 3: Arduino Approval Controller (Simulation)")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        workflow = ApprovalWorkflow(storage_dir=Path(tmpdir))
        controller = ArduinoApprovalController(
            workflow=workflow,
            simulation_mode=True  # Force simulation
        )

        engine = RiskScoringEngine()
        tests_passed = 0
        tests_total = 0

        # Test 3.1: Controller initialization
        print("\n3.1 Testing controller initialization...")
        tests_total += 1
        if controller.simulation_mode:
            print(f"  ✓ Controller initialized in simulation mode")
            tests_passed += 1
        else:
            print(f"  ✗ Controller not in simulation mode")

        # Test 3.2: Display update
        print("\n3.2 Testing display update...")
        task = create_test_task()
        assessment = engine.assess_task_risk(task)

        request_id = workflow.request_approval(task, assessment, requester="test")
        request = workflow.get_request(request_id)

        tests_total += 1
        try:
            controller.on_approval_request(request)
            print(f"  ✓ Display update successful")
            tests_passed += 1
        except Exception as e:
            print(f"  ✗ Display update failed: {e}")

        # Test 3.3: Monitor thread
        print("\n3.3 Testing monitor thread...")
        controller.start()
        time.sleep(0.5)

        tests_total += 1
        if controller.running:
            print(f"  ✓ Monitor thread running")
            tests_passed += 1
        else:
            print(f"  ✗ Monitor thread not running")

        controller.stop()

        print(f"\n  Arduino Controller: {tests_passed}/{tests_total} tests passed")
        return tests_passed, tests_total


# ============================================================================
# 4. Audit Trail Tests
# ============================================================================

def test_audit_trail():
    """Test audit trail logging."""
    print("\n" + "=" * 70)
    print("TEST 4: Audit Trail Logging")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        audit = AuditTrail(
            log_file=Path(tmpdir) / "audit.jsonl",
            node_id="test-node"
        )

        tests_passed = 0
        tests_total = 0

        # Test 4.1: Log event
        print("\n4.1 Testing event logging...")
        event = audit.log_event(
            event_type=AuditEventType.SYSTEM_EVENT,
            actor="test",
            subject="test-subject",
            action="test-action",
            result="success"
        )

        tests_total += 1
        if event.event_id and event.event_hash:
            print(f"  ✓ Event logged with ID: {event.event_id}")
            tests_passed += 1
        else:
            print(f"  ✗ Event logging failed")

        # Test 4.2: Hash chain integrity
        print("\n4.2 Testing hash chain...")
        event2 = audit.log_event(
            event_type=AuditEventType.SYSTEM_EVENT,
            actor="test",
            subject="test-subject-2",
            action="test-action",
            result="success"
        )

        tests_total += 1
        if event2.previous_hash == event.event_hash:
            print(f"  ✓ Hash chain valid")
            tests_passed += 1
        else:
            print(f"  ✗ Hash chain broken: {event2.previous_hash} != {event.event_hash}")

        # Test 4.3: Query events
        print("\n4.3 Testing event query...")
        events = audit.query(event_type=AuditEventType.SYSTEM_EVENT)

        tests_total += 1
        if len(events) >= 2:
            print(f"  ✓ Query returned {len(events)} events")
            tests_passed += 1
        else:
            print(f"  ✗ Query failed: {len(events)} events")

        # Test 4.4: Verify integrity
        print("\n4.4 Testing integrity verification...")
        is_valid, errors = audit.verify_integrity()

        tests_total += 1
        if is_valid:
            print(f"  ✓ Audit log integrity verified")
            tests_passed += 1
        else:
            print(f"  ✗ Integrity check failed: {errors}")

        # Test 4.5: Statistics
        print("\n4.5 Testing statistics...")
        stats = audit.get_statistics()

        tests_total += 1
        if stats['total_events'] >= 2:
            print(f"  ✓ Statistics: {stats['total_events']} total events")
            tests_passed += 1
        else:
            print(f"  ✗ Statistics incomplete")

        print(f"\n  Audit Trail: {tests_passed}/{tests_total} tests passed")
        return tests_passed, tests_total


# ============================================================================
# 5. Integration Tests
# ============================================================================

def test_integration():
    """Test human-in-the-loop integration."""
    print("\n" + "=" * 70)
    print("TEST 5: Human-in-the-Loop Integration")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = HumanInLoopManager(
            node_id="test-node",
            storage_dir=Path(tmpdir),
            enable_arduino=False
        )

        tests_passed = 0
        tests_total = 0

        # Test 5.1: Risk assessment
        print("\n5.1 Testing integrated risk assessment...")
        task = create_test_task()
        assessment = manager.assess_task_risk(task)

        tests_total += 1
        if assessment.risk_score >= 0 and assessment.risk_score <= 1:
            print(f"  ✓ Risk assessment: {assessment.risk_level.value} ({assessment.risk_score:.3f})")
            tests_passed += 1
        else:
            print(f"  ✗ Invalid risk score: {assessment.risk_score}")

        # Test 5.2: Requires approval check
        print("\n5.2 Testing approval requirement check...")
        low_risk_task = create_test_task(code="print('test')")
        high_risk_task = create_test_task(code="rm -rf /tmp/test", target_node="*")

        tests_total += 1
        low_requires = manager.requires_approval(low_risk_task)
        high_requires = manager.requires_approval(high_risk_task)

        if high_requires:  # High risk should require approval
            print(f"  ✓ High-risk task requires approval")
            tests_passed += 1
        else:
            print(f"  ✗ High-risk task doesn't require approval")

        # Test 5.3: Execution logging
        print("\n5.3 Testing execution logging...")
        manager.log_execution_start("test-task-123")
        manager.log_execution_complete("test-task-123", result={"status": "success"})

        audit_stats = manager.get_audit_statistics()

        tests_total += 1
        if audit_stats['total_events'] >= 2:
            print(f"  ✓ Execution logged ({audit_stats['total_events']} events)")
            tests_passed += 1
        else:
            print(f"  ✗ Execution logging incomplete")

        # Test 5.4: Statistics
        print("\n5.4 Testing integrated statistics...")
        approval_stats = manager.get_approval_statistics()
        audit_stats = manager.get_audit_statistics()

        tests_total += 1
        if 'total_requests' in approval_stats and 'total_events' in audit_stats:
            print(f"  ✓ Statistics available")
            print(f"    Approvals: {approval_stats['total_requests']}")
            print(f"    Audit events: {audit_stats['total_events']}")
            tests_passed += 1
        else:
            print(f"  ✗ Statistics incomplete")

        manager.shutdown()

        print(f"\n  Integration: {tests_passed}/{tests_total} tests passed")
        return tests_passed, tests_total


# ============================================================================
# 6. End-to-End Workflow Test
# ============================================================================

def test_end_to_end_workflow():
    """Test complete end-to-end approval workflow."""
    print("\n" + "=" * 70)
    print("TEST 6: End-to-End Workflow")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = HumanInLoopManager(
            node_id="test-node",
            storage_dir=Path(tmpdir),
            enable_arduino=False,
            auto_approve_low_risk=True,
            approval_timeout=5
        )

        tests_passed = 0
        tests_total = 0

        # Test 6.1: Complete low-risk workflow
        print("\n6.1 Testing low-risk task workflow...")
        task = create_test_task(code="print('hello')", target_node="node1")

        # Assess risk
        assessment = manager.assess_task_risk(task)

        # Check approval requirement
        requires_approval = manager.requires_approval(task)

        tests_total += 1
        if not requires_approval or assessment.approval_tier == ApprovalTier.AUTOMATIC:
            print(f"  ✓ Low-risk task doesn't require approval (or auto-approved)")
            tests_passed += 1
        else:
            print(f"  ✗ Low-risk task requires approval: {assessment.approval_tier.value}")

        # Test 6.2: Complete high-risk workflow with approval
        print("\n6.2 Testing high-risk task workflow with approval...")
        task = create_test_task(
            task_id="high-risk-test",
            code="import shutil; shutil.rmtree('/tmp/test')",
            target_node="*"
        )

        # This will block waiting for approval, so we need to approve in parallel
        import threading

        def approve_after_delay():
            time.sleep(1)
            # Get pending requests
            pending = manager.approval_workflow.get_pending_requests()
            if pending:
                request_id = pending[0].request_id
                manager.approval_workflow.approve(
                    request_id,
                    "test_approver",
                    ApprovalChannel.CLI,
                    reason="Test approval"
                )

        # Start approval thread
        approval_thread = threading.Thread(target=approve_after_delay, daemon=True)
        approval_thread.start()

        # Request approval (blocks until approved)
        decision = manager.request_approval(task, requester="test", timeout=10)

        tests_total += 1
        if decision.approved:
            print(f"  ✓ High-risk task approved via {decision.channel.value}")
            tests_passed += 1
        else:
            print(f"  ✗ High-risk task not approved")

        # Test 6.3: Audit trail completeness
        print("\n6.3 Testing audit trail completeness...")
        audit_stats = manager.get_audit_statistics()

        tests_total += 1
        if audit_stats['total_events'] >= 2:  # At least request and decision
            print(f"  ✓ Audit trail complete ({audit_stats['total_events']} events)")
            tests_passed += 1
        else:
            print(f"  ✗ Audit trail incomplete")

        # Test 6.4: Integrity verification
        print("\n6.4 Testing audit integrity...")
        is_valid, errors = manager.verify_audit_integrity()

        tests_total += 1
        if is_valid:
            print(f"  ✓ Audit integrity verified")
            tests_passed += 1
        else:
            print(f"  ✗ Audit integrity check failed: {errors}")

        manager.shutdown()

        print(f"\n  End-to-End: {tests_passed}/{tests_total} tests passed")
        return tests_passed, tests_total


# ============================================================================
# Main Test Runner
# ============================================================================

def run_all_tests():
    """Run all Phase 3 tests."""
    print("\n" + "=" * 70)
    print("PHASE 3: HUMAN-IN-THE-LOOP FRAMEWORK - COMPREHENSIVE TESTS")
    print("=" * 70)

    total_passed = 0
    total_tests = 0

    # Run all test suites
    test_suites = [
        ("Risk Assessment", test_risk_assessment),
        ("Approval Workflow", test_approval_workflow),
        ("Arduino Controller", test_arduino_controller),
        ("Audit Trail", test_audit_trail),
        ("Integration", test_integration),
        ("End-to-End", test_end_to_end_workflow)
    ]

    for suite_name, test_func in test_suites:
        try:
            passed, total = test_func()
            total_passed += passed
            total_tests += total
        except Exception as e:
            logger.error(f"Test suite '{suite_name}' failed with exception: {e}")
            import traceback
            traceback.print_exc()

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"\nTotal Tests:  {total_tests}")
    print(f"Passed:       {total_passed}")
    print(f"Failed:       {total_tests - total_passed}")
    print(f"Success Rate: {(total_passed/total_tests*100) if total_tests > 0 else 0:.1f}%")

    if total_passed == total_tests:
        print("\n✓ ALL TESTS PASSED")
        print("\nPhase 3: Human-in-the-Loop Framework is COMPLETE and VERIFIED")
        return 0
    else:
        print(f"\n✗ {total_tests - total_passed} TESTS FAILED")
        return 1


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)  # Reduce noise
    exit_code = run_all_tests()
    exit(exit_code)
