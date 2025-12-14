#!/usr/bin/env python3
"""
Orchestrator Auto-Execute - Autonomous Task Orchestration
Monitors for nodes to come online and automatically executes tasks

This is the autonomous orchestration layer - no human intervention needed!

Features:
- Detects when nodes start their command listener
- Automatically executes queued tasks
- Monitors execution progress
- Reports results
- Fully autonomous operation

Usage:
    python3 orchestrator_auto_execute.py [node_ip] [task_script] [check_interval]

Example:
    python3 orchestrator_auto_execute.py 192.168.1.183 macpro51/build_toon.sh 10
"""
import os
import platform

import socket
import subprocess
import time
import json
import sys
from datetime import datetime
from pathlib import Path

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    elif system == "Linux":
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()


class OrchestratorAutoExecute:
    def __init__(self, node_ip, task_script, check_interval=10, port=9999):
        self.node_ip = node_ip
        self.task_script = task_script
        self.check_interval = check_interval
        self.port = port
        self.base_path = Path(str(_STORAGE_BASE))
        self.results_dir = self.base_path / "cluster-deployment" / "execution-results"
        self.results_dir.mkdir(exist_ok=True)
        self.log_file = self.results_dir / f"orchestrator_{node_ip.replace('.', '_')}.log"

    def log(self, message, level="INFO"):
        """Log message to file and console"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] [{level}] {message}"
        print(log_msg)
        with open(self.log_file, "a") as f:
            f.write(log_msg + "\n")

    def check_node_online(self):
        """Check if node command listener is online"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((self.node_ip, self.port))
            sock.close()
            return result == 0
        except Exception as e:
            self.log(f"Error checking node: {e}", "WARNING")
            return False

    def send_command(self, command):
        """Send command to node and get response"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(30)
            sock.connect((self.node_ip, self.port))

            # Read welcome
            welcome = sock.recv(4096).decode('utf-8')
            self.log(f"Connected to node")

            # Send command
            sock.send(f"{command}\n".encode())
            self.log(f"Sent command: {command}")

            # Read response
            response = ""
            while True:
                try:
                    data = sock.recv(4096).decode('utf-8')
                    if not data:
                        break
                    response += data
                    if response.endswith("> "):
                        break
                except socket.timeout:
                    break

            sock.close()

            # Clean up prompt
            if response.endswith("> "):
                response = response[:-2]

            return response.strip()

        except Exception as e:
            self.log(f"Error sending command: {e}", "ERROR")
            return None

    def execute_task(self):
        """Execute task on remote node"""
        self.log("=" * 60)
        self.log("EXECUTING TASK ON REMOTE NODE")
        self.log("=" * 60)

        # Determine full path to script
        script_path = f"/mnt/ssdraid0/agentic-system/databases/cluster/nodes/{self.task_script}"

        # Check if script exists on remote node
        check_cmd = f"exec test -f {script_path} && echo 'EXISTS' || echo 'NOT_FOUND'"
        result = self.send_command(check_cmd)

        if result and "NOT_FOUND" in result:
            # Try alternate path
            script_path = fstr(_STORAGE_BASE / "databases/cluster/nodes/{self.task_script}")
            check_cmd = f"exec test -f {script_path} && echo 'EXISTS' || echo 'NOT_FOUND'"
            result = self.send_command(check_cmd)

        self.log(f"Script check result: {result}")

        # Execute script in background
        script_dir = str(Path(script_path).parent)
        script_name = Path(script_path).name

        exec_cmd = f"exec cd {script_dir} && nohup ./{script_name} > /tmp/toon-build.log 2>&1 & echo $!"

        self.log(f"Executing: {exec_cmd}")
        result = self.send_command(exec_cmd)

        if result:
            self.log(f"Execution started! Response: {result}")

            # Try to extract PID
            try:
                data = json.loads(result)
                if data.get('status') == 'success':
                    pid = data.get('stdout', '').strip()
                    self.log(f"Build process PID: {pid}")
                    return True
            except:
                self.log(f"Non-JSON response: {result}")
                if "returncode" in result or "success" in result.lower():
                    return True

        return False

    def monitor_execution(self):
        """Monitor task execution progress"""
        self.log("=" * 60)
        self.log("MONITORING EXECUTION")
        self.log("=" * 60)

        last_lines = 0
        consecutive_errors = 0
        max_consecutive_errors = 5

        while consecutive_errors < max_consecutive_errors:
            time.sleep(30)  # Check every 30 seconds

            # Get log tail
            log_cmd = "exec tail -20 /tmp/toon-build.log 2>/dev/null || echo 'No log yet'"
            result = self.send_command(log_cmd)

            if result:
                try:
                    data = json.loads(result)
                    if data.get('status') == 'success':
                        stdout = data.get('stdout', '')
                        if stdout and stdout != 'No log yet':
                            self.log("\n--- Build Progress ---")
                            self.log(stdout)
                            consecutive_errors = 0  # Reset error count
                        else:
                            self.log("Log file not available yet...")
                    else:
                        consecutive_errors += 1
                        self.log(f"Error reading log (attempt {consecutive_errors}/{max_consecutive_errors})")
                except json.JSONDecodeError:
                    self.log("Could not parse response")
                    consecutive_errors += 1

            # Check if build is complete
            check_cmd = "exec test -f /mnt/ssdraid0/agentic-system/databases/cluster/nodes/macpro51/toon-results/BUILD_SUMMARY.md && echo 'COMPLETE' || echo 'RUNNING'"
            result = self.send_command(check_cmd)

            if result and 'COMPLETE' in str(result):
                self.log("=" * 60)
                self.log("BUILD COMPLETE!")
                self.log("=" * 60)
                return True

        self.log("Monitoring stopped due to consecutive errors", "WARNING")
        return False

    def collect_results(self):
        """Collect and display build results"""
        self.log("=" * 60)
        self.log("COLLECTING RESULTS")
        self.log("=" * 60)

        # Try to read BUILD_SUMMARY.md from shared storage
        summary_path = self.base_path / "databases/cluster/nodes/macpro51/toon-results/BUILD_SUMMARY.md"

        if summary_path.exists():
            self.log("Found BUILD_SUMMARY.md on shared storage!")
            with open(summary_path) as f:
                summary = f.read()

            self.log("\n" + "=" * 60)
            self.log("BUILD SUMMARY")
            self.log("=" * 60)
            self.log(summary)

            # Save to orchestrator results
            result_file = self.results_dir / f"toon_build_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(result_file, "w") as f:
                f.write(summary)

            self.log(f"\nResults saved to: {result_file}")
            return True
        else:
            self.log("BUILD_SUMMARY.md not found yet", "WARNING")
            return False

    def run(self):
        """Main orchestration loop"""
        self.log("=" * 60)
        self.log("ORCHESTRATOR AUTO-EXECUTE STARTED")
        self.log("=" * 60)
        self.log(f"Node IP: {self.node_ip}")
        self.log(f"Port: {self.port}")
        self.log(f"Task Script: {self.task_script}")
        self.log(f"Check Interval: {self.check_interval}s")
        self.log("")

        # Phase 1: Wait for node to come online
        self.log("Phase 1: Waiting for node to come online...")
        attempts = 0
        while True:
            attempts += 1
            self.log(f"Attempt {attempts}: Checking {self.node_ip}:{self.port}")

            if self.check_node_online():
                self.log("✅ Node is ONLINE!")
                break

            self.log(f"⏳ Node offline, waiting {self.check_interval} seconds...")
            time.sleep(self.check_interval)

        # Phase 2: Execute task
        self.log("\nPhase 2: Executing task...")
        if not self.execute_task():
            self.log("❌ Task execution failed!", "ERROR")
            return False

        # Phase 3: Monitor execution
        self.log("\nPhase 3: Monitoring execution...")
        if not self.monitor_execution():
            self.log("⚠️  Monitoring ended without completion", "WARNING")
            # Don't return False - results might still be available

        # Phase 4: Collect results
        self.log("\nPhase 4: Collecting results...")
        time.sleep(5)  # Give filesystem a moment to sync
        if self.collect_results():
            self.log("\n✅ ORCHESTRATION COMPLETE!")
            return True
        else:
            self.log("\n⚠️  Results not found, but task may have completed", "WARNING")
            return False

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    node_ip = sys.argv[1]
    task_script = sys.argv[2]
    check_interval = int(sys.argv[3]) if len(sys.argv) > 3 else 10

    orchestrator = OrchestratorAutoExecute(node_ip, task_script, check_interval)
    success = orchestrator.run()

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
