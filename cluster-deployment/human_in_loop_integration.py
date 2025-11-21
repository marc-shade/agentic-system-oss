#!/usr/bin/env python3
"""
Human-in-the-Loop Integration for GitHubNodeDaemon
===================================================

Integrates all Phase 3 components with the daemon:
- Risk assessment engine
- Approval workflow system
- Arduino approval controller (macOS)
- Audit trail logging

Provides a single, clean API for the daemon to use.

Usage in daemon:
    from human_in_loop_integration import HumanInLoopManager

    # Initialize
    manager = HumanInLoopManager(node_id="macpro51")

    # Check if approval needed before executing task
    if manager.requires_approval(task):
        decision = manager.request_approval(task, requester="daemon")

        if not decision.approved:
            # Task rejected - don't execute
            return {"status": "rejected", "reason": decision.reason}

    # Task approved (or low risk) - execute
    result = execute_task(task)

    # Log execution
    manager.log_execution(task, result)
"""

import logging
import platform
from pathlib import Path
from typing import Dict, Optional, Any

from risk_assessment import RiskScoringEngine, RiskAssessment, ApprovalTier
from approval_workflow import ApprovalWorkflow, ApprovalRequest, ApprovalDecision, ApprovalChannel, ApprovalStatus
from arduino_approval_controller import ArduinoApprovalController
from audit_trail import AuditTrail

logger = logging.getLogger(__name__)

# Platform detection
IS_MACOS = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"


