#!/usr/bin/env python3
"""
Arduino Approval Service - Prometheus Metrics Exporter
======================================================

Exports Prometheus metrics for Arduino approval service monitoring.

Metrics:
- arduino_approval_requests_total - Total approval requests
- arduino_approval_request_duration_seconds - Request processing time
- arduino_approval_decisions_total - Approval decisions (approved/rejected)
- arduino_connected - Arduino hardware connection status
- arduino_active_requests - Currently pending requests

Run alongside arduino-approval-api.py
"""

import time
from prometheus_client import Counter, Gauge, Histogram, start_http_server
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Metrics
arduino_connected = Gauge(
    'arduino_connected',
    'Arduino hardware connection status (1=connected, 0=disconnected)'
)

active_requests = Gauge(
    'arduino_active_requests',
    'Number of currently pending approval requests'
)

approval_requests_total = Counter(
    'arduino_approval_requests_total',
    'Total number of approval requests',
    ['requester_node', 'risk_level']
)

approval_decisions_total = Counter(
    'arduino_approval_decisions_total',
    'Total number of approval decisions',
    ['decision', 'risk_level']
)

request_duration = Histogram(
    'arduino_approval_request_duration_seconds',
    'Time spent waiting for approval decision',
    buckets=[5, 10, 20, 30, 60, 120, 300]
)


def scrape_arduino_service():
    """Scrape Arduino approval service for metrics."""
    try:
        response = requests.get('http://localhost:9001/health', timeout=2)

        if response.status_code == 200:
            data = response.json()

            # Update gauges
            arduino_connected.set(1 if data.get('arduino_connected') else 0)
            active_requests.set(data.get('active_requests', 0))

            return True
        else:
            arduino_connected.set(0)
            return False

    except requests.RequestException as e:
        logger.warning(f"Failed to scrape Arduino service: {e}")
        arduino_connected.set(0)
        return False


def main():
    """Start metrics exporter."""
    # Start Prometheus metrics server on port 9002
    start_http_server(9002)
    logger.info("Arduino metrics exporter started on port 9002")
    logger.info("Metrics available at http://localhost:9002/metrics")

    # Scrape loop
    while True:
        scrape_arduino_service()
        time.sleep(15)  # Scrape every 15 seconds


if __name__ == '__main__':
    main()
