#!/usr/bin/env python3
"""
Arduino Approval Client
=======================

Client library for requesting Arduino approval from any cluster node.

Usage:
    from arduino_approval_client import request_arduino_approval

    approved = request_arduino_approval(
        task_description="Delete /tmp/data",
        risk_level="high",
        requester_node="mac-studio",
        timeout=60
    )

    if approved:
        # Proceed with task
        pass
    else:
        # Task rejected
        pass
"""

import requests
import time
from typing import Optional

# Arduino approval service endpoint (macpro51)
ARDUINO_SERVICE_URL = "http://macpro51.local:9001"
# Fallback IP if mDNS doesn't resolve
ARDUINO_SERVICE_IP = "http://192.168.1.183:9001"


def request_arduino_approval(
    task_description: str,
    risk_level: str,
    requester_node: str,
    timeout: int = 60
) -> bool:
    """
    Request approval from Arduino on macpro51.

    Args:
        task_description: Description of task needing approval
        risk_level: One of: low, medium, high, critical
        requester_node: ID of requesting node
        timeout: Timeout in seconds (default: 60)

    Returns:
        True if approved, False if rejected or timeout
    """
    # Try service URL, fallback to IP
    for base_url in [ARDUINO_SERVICE_URL, ARDUINO_SERVICE_IP]:
        try:
            # Submit approval request
            response = requests.post(
                f"{base_url}/approval/request",
                json={
                    "task_description": task_description,
                    "risk_level": risk_level,
                    "requester_node": requester_node
                },
                timeout=5
            )

            if response.status_code != 200:
                print(f"Approval request failed: {response.text}")
                continue

            request_id = response.json()['request_id']
            print(f"Approval request {request_id} sent to Arduino")
            print(f"Waiting for physical approval (timeout: {timeout}s)...")

            # Poll for response
            start_time = time.time()
            while time.time() - start_time < timeout:
                time.sleep(2)  # Poll every 2 seconds

                status_response = requests.get(
                    f"{base_url}/approval/status/{request_id}",
                    timeout=5
                )

                if status_response.status_code == 200:
                    status_data = status_response.json()

                    if status_data['status'] == 'approved':
                        print(f"✓ Request {request_id} APPROVED")
                        return True
                    elif status_data['status'] == 'rejected':
                        print(f"✗ Request {request_id} REJECTED")
                        return False

            # Timeout
            print(f"⏱️ Request {request_id} TIMEOUT after {timeout}s")
            return False

        except requests.RequestException as e:
            print(f"Connection error to {base_url}: {e}")
            continue

    print("✗ Failed to connect to Arduino approval service")
    return False


def check_service_health() -> Optional[dict]:
    """
    Check if Arduino approval service is available.

    Returns:
        Health status dict or None if unavailable
    """
    for base_url in [ARDUINO_SERVICE_URL, ARDUINO_SERVICE_IP]:
        try:
            response = requests.get(f"{base_url}/health", timeout=5)
            if response.status_code == 200:
                return response.json()
        except requests.RequestException:
            continue

    return None


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    import socket

    print("=" * 70)
    print("Arduino Approval Client Test")
    print("=" * 70)

    # Get current node
    current_node = socket.gethostname()
    print(f"\nRequester node: {current_node}")

    # Check service health
    print("\nChecking service health...")
    health = check_service_health()

    if health:
        print(f"✓ Service healthy")
        print(f"  Arduino connected: {health['arduino_connected']}")
        print(f"  Active requests: {health['active_requests']}")
    else:
        print("✗ Service unavailable")
        exit(1)

    # Test approval request
    print("\n" + "-" * 70)
    print("Requesting approval for HIGH RISK operation...")
    print("-" * 70)

    approved = request_arduino_approval(
        task_description="rm -rf /tmp/test",
        risk_level="high",
        requester_node=current_node,
        timeout=30
    )

    print("\n" + "=" * 70)
    if approved:
        print("RESULT: ✓ APPROVED - Proceeding with operation")
    else:
        print("RESULT: ✗ REJECTED - Operation cancelled")
    print("=" * 70)
