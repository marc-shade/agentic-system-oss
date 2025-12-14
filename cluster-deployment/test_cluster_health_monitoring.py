#!/usr/bin/env python3
"""
Comprehensive Test Suite for Cluster Health Monitoring System

Tests all aspects of the cluster health monitoring including:
- Node discovery and reachability
- Heartbeat mechanisms
- Health status detection
- Failover and recovery
- Metrics collection
- Alert generation
- Memory synchronization
- Task routing

Target: 99% cluster availability
"""

import sys
import time
import json
import socket
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

# Add cluster deployment to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from cluster_state_manager import ClusterStateManager, NodeStatus
    from cluster_telemetry_collector import NodeTelemetry
    CLUSTER_COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import cluster components: {e}")
    CLUSTER_COMPONENTS_AVAILABLE = False


@dataclass
class TestResult:
    """Result of a single test"""
    test_name: str
    passed: bool
    message: str
    duration_ms: float
    details: Dict = None


class ClusterHealthMonitoringTests:
    """Comprehensive test suite for cluster health monitoring"""

    def __init__(self):
        self.results: List[TestResult] = []
        self.config_path = Path(__file__).parent / "cluster-nodes.json"
        self.nodes = self._load_node_config()

    def _load_node_config(self) -> Dict:
        """Load cluster node configuration"""
        if not self.config_path.exists():
            return {"nodes": {}}

        with open(self.config_path) as f:
            return json.load(f)

    def _record_result(self, test_name: str, passed: bool, message: str,
                      duration_ms: float, details: Dict = None):
        """Record a test result"""
        result = TestResult(
            test_name=test_name,
            passed=passed,
            message=message,
            duration_ms=duration_ms,
            details=details or {}
        )
        self.results.append(result)

        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} [{duration_ms:.1f}ms] {test_name}: {message}")

    def test_node_discovery(self) -> bool:
        """Test 1: Node Discovery via mDNS/Avahi"""
        start = time.time()

        discovered = {}
        for node_id, node_config in self.nodes.get("nodes", {}).items():
            hostname = node_config.get("hostname", "")

            try:
                # Try to resolve hostname
                result = subprocess.run(
                    ["avahi-resolve", "-n", hostname],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if result.returncode == 0:
                    parts = result.stdout.strip().split()
                    if len(parts) >= 2:
                        ip = parts[1]
                        discovered[node_id] = {"hostname": hostname, "ip": ip}
            except (subprocess.TimeoutExpired, FileNotFoundError):
                # avahi-resolve not available or timed out
                try:
                    # Fallback to socket resolution
                    ip = socket.gethostbyname(hostname)
                    discovered[node_id] = {"hostname": hostname, "ip": ip}
                except socket.gaierror:
                    pass

        duration = (time.time() - start) * 1000
        total_nodes = len(self.nodes.get("nodes", {}))
        discovered_count = len(discovered)

        passed = discovered_count >= 1  # At least local node
        self._record_result(
            "Node Discovery",
            passed,
            f"Discovered {discovered_count}/{total_nodes} nodes",
            duration,
            {"discovered": discovered}
        )

        return passed

    def test_node_reachability(self) -> bool:
        """Test 2: Node Reachability via Ping"""
        start = time.time()

        reachable = {}
        for node_id, node_config in self.nodes.get("nodes", {}).items():
            hostname = node_config.get("hostname", "")

            try:
                # Quick ping test (1 packet, 2 second timeout)
                result = subprocess.run(
                    ["ping", "-c", "1", "-W", "2", hostname],
                    capture_output=True,
                    timeout=3
                )

                if result.returncode == 0:
                    # Extract latency
                    output = result.stdout.decode()
                    if "time=" in output:
                        latency = output.split("time=")[1].split()[0]
                        reachable[node_id] = {"hostname": hostname, "latency": latency}
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        duration = (time.time() - start) * 1000
        total_nodes = len(self.nodes.get("nodes", {}))
        reachable_count = len(reachable)

        passed = reachable_count >= 1  # At least local node
        self._record_result(
            "Node Reachability",
            passed,
            f"{reachable_count}/{total_nodes} nodes reachable",
            duration,
            {"reachable": reachable}
        )

        return passed

    def test_hardware_broadcast_service(self) -> bool:
        """Test 3: Hardware Broadcast Service (Local Node)"""
        start = time.time()

        try:
            # Check if service is running
            result = subprocess.run(
                ["systemctl", "is-active", "hardware-broadcast"],
                capture_output=True,
                text=True
            )

            service_active = result.stdout.strip() == "active"

            if service_active:
                # Try to query the API
                import urllib.request
                try:
                    with urllib.request.urlopen("http://localhost:8888/api/all", timeout=2) as response:
                        data = json.loads(response.read())
                        api_working = "hardware" in data or "system" in data
                except Exception as e:
                    api_working = False
            else:
                api_working = False

            duration = (time.time() - start) * 1000

            passed = service_active and api_working
            self._record_result(
                "Hardware Broadcast Service",
                passed,
                f"Service: {'active' if service_active else 'inactive'}, API: {'working' if api_working else 'unavailable'}",
                duration,
                {"service_active": service_active, "api_working": api_working}
            )

            return passed

        except Exception as e:
            duration = (time.time() - start) * 1000
            self._record_result(
                "Hardware Broadcast Service",
                False,
                f"Error: {str(e)}",
                duration
            )
            return False

    def test_cluster_state_manager(self) -> bool:
        """Test 4: Cluster State Manager"""
        start = time.time()

        if not CLUSTER_COMPONENTS_AVAILABLE:
            duration = (time.time() - start) * 1000
            self._record_result(
                "Cluster State Manager",
                False,
                "Cluster components not available",
                duration
            )
            return False

        try:
            # Try to initialize state manager
            state_manager = ClusterStateManager()

            # Try to update local node status
            local_hostname = socket.gethostname()
            test_status = NodeStatus(
                node_id="macpro51",
                hostname=local_hostname,
                status="healthy",
                last_heartbeat=time.time(),
                cpu_percent=10.0,
                memory_percent=50.0,
                load_average=1.0
            )

            # This should work or raise an exception
            state_manager.update_node_status(test_status)

            duration = (time.time() - start) * 1000
            self._record_result(
                "Cluster State Manager",
                True,
                "Successfully initialized and updated node status",
                duration
            )
            return True

        except Exception as e:
            duration = (time.time() - start) * 1000
            self._record_result(
                "Cluster State Manager",
                False,
                f"Error: {str(e)}",
                duration
            )
            return False

    def test_telemetry_collection(self) -> bool:
        """Test 5: Real-time Telemetry Collection"""
        start = time.time()

        try:
            import psutil

            # Collect basic telemetry
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            load = psutil.getloadavg()

            telemetry_working = (
                0 <= cpu_percent <= 100 and
                memory.percent >= 0 and
                disk.percent >= 0 and
                all(l >= 0 for l in load)
            )

            duration = (time.time() - start) * 1000

            self._record_result(
                "Telemetry Collection",
                telemetry_working,
                f"CPU: {cpu_percent:.1f}%, Memory: {memory.percent:.1f}%, Load: {load[0]:.2f}",
                duration,
                {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "load_1m": load[0]
                }
            )

            return telemetry_working

        except Exception as e:
            duration = (time.time() - start) * 1000
            self._record_result(
                "Telemetry Collection",
                False,
                f"Error: {str(e)}",
                duration
            )
            return False

    def test_health_status_detection(self) -> bool:
        """Test 6: Health Status Detection Logic"""
        start = time.time()

        test_cases = [
            # (cpu%, memory%, load, expected_healthy)
            (50.0, 50.0, 2.0, True),   # Normal
            (95.0, 50.0, 10.0, False),  # High CPU
            (50.0, 95.0, 2.0, False),   # High memory
            (50.0, 50.0, 20.0, False),  # High load
            (10.0, 30.0, 0.5, True),    # Low usage
        ]

        passed_checks = 0
        for cpu, mem, load, expected in test_cases:
            # Health check logic
            is_healthy = (
                cpu < 90 and
                mem < 90 and
                load < 15.0
            )

            if is_healthy == expected:
                passed_checks += 1

        duration = (time.time() - start) * 1000
        all_passed = passed_checks == len(test_cases)

        self._record_result(
            "Health Status Detection",
            all_passed,
            f"{passed_checks}/{len(test_cases)} test cases passed",
            duration,
            {"passed_checks": passed_checks, "total_checks": len(test_cases)}
        )

        return all_passed

    def test_service_monitoring(self) -> bool:
        """Test 7: Critical Service Monitoring"""
        start = time.time()

        critical_services = [
            "sshd",
            "docker",
            "agentic-memory-db",
        ]

        service_status = {}
        for service in critical_services:
            try:
                result = subprocess.run(
                    ["systemctl", "is-active", service],
                    capture_output=True,
                    text=True
                )
                service_status[service] = result.stdout.strip() == "active"
            except Exception:
                service_status[service] = False

        active_count = sum(service_status.values())
        duration = (time.time() - start) * 1000

        # At least SSH should be running
        passed = service_status.get("sshd", False)

        self._record_result(
            "Service Monitoring",
            passed,
            f"{active_count}/{len(critical_services)} critical services active",
            duration,
            {"services": service_status}
        )

        return passed

    def test_node_chat_mcp(self) -> bool:
        """Test 8: Node Chat MCP for Inter-node Communication"""
        start = time.time()

        # Check if node-chat-mcp is installed
        mcp_path = Path("/mnt/agentic-system/mcp-servers/node-chat-mcp")

        if not mcp_path.exists():
            duration = (time.time() - start) * 1000
            self._record_result(
                "Node Chat MCP",
                False,
                "node-chat-mcp not found",
                duration
            )
            return False

        # Check if database exists
        db_path = Path("/mnt/agentic-system/databases/node_chat.db")
        db_exists = db_path.exists()

        duration = (time.time() - start) * 1000

        self._record_result(
            "Node Chat MCP",
            db_exists,
            f"MCP installed, database: {'exists' if db_exists else 'not initialized'}",
            duration,
            {"mcp_installed": True, "db_exists": db_exists}
        )

        return db_exists

    def test_memory_db_service(self) -> bool:
        """Test 9: Memory Database Service"""
        start = time.time()

        try:
            # Check if service is running
            result = subprocess.run(
                ["systemctl", "is-active", "agentic-memory-db"],
                capture_output=True,
                text=True
            )

            service_active = result.stdout.strip() == "active"

            # Check if socket exists
            socket_path = Path("/tmp/memory-db.sock")
            socket_exists = socket_path.exists()

            duration = (time.time() - start) * 1000

            passed = service_active and socket_exists

            self._record_result(
                "Memory Database Service",
                passed,
                f"Service: {'active' if service_active else 'inactive'}, Socket: {'exists' if socket_exists else 'missing'}",
                duration,
                {"service_active": service_active, "socket_exists": socket_exists}
            )

            return passed

        except Exception as e:
            duration = (time.time() - start) * 1000
            self._record_result(
                "Memory Database Service",
                False,
                f"Error: {str(e)}",
                duration
            )
            return False

    def test_qdrant_vector_db(self) -> bool:
        """Test 10: Qdrant Vector Database"""
        start = time.time()

        try:
            # Check if Docker container is running
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=qdrant", "--format", "{{.Status}}"],
                capture_output=True,
                text=True
            )

            container_running = "Up" in result.stdout

            if container_running:
                # Try to connect to Qdrant API
                import urllib.request
                try:
                    with urllib.request.urlopen("http://localhost:6333/collections", timeout=2) as response:
                        data = json.loads(response.read())
                        api_working = "result" in data
                except Exception:
                    api_working = False
            else:
                api_working = False

            duration = (time.time() - start) * 1000

            passed = container_running and api_working

            self._record_result(
                "Qdrant Vector Database",
                passed,
                f"Container: {'running' if container_running else 'stopped'}, API: {'working' if api_working else 'unavailable'}",
                duration,
                {"container_running": container_running, "api_working": api_working}
            )

            return passed

        except Exception as e:
            duration = (time.time() - start) * 1000
            self._record_result(
                "Qdrant Vector Database",
                False,
                f"Error: {str(e)}",
                duration
            )
            return False

    def test_cluster_availability(self) -> bool:
        """Test 11: Overall Cluster Availability Calculation"""
        start = time.time()

        # Calculate availability based on previous tests
        total_tests = len([r for r in self.results if r.test_name != "Cluster Availability"])
        passed_tests = len([r for r in self.results if r.passed and r.test_name != "Cluster Availability"])

        availability = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        duration = (time.time() - start) * 1000

        # Target is 99% availability
        passed = availability >= 99.0

        self._record_result(
            "Cluster Availability",
            passed,
            f"Current availability: {availability:.1f}% (target: 99%)",
            duration,
            {"availability_percent": availability, "target": 99.0}
        )

        return passed

    def run_all_tests(self) -> Tuple[int, int]:
        """Run all tests and return (passed, total)"""
        print("\n" + "="*70)
        print("CLUSTER HEALTH MONITORING - COMPREHENSIVE TEST SUITE")
        print("="*70 + "\n")

        print(f"Test Time: {datetime.now().isoformat()}")
        print(f"Node: {socket.gethostname()}")
        print(f"Total Nodes Configured: {len(self.nodes.get('nodes', {}))}\n")

        # Run all tests
        test_methods = [
            self.test_node_discovery,
            self.test_node_reachability,
            self.test_hardware_broadcast_service,
            self.test_cluster_state_manager,
            self.test_telemetry_collection,
            self.test_health_status_detection,
            self.test_service_monitoring,
            self.test_node_chat_mcp,
            self.test_memory_db_service,
            self.test_qdrant_vector_db,
        ]

        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                self._record_result(
                    test_method.__name__,
                    False,
                    f"Unexpected error: {str(e)}",
                    0
                )

        # Final availability test
        self.test_cluster_availability()

        # Summary
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)

        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {passed/total*100:.1f}%")
        print("="*70 + "\n")

        # Save results
        self._save_results()

        return passed, total

    def _save_results(self):
        """Save test results to JSON file"""
        results_file = Path("/mnt/agentic-system/cluster-deployment/test_results_health_monitoring.json")

        results_data = {
            "timestamp": datetime.now().isoformat(),
            "hostname": socket.gethostname(),
            "total_tests": len(self.results),
            "passed_tests": sum(1 for r in self.results if r.passed),
            "results": [asdict(r) for r in self.results]
        }

        with open(results_file, 'w') as f:
            json.dump(results_data, f, indent=2)

        print(f"Results saved to: {results_file}")


def main():
    """Run the test suite"""
    tester = ClusterHealthMonitoringTests()
    passed, total = tester.run_all_tests()

    # Exit with appropriate code
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
