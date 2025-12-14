#!/usr/bin/env python3
"""
Arduino Approval API Service
============================

HTTP API for cluster-wide Arduino approval requests.

Endpoints:
- POST /approval/request - Request approval (shows on Arduino)
- POST /approval/respond - Respond to approval request
- GET /approval/status/<request_id> - Check approval status
- GET /health - Service health check

Run as systemd service on macpro51.
"""

import json
import logging
import sys
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, Optional
from flask import Flask, request, jsonify
from threading import Lock

# Add paths
sys.path.insert(0, '/mnt/agentic-system/arduino-surface/bridge')
from surface_bridge import ArduinoSurface

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


class RiskLevel(Enum):
    """Risk levels for approval requests."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalStatus(Enum):
    """Approval request status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


@dataclass
class ApprovalRequest:
    """Approval request data."""
    request_id: str
    task_description: str
    risk_level: RiskLevel
    requester_node: str
    timestamp: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    response_time: Optional[str] = None


class ArduinoApprovalService:
    """
    Service that manages Arduino approval requests from cluster nodes.
    """

    def __init__(self, arduino_port: str = "/dev/ttyACM0"):
        self.arduino_port = arduino_port
        self.arduino: Optional[ArduinoSurface] = None
        self.lock = Lock()

        # Active requests
        self.requests: Dict[str, ApprovalRequest] = {}
        self.current_request: Optional[ApprovalRequest] = None

        # Initialize Arduino
        self._init_arduino()

    def _init_arduino(self):
        """Initialize Arduino connection."""
        try:
            self.arduino = ArduinoSurface(self.arduino_port)
            if self.arduino.connect():
                logger.info(f"✓ Arduino connected on {self.arduino_port}")
                # Show ready message
                self.arduino.lcd_clear()
                self.arduino.lcd_write(0, 0, "Approval System")
                self.arduino.lcd_write(1, 0, "Ready")
                self.arduino.set_led(0, 0, 255, 0)  # Green = ready
            else:
                logger.error("Failed to connect to Arduino")
                self.arduino = None
        except Exception as e:
            logger.error(f"Arduino initialization error: {e}")
            self.arduino = None

    def request_approval(
        self,
        task_description: str,
        risk_level: RiskLevel,
        requester_node: str
    ) -> str:
        """
        Request approval for a task.

        Returns:
            request_id
        """
        with self.lock:
            request_id = str(uuid.uuid4())

            approval_request = ApprovalRequest(
                request_id=request_id,
                task_description=task_description,
                risk_level=risk_level,
                requester_node=requester_node,
                timestamp=datetime.utcnow().isoformat()
            )

            self.requests[request_id] = approval_request
            self.current_request = approval_request

            # Display on Arduino
            self._display_request(approval_request)

            logger.info(f"Approval requested: {request_id} from {requester_node}")
            return request_id

    def _display_request(self, req: ApprovalRequest):
        """Display approval request on Arduino."""
        if not self.arduino:
            logger.warning("Arduino not connected - cannot display request")
            return

        try:
            # Clear display
            self.arduino.lcd_clear()
            time.sleep(0.1)

            # Line 1: "APPROVAL REQ"
            self.arduino.lcd_write(0, 0, "APPROVAL REQ")
            time.sleep(0.05)

            # Line 2: Risk + truncated task
            risk_str = req.risk_level.value.upper()[:4]
            task_str = req.task_description[:10]
            self.arduino.lcd_write(1, 0, f"{risk_str}: {task_str}")
            time.sleep(0.05)

            # Set LED based on risk
            colors = {
                RiskLevel.LOW: (0, 255, 0),      # Green
                RiskLevel.MEDIUM: (255, 255, 0), # Yellow
                RiskLevel.HIGH: (255, 128, 0),   # Orange
                RiskLevel.CRITICAL: (255, 0, 0)  # Red
            }
            r, g, b = colors[req.risk_level]
            self.arduino.set_led(0, r, g, b)
            time.sleep(0.05)

            # Play alert beep
            freqs = {
                RiskLevel.LOW: 1000,
                RiskLevel.MEDIUM: 1500,
                RiskLevel.HIGH: 2000,
                RiskLevel.CRITICAL: 2500
            }
            self.arduino.beep(300, freqs[req.risk_level])

            logger.info(f"Displayed request {req.request_id} on Arduino")

        except Exception as e:
            logger.error(f"Error displaying request: {e}")

    def respond_approval(self, request_id: str, approved: bool) -> bool:
        """
        Respond to approval request.

        Args:
            request_id: Request to respond to
            approved: True for approve, False for reject

        Returns:
            True if successful
        """
        with self.lock:
            if request_id not in self.requests:
                logger.warning(f"Unknown request ID: {request_id}")
                return False

            req = self.requests[request_id]

            if req.status != ApprovalStatus.PENDING:
                logger.warning(f"Request {request_id} already responded to")
                return False

            # Update status
            req.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
            req.response_time = datetime.utcnow().isoformat()

            # Show confirmation on Arduino
            self._display_response(approved)

            # Clear current request
            if self.current_request and self.current_request.request_id == request_id:
                self.current_request = None

            logger.info(f"Request {request_id} {'APPROVED' if approved else 'REJECTED'}")
            return True

    def _display_response(self, approved: bool):
        """Display approval/rejection confirmation."""
        if not self.arduino:
            return

        try:
            self.arduino.lcd_clear()
            time.sleep(0.1)

            if approved:
                self.arduino.lcd_write(0, 0, "  APPROVED")
                self.arduino.set_led(0, 0, 255, 0)  # Green
                self.arduino.beep(200, 2000)  # Success beep
            else:
                self.arduino.lcd_write(0, 0, "  REJECTED")
                self.arduino.set_led(0, 255, 0, 0)  # Red
                self.arduino.beep(500, 1000)  # Rejection beep

            time.sleep(2)

            # Return to ready state
            self.arduino.lcd_clear()
            self.arduino.lcd_write(0, 0, "Approval System")
            self.arduino.lcd_write(1, 0, "Ready")
            self.arduino.set_led(0, 0, 255, 0)  # Green

        except Exception as e:
            logger.error(f"Error displaying response: {e}")

    def get_status(self, request_id: str) -> Optional[Dict]:
        """Get approval request status."""
        with self.lock:
            if request_id in self.requests:
                return asdict(self.requests[request_id])
            return None


