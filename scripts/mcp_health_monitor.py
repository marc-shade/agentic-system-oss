#!/usr/bin/env python3
"""
MCP Server Health Monitor and Auto-Recovery System

Monitors MCP servers for health and automatically restarts failed servers
with exponential backoff. Designed to run as a systemd service.

Features:
- Reads MCP server config from ~/.claude.json
- Monitors process existence via PID tracking
- Restarts failed servers with exponential backoff
- Logs events to console and optional enhanced-memory
- Alerts on repeated failures

Usage:
    python3 mcp_health_monitor.py [--check-once] [--verbose]
"""

import os
import sys
import json
import time
import signal
import subprocess
import logging
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


@dataclass
class ServerState:
    """Track state for a single MCP server."""
    name: str
    command: str
    args: List[str]
    env: Dict[str, str]
    pid: Optional[int] = None
    last_restart: Optional[datetime] = None
    restart_count: int = 0
    consecutive_failures: int = 0
    backoff_seconds: float = 10.0
    disabled: bool = False
    healthy: bool = False


@dataclass
class MonitorConfig:
    """Configuration for the health monitor."""
    check_interval: int = 30  # seconds between health checks
    max_restart_attempts: int = 5  # before alerting
    base_backoff: float = 10.0  # initial backoff in seconds
    max_backoff: float = 300.0  # max backoff (5 minutes)
    backoff_multiplier: float = 2.0  # exponential backoff factor
    cooldown_period: int = 300  # seconds before resetting failure count
    claude_json_path: str = field(default_factory=lambda: str(Path.home() / ".claude.json"))


