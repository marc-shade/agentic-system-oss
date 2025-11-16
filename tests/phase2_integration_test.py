#!/usr/bin/env python3
"""
Phase 2 Integration Test
Verifies all Builder node Phase 2 services are operational
"""

import json
import subprocess
import requests
import sys
from pathlib import Path
from datetime import datetime


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'


def print_header(text):
    print(f"\n{Colors.BLUE}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BLUE}{'=' * 70}{Colors.RESET}\n")


def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")


def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")


def test_builder_api():
    """Test Builder API is running and responsive"""
    print_header("Testing Builder API")

    tests_passed = 0
    tests_failed = 0

    # Test health endpoint
    try:
        response = requests.get("http://localhost:9000/api/v1/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy":
                print_success(f"Health endpoint: {data['status']}")
                print(f"  Services: {data.get('services', {})}")
                tests_passed += 1
            else:
                print_error(f"Health endpoint degraded: {data}")
                tests_failed += 1
        else:
            print_error(f"Health endpoint returned {response.status_code}")
            tests_failed += 1
    except Exception as e:
        print_error(f"Health endpoint failed: {e}")
        tests_failed += 1

    # Test status endpoint
    try:
        response = requests.get("http://localhost:9000/api/v1/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success("Status endpoint responsive")
            print(f"  Node ID: {data.get('node_id')}")
            print(f"  Node Type: {data.get('node_type')}")
            print(f"  Capabilities: {len(data.get('capabilities', []))} available")
            tests_passed += 1
        else:
            print_error(f"Status endpoint returned {response.status_code}")
            tests_failed += 1
    except Exception as e:
        print_error(f"Status endpoint failed: {e}")
        tests_failed += 1

    # Test capabilities endpoint
    try:
        response = requests.get("http://localhost:9000/api/v1/capabilities", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Capabilities endpoint: {len(data.get('capabilities', []))} capabilities")
            tests_passed += 1
        else:
            print_error(f"Capabilities endpoint returned {response.status_code}")
            tests_failed += 1
    except Exception as e:
        print_error(f"Capabilities endpoint failed: {e}")
        tests_failed += 1

    return tests_passed, tests_failed


def test_heartbeat_service():
    """Test heartbeat service is running"""
    print_header("Testing Heartbeat Service")

    tests_passed = 0
    tests_failed = 0

    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", "builder-heartbeat.service"],
            capture_output=True,
            text=True
        )

        if result.stdout.strip() == "active":
            print_success("Heartbeat service is active")
            tests_passed += 1

            # Check recent logs
            log_result = subprocess.run(
                ["journalctl", "--user", "-u", "builder-heartbeat.service",
                 "--no-pager", "--since", "2 minutes ago", "-n", "5"],
                capture_output=True,
                text=True
            )

            if log_result.returncode == 0 and log_result.stdout:
                print_success("Heartbeat service is logging")
                if "Connection error" in log_result.stdout:
                    print_warning("  Note: Connection errors expected until orchestrator endpoint is ready")
                tests_passed += 1
            else:
                print_warning("No recent heartbeat logs found")
        else:
            print_error(f"Heartbeat service is not active: {result.stdout.strip()}")
            tests_failed += 1

    except Exception as e:
        print_error(f"Heartbeat service check failed: {e}")
        tests_failed += 1

    return tests_passed, tests_failed


def test_shared_storage():
    """Test orchestrator shared storage is mounted"""
    print_header("Testing Shared Storage Mount")

    tests_passed = 0
    tests_failed = 0

    mount_point = Path("/home/marc/mnt/orchestrator")

    # Check if mount point exists
    if not mount_point.exists():
        print_error(f"Mount point does not exist: {mount_point}")
        return 0, 1

    # Check systemd mount status
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", "home-marc-mnt-orchestrator.mount"],
            capture_output=True,
            text=True
        )

        if result.stdout.strip() == "active":
            print_success("SSHFS mount is active")
            tests_passed += 1
        else:
            print_error(f"Mount is not active: {result.stdout.strip()}")
            tests_failed += 1
    except Exception as e:
        print_error(f"Mount status check failed: {e}")
        tests_failed += 1

    # Check if mount is accessible
    try:
        files = list(mount_point.iterdir())
        if files:
            print_success(f"Mount is accessible ({len(files)} items)")
            print(f"  Sample files: {', '.join([f.name for f in files[:5]])}")
            tests_passed += 1
        else:
            print_warning("Mount is accessible but appears empty")
            tests_failed += 1
    except Exception as e:
        print_error(f"Mount accessibility check failed: {e}")
        tests_failed += 1

    return tests_passed, tests_failed


def test_mcp_configuration():
    """Test MCP servers are properly configured"""
    print_header("Testing MCP Server Configuration")

    tests_passed = 0
    tests_failed = 0

    claude_config = Path.home() / ".claude.json"

    if not claude_config.exists():
        print_error("~/.claude.json not found")
        return 0, 1

    try:
        with open(claude_config) as f:
            config = json.load(f)

        mcp_servers = config.get("mcpServers", {})

        if not mcp_servers:
            print_error("No MCP servers configured")
            return 0, 1

        print_success(f"Found {len(mcp_servers)} MCP servers configured")

        expected_servers = ["enhanced-memory", "agent-runtime-mcp", "ember-mcp"]

        for server_name in expected_servers:
            if server_name in mcp_servers:
                server_config = mcp_servers[server_name]
                disabled = server_config.get("disabled", False)

                if disabled:
                    print_warning(f"  {server_name}: configured but disabled")
                else:
                    print_success(f"  {server_name}: configured and enabled")

                    # Check if server file exists
                    args = server_config.get("args", [])
                    if args and Path(args[0]).exists():
                        print(f"    Path: {args[0]}")
                        tests_passed += 1
                    else:
                        print_warning(f"    Path not found: {args[0] if args else 'N/A'}")
            else:
                print_error(f"  {server_name}: not configured")
                tests_failed += 1

    except Exception as e:
        print_error(f"MCP configuration check failed: {e}")
        tests_failed += 1

    return tests_passed, tests_failed


def test_service_status():
    """Test all systemd services are running"""
    print_header("Testing Systemd Services")

    tests_passed = 0
    tests_failed = 0

    services = {
        "builder-api.service": "Builder API",
        "builder-heartbeat.service": "Heartbeat Service",
        "home-marc-mnt-orchestrator.mount": "Shared Storage Mount"
    }

    for service_name, description in services.items():
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-active", service_name],
                capture_output=True,
                text=True
            )

            status = result.stdout.strip()
            if status == "active":
                print_success(f"{description}: {status}")
                tests_passed += 1
            else:
                print_error(f"{description}: {status}")
                tests_failed += 1
        except Exception as e:
            print_error(f"{description} check failed: {e}")
            tests_failed += 1

    return tests_passed, tests_failed


