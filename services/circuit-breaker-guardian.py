#!/usr/bin/env python3
"""
Circuit Breaker Guardian - Independent Safety Monitor for AGI Operations

This daemon runs as an independent systemd service with veto power over
destructive AGI operations. It implements the circuit breaker pattern to
prevent cascading failures when the AGI safety system misbehaves.

Architecture Layer: 2 (Circuit Breaker Guardian)
Designed based on: OBSERVABILITY-LAYER-DESIGN.md

Key Features:
- Independent process (not controlled by AGI loop)
- Unix socket IPC for AGI → Guardian communication
- Circuit breaker state machine: CLOSED → OPEN → HALF-OPEN
- Rate limiting on destructive operations
- Alerting when circuit opens
- Audit logging of all decisions

Author: AGI Development System
Created: 2025-12-03
"""

import asyncio
import json
import logging
import os
import signal
import socket
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List
import hashlib

# Configuration
SOCKET_PATH = "/var/run/agi-guardian/guardian.sock"
STATE_FILE = "/var/lib/agi-guardian/state.json"
AUDIT_LOG_DIR = "/var/log/agi-guardian"
PID_FILE = "/var/run/agi-guardian/guardian.pid"

# Thresholds
FAILURE_THRESHOLD = 3
RECOVERY_TIMEOUT = 300  # seconds
MIN_CONFIDENCE_DESTRUCTIVE = 0.7
RATE_LIMIT_SECONDS = 60
MAX_DESTRUCTIVE_OPS_PER_HOUR = 5

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"{AUDIT_LOG_DIR}/guardian.log") if Path(AUDIT_LOG_DIR).exists() else logging.StreamHandler()
    ]
)
logger = logging.getLogger("circuit-breaker-guardian")


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation, allowing requests
    OPEN = "open"          # Blocking all destructive operations
    HALF_OPEN = "half_open"  # Testing if system has recovered


class OperationType(Enum):
    """Types of operations that require guardian approval."""
    ROLLBACK = "rollback"
    GIT_RESET = "git_reset"
    FILE_DELETE = "file_delete"
    SELF_MODIFY = "self_modify"
    CONFIG_CHANGE = "config_change"
    CAPABILITY_INSTALL = "capability_install"


