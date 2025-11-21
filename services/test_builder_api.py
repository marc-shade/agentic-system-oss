#!/usr/bin/env python3
"""
Test script for Builder Node API
Validates all endpoints and Prometheus metrics
"""

import json
import time
import requests
from typing import Dict

# API Configuration
API_BASE = "http://localhost:9000"
API_V1 = f"{API_BASE}/api/v1"


class BuilderAPITester:
    """Test suite for Builder Node API"""

    def __init__(self):
        self.test_build_id = None
        self.passed = 0
        self.failed = 0

    def log(self, message: str, status: str = "INFO"):
        """Log test message"""
        prefix = {
            "INFO": "ℹ️ ",
            "PASS": "✅",
            "FAIL": "❌",
            "WARN": "⚠️ ",
        }.get(status, "  ")
        print(f"{prefix} {message}")

    def test_endpoint(self, name: str, method: str, endpoint: str, **kwargs) -> Dict:
        """Test an API endpoint"""
        url = f"{API_BASE}{endpoint}" if endpoint.startswith("/") else endpoint

        try:
            self.log(f"Testing: {name}", "INFO")
            self.log(f"  {method} {endpoint}", "INFO")

            if method == "GET":
                response = requests.get(url, **kwargs)
            elif method == "POST":
                response = requests.post(url, **kwargs)
            else:
                raise ValueError(f"Unsupported method: {method}")

            # Log response
            self.log(f"  Status: {response.status_code}", "INFO")

            if response.status_code in [200, 201]:
                self.passed += 1
                self.log(f"{name} - PASSED", "PASS")
                try:
                    return response.json()
                except:
                    return {"content": response.text}
            else:
                self.failed += 1
                self.log(f"{name} - FAILED (status={response.status_code})", "FAIL")
                return {"error": response.text}

        except Exception as e:
            self.failed += 1
            self.log(f"{name} - FAILED ({e})", "FAIL")
            return {"error": str(e)}

    def run_tests(self):
        """Run all API tests"""
        self.log("=== Builder Node API Test Suite ===", "INFO")
        self.log(f"API Base: {API_BASE}", "INFO")
        print()

        # Test 1: Root endpoint
        result = self.test_endpoint(
            "Root Endpoint",
            "GET",
            "/",
        )
        if result:
            self.log(f"  API Version: {result.get('version')}", "INFO")
            self.log(f"  Node ID: {result.get('node_id')}", "INFO")
        print()

        # Test 2: Health check
        result = self.test_endpoint(
            "Health Check",
            "GET",
            "/health",
        )
        if result:
            self.log(f"  Status: {result.get('status')}", "INFO")
            self.log(f"  Services: {result.get('services')}", "INFO")
        print()

        # Test 3: Readiness check
        result = self.test_endpoint(
            "Readiness Check",
            "GET",
            "/ready",
        )
        if result:
            self.log(f"  Ready: {result.get('ready')}", "INFO")
            self.log(f"  Queue Size: {result.get('queue_size')}", "INFO")
            self.log(f"  Active Builds: {result.get('active_builds')}", "INFO")
        print()

        # Test 4: Submit build
        build_data = {
            "project_id": "test-project",
            "git_commit": "abc123def456",
            "git_branch": "main",
            "build_type": "release",
            "tags": ["test", "api-validation"],
            "priority": 7,
        }

        result = self.test_endpoint(
            "Submit Build",
            "POST",
            "/api/v1/build",
            json=build_data,
        )
        if result and "build_id" in result:
            self.test_build_id = result["build_id"]
            self.log(f"  Build ID: {self.test_build_id}", "INFO")
            self.log(f"  Build Number: {result.get('build_number')}", "INFO")
            self.log(f"  Status: {result.get('status')}", "INFO")
        print()

        # Test 5: Get build status (if build was created)
        if self.test_build_id:
            result = self.test_endpoint(
                "Get Build Status",
                "GET",
                f"/api/v1/build/{self.test_build_id}",
            )
            if result:
                self.log(f"  Project: {result.get('project_id')}", "INFO")
                self.log(f"  Status: {result.get('status')}", "INFO")
                self.log(f"  Node: {result.get('node_id')}", "INFO")
                self.log(f"  Git Commit: {result.get('git_commit')}", "INFO")
            print()

        # Test 6: Get build logs
        if self.test_build_id:
            result = self.test_endpoint(
                "Get Build Logs",
                "GET",
                f"/api/v1/build/{self.test_build_id}/logs",
            )
            if result:
                content = result.get("content", "")
                self.log(f"  Log Length: {len(content)} bytes", "INFO")
            print()

        # Test 7: Get artifacts manifest
        if self.test_build_id:
            result = self.test_endpoint(
                "Get Artifacts Manifest",
                "GET",
                f"/api/v1/artifacts/{self.test_build_id}/download",
            )
            if result:
                artifacts = result.get("artifacts", [])
                self.log(f"  Artifacts Count: {len(artifacts)}", "INFO")
            print()

        # Test 8: Webhook callback - start
        if self.test_build_id:
            callback_data = {
                "build_id": self.test_build_id,
                "action": "start",
                "metadata": {},
            }

            result = self.test_endpoint(
                "Webhook Callback - Start",
                "POST",
                "/api/v1/build/callback",
                json=callback_data,
            )
            print()

            # Wait a moment
            time.sleep(1)

        # Test 9: Webhook callback - complete
        if self.test_build_id:
            callback_data = {
                "build_id": self.test_build_id,
                "action": "complete",
                "metadata": {
                    "success": True,
                    "exit_code": 0,
                    "duration": 45.2,
                },
            }

            result = self.test_endpoint(
                "Webhook Callback - Complete",
                "POST",
                "/api/v1/build/callback",
                json=callback_data,
            )
            print()

        # Test 10: Prometheus metrics
        result = self.test_endpoint(
            "Prometheus Metrics",
            "GET",
            "/api/v1/metrics",
        )
        if result and "content" in result:
            metrics_text = result["content"]
            self.log(f"  Metrics Size: {len(metrics_text)} bytes", "INFO")

            # Parse some key metrics
            for line in metrics_text.split("\n"):
                if line.startswith("builder_"):
                    if any(
                        x in line
                        for x in [
                            "active_builds",
                            "builds_total",
                            "artifact_storage_bytes",
                            "total_artifacts",
                        ]
                    ):
                        self.log(f"  {line}", "INFO")
        print()

        # Test Summary
        self.log("=== Test Summary ===", "INFO")
        total = self.passed + self.failed
        self.log(f"Total Tests: {total}", "INFO")
        self.log(f"Passed: {self.passed}", "PASS")
        if self.failed > 0:
            self.log(f"Failed: {self.failed}", "FAIL")
        else:
            self.log(f"Failed: {self.failed}", "INFO")

        success_rate = (self.passed / total * 100) if total > 0 else 0
        self.log(f"Success Rate: {success_rate:.1f}%", "INFO")

        return self.failed == 0


def main():
    """Main test entry point"""
    import sys

    # Wait for API to be ready
    print("Waiting for API to be ready...")
    max_retries = 10
    for i in range(max_retries):
        try:
            response = requests.get(f"{API_BASE}/health", timeout=2)
            if response.status_code == 200:
                print("✅ API is ready!\n")
                break
        except:
            pass

        if i < max_retries - 1:
            print(f"  Retry {i+1}/{max_retries}...")
            time.sleep(2)
    else:
        print("❌ API is not responding. Make sure it's running.")
        print(f"   Start it with: python3 {__file__.replace('test_', '')}")
        sys.exit(1)

    # Run tests
    tester = BuilderAPITester()
    success = tester.run_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
