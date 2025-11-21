#!/usr/bin/env python3
"""
Webhook Delivery System for Builder Node
Sends build completion notifications to orchestrator
"""

import json
import requests
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


class WebhookDelivery:
    """Handles webhook delivery with retry logic"""

    def __init__(self, log_file: str = "/home/marc/agentic-system/logs/webhooks.log"):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Retry configuration
        self.max_retries = 3
        self.retry_delays = [1, 5, 15]  # Exponential backoff: 1s, 5s, 15s
        self.timeout = 10  # 10 seconds per attempt

    def send_build_completed(
        self,
        webhook_url: str,
        build_id: str,
        project_id: str,
        status: str,
        duration_seconds: int,
        artifacts: Dict,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Send build completion webhook"""

        payload = {
            "event": "build.completed",
            "timestamp": datetime.now().isoformat(),
            "node_id": "macpro51",
            "build_id": build_id,
            "project_id": project_id,
            "status": status,
            "duration_seconds": duration_seconds,
            "artifacts": artifacts,
            "logs_url": f"http://macpro51.local:9000/api/v1/artifacts/{build_id}/logs",
            "download_url": f"http://macpro51.local:9000/api/v1/artifacts/{build_id}/download",
            "metadata": metadata or {},
        }

        return self._deliver_webhook(webhook_url, payload)

    def send_build_started(
        self,
        webhook_url: str,
        build_id: str,
        project_id: str,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Send build started webhook"""

        payload = {
            "event": "build.started",
            "timestamp": datetime.now().isoformat(),
            "node_id": "macpro51",
            "build_id": build_id,
            "project_id": project_id,
            "metadata": metadata or {},
        }

        return self._deliver_webhook(webhook_url, payload)

    def send_build_failed(
        self,
        webhook_url: str,
        build_id: str,
        project_id: str,
        error_message: str,
        exit_code: Optional[int] = None,
    ) -> Dict:
        """Send build failed webhook"""

        payload = {
            "event": "build.failed",
            "timestamp": datetime.now().isoformat(),
            "node_id": "macpro51",
            "build_id": build_id,
            "project_id": project_id,
            "error": error_message,
            "exit_code": exit_code,
            "logs_url": f"http://macpro51.local:9000/api/v1/artifacts/{build_id}/logs",
        }

        return self._deliver_webhook(webhook_url, payload)

    def _deliver_webhook(self, url: str, payload: Dict) -> Dict:
        """Deliver webhook with retry logic"""

        event_type = payload.get("event", "unknown")
        build_id = payload.get("build_id", "unknown")

        logger.info(f"Delivering webhook: {event_type} for build {build_id} to {url}")

        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    timeout=self.timeout,
                    headers={"Content-Type": "application/json"},
                )

                # Log delivery
                self._log_delivery(
                    url=url,
                    payload=payload,
                    attempt=attempt + 1,
                    status_code=response.status_code,
                    response_text=response.text[:500],  # Limit response length
                    success=response.status_code < 300,
                )

                if response.status_code < 300:
                    logger.info(
                        f"Webhook delivered successfully on attempt {attempt + 1}: "
                        f"{event_type} -> {url}"
                    )
                    return {
                        "success": True,
                        "status_code": response.status_code,
                        "response": response.text,
                        "attempt": attempt + 1,
                    }
                else:
                    logger.warning(
                        f"Webhook delivery failed (HTTP {response.status_code}) "
                        f"on attempt {attempt + 1}: {url}"
                    )

                    # Don't retry if 4xx error (client error)
                    if 400 <= response.status_code < 500:
                        logger.error(
                            f"Client error {response.status_code}, not retrying: {url}"
                        )
                        break

            except requests.exceptions.Timeout:
                logger.warning(
                    f"Webhook delivery timeout on attempt {attempt + 1}: {url}"
                )
                self._log_delivery(
                    url=url,
                    payload=payload,
                    attempt=attempt + 1,
                    status_code=None,
                    response_text="Timeout",
                    success=False,
                )

            except requests.exceptions.ConnectionError as e:
                logger.warning(
                    f"Connection error on attempt {attempt + 1}: {url} - {e}"
                )
                self._log_delivery(
                    url=url,
                    payload=payload,
                    attempt=attempt + 1,
                    status_code=None,
                    response_text=f"Connection error: {e}",
                    success=False,
                )

            except Exception as e:
                logger.error(
                    f"Unexpected error on attempt {attempt + 1}: {url} - {e}"
                )
                self._log_delivery(
                    url=url,
                    payload=payload,
                    attempt=attempt + 1,
                    status_code=None,
                    response_text=f"Error: {e}",
                    success=False,
                )

            # Wait before retry (except on last attempt)
            if attempt < self.max_retries - 1:
                delay = self.retry_delays[attempt]
                logger.info(f"Waiting {delay}s before retry {attempt + 2}/{self.max_retries}")
                time.sleep(delay)

        # All retries failed
        logger.error(
            f"Webhook delivery failed after {self.max_retries} attempts: "
            f"{event_type} -> {url}"
        )

        return {
            "success": False,
            "error": f"Failed after {self.max_retries} attempts",
            "url": url,
        }

    def _log_delivery(
        self,
        url: str,
        payload: Dict,
        attempt: int,
        status_code: Optional[int],
        response_text: str,
        success: bool,
    ):
        """Log webhook delivery to file"""

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": payload.get("event", "unknown"),
            "build_id": payload.get("build_id", "unknown"),
            "url": url,
            "attempt": attempt,
            "status_code": status_code,
            "response": response_text,
            "success": success,
        }

        with open(self.log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    def get_recent_deliveries(self, limit: int = 100) -> list:
        """Get recent webhook deliveries from log"""

        if not self.log_file.exists():
            return []

        deliveries = []
        with open(self.log_file) as f:
            for line in f:
                try:
                    deliveries.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue

        # Return most recent
        return deliveries[-limit:]


if __name__ == "__main__":
    # Test webhook delivery
    webhook = WebhookDelivery()

    print("Testing webhook delivery system...")

    # Test build completed webhook (will fail as orchestrator doesn't have endpoint yet)
    result = webhook.send_build_completed(
        webhook_url="http://192.168.1.16:9000/api/v1/build/callback",
        build_id="test-build-123",
        project_id="test-project",
        status="success",
        duration_seconds=120,
        artifacts={
            "count": 3,
            "size_bytes": 1048576,
            "location": "/home/marc/agentic-system/artifacts/builds/test-project/test-build-123",
        },
    )

    print(f"\nDelivery result: {json.dumps(result, indent=2)}")

    # Show recent deliveries
    recent = webhook.get_recent_deliveries(limit=5)
    print(f"\nRecent deliveries ({len(recent)}):")
    for delivery in recent:
        print(f"  {delivery['timestamp']}: {delivery['event']} -> {delivery['success']}")