class MCPHealthMonitor:
    """Monitor and recover MCP servers."""

    def __init__(self, config: Optional[MonitorConfig] = None):
        self.config = config or MonitorConfig()
        self.servers: Dict[str, ServerState] = {}
        self.running = True
        self.start_time = datetime.now()

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

    def load_server_config(self) -> bool:
        """Load MCP server configuration from ~/.claude.json."""
        try:
            config_path = Path(self.config.claude_json_path)
            if not config_path.exists():
                logger.error(f"Config file not found: {config_path}")
                return False

            with open(config_path) as f:
                claude_config = json.load(f)

            mcp_servers = claude_config.get("mcpServers", {})

            for name, server_config in mcp_servers.items():
                if server_config.get("disabled", False):
                    logger.info(f"Skipping disabled server: {name}")
                    continue

                self.servers[name] = ServerState(
                    name=name,
                    command=server_config.get("command", ""),
                    args=server_config.get("args", []),
                    env=server_config.get("env", {}),
                    disabled=server_config.get("disabled", False)
                )

            logger.info(f"Loaded {len(self.servers)} MCP server configurations")
            return True

        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return False

    def find_server_process(self, server: ServerState) -> Optional[int]:
        """Find the PID of a running MCP server process."""
        try:
            # Build the command pattern to search for
            if server.args:
                # Search for the main script/module in the args
                search_pattern = server.args[-1] if server.args else server.command
            else:
                search_pattern = server.command

            # Use pgrep to find matching processes
            result = subprocess.run(
                ["pgrep", "-f", search_pattern],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                # Return first matching PID
                return int(pids[0])
            return None

        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout finding process for {server.name}")
            return None
        except Exception as e:
            logger.debug(f"Error finding process for {server.name}: {e}")
            return None

    def check_process_health(self, pid: int) -> bool:
        """Check if a process is running and healthy."""
        try:
            # Check if process exists
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def restart_server(self, server: ServerState) -> bool:
        """Attempt to restart an MCP server."""
        logger.info(f"Attempting to restart server: {server.name}")

        # Kill any existing process
        if server.pid:
            try:
                os.kill(server.pid, signal.SIGTERM)
                time.sleep(2)
                try:
                    os.kill(server.pid, signal.SIGKILL)
                except OSError:
                    pass  # Already dead
            except OSError:
                pass  # Process doesn't exist

        # Build environment
        env = os.environ.copy()
        env.update(server.env)

        try:
            # Start the server process
            cmd = [server.command] + server.args

            # Start detached from this process
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )

            # Wait briefly and check if it's still running
            time.sleep(3)

            if process.poll() is None:
                server.pid = process.pid
                server.last_restart = datetime.now()
                server.restart_count += 1
                server.consecutive_failures = 0
                server.backoff_seconds = self.config.base_backoff
                logger.info(f"Successfully restarted {server.name} (PID: {server.pid})")
                return True
            else:
                logger.error(f"Server {server.name} exited immediately after start")
                return False

        except Exception as e:
            logger.error(f"Failed to restart {server.name}: {e}")
            return False

    def handle_failure(self, server: ServerState):
        """Handle a server failure with exponential backoff."""
        server.consecutive_failures += 1
        server.healthy = False

        # Calculate backoff
        server.backoff_seconds = min(
            self.config.base_backoff * (self.config.backoff_multiplier ** server.consecutive_failures),
            self.config.max_backoff
        )

        if server.consecutive_failures >= self.config.max_restart_attempts:
            logger.error(
                f"ALERT: Server {server.name} has failed {server.consecutive_failures} times. "
                f"Manual intervention may be required."
            )
            # Could add Arduino alert or notification here
            return

        # Check if we should wait before restarting
        if server.last_restart:
            time_since_restart = (datetime.now() - server.last_restart).total_seconds()
            if time_since_restart < server.backoff_seconds:
                wait_time = server.backoff_seconds - time_since_restart
                logger.info(f"Waiting {wait_time:.1f}s before restarting {server.name} (backoff)")
                return

        # Attempt restart
        if self.restart_server(server):
            logger.info(f"Recovery successful for {server.name}")
        else:
            logger.error(f"Recovery failed for {server.name}")

    def check_all_servers(self) -> Dict[str, bool]:
        """Check health of all servers and return status."""
        status = {}

        for name, server in self.servers.items():
            if server.disabled:
                status[name] = True
                continue

            # Find or verify process
            if server.pid:
                healthy = self.check_process_health(server.pid)
            else:
                pid = self.find_server_process(server)
                if pid:
                    server.pid = pid
                    healthy = True
                else:
                    healthy = False

            server.healthy = healthy
            status[name] = healthy

            if not healthy:
                logger.warning(f"Server {name} is unhealthy")
                self.handle_failure(server)
            else:
                # Reset failure count after cooldown
                if server.last_restart:
                    time_since = (datetime.now() - server.last_restart).total_seconds()
                    if time_since > self.config.cooldown_period:
                        server.consecutive_failures = 0
                        server.backoff_seconds = self.config.base_backoff

        return status

    def get_status_report(self) -> Dict[str, Any]:
        """Generate a status report."""
        healthy_count = sum(1 for s in self.servers.values() if s.healthy)
        total_count = len(self.servers)

        return {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "healthy": healthy_count,
            "total": total_count,
            "servers": {
                name: {
                    "healthy": server.healthy,
                    "pid": server.pid,
                    "restart_count": server.restart_count,
                    "consecutive_failures": server.consecutive_failures,
                    "last_restart": server.last_restart.isoformat() if server.last_restart else None
                }
                for name, server in self.servers.items()
            }
        }

    def run(self, check_once: bool = False):
        """Main monitoring loop."""
        logger.info("MCP Health Monitor starting...")

        if not self.load_server_config():
            logger.error("Failed to load configuration, exiting")
            return 1

        logger.info(f"Monitoring {len(self.servers)} servers every {self.config.check_interval}s")

        if check_once:
            status = self.check_all_servers()
            report = self.get_status_report()
            print(json.dumps(report, indent=2))
            healthy = all(status.values())
            return 0 if healthy else 1

        while self.running:
            try:
                status = self.check_all_servers()

                healthy_count = sum(status.values())
                total_count = len(status)

                if healthy_count == total_count:
                    logger.debug(f"All {total_count} servers healthy")
                else:
                    logger.warning(f"{healthy_count}/{total_count} servers healthy")

                # Sleep with interrupt checking
                for _ in range(self.config.check_interval):
                    if not self.running:
                        break
                    time.sleep(1)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(10)

        logger.info("MCP Health Monitor stopped")
        return 0


def main():
    parser = argparse.ArgumentParser(description="MCP Server Health Monitor")
    parser.add_argument("--check-once", action="store_true",
                       help="Check once and exit (for cron/manual use)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    parser.add_argument("--interval", type=int, default=30,
                       help="Check interval in seconds (default: 30)")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    config = MonitorConfig(check_interval=args.interval)
    monitor = MCPHealthMonitor(config)

    return monitor.run(check_once=args.check_once)


if __name__ == "__main__":
    sys.exit(main())