@dataclass
class GuardianState:
    """Persistent state of the circuit breaker guardian."""
    circuit_state: str = "closed"
    failure_count: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    total_blocked: int = 0
    total_approved: int = 0
    recent_operations: List[Dict] = None
    last_destructive_op_time: Optional[float] = None
    hourly_destructive_count: int = 0
    hourly_reset_time: Optional[float] = None

    def __post_init__(self):
        if self.recent_operations is None:
            self.recent_operations = []

    def to_dict(self) -> dict:
        return {
            "circuit_state": self.circuit_state,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "last_success_time": self.last_success_time,
            "total_blocked": self.total_blocked,
            "total_approved": self.total_approved,
            "recent_operations": self.recent_operations[-100:],  # Keep last 100
            "last_destructive_op_time": self.last_destructive_op_time,
            "hourly_destructive_count": self.hourly_destructive_count,
            "hourly_reset_time": self.hourly_reset_time
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'GuardianState':
        return cls(
            circuit_state=data.get("circuit_state", "closed"),
            failure_count=data.get("failure_count", 0),
            last_failure_time=data.get("last_failure_time"),
            last_success_time=data.get("last_success_time"),
            total_blocked=data.get("total_blocked", 0),
            total_approved=data.get("total_approved", 0),
            recent_operations=data.get("recent_operations", []),
            last_destructive_op_time=data.get("last_destructive_op_time"),
            hourly_destructive_count=data.get("hourly_destructive_count", 0),
            hourly_reset_time=data.get("hourly_reset_time")
        )


@dataclass
class ApprovalRequest:
    """Request for approval from AGI system."""
    operation_type: str
    confidence: float
    reason: str
    requester: str
    context: Dict[str, Any]
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


@dataclass
class ApprovalResponse:
    """Response from guardian to AGI system."""
    approved: bool
    reason: str
    circuit_state: str
    request_id: str
    recommendations: List[str] = None

    def __post_init__(self):
        if self.recommendations is None:
            self.recommendations = []


class ImmutableAuditLog:
    """Append-only audit log with cryptographic integrity."""

    def __init__(self, log_dir: str = AUDIT_LOG_DIR):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.chain_file = self.log_dir / "hash_chain.json"
        self.last_hash = self._load_last_hash()

    def _load_last_hash(self) -> Optional[str]:
        if self.chain_file.exists():
            try:
                data = json.loads(self.chain_file.read_text())
                return data.get("last_hash")
            except:
                return None
        return None

    def _save_last_hash(self):
        self.chain_file.write_text(json.dumps({"last_hash": self.last_hash}))

    def log(self, event_type: str, data: Dict[str, Any]) -> str:
        """Log an event with hash chain integrity."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "data": data,
            "previous_hash": self.last_hash
        }

        # Compute hash
        entry_json = json.dumps(entry, sort_keys=True)
        entry_hash = hashlib.sha256(entry_json.encode()).hexdigest()
        entry["hash"] = entry_hash

        # Write to date-based log file
        date_file = self.log_dir / f"{datetime.utcnow().date()}.jsonl"
        with open(date_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

        # Update chain
        self.last_hash = entry_hash
        self._save_last_hash()

        return entry_hash

    def verify_integrity(self) -> bool:
        """Verify the entire audit chain hasn't been tampered with."""
        previous_hash = None

        for log_file in sorted(self.log_dir.glob("*.jsonl")):
            with open(log_file) as f:
                for line in f:
                    entry = json.loads(line)

                    # Verify chain
                    if entry["previous_hash"] != previous_hash:
                        logger.error(f"Chain broken at {entry['timestamp']}")
                        return False

                    # Verify hash
                    stored_hash = entry.pop("hash")
                    computed_hash = hashlib.sha256(
                        json.dumps(entry, sort_keys=True).encode()
                    ).hexdigest()

                    if computed_hash != stored_hash:
                        logger.error(f"Hash mismatch at {entry['timestamp']}")
                        return False

                    previous_hash = stored_hash

        return True


class CircuitBreakerGuardian:
    """
    Independent safety guardian with veto power over AGI operations.

    Implements the circuit breaker pattern to prevent cascading failures
    when the AGI safety system itself becomes a source of problems.
    """

    def __init__(self):
        self.state = GuardianState()
        self.audit = ImmutableAuditLog()
        self.running = False
        self._load_state()

    def _load_state(self):
        """Load persistent state from disk."""
        state_path = Path(STATE_FILE)
        if state_path.exists():
            try:
                data = json.loads(state_path.read_text())
                self.state = GuardianState.from_dict(data)
                logger.info(f"Loaded state: circuit={self.state.circuit_state}, failures={self.state.failure_count}")
            except Exception as e:
                logger.error(f"Failed to load state: {e}")

    def _save_state(self):
        """Persist state to disk."""
        state_path = Path(STATE_FILE)
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(self.state.to_dict(), indent=2))

    def _check_hourly_reset(self):
        """Reset hourly counter if needed."""
        now = time.time()
        if self.state.hourly_reset_time is None:
            self.state.hourly_reset_time = now
            self.state.hourly_destructive_count = 0
        elif now - self.state.hourly_reset_time > 3600:
            self.state.hourly_reset_time = now
            self.state.hourly_destructive_count = 0

    def _is_destructive(self, op_type: str) -> bool:
        """Check if operation type is destructive."""
        destructive_ops = {
            OperationType.ROLLBACK.value,
            OperationType.GIT_RESET.value,
            OperationType.FILE_DELETE.value,
            OperationType.SELF_MODIFY.value
        }
        return op_type in destructive_ops

    def approve_operation(self, request: ApprovalRequest) -> ApprovalResponse:
        """
        Evaluate whether to approve an operation.

        This is the core decision-making function that implements:
        - Circuit breaker state machine
        - Confidence threshold checking
        - Rate limiting
        - Hourly operation limits
        """
        request_id = hashlib.sha256(
            f"{request.timestamp}:{request.operation_type}:{request.requester}".encode()
        ).hexdigest()[:16]

        logger.info(f"[{request_id}] Approval request: {request.operation_type} (confidence={request.confidence:.1%})")

        recommendations = []

        # Check circuit state
        current_state = CircuitState(self.state.circuit_state)

        if current_state == CircuitState.OPEN:
            # Check if we should transition to half-open
            if self.state.last_failure_time and \
               time.time() - self.state.last_failure_time > RECOVERY_TIMEOUT:
                self.state.circuit_state = CircuitState.HALF_OPEN.value
                current_state = CircuitState.HALF_OPEN
                logger.info(f"[{request_id}] Circuit transitioning to HALF_OPEN after recovery timeout")
                self.audit.log("CIRCUIT_HALF_OPEN", {"request_id": request_id})
            else:
                # Still in OPEN state - block all destructive ops
                if self._is_destructive(request.operation_type):
                    self.state.total_blocked += 1
                    self._save_state()
                    self.audit.log("BLOCKED_CIRCUIT_OPEN", {
                        "request_id": request_id,
                        "operation": request.operation_type,
                        "time_until_half_open": RECOVERY_TIMEOUT - (time.time() - (self.state.last_failure_time or 0))
                    })
                    return ApprovalResponse(
                        approved=False,
                        reason=f"Circuit OPEN - blocking all destructive operations. Recovery in {int(RECOVERY_TIMEOUT - (time.time() - (self.state.last_failure_time or 0)))}s",
                        circuit_state=self.state.circuit_state,
                        request_id=request_id,
                        recommendations=["Wait for circuit recovery", "Manual override requires admin intervention"]
                    )

        # For destructive operations, apply additional checks
        if self._is_destructive(request.operation_type):
            # Check 1: Confidence threshold
            if request.confidence < MIN_CONFIDENCE_DESTRUCTIVE:
                self._record_failure(f"Low confidence: {request.confidence:.1%}")
                self.audit.log("BLOCKED_LOW_CONFIDENCE", {
                    "request_id": request_id,
                    "operation": request.operation_type,
                    "confidence": request.confidence,
                    "threshold": MIN_CONFIDENCE_DESTRUCTIVE
                })
                recommendations.append(f"Increase confidence above {MIN_CONFIDENCE_DESTRUCTIVE:.0%} threshold")
                return ApprovalResponse(
                    approved=False,
                    reason=f"Confidence {request.confidence:.1%} below minimum {MIN_CONFIDENCE_DESTRUCTIVE:.0%}",
                    circuit_state=self.state.circuit_state,
                    request_id=request_id,
                    recommendations=recommendations
                )

            # Check 2: Rate limiting
            if self.state.last_destructive_op_time and \
               time.time() - self.state.last_destructive_op_time < RATE_LIMIT_SECONDS:
                wait_time = int(RATE_LIMIT_SECONDS - (time.time() - self.state.last_destructive_op_time))
                self.audit.log("BLOCKED_RATE_LIMIT", {
                    "request_id": request_id,
                    "operation": request.operation_type,
                    "wait_time": wait_time
                })
                return ApprovalResponse(
                    approved=False,
                    reason=f"Rate limited - wait {wait_time}s between destructive operations",
                    circuit_state=self.state.circuit_state,
                    request_id=request_id,
                    recommendations=[f"Wait {wait_time} seconds before retry"]
                )

            # Check 3: Hourly limit
            self._check_hourly_reset()
            if self.state.hourly_destructive_count >= MAX_DESTRUCTIVE_OPS_PER_HOUR:
                self.audit.log("BLOCKED_HOURLY_LIMIT", {
                    "request_id": request_id,
                    "operation": request.operation_type,
                    "count": self.state.hourly_destructive_count,
                    "limit": MAX_DESTRUCTIVE_OPS_PER_HOUR
                })
                return ApprovalResponse(
                    approved=False,
                    reason=f"Hourly limit ({MAX_DESTRUCTIVE_OPS_PER_HOUR}) reached for destructive operations",
                    circuit_state=self.state.circuit_state,
                    request_id=request_id,
                    recommendations=["Wait for hourly reset", "Review why so many destructive ops needed"]
                )

        # Half-open test
        if current_state == CircuitState.HALF_OPEN:
            logger.info(f"[{request_id}] HALF_OPEN test - allowing one operation")
            # Allow one operation as a test
            self.state.circuit_state = CircuitState.CLOSED.value
            self.state.failure_count = 0
            self.audit.log("CIRCUIT_CLOSED", {"request_id": request_id, "reason": "half_open_test_passed"})

        # APPROVED - update state
        self.state.total_approved += 1
        self.state.last_success_time = time.time()

        if self._is_destructive(request.operation_type):
            self.state.last_destructive_op_time = time.time()
            self.state.hourly_destructive_count += 1

        # Record operation
        self.state.recent_operations.append({
            "request_id": request_id,
            "operation": request.operation_type,
            "confidence": request.confidence,
            "timestamp": time.time(),
            "approved": True,
            "requester": request.requester
        })

        self._save_state()

        self.audit.log("APPROVED", {
            "request_id": request_id,
            "operation": request.operation_type,
            "confidence": request.confidence,
            "requester": request.requester,
            "context": request.context
        })

        logger.info(f"[{request_id}] APPROVED: {request.operation_type}")

        return ApprovalResponse(
            approved=True,
            reason="Operation approved",
            circuit_state=self.state.circuit_state,
            request_id=request_id,
            recommendations=[]
        )

    def _record_failure(self, reason: str):
        """Record a failure and potentially open the circuit."""
        self.state.failure_count += 1
        self.state.last_failure_time = time.time()
        self.state.total_blocked += 1

        logger.warning(f"Failure recorded: {reason} (count={self.state.failure_count})")

        if self.state.failure_count >= FAILURE_THRESHOLD:
            self.state.circuit_state = CircuitState.OPEN.value
            self._alert_circuit_open(reason)
            self.audit.log("CIRCUIT_OPEN", {
                "reason": reason,
                "failure_count": self.state.failure_count
            })

        self._save_state()

    def _alert_circuit_open(self, reason: str):
        """Alert when circuit opens - blocking all destructive operations."""
        logger.critical(f"CIRCUIT BREAKER OPEN - All destructive operations blocked!")
        logger.critical(f"Reason: {reason}")
        logger.critical(f"Recovery timeout: {RECOVERY_TIMEOUT}s")

        # Could integrate with alerting systems here (email, Slack, etc.)
        # For now, write to a prominent location
        alert_file = Path("/tmp/agi-guardian-alert.txt")
        alert_file.write_text(f"""
AGI CIRCUIT BREAKER ALERT
=========================
Time: {datetime.now().isoformat()}
Status: CIRCUIT OPEN - All destructive AGI operations BLOCKED
Reason: {reason}
Failure Count: {self.state.failure_count}
Recovery: Automatic after {RECOVERY_TIMEOUT}s, or manual intervention

To manually reset:
  echo '{{"action": "reset_circuit"}}' | nc -U {SOCKET_PATH}
""")

    def report_outcome(self, request_id: str, success: bool, details: str = ""):
        """Report the outcome of an approved operation for learning."""
        if not success:
            self._record_failure(f"Operation {request_id} failed: {details}")

        self.audit.log("OUTCOME_REPORTED", {
            "request_id": request_id,
            "success": success,
            "details": details
        })

    def get_status(self) -> Dict[str, Any]:
        """Get current guardian status."""
        return {
            "circuit_state": self.state.circuit_state,
            "failure_count": self.state.failure_count,
            "total_approved": self.state.total_approved,
            "total_blocked": self.state.total_blocked,
            "last_failure": datetime.fromtimestamp(self.state.last_failure_time).isoformat() if self.state.last_failure_time else None,
            "last_success": datetime.fromtimestamp(self.state.last_success_time).isoformat() if self.state.last_success_time else None,
            "hourly_destructive_count": self.state.hourly_destructive_count,
            "audit_integrity": self.audit.verify_integrity(),
            "uptime": time.time() - self._start_time if hasattr(self, '_start_time') else 0
        }

    def reset_circuit(self, admin_override: bool = False) -> bool:
        """Manually reset the circuit breaker."""
        if admin_override:
            self.state.circuit_state = CircuitState.CLOSED.value
            self.state.failure_count = 0
            self._save_state()
            self.audit.log("CIRCUIT_MANUAL_RESET", {"admin_override": True})
            logger.info("Circuit manually reset by admin")
            return True
        return False


