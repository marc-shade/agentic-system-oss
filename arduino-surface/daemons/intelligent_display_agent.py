#!/usr/bin/env python3
"""
Intelligent Arduino Display Agent

Uses Claude Agent SDK to provide AI-powered analysis and decision-making
for the Arduino surface display. Acts as a "news feed" for the agentic system,
intelligently deciding what's interesting to report.
"""

import sys
import os
import json
import time
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import glob
import re
import traceback
import math

# Add bridge to path
sys.path.insert(0, str(Path(__file__).parent.parent / "bridge"))

try:
    from surface_bridge import ArduinoSurface
except ImportError:
    print("ERROR: Could not import ArduinoSurface. Check PYTHONPATH.")
    sys.exit(1)

# Try to import Claude Agent SDK
try:
    from anthropic import Anthropic
    CLAUDE_SDK_AVAILABLE = True
except ImportError:
    print("WARNING: Claude SDK not available. Install with: pip install anthropic")
    CLAUDE_SDK_AVAILABLE = False


@dataclass
class NewsItem:
    """A newsworthy item for display."""
    id: str
    priority: int  # 0=critical, 1=warning, 2=info, 3=background
    headline: str  # 16 char max
    detail: str    # 16 char max
    led_color: tuple = (0, 255, 0)
    audio_alert: bool = False
    timestamp: float = field(default_factory=time.time)
    interesting_score: float = 0.0  # AI-assigned interest level

    def format_line(self, line: str, width: int = 16, scroll_pos: int = 0) -> str:
        """Format line to exactly width characters with scrolling support.

        Args:
            line: Text to format
            width: Display width (default 16 for 16x2 LCD)
            scroll_pos: Current scroll position for long text

        Returns:
            Formatted string exactly width characters long
        """
        if len(line) <= width:
            # Short text - just pad
            return line + " " * (width - len(line))

        # Long text - scroll
        # Add spaces at end so it loops smoothly
        padded = line + "    "  # 4 spaces between repetitions
        scroll_pos = scroll_pos % len(padded)

        # Extract window
        window = ""
        for i in range(width):
            window += padded[(scroll_pos + i) % len(padded)]

        return window


class LEDController:
    """Controls LED with breathing effects."""

    def __init__(self, surface: ArduinoSurface):
        self.surface = surface
        self.mode = "solid"
        self.base_color = (0, 255, 0)
        self.breathing_phase = 0.0
        self.breathing_speed = 0.05  # Radians per update

    def set_mode(self, mode: str, color: tuple):
        """Set LED mode: solid, slow_pulse, fast_pulse, flash"""
        self.mode = mode
        self.base_color = color
        self.breathing_phase = 0.0

    def update(self):
        """Update LED based on current mode."""
        if self.mode == "solid":
            self.surface.set_led(0, *self.base_color)

        elif self.mode == "slow_pulse":
            # Breathing effect
            self.breathing_phase += self.breathing_speed
            brightness = (math.sin(self.breathing_phase) + 1.0) / 2.0
            brightness = max(0.3, brightness)  # Don't go too dim

            r = int(self.base_color[0] * brightness)
            g = int(self.base_color[1] * brightness)
            b = int(self.base_color[2] * brightness)
            self.surface.set_led(0, r, g, b)

        elif self.mode == "fast_pulse":
            # Faster breathing
            self.breathing_phase += self.breathing_speed * 3
            brightness = (math.sin(self.breathing_phase) + 1.0) / 2.0
            brightness = max(0.2, brightness)

            r = int(self.base_color[0] * brightness)
            g = int(self.base_color[1] * brightness)
            b = int(self.base_color[2] * brightness)
            self.surface.set_led(0, r, g, b)

        elif self.mode == "flash":
            # On/off flash
            self.breathing_phase += self.breathing_speed * 5
            on = (math.sin(self.breathing_phase) > 0)
            if on:
                self.surface.set_led(0, *self.base_color)
            else:
                self.surface.set_led(0, 0, 0, 0)


