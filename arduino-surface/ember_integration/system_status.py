#!/usr/bin/env python3
"""
System status aggregation for Arduino Surface.
Collects host resource metrics, MCP server availability, and local LLM readiness.
"""

from __future__ import annotations

import json
import os
import socket
import time
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

import psutil

# Default endpoint shared with LCD filter when no env override is provided.
DEFAULT_LLM_ENDPOINT = "http://127.0.0.1:11434/v1/chat/completions"


class SystemStatus:
    """Aggregate system-wide status information for display."""

    def __init__(self):
        self.config_path = Path.home() / "Library/Application Support/Claude/claude_desktop_config.json"
        self.llm_enabled = os.environ.get("LCD_FILTER_USE_LLM", "1").lower() not in {"0", "false", "off"}
        self.llm_endpoint = os.environ.get("LCD_FILTER_LLM_ENDPOINT", DEFAULT_LLM_ENDPOINT)
        self.llm_cache: Dict[str, Optional[str]] = {"status": None}
        self.llm_last_check: float = 0.0
        self.llm_check_interval = 60.0  # seconds

        # Prime psutil so cpu_percent() has a baseline without blocking later.
        psutil.cpu_percent(interval=None)

    def collect(self) -> Dict[str, object]:
        """Return a snapshot of system status metrics."""
        system_metrics = self._collect_system_metrics()
        mcp_status = self._collect_mcp_servers()
        llm_status = self._collect_llm_status()
        surface_daemon = self._collect_surface_status()

        return {
            "cpu_percent": system_metrics["cpu_percent"],
            "memory_percent": system_metrics["memory_percent"],
            "memory_used_gb": system_metrics["memory_used_gb"],
            "memory_total_gb": system_metrics["memory_total_gb"],
            "disk_percent": system_metrics["disk_percent"],
            "uptime_hours": system_metrics["uptime_hours"],
            "load_average": system_metrics["load_average"],
            "mcp": mcp_status,
            "llm": llm_status,
            "surface_daemon": surface_daemon,
        }

    def _collect_system_metrics(self) -> Dict[str, object]:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        cpu_percent = int(round(psutil.cpu_percent(interval=None)))

        uptime_hours = int((time.time() - psutil.boot_time()) / 3600)
        try:
            load_avg = os.getloadavg()
        except OSError:
            load_avg = (0.0, 0.0, 0.0)

        return {
            "memory_percent": int(round(memory.percent)),
            "memory_used_gb": round(memory.used / (1024 ** 3), 1),
            "memory_total_gb": round(memory.total / (1024 ** 3), 1),
            "disk_percent": int(round(disk.percent)),
            "cpu_percent": cpu_percent,
            "uptime_hours": uptime_hours,
            "load_average": tuple(round(val, 2) for val in load_avg),
        }

    def _collect_mcp_servers(self) -> Dict[str, object]:
        total = 0
        running = 0
        details: List[Dict[str, object]] = []

        if self.config_path.exists():
            try:
                config = json.loads(self.config_path.read_text())
                servers = config.get("mcpServers", {})
            except Exception:
                servers = {}
        else:
            servers = {}

        for name, entry in servers.items():
            total += 1
            command = entry.get("command", "")
            args = entry.get("args", [])

            identifiers = []
            if args:
                identifiers.append(args[0])
                identifiers.append(Path(args[0]).name)
            identifiers.append(command)
            identifiers = [ident for ident in identifiers if ident]

            is_running = self._process_running(identifiers)
            if is_running:
                running += 1

            details.append({
                "name": name,
                "running": is_running,
                "command": command,
                "args": args,
            })

        missing = [item["name"] for item in details if not item["running"]]

        return {
            "total": total,
            "running": running,
            "details": details,
            "missing": missing,
        }

    def _collect_llm_status(self) -> Dict[str, object]:
        if not self.llm_enabled or not self.llm_endpoint:
            return {"status": "disabled", "endpoint": self.llm_endpoint}

        now = time.time()
        if (now - self.llm_last_check) > self.llm_check_interval or not self.llm_cache.get("status"):
            status = self._ping_llm_endpoint()
            self.llm_cache["status"] = status
            self.llm_last_check = now

        return {
            "status": self.llm_cache.get("status", "unknown"),
            "endpoint": self.llm_endpoint,
        }

    def _collect_surface_status(self) -> Dict[str, object]:
        identifiers = ["arduino_enhanced_daemon.py"]
        running = self._process_running(identifiers, include_count=True)
        return {
            "instances": running,
        }

    def _process_running(self, identifiers: List[str], include_count: bool = False) -> object:
        """
        Return True if any of the identifiers are found in running process cmdlines.
        When include_count=True the number of matching processes is returned instead.
        """
        matches = 0
        lowered = [ident.lower() for ident in identifiers if ident]

        for proc in psutil.process_iter(attrs=["cmdline", "name"]):
            try:
                cmdline = proc.info.get("cmdline") or []
                joined = " ".join(cmdline).lower()
                name = (proc.info.get("name") or "").lower()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

            if any(ident in joined or ident == name for ident in lowered):
                matches += 1

        if include_count:
            return matches
        return matches > 0

    def _ping_llm_endpoint(self) -> str:
        """Check socket connectivity to the configured LLM endpoint."""
        try:
            parsed = urlparse(self.llm_endpoint)
            host = parsed.hostname
            port = parsed.port or (443 if parsed.scheme == "https" else 80)

            if not host:
                return "unknown"

            with socket.create_connection((host, port), timeout=2):
                return "ready"

        except OSError:
            return "down"
        except Exception:
            return "unknown"
