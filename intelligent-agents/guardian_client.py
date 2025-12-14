#!/usr/bin/env python3
"""
Guardian Client - Interface for AGI Systems to Communicate with Circuit Breaker Guardian

This module provides a simple async/sync interface for AGI systems to request
approval for destructive operations from the independent Circuit Breaker Guardian.

Usage:
    from guardian_client import GuardianClient

    # Async usage
    async with GuardianClient() as client:
        response = await client.request_approval(
            operation_type="rollback",
            confidence=0.75,
            reason="Regression detected",
            context={"files_affected": 5}
        )
        if response.approved:
            # Proceed with operation
            ...
            # Report outcome
            await client.report_outcome(response.request_id, success=True)

    # Sync usage
    client = GuardianClient()
    response = client.request_approval_sync(...)

Author: AGI Development System
Created: 2025-12-03
"""

import asyncio
import json
import logging
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Default socket path - matches guardian daemon
GUARDIAN_SOCKET = "/var/run/agi-guardian/guardian.sock"


@dataclass
class ApprovalResponse:
    """Response from the Circuit Breaker Guardian."""
    approved: bool
    reason: str
    circuit_state: str
    request_id: str
    recommendations: List[str]

    @classmethod
    def from_dict(cls, data: dict) -> 'ApprovalResponse':
        return cls(
            approved=data.get("approved", False),
            reason=data.get("reason", "Unknown"),
            circuit_state=data.get("circuit_state", "unknown"),
            request_id=data.get("request_id", ""),
            recommendations=data.get("recommendations", [])
        )

    @classmethod
    def fallback_blocked(cls, reason: str) -> 'ApprovalResponse':
        """Return a blocked response for when guardian is unavailable."""
        return cls(
            approved=False,
            reason=reason,
            circuit_state="unknown",
            request_id="",
            recommendations=["Check guardian service status", "Verify socket permissions"]
        )


@dataclass
class GuardianStatus:
    """Status of the Circuit Breaker Guardian."""
    circuit_state: str
    failure_count: int
    total_approved: int
    total_blocked: int
    last_failure: Optional[str]
    last_success: Optional[str]
    hourly_destructive_count: int
    audit_integrity: bool
    uptime: float

    @classmethod
    def from_dict(cls, data: dict) -> 'GuardianStatus':
        return cls(
            circuit_state=data.get("circuit_state", "unknown"),
            failure_count=data.get("failure_count", 0),
            total_approved=data.get("total_approved", 0),
            total_blocked=data.get("total_blocked", 0),
            last_failure=data.get("last_failure"),
            last_success=data.get("last_success"),
            hourly_destructive_count=data.get("hourly_destructive_count", 0),
            audit_integrity=data.get("audit_integrity", False),
            uptime=data.get("uptime", 0)
        )