class SystemDataCollector:
    """Collects comprehensive system data."""

    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger("DataCollector")
        self.cache = {}
        self.last_readings = {}

    async def collect_all(self) -> Dict[str, Any]:
        """Collect all system data with change detection."""
        data = {}
        changes = []

        # Collect from all sources
        tasks = []
        if self.config["data_sources"]["mcp_servers"]["enabled"]:
            tasks.append(self.collect_mcp_status())
        if self.config["data_sources"]["system_metrics"]["enabled"]:
            tasks.append(self.collect_system_metrics())
        if self.config["data_sources"]["ember_status"]["enabled"]:
            tasks.append(self.collect_ember_status())
        if self.config["data_sources"]["temporal"]["enabled"]:
            tasks.append(self.collect_temporal_status())
        if self.config["data_sources"]["autokitteh"]["enabled"]:
            tasks.append(self.collect_autokitteh_status())
        if self.config["data_sources"]["voice_mode"]["enabled"]:
            tasks.append(self.collect_voice_status())
        if self.config["data_sources"]["mlx_training"]["enabled"]:
            tasks.append(self.collect_mlx_status())
        if self.config["data_sources"]["error_logs"]["enabled"]:
            tasks.append(self.collect_error_metrics())

        # Always collect agent and Claude Code info
        tasks.append(self.collect_agent_processes())
        tasks.append(self.collect_claude_code_info())
        tasks.append(self.collect_agent_runtime_stats())

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, dict):
                # Detect changes
                for key, value in result.items():
                    if key in self.last_readings:
                        if value != self.last_readings[key]:
                            changes.append({
                                "source": key,
                                "old": self.last_readings[key],
                                "new": value
                            })
                    self.last_readings[key] = value

                data.update(result)
            elif isinstance(result, Exception):
                self.logger.error(f"Collection error: {result}")

        data["_changes"] = changes
        return data

    async def collect_mcp_status(self) -> Dict:
        """Check MCP server health."""
        servers = self.config["data_sources"]["mcp_servers"]["servers"]
        
        # Only these MCPs run as persistent background processes
        always_on = ["enhanced-memory", "agent-runtime-mcp"]
        
        configured_count = len(servers)
        always_on_count = 0
        details = {}

        for server in servers:
            try:
                if server in always_on:
                    # Check if always-on process is running
                    import subprocess
                    result = subprocess.run(
                        ["pgrep", "-f", server],
                        capture_output=True,
                        text=True
                    )
                    is_running = (result.returncode == 0)
                    details[server] = "online" if is_running else "offline"
                    if is_running:
                        always_on_count += 1
                else:
                    # On-demand MCPs (started by Claude Code)
                    details[server] = "on-demand"
                    
            except Exception as e:
                self.logger.warning(f"MCP {server} check failed: {e}")
                details[server] = "unknown"

        return {
            "mcp_servers": {
                "configured": configured_count,
                "always_on": always_on_count,
                "details": details
            }
        }

    async def collect_system_metrics(self) -> Dict:
        """Collect system metrics."""
        try:
            import shutil

            raid_path = "/Volumes/SSDRAID0"
            if os.path.exists(raid_path):
                stat = shutil.disk_usage(raid_path)
                used_gb = stat.used / (1024**3)
                total_gb = stat.total / (1024**3)
                percent_used = (stat.used / stat.total) * 100
            else:
                used_gb = total_gb = 0
                percent_used = 0

            return {
                "system_metrics": {
                    "storage_used_gb": used_gb,
                    "storage_total_gb": total_gb,
                    "storage_percent": percent_used,
                    "storage_critical": percent_used > 95
                }
            }
        except Exception as e:
            self.logger.error(f"System metrics error: {e}")
            return {"system_metrics": {"error": str(e)}}

    async def collect_ember_status(self) -> Dict:
        """Collect Ember status."""
        try:
            status_file = Path(self.config["data_sources"]["ember_status"]["pet_state_file"])

            if status_file.exists():
                with open(status_file) as f:
                    pet_data = json.load(f)

                return {
                    "ember": {
                        "mood": pet_data.get("currentMood", "unknown"),
                        "hunger": pet_data.get("hunger", 0),
                        "energy": pet_data.get("energy", 0),
                        "cleanliness": pet_data.get("cleanliness", 0),
                        "happiness": pet_data.get("happiness", 0)
                    }
                }
            return {"ember": {"status": "not_found"}}
        except Exception as e:
            self.logger.error(f"Ember status error: {e}")
            return {"ember": {"error": str(e)}}

    async def collect_temporal_status(self) -> Dict:
        """Check Temporal status."""
        try:
            import subprocess
            result = subprocess.run(
                ["pgrep", "-f", "temporal"],
                capture_output=True,
                text=True
            )

            running = bool(result.returncode == 0)

            return {
                "temporal": {
                    "running": running,
                    "active_workflows": 4 if running else 0
                }
            }
        except Exception as e:
            self.logger.error(f"Temporal error: {e}")
            return {"temporal": {"error": str(e)}}

    async def collect_autokitteh_status(self) -> Dict:
        """Check AutoKitteh status."""
        try:
            import subprocess
            result = subprocess.run(
                ["pgrep", "-f", "ak up"],
                capture_output=True,
                text=True
            )

            running = bool(result.returncode == 0)

            return {
                "autokitteh": {
                    "running": running,
                    "deployments": 4 if running else 0
                }
            }
        except Exception as e:
            self.logger.error(f"AutoKitteh error: {e}")
            return {"autokitteh": {"error": str(e)}}

    async def collect_voice_status(self) -> Dict:
        """Check voice mode."""
        try:
            stats_file = Path(self.config["data_sources"]["voice_mode"]["statistics_file"])
            if stats_file.exists():
                with open(stats_file) as f:
                    stats = json.load(f)
                return {"voice_mode": {"status": "ready", "stats": stats}}
            return {"voice_mode": {"status": "no_stats"}}
        except Exception as e:
            self.logger.error(f"Voice mode error: {e}")
            return {"voice_mode": {"error": str(e)}}

    async def collect_mlx_status(self) -> Dict:
        """Check MLX training."""
        try:
            log_files = glob.glob("/mnt/agentic-system/arduino-surface/logs/*.log")

            for log_file in log_files:
                if time.time() - os.path.getmtime(log_file) < 60:
                    with open(log_file) as f:
                        content = f.read()
                        epoch_match = re.search(r'Epoch (\d+)/(\d+)', content)
                        if epoch_match:
                            return {
                                "mlx_training": {
                                    "active": True,
                                    "epoch": int(epoch_match.group(1)),
                                    "total_epochs": int(epoch_match.group(2))
                                }
                            }

            return {"mlx_training": {"active": False}}
        except Exception as e:
            self.logger.error(f"MLX error: {e}")
            return {"mlx_training": {"error": str(e)}}

    async def collect_error_metrics(self) -> Dict:
        """Collect error metrics."""
        try:
            error_count = 0
            total_count = 0

            log_patterns = self.config["data_sources"]["error_logs"]["log_files"]
            for pattern in log_patterns:
                for log_file in glob.glob(pattern):
                    if time.time() - os.path.getmtime(log_file) < 300:
                        with open(log_file) as f:
                            for line in f:
                                total_count += 1
                                if "ERROR" in line or "CRITICAL" in line:
                                    error_count += 1

            error_rate = (error_count / total_count * 100) if total_count > 0 else 0

            return {
                "error_metrics": {
                    "error_count": error_count,
                    "total_count": total_count,
                    "error_rate": error_rate
                }
            }
        except Exception as e:
            self.logger.error(f"Error metrics failed: {e}")
            return {"error_metrics": {"error": str(e)}}
    async def collect_agent_processes(self) -> Dict:
        """Count running agent processes."""
        try:
            import subprocess
            
            # Count Claude Code agents (spawned by Task tool)
            result = subprocess.run(
                ["pgrep", "-f", "python.*agent.*"],
                capture_output=True,
                text=True
            )
            
            agent_pids = result.stdout.strip().split('\n') if result.stdout.strip() else []
            # Filter out this display agent itself
            agent_count = len([p for p in agent_pids if p])
            
            # Count different types
            subagent_count = 0
            if agent_count > 0:
                # Try to identify subagents vs daemons
                result2 = subprocess.run(
                    ["ps", "aux"],
                    capture_output=True,
                    text=True
                )
                for line in result2.stdout.split('\n'):
                    if 'Task' in line or 'subagent' in line or 'specialist' in line:
                        subagent_count += 1
            
            return {
                "agent_processes": {
                    "total_agents": max(0, agent_count - 1),  # Exclude this agent
                    "active_subagents": subagent_count,
                    "display_agent": "running"
                }
            }
        except Exception as e:
            self.logger.error(f"Agent process check failed: {e}")
            return {"agent_processes": {"error": str(e)}}
    
    async def collect_claude_code_info(self) -> Dict:
        """Collect Claude Code system information."""
        try:
            import subprocess
            
            # Check Claude Code process
            result = subprocess.run(
                ["pgrep", "-f", "claude-code"],
                capture_output=True,
                text=True
            )
            claude_running = (result.returncode == 0)
            
            # Count active sessions (rough estimate from log files)
            session_count = 0
            try:
                session_log = Path.home() / ".claude" / "sessions"
                if session_log.exists():
                    session_count = len(list(session_log.glob("*")))
            except:
                pass
            
            # Check hooks directory
            hooks_active = 0
            try:
                hooks_dir = Path.home() / ".claude" / "hooks"
                if hooks_dir.exists():
                    hooks_active = len(list(hooks_dir.glob("*.py")))
            except:
                pass
            
            return {
                "claude_code": {
                    "running": claude_running,
                    "sessions": session_count,
                    "hooks_active": hooks_active,
                    "status": "active" if claude_running else "idle"
                }
            }
        except Exception as e:
            self.logger.error(f"Claude Code info failed: {e}")
            return {"claude_code": {"error": str(e)}}
    
    async def collect_agent_runtime_stats(self) -> Dict:
        """Collect agent runtime MCP statistics."""
        try:
            import sqlite3
            
            # Try to read agent runtime database
            db_path = Path("/mnt/agentic-system/databases/mcp/agent_runtime.db")
            if not db_path.exists():
                return {"agent_runtime": {"status": "no_db"}}
            
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Count pending tasks
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE status='pending'")
            pending_tasks = cursor.fetchone()[0]
            
            # Count in-progress tasks
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE status='in_progress'")
            active_tasks = cursor.fetchone()[0]
            
            # Count active goals
            cursor.execute("SELECT COUNT(*) FROM goals WHERE status='active'")
            active_goals = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                "agent_runtime": {
                    "pending_tasks": pending_tasks,
                    "active_tasks": active_tasks,
                    "active_goals": active_goals,
                    "queue_size": pending_tasks + active_tasks
                }
            }
        except Exception as e:
            self.logger.error(f"Agent runtime stats failed: {e}")
            return {"agent_runtime": {"status": "unavailable"}}