class GuardianServer:
    """Unix socket server for AGI → Guardian communication."""

    def __init__(self, guardian: CircuitBreakerGuardian):
        self.guardian = guardian
        self.socket_path = Path(SOCKET_PATH)
        self.server = None

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle incoming requests from AGI systems."""
        try:
            data = await reader.read(8192)
            if not data:
                return

            request_data = json.loads(data.decode())
            action = request_data.get("action", "approve")

            if action == "approve":
                # Approval request
                request = ApprovalRequest(
                    operation_type=request_data["operation_type"],
                    confidence=request_data["confidence"],
                    reason=request_data.get("reason", ""),
                    requester=request_data.get("requester", "unknown"),
                    context=request_data.get("context", {})
                )
                response = self.guardian.approve_operation(request)
                result = {
                    "approved": response.approved,
                    "reason": response.reason,
                    "circuit_state": response.circuit_state,
                    "request_id": response.request_id,
                    "recommendations": response.recommendations
                }

            elif action == "report_outcome":
                self.guardian.report_outcome(
                    request_data["request_id"],
                    request_data["success"],
                    request_data.get("details", "")
                )
                result = {"status": "recorded"}

            elif action == "status":
                result = self.guardian.get_status()

            elif action == "reset_circuit":
                success = self.guardian.reset_circuit(admin_override=True)
                result = {"reset": success}

            elif action == "verify_audit":
                result = {"integrity": self.guardian.audit.verify_integrity()}

            else:
                result = {"error": f"Unknown action: {action}"}

            writer.write(json.dumps(result).encode())
            await writer.drain()

        except Exception as e:
            logger.error(f"Error handling client: {e}", exc_info=True)
            try:
                writer.write(json.dumps({"error": str(e)}).encode())
                await writer.drain()
            except:
                pass
        finally:
            writer.close()
            await writer.wait_closed()

    async def start(self):
        """Start the Unix socket server."""
        # Ensure socket directory exists
        self.socket_path.parent.mkdir(parents=True, exist_ok=True)

        # Remove existing socket
        if self.socket_path.exists():
            self.socket_path.unlink()

        self.server = await asyncio.start_unix_server(
            self.handle_client,
            path=str(self.socket_path)
        )

        # Set socket permissions (allow all local processes)
        os.chmod(str(self.socket_path), 0o666)

        logger.info(f"Guardian server listening on {self.socket_path}")

        async with self.server:
            await self.server.serve_forever()

    async def stop(self):
        """Stop the server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        if self.socket_path.exists():
            self.socket_path.unlink()