def main():
    """Run all Phase 2 integration tests"""
    print_header("Phase 2 Integration Test Suite")
    print(f"Builder Node: macpro51")
    print(f"Test Time: {datetime.now().isoformat()}")

    total_passed = 0
    total_failed = 0

    # Run all tests
    passed, failed = test_service_status()
    total_passed += passed
    total_failed += failed

    passed, failed = test_builder_api()
    total_passed += passed
    total_failed += failed

    passed, failed = test_heartbeat_service()
    total_passed += passed
    total_failed += failed

    passed, failed = test_shared_storage()
    total_passed += passed
    total_failed += failed

    passed, failed = test_mcp_configuration()
    total_passed += passed
    total_failed += failed

    # Print summary
    print_header("Test Summary")
    print(f"Total Tests: {total_passed + total_failed}")
    print(f"{Colors.GREEN}Passed: {total_passed}{Colors.RESET}")
    print(f"{Colors.RED}Failed: {total_failed}{Colors.RESET}")

    if total_failed == 0:
        print(f"\n{Colors.GREEN}{'=' * 70}{Colors.RESET}")
        print(f"{Colors.GREEN}ALL PHASE 2 SERVICES OPERATIONAL{Colors.RESET}")
        print(f"{Colors.GREEN}{'=' * 70}{Colors.RESET}\n")
        return 0
    else:
        print(f"\n{Colors.RED}{'=' * 70}{Colors.RESET}")
        print(f"{Colors.RED}SOME TESTS FAILED - CHECK CONFIGURATION{Colors.RESET}")
        print(f"{Colors.RED}{'=' * 70}{Colors.RESET}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