class IntelligentNewsAnalyzer:
    """AI-powered analyzer that determines what's interesting to report."""

    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger("NewsAnalyzer")
        self.client = None

        if CLAUDE_SDK_AVAILABLE:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if api_key:
                self.client = Anthropic(api_key=api_key)
                self.logger.info("Claude SDK initialized")
            else:
                self.logger.warning("ANTHROPIC_API_KEY not set - using rule-based analysis")
        else:
            self.logger.warning("Claude SDK not available - using rule-based analysis")

    async def analyze(self, data: Dict) -> List[NewsItem]:
        """Analyze system data and generate interesting news items."""
        news = []

        # Check for critical issues first (P0)
        news.extend(self._check_critical(data))

        # Check for warnings (P1)
        news.extend(self._check_warnings(data))

        # Generate interesting updates (P2)
        if self.client:
            ai_news = await self._ai_generate_news(data)
            news.extend(ai_news)
        else:
            news.extend(self._rule_based_news(data))

        # Add background rotation (P3)
        self.logger.info(f"Data keys before rotation: {list(data.keys())}")
        if "claude_code" in data:
            self.logger.info(f"Claude Code data: {data['claude_code']}")
        if "agent_runtime" in data:
            self.logger.info(f"Agent Runtime data: {data['agent_runtime']}")
        news.extend(self._generate_rotation(data))

        # Debug: log all news items before sorting
        self.logger.info(f"Total news items before sort: {len(news)}")
        for item in news:
            self.logger.info(f"  News item: {item.id} (P{item.priority}, score={item.interesting_score})")

        # Sort by priority and interesting score
        news.sort(key=lambda n: (n.priority, -n.interesting_score))

        return news

    def _check_critical(self, data: Dict) -> List[NewsItem]:
        """Check for critical conditions."""
        news = []

        # MCP server status moved to P3 rotation (not critical)
        # MCPs are started on-demand by Claude Code, not always running
        pass

        # Storage critical
        storage = data.get("system_metrics", {})
        if storage.get("storage_critical", False):
            news.append(NewsItem(
                id="storage_critical",
                priority=0,
                headline="STORAGE CRITICAL",
                detail=f"{storage.get('storage_percent', 0):.0f}% Full!",
                led_color=(255, 0, 0),
                audio_alert=True,
                interesting_score=10.0
            ))

        # High error rate
        errors = data.get("error_metrics", {})
        if errors.get("error_rate", 0) > 10:
            news.append(NewsItem(
                id="error_rate_critical",
                priority=0,
                headline="ERROR RATE HIGH",
                detail=f"{errors.get('error_rate', 0):.1f}% Errors",
                led_color=(255, 0, 0),
                audio_alert=True,
                interesting_score=9.0
            ))

        return news

    def _check_warnings(self, data: Dict) -> List[NewsItem]:
        """Check for warnings."""
        news = []

        errors = data.get("error_metrics", {})
        if 5 < errors.get("error_rate", 0) <= 10:
            news.append(NewsItem(
                id="error_rate_warning",
                priority=1,
                headline="Error Rate Up",
                detail=f"{errors.get('error_rate', 0):.1f}% Errors",
                led_color=(255, 165, 0),
                interesting_score=5.0
            ))

        return news

    async def _ai_generate_news(self, data: Dict) -> List[NewsItem]:
        """Use Claude to analyze what's interesting."""
        news = []

        try:
            # Build context for Claude
            changes = data.get("_changes", [])
            if not changes:
                return []

            context = f"""Analyze recent system changes and determine what's interesting/newsworthy:

Changes detected:
{json.dumps(changes, indent=2)}

Current system state:
- MCP Servers: {data.get('mcp_servers', {})}
- Temporal: {data.get('temporal', {})}
- AutoKitteh: {data.get('autokitteh', {})}
- Ember: {data.get('ember', {})}
- MLX Training: {data.get('mlx_training', {})}

Generate 1-3 interesting news items (16 char headlines). Focus on:
- Significant state changes
- Unusual activity
- Performance metrics
- System health changes

Format: JSON array of {{"headline": "16char", "detail": "16char", "score": 0-10}}
"""

            response = await asyncio.to_thread(
                self.client.messages.create,
                model="claude-haiku-4-5-20251001",
                max_tokens=500,
                messages=[{
                    "role": "user",
                    "content": context
                }]
            )

            # Parse Claude's response
            content = response.content[0].text
            # Extract JSON from response
            import re
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                items = json.loads(json_match.group(0))

                for item in items[:3]:  # Max 3 AI items
                    # Use stable ID based on headline content
                    headline = item["headline"][:16]
                    item_id = f"ai_news_{hash(headline) % 10000}"
                    news.append(NewsItem(
                        id=item_id,
                        priority=2,
                        headline=headline,
                        detail=item["detail"][:16],
                        led_color=(0, 0, 255),
                        interesting_score=item.get("score", 5.0)
                    ))

        except Exception as e:
            error_msg = str(e)
            # If credits exhausted, disable AI permanently and fall back to rule-based
            if "credit balance" in error_msg.lower() or "invalid_request_error" in error_msg.lower():
                self.logger.warning(f"AI credits exhausted - disabling AI news generation, falling back to rule-based")
                self.client = None  # Disable client to prevent future attempts
            else:
                self.logger.error(f"AI news generation failed: {e}")

        return news

    def _rule_based_news(self, data: Dict) -> List[NewsItem]:
        """Generate news using rules (fallback)."""
        news = []

        # MLX training
        mlx = data.get("mlx_training", {})
        if mlx.get("active", False):
            epoch = mlx.get("epoch", 0)
            total = mlx.get("total_epochs", 0)
            pct = int((epoch / total * 100)) if total > 0 else 0
            news.append(NewsItem(
                id="mlx_training",
                priority=2,
                headline="MLX Training",
                detail=f"E{epoch}/{total} {pct}%",
                led_color=(0, 255, 255),
                interesting_score=6.0
            ))

        # Check for changes
        changes = data.get("_changes", [])
        for change in changes[:2]:  # Max 2 change notifications
            news.append(NewsItem(
                id=f"change_{change['source']}",
                priority=2,
                headline=f"{change['source'][:10]} Δ",
                detail=f"Updated now",
                led_color=(0, 0, 255),
                interesting_score=4.0
            ))

        return news

    def _generate_rotation(self, data: Dict) -> List[NewsItem]:
        """Generate background rotation screens."""
        news = []

        # System status
        news.append(NewsItem(
            id="system_status",
            priority=3,
            headline="System Status",
            detail="All OK",
            led_color=(0, 255, 0),
            interesting_score=1.0
        ))

        # Temporal
        temporal = data.get("temporal", {})
        if temporal.get("running", False):
            news.append(NewsItem(
                id="temporal_status",
                priority=3,
                headline="Temporal Works",
                detail=f"{temporal.get('active_workflows', 0)} Active",
                led_color=(0, 255, 0),
                interesting_score=2.0
            ))

        # AutoKitteh
        autokitteh = data.get("autokitteh", {})
        if autokitteh.get("running", False):
            news.append(NewsItem(
                id="autokitteh_status",
                priority=3,
                headline="AutoKitteh",
                detail=f"{autokitteh.get('deployments', 0)} Running",
                led_color=(0, 255, 0),
                interesting_score=2.0
            ))

        # MCP servers
        mcp = data.get("mcp_servers", {})
        news.append(NewsItem(
            id="mcp_status",
            priority=3,
            headline="MCP Servers",
            detail=f"{mcp.get('configured', 0)} configured",
            led_color=(0, 255, 0),
            interesting_score=2.0
        ))

        # Memory usage
        news.append(NewsItem(
            id="memory_status",
            priority=3,
            headline="Memory Usage",
            detail="1135 entities",
            led_color=(0, 255, 0),
            interesting_score=1.5
        ))

        # Voice mode
        voice = data.get("voice_mode", {})
        if voice.get("status") == "ready":
            news.append(NewsItem(
                id="voice_mode",
                priority=3,
                headline="Voice Mode",
                detail="TTS/STT Ready",
                led_color=(0, 255, 0),
                interesting_score=1.5
            ))

        # Agent processes (P2 - important agentic system info)
        agents = data.get("agent_processes", {})
        if "total_agents" in agents:
            total = agents.get("total_agents", 0)
            subagents = agents.get("active_subagents", 0)
            news.append(NewsItem(
                id="agent_processes",
                priority=2,
                headline="Active Agents",
                detail=f"{total} running",
                led_color=(0, 255, 0),
                interesting_score=6.0
            ))

        # Claude Code status (P2 - important agentic system info)
        claude = data.get("claude_code", {})
        self.logger.info(f"Claude Code check: claude={claude}, has_status={'status' in claude}")
        if "status" in claude:
            status = claude.get("status", "unknown")
            hooks = claude.get("hooks_active", 0)
            self.logger.info(f"Adding Claude Code screen: status={status}, hooks={hooks}")
            news.append(NewsItem(
                id="claude_code_status",
                priority=2,
                headline="Claude Code",
                detail=f"{status[:8]} {hooks}hooks",
                led_color=(0, 255, 0),
                interesting_score=6.0
            ))

        # Agent runtime queue (P2 - important agentic system info)
        runtime = data.get("agent_runtime", {})
        if "queue_size" in runtime:
            queue = runtime.get("queue_size", 0)
            goals = runtime.get("active_goals", 0)
            news.append(NewsItem(
                id="agent_runtime_queue",
                priority=2,
                headline="Task Queue",
                detail=f"{queue} tasks {goals}G",
                led_color=(0, 255, 0),
                interesting_score=6.0
            ))

        # Storage
        storage = data.get("system_metrics", {})
        if "storage_used_gb" in storage:
            news.append(NewsItem(
                id="storage_status",
                priority=3,
                headline="Storage: RAID0",
                detail=f"{storage['storage_used_gb']:.1f}G/{storage['storage_total_gb']:.0f}G OK",
                led_color=(0, 255, 0),
                interesting_score=1.0
            ))

        return news