async def main():
    """Main entry point for the guardian daemon."""
    # Create directories
    for path in [SOCKET_PATH, STATE_FILE, AUDIT_LOG_DIR]:
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    # Write PID file
    pid_path = Path(PID_FILE)
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text(str(os.getpid()))

    # Initialize guardian
    guardian = CircuitBreakerGuardian()
    guardian._start_time = time.time()
    guardian.running = True

    # Initialize server
    server = GuardianServer(guardian)

    # Handle signals
    loop = asyncio.get_event_loop()

    def handle_shutdown(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        guardian.running = False
        loop.call_soon_threadsafe(loop.stop)

    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    # Log startup
    guardian.audit.log("GUARDIAN_START", {
        "pid": os.getpid(),
        "socket_path": str(SOCKET_PATH),
        "config": {
            "failure_threshold": FAILURE_THRESHOLD,
            "recovery_timeout": RECOVERY_TIMEOUT,
            "min_confidence": MIN_CONFIDENCE_DESTRUCTIVE,
            "rate_limit": RATE_LIMIT_SECONDS,
            "hourly_limit": MAX_DESTRUCTIVE_OPS_PER_HOUR
        }
    })

    logger.info("=" * 60)
    logger.info("Circuit Breaker Guardian Starting")
    logger.info(f"  Socket: {SOCKET_PATH}")
    logger.info(f"  State:  {STATE_FILE}")
    logger.info(f"  Audit:  {AUDIT_LOG_DIR}")
    logger.info(f"  Current state: {guardian.state.circuit_state}")
    logger.info("=" * 60)

    try:
        await server.start()
    except asyncio.CancelledError:
        pass
    finally:
        await server.stop()
        guardian.audit.log("GUARDIAN_STOP", {"pid": os.getpid()})
        if pid_path.exists():
            pid_path.unlink()
        logger.info("Guardian shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