class HumanInLoopManager:
    """
    Unified manager for human-in-the-loop components.

    Provides simple API for daemon integration.
    """

    def __init__(
        self,
        node_id: str,
        storage_dir: Optional[Path] = None,
        enable_arduino: bool = True,
        arduino_port: Optional[str] = None,
        approval_timeout: int = 300,  # 5 minutes
        auto_approve_low_risk: bool = True
    ):
        """
        Initialize human-in-the-loop manager.

        Args:
            node_id: Node identifier
            storage_dir: Storage directory for state
            enable_arduino: Enable Arduino controller (macOS only)
            arduino_port: Arduino serial port (auto-detect if None)
            approval_timeout: Default approval timeout (seconds)
            auto_approve_low_risk: Automatically approve low-risk operations
        """
        self.node_id = node_id

        if storage_dir is None:
            storage_dir = Path.home() / ".cache" / "gitMQ-human-in-loop"

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        logger.info("Initializing human-in-the-loop components...")

        # Risk assessment engine
        self.risk_engine = RiskScoringEngine()
        logger.info("✓ Risk scoring engine initialized")

        # Approval workflow
        self.approval_workflow = ApprovalWorkflow(
            storage_dir=self.storage_dir / "approvals",
            default_timeout=approval_timeout,
            auto_approve_low_risk=auto_approve_low_risk
        )
        logger.info("✓ Approval workflow initialized")

        # Arduino controller (macOS only)
        self.arduino = None
        if enable_arduino and IS_MACOS:
            try:
                self.arduino = ArduinoApprovalController(
                    workflow=self.approval_workflow,
                    port=arduino_port,
                    simulation_mode=False
                )
                self.arduino.start()
                logger.info("✓ Arduino approval controller initialized")
            except Exception as e:
                logger.warning(f"Arduino controller failed to initialize: {e}")
                logger.warning("Continuing without Arduino support")
        elif enable_arduino and IS_LINUX:
            # Simulation mode on Linux
            self.arduino = ArduinoApprovalController(
                workflow=self.approval_workflow,
                simulation_mode=True
            )
            self.arduino.start()
            logger.info("✓ Arduino controller initialized (simulation mode)")
        else:
            logger.info("Arduino controller disabled")

        # Audit trail
        self.audit_trail = AuditTrail(
            log_file=self.storage_dir / "audit" / "audit.jsonl",
            node_id=node_id
        )
        logger.info("✓ Audit trail initialized")

        logger.info("Human-in-the-loop system ready")

    def assess_task_risk(self, task: Dict[str, Any]) -> RiskAssessment:
        """
        Assess risk level of a task.

        Args:
            task: Task data (TaskPayload dict)

        Returns:
            RiskAssessment with score and approval tier
        """
        return self.risk_engine.assess_task_risk(task)

    def requires_approval(self, task: Dict[str, Any]) -> bool:
        """
        Check if task requires human approval.

        Args:
            task: Task data

        Returns:
            True if human approval needed, False if can auto-execute
        """
        assessment = self.assess_task_risk(task)

        # Automatic tier = no approval needed
        if assessment.approval_tier == ApprovalTier.AUTOMATIC:
            return False

        return True

    def request_approval(
        self,
        task: Dict[str, Any],
        requester: str = "daemon",
        timeout: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ApprovalDecision:
        """
        Request approval for a task (blocking).

        Automatically assesses risk, requests approval, and waits for decision.

        Args:
            task: Task data
            requester: Who is requesting approval
            timeout: Timeout in seconds (None for default)
            context: Additional context

        Returns:
            ApprovalDecision with approved=True/False
        """
        # Assess risk
        risk_assessment = self.assess_task_risk(task)

        logger.info(f"Task {task.get('task_id', 'unknown')} risk assessment:")
        logger.info(f"  Risk Level: {risk_assessment.risk_level.value}")
        logger.info(f"  Risk Score: {risk_assessment.risk_score:.3f}")
        logger.info(f"  Approval Tier: {risk_assessment.approval_tier.value}")

        # Log approval request
        request_id = self.approval_workflow.request_approval(
            task=task,
            risk_assessment=risk_assessment,
            requester=requester,
            timeout=timeout,
            context=context
        )

        # Get request for audit logging
        request = self.approval_workflow.get_request(request_id)
        if request:
            self.audit_trail.log_approval_request(request)

        # Wait for decision (blocking)
        decision = self.approval_workflow.wait_for_approval(request_id, timeout=timeout)

        # Log decision
        if request:
            self.audit_trail.log_approval_decision(request, decision)

        # Log timeout if applicable
        if request and request.status == ApprovalStatus.TIMEOUT:
            self.audit_trail.log_timeout(request)

        logger.info(f"Approval decision: {'APPROVED' if decision.approved else 'REJECTED'}")
        logger.info(f"  Channel: {decision.channel.value}")
        logger.info(f"  Approver: {decision.approver}")

        return decision

    def log_execution_start(
        self,
        task_id: str,
        executor: str = "daemon",
        context: Optional[Dict] = None
    ):
        """
        Log task execution start.

        Args:
            task_id: Task identifier
            executor: Who is executing
            context: Additional context
        """
        self.audit_trail.log_execution_start(task_id, executor, context)

    def log_execution_complete(
        self,
        task_id: str,
        executor: str = "daemon",
        result: Any = None
    ):
        """
        Log task execution completion.

        Args:
            task_id: Task identifier
            executor: Who executed
            result: Execution result
        """
        self.audit_trail.log_execution_complete(task_id, executor, result)

    def log_execution_failed(
        self,
        task_id: str,
        executor: str = "daemon",
        error: str = ""
    ):
        """
        Log task execution failure.

        Args:
            task_id: Task identifier
            executor: Who executed
            error: Error message
        """
        self.audit_trail.log_execution_failed(task_id, executor, error)

    def get_approval_statistics(self) -> Dict[str, Any]:
        """Get approval statistics."""
        return self.approval_workflow.get_approval_statistics()

    def get_audit_statistics(self) -> Dict[str, Any]:
        """Get audit trail statistics."""
        return self.audit_trail.get_statistics()

    def verify_audit_integrity(self) -> tuple[bool, list[str]]:
        """Verify audit log integrity."""
        return self.audit_trail.verify_integrity()

    def export_compliance_report(
        self,
        start_date: str,
        end_date: str,
        output_file: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Generate compliance report.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            output_file: Optional output file

        Returns:
            Compliance report dictionary
        """
        return self.audit_trail.export_compliance_report(
            start_date=start_date,
            end_date=end_date,
            output_file=output_file
        )

    def shutdown(self):
        """Shutdown human-in-the-loop system."""
        logger.info("Shutting down human-in-the-loop system...")

        # Stop Arduino controller
        if self.arduino:
            self.arduino.stop()
            logger.info("✓ Arduino controller stopped")

        logger.info("Human-in-the-loop system shutdown complete")


# ============================================================================
# Daemon Integration Patch
# ============================================================================

def patch_daemon_execute_code(daemon_instance):
    """
    Patch GitHubNodeDaemon.execute_code_secure() to add human-in-the-loop.

    This function monkey-patches the daemon's execute_code_secure method
    to add approval workflow integration.

    Args:
        daemon_instance: Instance of GitHubNodeDaemon
    """
    # Save original method
    original_execute = daemon_instance.execute_code_secure

    # Create human-in-loop manager
    hil_manager = HumanInLoopManager(
        node_id=daemon_instance.node_id,
        enable_arduino=True,
        auto_approve_low_risk=True
    )

    def execute_code_with_approval(task):
        """
        Execute code with human-in-the-loop approval.

        Replaces execute_code_secure() to add approval workflow.
        """
        task_id = task.get("task_id", "unknown")
        task_dict = task if isinstance(task, dict) else task.model_dump()

        # Check if approval required
        if hil_manager.requires_approval(task_dict):
            logger.info(f"Task {task_id} requires approval")

            # Request approval (blocking)
            decision = hil_manager.request_approval(
                task=task_dict,
                requester="daemon"
            )

            if not decision.approved:
                # Task rejected
                logger.warning(f"Task {task_id} REJECTED by {decision.approver}")

                return {
                    "status": "rejected",
                    "error": f"Rejected by {decision.approver}: {decision.reason}",
                    "exit_code": 1,
                    "approval_decision": decision.to_dict()
                }

            logger.info(f"Task {task_id} APPROVED by {decision.approver}")
        else:
            logger.info(f"Task {task_id} auto-approved (low risk)")

        # Log execution start
        hil_manager.log_execution_start(task_id)

        # Execute task (original method)
        try:
            result = original_execute(task)

            # Log execution result
            if result.get("status") == "success":
                hil_manager.log_execution_complete(task_id, result=result)
            else:
                hil_manager.log_execution_failed(
                    task_id,
                    error=result.get("error", "Unknown error")
                )

            return result

        except Exception as e:
            # Log execution failure
            hil_manager.log_execution_failed(task_id, error=str(e))
            raise

    # Replace method
    daemon_instance.execute_code_secure = execute_code_with_approval

    # Store manager for later access
    daemon_instance.hil_manager = hil_manager

    logger.info("✓ Daemon patched with human-in-the-loop approval workflow")


# ============================================================================
# Example Usage
# ============================================================================

def example_integration():
    """Example: Use HumanInLoopManager."""
    print("\n" + "=" * 70)
    print("Human-in-the-Loop Integration Example")
    print("=" * 70)

    # Initialize manager
    manager = HumanInLoopManager(
        node_id="macpro51",
        enable_arduino=False,  # Disable for demo
        auto_approve_low_risk=True
    )

    # Example tasks
    tasks = [
        # Low risk - auto-approved
        {
            "task_id": "task-001",
            "type": "code_execution",
            "target_node": "macpro51",
            "payload": {
                "code": "print('Hello, World!')",
                "code_language": "python"
            }
        },
        # High risk - requires approval
        {
            "task_id": "task-002",
            "type": "code_execution",
            "target_node": "*",
            "payload": {
                "code": "import os; os.system('rm -rf /tmp/test')",
                "code_language": "python"
            }
        }
    ]

    print("\n1. Processing tasks with human-in-the-loop:")

    for i, task in enumerate(tasks, 1):
        print(f"\n   Task {i}: {task['task_id']}")

        # Assess risk
        assessment = manager.assess_task_risk(task)
        print(f"     Risk: {assessment.risk_level.value} ({assessment.risk_score:.3f})")
        print(f"     Tier: {assessment.approval_tier.value}")

        # Check if approval needed
        if manager.requires_approval(task):
            print(f"     ⚠️  Approval required")

            # In real scenario, would wait for human decision
            # For demo, auto-reject high-risk tasks
            print(f"     (Demo: auto-rejecting for safety)")
            continue
        else:
            print(f"     ✓ Auto-approved (low risk)")

        # Log execution
        manager.log_execution_start(task["task_id"])
        # Simulate execution
        manager.log_execution_complete(task["task_id"], result={"status": "success"})
        print(f"     ✓ Executed and logged")

    # Show statistics
    print("\n2. Statistics:")

    approval_stats = manager.get_approval_statistics()
    print(f"   Approval requests: {approval_stats['total_requests']}")

    audit_stats = manager.get_audit_statistics()
    print(f"   Audit events: {audit_stats['total_events']}")
    print(f"   Event types: {audit_stats['by_type']}")

    # Verify integrity
    is_valid, errors = manager.verify_audit_integrity()
    print(f"\n3. Audit integrity: {'✓ VALID' if is_valid else '✗ INVALID'}")
    if errors:
        for error in errors:
            print(f"     - {error}")

    # Shutdown
    manager.shutdown()

    print("\n" + "=" * 70)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    example_integration()
    print("\nHuman-in-the-loop integration module loaded successfully ✓")