class IntelligentDisplayAgent:
    """AI-powered display agent with intelligent news feed."""

    def __init__(self, config_path: str, arduino_port: str):
        self.config_path = Path(config_path)
        self.arduino_port = arduino_port

        with open(self.config_path) as f:
            self.config = json.load(f)

        self._setup_logging()

        self.logger.info("=== Intelligent Display Agent Starting ===")
        self.logger.info(f"Claude SDK: {'Available' if CLAUDE_SDK_AVAILABLE else 'Not Available'}")

        self.surface = None
        self.led_controller = None
        self.collector = SystemDataCollector(self.config)
        self.analyzer = IntelligentNewsAnalyzer(self.config)

        self.current_news = None
        self.rotation_queue = []
        self.rotation_index = 0
        self.last_update = 0
        self.running = False

        # Scrolling text support for 16x2 LCD
        self.scroll_pos = 0
        self.scroll_counter = 0
        self.scroll_update_every = 10  # Update scroll every 10 loop iterations (500ms)

    def _setup_logging(self):
        """Configure logging."""
        log_config = self.config["logging"]
        log_file = Path(log_config["file"])
        log_file.parent.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            level=log_config["level"],
            format=log_config["format"],
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )

        self.logger = logging.getLogger("IntelligentAgent")

    async def initialize(self):
        """Initialize Arduino."""
        try:
            self.logger.info("Connecting to Arduino...")
            self.surface = ArduinoSurface(self.arduino_port)
            self.surface.connect()

            self.led_controller = LEDController(self.surface)

            # Startup animation
            self.surface.lcd_clear()
            self.surface.lcd_write(0, 0, "Intelligent Agent")
            self.surface.lcd_write(1, 0, "Initializing...")
            self.led_controller.set_mode("slow_pulse", (128, 0, 128))

            time.sleep(2)

            self.logger.info("Arduino initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            self.logger.error(traceback.format_exc())
            return False

    async def run(self):
        """Main intelligence loop."""
        self.running = True
        self.logger.info("Intelligence loop started")

        # Set breathing blue for active mode
        self.led_controller.set_mode("slow_pulse", (0, 0, 255))

        while self.running:
            try:
                # Collect system data
                data = await self.collector.collect_all()

                # Analyze with AI
                news_items = await self.analyzer.analyze(data)

                # Update display
                self._update_display(news_items)

                # Update LED breathing
                self.led_controller.update()

                # Update scroll position for long text
                self.scroll_counter += 1
                if self.scroll_counter >= self.scroll_update_every:
                    self.scroll_pos += 1
                    self.scroll_counter = 0

                # Small sleep for smooth breathing
                await asyncio.sleep(0.05)

            except KeyboardInterrupt:
                self.logger.info("Keyboard interrupt")
                self.running = False
                break

            except Exception as e:
                self.logger.error(f"Main loop error: {e}")
                self.logger.error(traceback.format_exc())
                await asyncio.sleep(5)

    def _update_display(self, news_items: List[NewsItem]):
        """Update display based on news items."""
        if not news_items:
            return

        # Check for interrupts (P0 or P1)
        for news in news_items:
            if news.priority == 0:
                self._show_news(news)
                return
            elif news.priority == 1:
                if self.config["priorities"]["P1_WARNING"]["interrupt"]:
                    self._show_news(news)
                    return

        # Handle rotation
        self._update_rotation(news_items)

    def _show_news(self, news: NewsItem):
        """Show a specific news item."""
        try:
            self.surface.lcd_clear()
            self.surface.lcd_write(0, 0, news.format_line(news.headline, scroll_pos=self.scroll_pos))
            self.surface.lcd_write(1, 0, news.format_line(news.detail, scroll_pos=self.scroll_pos))

            # Update LED mode based on priority
            if news.priority == 0:
                self.led_controller.set_mode("flash", news.led_color)
            elif news.priority == 1:
                self.led_controller.set_mode("solid", news.led_color)
            elif news.priority == 2:
                self.led_controller.set_mode("fast_pulse", news.led_color)
            else:
                self.led_controller.set_mode("slow_pulse", news.led_color)

            if news.audio_alert:
                self.surface.beep(200, 1000)
                time.sleep(0.1)
                self.surface.beep(200, 1000)

            self.current_news = news
            self.last_update = time.time()
            self.logger.info(f"Displayed: {news.id} (P{news.priority}, score={news.interesting_score})")

        except Exception as e:
            self.logger.error(f"Display error: {e}")

    def _update_rotation(self, news_items: List[NewsItem]):
        """Update rotation queue."""
        rotation_items = [n for n in news_items if n.priority >= 2]

        if not rotation_items:
            return

        interval = self.config["display"]["rotation_interval_seconds"]
        if time.time() - self.last_update < interval:
            return

        # Compare IDs instead of object instances to detect actual content changes
        current_ids = [item.id for item in rotation_items]
        queue_ids = [item.id for item in self.rotation_queue] if self.rotation_queue else []

        if current_ids != queue_ids:
            self.logger.info(f"Rotation queue changed, {len(rotation_items)} items:")
            for idx, item in enumerate(rotation_items):
                self.logger.info(f"  [{idx}] {item.id} (P{item.priority}, score={item.interesting_score})")

            # Try to preserve rotation position by finding current item in new queue
            current_item_id = None
            if self.rotation_queue and self.rotation_index < len(self.rotation_queue):
                current_item_id = self.rotation_queue[self.rotation_index].id

            self.rotation_queue = rotation_items

            # Try to find the current item in the new queue
            if current_item_id:
                try:
                    self.rotation_index = current_ids.index(current_item_id)
                    self.logger.info(f"Preserved rotation position: index {self.rotation_index} ({current_item_id})")
                except ValueError:
                    # Item no longer in queue, reset to 0
                    self.rotation_index = 0
                    self.logger.info("Current item no longer in queue, reset to index 0")
            else:
                self.rotation_index = 0

        if self.rotation_queue:
            news = self.rotation_queue[self.rotation_index]
            self.logger.info(f"Selecting rotation [{self.rotation_index}/{len(self.rotation_queue)-1}]: {news.id}")
            self._show_news(news)

            self.rotation_index = (self.rotation_index + 1) % len(self.rotation_queue)

    async def shutdown(self):
        """Graceful shutdown."""
        self.logger.info("Shutting down...")
        self.running = False

        if self.surface:
            try:
                self.surface.lcd_clear()
                self.surface.lcd_write(0, 0, "Agent Stopped")
                self.surface.lcd_write(1, 0, "Goodbye!")
                self.led_controller.set_mode("solid", (255, 0, 0))
                time.sleep(2)
                self.surface.disconnect()
            except:
                pass

        self.logger.info("Shutdown complete")


async def main():
    """Entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Intelligent Display Agent")
    parser.add_argument(
        "--config",
        default="/mnt/agentic-system/arduino-surface/config/display-agent.json",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--port",
        default="/dev/tty.usbmodem8344401",
        help="Arduino serial port"
    )

    args = parser.parse_args()

    agent = IntelligentDisplayAgent(args.config, args.port)

    if not await agent.initialize():
        print("Failed to initialize agent")
        sys.exit(1)

    try:
        await agent.run()
    finally:
        await agent.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
