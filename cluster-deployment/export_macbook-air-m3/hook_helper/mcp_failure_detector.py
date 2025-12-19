#!/usr/bin/env python3
"""
MCP Failure Detector - Hook helper module

Detects MCP service failures and provides diagnostic information
Integrates with mcp-controller for health monitoring
"""

import re
from typing import Optional, Dict


def detect_failed_service(error_message: str) -> Optional[str]:
    """
    Detect which MCP service failed from error message

    Args:
        error_message: Error message from tool execution

    Returns:
        Service name if detected, None otherwise
    """
    if not error_message:
        return None

    # Common patterns for MCP failures
    patterns = [
        r"mcp__([^_]+(?:_[^_]+)*?)__",  # mcp__service-name__tool
        r"Not connected.*?([a-z-]+)",  # "Not connected" followed by service name
        r"Server '([^']+)' not available",
        r"Failed to connect to ([a-z-]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, error_message, re.IGNORECASE)
        if match:
            service_name = match.group(1)
            # Clean up service name
            service_name = service_name.replace("_", "-")
            return service_name

    return None


def should_check_mcp_health(tool_name: str, error_message: str) -> bool:
    """
    Determine if we should check MCP health based on tool and error

    Args:
        tool_name: Name of the tool that was called
        error_message: Error message if any

    Returns:
        True if we should check MCP health
    """
    if not error_message:
        return False

    # Check for MCP-related errors
    mcp_error_indicators = [
        "not connected",
        "connection refused",
        "server not available",
        "failed to connect",
        "timeout",
        "broken pipe",
        "mcp error",
    ]

    error_lower = error_message.lower()
    return any(indicator in error_lower for indicator in mcp_error_indicators)


def format_health_summary(health_data: Dict) -> str:
    """
    Format health data for display in hooks

    Args:
        health_data: Health data from mcp-controller

    Returns:
        Formatted summary string
    """
    if not health_data:
        return "No health data available"

    service = health_data.get("service", "unknown")
    status = health_data.get("status", "unknown")
    running = health_data.get("running", False)

    summary = f"MCP Service: {service}\n"
    summary += f"Status: {status}\n"
    summary += f"Running: {'Yes' if running else 'No'}\n"

    if health_data.get("recent_errors"):
        summary += f"\nRecent Errors:\n"
        for error in health_data["recent_errors"][:2]:
            summary += f"  - {error[:100]}...\n"

    return summary


def generate_fix_recommendation(health_data: Dict) -> str:
    """
    Generate fix recommendation based on health data

    Args:
        health_data: Health data from mcp-controller

    Returns:
        Recommendation string
    """
    status = health_data.get("status", "unknown")
    service = health_data.get("service", "unknown")

    if status == "down":
        return f"""
Service {service} is DOWN.

Immediate actions:
1. Use /mcp-fix {service} for detailed diagnostics
2. Check logs: {health_data.get('log_file', 'unknown')}
3. Consider creating a watchdog: /mcp-watchdog {service}

Note: MCP services managed by Claude Code require a restart to recover.
The controller can create watchdog scripts for auto-monitoring.
"""

    elif status == "degraded":
        return f"""
Service {service} is DEGRADED (running but with errors).

Recommended actions:
1. Review recent errors with /mcp-fix {service}
2. Check if the service needs configuration updates
3. Monitor with a watchdog: /mcp-watchdog {service}
"""

    return f"Service {service} status: {status}"


# Example usage in hooks:
#
# In pre-tool-use.py:
# from mcp_failure_detector import should_check_mcp_health, detect_failed_service
#
# if should_check_mcp_health(tool_name, error):
#     service = detect_failed_service(error)
#     if service:
#         # Query mcp-controller for health
#         health = mcp__mcp_controller__check_mcp_service(service)
#         recommendation = generate_fix_recommendation(health)
#         # Log or announce via voice-mode