# Global service instance
service = ArduinoApprovalService()


# ============================================================================
# API Endpoints
# ============================================================================

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'arduino_connected': service.arduino is not None,
        'active_requests': len([r for r in service.requests.values()
                                if r.status == ApprovalStatus.PENDING])
    })


@app.route('/approval/request', methods=['POST'])
def request_approval():
    """Request approval for a task."""
    data = request.json

    # Validate input
    required = ['task_description', 'risk_level', 'requester_node']
    if not all(k in data for k in required):
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        risk_level = RiskLevel(data['risk_level'])
    except ValueError:
        return jsonify({'error': 'Invalid risk_level'}), 400

    # Create request
    request_id = service.request_approval(
        task_description=data['task_description'],
        risk_level=risk_level,
        requester_node=data['requester_node']
    )

    return jsonify({
        'request_id': request_id,
        'status': 'pending',
        'message': 'Approval request displayed on Arduino'
    })


@app.route('/approval/respond', methods=['POST'])
def respond_approval():
    """Respond to approval request."""
    data = request.json

    if 'request_id' not in data or 'approved' not in data:
        return jsonify({'error': 'Missing request_id or approved'}), 400

    success = service.respond_approval(
        request_id=data['request_id'],
        approved=data['approved']
    )

    if success:
        return jsonify({
            'status': 'success',
            'approved': data['approved']
        })
    else:
        return jsonify({'error': 'Invalid or already responded request'}), 400


@app.route('/approval/status/<request_id>', methods=['GET'])
def get_status(request_id: str):
    """Get approval request status."""
    status = service.get_status(request_id)

    if status:
        return jsonify(status)
    else:
        return jsonify({'error': 'Request not found'}), 404


if __name__ == '__main__':
    logger.info("Starting Arduino Approval API Service")
    logger.info("Endpoints:")
    logger.info("  POST /approval/request - Request approval")
    logger.info("  POST /approval/respond - Respond to request")
    logger.info("  GET /approval/status/<id> - Check status")
    logger.info("  GET /health - Health check")

    app.run(host='0.0.0.0', port=9001, debug=False)