class GuardianClient:
    """
    Client for communicating with the Circuit Breaker Guardian.

    The guardian is an independent safety system that must approve
    all destructive AGI operations before they can proceed.
    """

    def __init__(self, socket_path: str = GUARDIAN_SOCKET, timeout: float = 5.0):
        self.socket_path = socket_path
        self.timeout = timeout
        self._reader = None
        self._writer = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()

    def _check_guardian_available(self) -> bool:
        """Check if the guardian socket exists."""
        return Path(self.socket_path).exists()

    async def _send_request(self, request: dict) -> dict:
        """Send a request to the guardian and get response."""
        if not self._check_guardian_available():
            logger.warning(f"Guardian socket not found at {self.socket_path}")
            return {"error": "Guardian unavailable", "approved": False}

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_unix_connection(self.socket_path),
                timeout=self.timeout
            )

            writer.write(json.dumps(request).encode())
            await writer.drain()

            data = await asyncio.wait_for(
                reader.read(8192),
                timeout=self.timeout
            )

            writer.close()
            await writer.wait_closed()

            return json.loads(data.decode())

        except asyncio.TimeoutError:
            logger.error("Guardian request timed out")
            return {"error": "Request timed out", "approved": False}
        except ConnectionRefusedError:
            logger.error("Guardian connection refused")
            return {"error": "Connection refused", "approved": False}
        except Exception as e:
            logger.error(f"Guardian communication error: {e}")
            return {"error": str(e), "approved": False}

    def _send_request_sync(self, request: dict) -> dict:
        """Synchronous version of _send_request."""
        if not self._check_guardian_available():
            logger.warning(f"Guardian socket not found at {self.socket_path}")
            return {"error": "Guardian unavailable", "approved": False}

        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect(self.socket_path)

            sock.sendall(json.dumps(request).encode())
            data = sock.recv(8192)
            sock.close()

            return json.loads(data.decode())

        except socket.timeout:
            logger.error("Guardian request timed out")
            return {"error": "Request timed out", "approved": False}
        except ConnectionRefusedError:
            logger.error("Guardian connection refused")
            return {"error": "Connection refused", "approved": False}
        except Exception as e:
            logger.error(f"Guardian communication error: {e}")
            return {"error": str(e), "approved": False}

    async def request_approval(
        self,
        operation_type: str,
        confidence: float,
        reason: str = "",
        requester: str = "unknown",
        context: Dict[str, Any] = None
    ) -> ApprovalResponse:
        """
        Request approval for a destructive operation.

        Args:
            operation_type: Type of operation (rollback, git_reset, file_delete, etc.)
            confidence: Confidence score (0.0 - 1.0)
            reason: Human-readable reason for the operation
            requester: Identifier of the requesting system
            context: Additional context about the operation

        Returns:
            ApprovalResponse with approval decision and recommendations
        """
        request = {
            "action": "approve",
            "operation_type": operation_type,
            "confidence": confidence,
            "reason": reason,
            "requester": requester,
            "context": context or {}
        }

        response = await self._send_request(request)

        if "error" in response:
            logger.warning(f"Guardian error: {response['error']}")
            return ApprovalResponse.fallback_blocked(response["error"])

        return ApprovalResponse.from_dict(response)

    def request_approval_sync(
        self,
        operation_type: str,
        confidence: float,
        reason: str = "",
        requester: str = "unknown",
        context: Dict[str, Any] = None
    ) -> ApprovalResponse:
        """Synchronous version of request_approval."""
        request = {
            "action": "approve",
            "operation_type": operation_type,
            "confidence": confidence,
            "reason": reason,
            "requester": requester,
            "context": context or {}
        }

        response = self._send_request_sync(request)

        if "error" in response:
            logger.warning(f"Guardian error: {response['error']}")
            return ApprovalResponse.fallback_blocked(response["error"])

        return ApprovalResponse.from_dict(response)

    async def report_outcome(
        self,
        request_id: str,
        success: bool,
        details: str = ""
    ) -> bool:
        """
        Report the outcome of an approved operation.

        This helps the guardian learn and adjust its behavior.
        Failed operations may contribute to opening the circuit.
        """
        request = {
            "action": "report_outcome",
            "request_id": request_id,
            "success": success,
            "details": details
        }

        response = await self._send_request(request)
        return response.get("status") == "recorded"

    def report_outcome_sync(
        self,
        request_id: str,
        success: bool,
        details: str = ""
    ) -> bool:
        """Synchronous version of report_outcome."""
        request = {
            "action": "report_outcome",
            "request_id": request_id,
            "success": success,
            "details": details
        }

        response = self._send_request_sync(request)
        return response.get("status") == "recorded"

    async def get_status(self) -> GuardianStatus:
        """Get current guardian status."""
        response = await self._send_request({"action": "status"})
        return GuardianStatus.from_dict(response)

    def get_status_sync(self) -> GuardianStatus:
        """Synchronous version of get_status."""
        response = self._send_request_sync({"action": "status"})
        return GuardianStatus.from_dict(response)

    async def verify_audit(self) -> bool:
        """Verify audit log integrity."""
        response = await self._send_request({"action": "verify_audit"})
        return response.get("integrity", False)

    async def reset_circuit(self) -> bool:
        """Request circuit reset (requires admin override)."""
        response = await self._send_request({"action": "reset_circuit"})
        return response.get("reset", False)


# Convenience function for simple approval checks
def require_guardian_approval(
    operation_type: str,
    confidence: float,
    reason: str = "",
    requester: str = "unknown",
    context: Dict[str, Any] = None,
    fail_open: bool = False
) -> ApprovalResponse:
    """
    Convenience function to request guardian approval synchronously.

    Args:
        operation_type: Type of operation
        confidence: Confidence score
        reason: Reason for operation
        requester: Requesting system identifier
        context: Additional context
        fail_open: If True, allow operation when guardian unavailable

    Returns:
        ApprovalResponse
    """
    client = GuardianClient()
    response = client.request_approval_sync(
        operation_type=operation_type,
        confidence=confidence,
        reason=reason,
        requester=requester,
        context=context
    )

    # If guardian is unavailable and fail_open is True, allow the operation
    # This should be used VERY carefully - default is fail_closed
    if not response.approved and "unavailable" in response.reason.lower() and fail_open:
        logger.warning("Guardian unavailable - FAIL OPEN mode - allowing operation")
        return ApprovalResponse(
            approved=True,
            reason="Guardian unavailable - fail_open mode",
            circuit_state="unknown",
            request_id="",
            recommendations=["Start guardian service ASAP"]
        )

    return response


# CLI for testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python guardian_client.py <command> [args]")
        print("Commands:")
        print("  status             - Get guardian status")
        print("  test <confidence>  - Test approval request")
        print("  verify             - Verify audit log")
        print("  reset              - Reset circuit (admin)")
        sys.exit(1)

    command = sys.argv[1]
    client = GuardianClient()

    if command == "status":
        status = client.get_status_sync()
        print(f"Circuit State: {status.circuit_state}")
        print(f"Failures: {status.failure_count}")
        print(f"Approved: {status.total_approved}")
        print(f"Blocked: {status.total_blocked}")
        print(f"Hourly Ops: {status.hourly_destructive_count}")
        print(f"Audit OK: {status.audit_integrity}")

    elif command == "test":
        confidence = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
        response = client.request_approval_sync(
            operation_type="test",
            confidence=confidence,
            reason="Testing guardian client",
            requester="cli_test"
        )
        print(f"Approved: {response.approved}")
        print(f"Reason: {response.reason}")
        print(f"Circuit: {response.circuit_state}")
        if response.recommendations:
            print(f"Recommendations: {', '.join(response.recommendations)}")

    elif command == "verify":
        result = asyncio.run(client.verify_audit())
        print(f"Audit Integrity: {'OK' if result else 'COMPROMISED'}")

    elif command == "reset":
        result = asyncio.run(client.reset_circuit())
        print(f"Reset: {'Success' if result else 'Failed'}")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
