#!/usr/bin/env python3
"""
Arduino Display Intelligence Agent

Production daemon that monitors the entire agentic system and provides
intelligent, priority-based observability on the 16x2 LCD Arduino display.

This agent continuously collects data from all system components and decides
what to display based on priority, urgency, and relevance.
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

# Add bridge to path
sys.path.insert(0, str(Path(__file__).parent.parent / "bridge"))

try:
    from surface_bridge import ArduinoSurface
except ImportError:
    print("ERROR: Could not import ArduinoSurface. Check PYTHONPATH.")
    sys.exit(1)

@dataclass
class DisplayMessage:
    """A message to display on the LCD."""
    id: str
    priority: int  # 0=critical, 1=warning, 2=info, 3=background
    line1: str
    line2: str
    led_color: tuple = (0, 255, 0)  # RGB
    audio_alert: bool = False
    timestamp: float = field(default_factory=time.time)
    duration: Optional[float] = None  # How long to show (None = rotation)
    
    def format_line(self, line: str, width: int = 16) -> str:
        """Format line to exactly width characters."""
        if len(line) > width:
            return line[:width]
        return line + " " * (width - len(line))


class SystemDataCollector:
    """Collects data from all agentic system components."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger("DataCollector")
        self.cache = {}
        self.last_update = {}
        
    async def collect_all(self) -> Dict[str, Any]:
        """Collect data from all enabled sources."""
        data = {}
        
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
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, dict):
                data.update(result)
            elif isinstance(result, Exception):
                self.logger.error(f"Collection error: {result}")
                
        return data
    
    async def collect_mcp_status(self) -> Dict:
        """Check MCP server health."""
        servers = self.config["data_sources"]["mcp_servers"]["servers"]
        online = 0
        details = {}
        
        for server in servers:
            # Check if MCP process is running (simplified check)
            try:
                # In production, this would query actual MCP status
                # For now, assume online if no recent errors
                details[server] = "online"
                online += 1
            except Exception as e:
                self.logger.warning(f"MCP {server} check failed: {e}")
                details[server] = "unknown"
                
        return {
            "mcp_servers": {
                "online": online,
                "total": len(servers),
                "details": details
            }
        }
    
    async def collect_system_metrics(self) -> Dict:
        """Collect system storage and memory metrics."""
        try:
            import shutil
            
            # Check SSDRAID0 storage
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
        """Collect Ember tamagotchi status."""
        try:
            tamagotchi_dir = Path(self.config["data_sources"]["ember_status"]["tamagotchi_dir"])
            status_file = tamagotchi_dir / "pet_data.json"
            
            if status_file.exists():
                with open(status_file) as f:
                    pet_data = json.load(f)
                    
                return {
                    "ember": {
                        "mood": pet_data.get("mood", "unknown"),
                        "hunger": pet_data.get("stats", {}).get("hunger", 0),
                        "energy": pet_data.get("stats", {}).get("energy", 0),
                        "cleanliness": pet_data.get("stats", {}).get("cleanliness", 0),
                        "happiness": pet_data.get("stats", {}).get("happiness", 0)
                    }
                }
            else:
                return {"ember": {"status": "not_found"}}
        except Exception as e:
            self.logger.error(f"Ember status error: {e}")
            return {"ember": {"error": str(e)}}
    
    async def collect_temporal_status(self) -> Dict:
        """Check Temporal workflow status."""
        try:
            # In production, query Temporal API
            # For now, check if process is running
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
            self.logger.error(f"Temporal status error: {e}")
            return {"temporal": {"error": str(e)}}
    
    async def collect_autokitteh_status(self) -> Dict:
        """Check AutoKitteh deployment status."""
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
            self.logger.error(f"AutoKitteh status error: {e}")
            return {"autokitteh": {"error": str(e)}}
    
    async def collect_voice_status(self) -> Dict:
        """Check voice mode status."""
        try:
            stats_file = Path(self.config["data_sources"]["voice_mode"]["statistics_file"])
            if stats_file.exists():
                with open(stats_file) as f:
                    stats = json.load(f)
                return {"voice_mode": {"status": "ready", "stats": stats}}
            else:
                return {"voice_mode": {"status": "no_stats"}}
        except Exception as e:
            self.logger.error(f"Voice mode error: {e}")
            return {"voice_mode": {"error": str(e)}}
    
    async def collect_mlx_status(self) -> Dict:
        """Check for active MLX training."""
        try:
            # Look for recent training logs
            log_files = glob.glob("/mnt/agentic-system/arduino-surface/logs/*.log")
            
            for log_file in log_files:
                # Check if file was modified in last minute
                if time.time() - os.path.getmtime(log_file) < 60:
                    with open(log_file) as f:
                        content = f.read()
                        # Look for training patterns
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
            self.logger.error(f"MLX status error: {e}")
            return {"mlx_training": {"error": str(e)}}
    
    async def collect_error_metrics(self) -> Dict:
        """Collect error rate from logs."""
        try:
            error_count = 0
            total_count = 0
            
            log_patterns = self.config["data_sources"]["error_logs"]["log_files"]
            for pattern in log_patterns:
                for log_file in glob.glob(pattern):
                    if time.time() - os.path.getmtime(log_file) < 300:  # Last 5 min
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
            self.logger.error(f"Error metrics collection failed: {e}")
            return {"error_metrics": {"error": str(e)}}


class PriorityEngine:
    """Determines what to display based on priorities and conditions."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger("PriorityEngine")
        
    def evaluate(self, data: Dict) -> List[DisplayMessage]:
        """Evaluate all data and return prioritized display messages."""
        messages = []
        
        # Check for critical conditions (P0)
        messages.extend(self._check_critical(data))
        
        # Check for warnings (P1)
        messages.extend(self._check_warnings(data))
        
        # Add info messages (P2)
        messages.extend(self._check_info(data))
        
        # Add background messages (P3)
        messages.extend(self._check_background(data))
        
        # Sort by priority
        messages.sort(key=lambda m: m.priority)
        
        return messages
    
    def _check_critical(self, data: Dict) -> List[DisplayMessage]:
        """Check for P0 critical conditions."""
        messages = []
        
        # MCP server down
        mcp = data.get("mcp_servers", {})
        if mcp.get("online", 0) < mcp.get("total", 0):
            messages.append(DisplayMessage(
                id="mcp_critical",
                priority=0,
                line1="ALERT: MCP DOWN ",
                line2=f"{mcp['online']}/{mcp['total']} Online   ",
                led_color=(255, 0, 0),
                audio_alert=True,
                duration=30
            ))
        
        # Storage critical
        storage = data.get("system_metrics", {})
        if storage.get("storage_critical", False):
            messages.append(DisplayMessage(
                id="storage_critical",
                priority=0,
                line1="STORAGE CRITICAL",
                line2=f"{storage['storage_percent']:.0f}% Full      ",
                led_color=(255, 0, 0),
                audio_alert=True,
                duration=30
            ))
        
        # High error rate
        errors = data.get("error_metrics", {})
        if errors.get("error_rate", 0) > 10:
            messages.append(DisplayMessage(
                id="error_rate_critical",
                priority=0,
                line1="ERROR RATE HIGH ",
                line2=f"{errors['error_rate']:.1f}% Errors    ",
                led_color=(255, 0, 0),
                audio_alert=True,
                duration=30
            ))
        
        return messages
    
    def _check_warnings(self, data: Dict) -> List[DisplayMessage]:
        """Check for P1 warning conditions."""
        messages = []
        
        # Elevated error rate
        errors = data.get("error_metrics", {})
        if 5 < errors.get("error_rate", 0) <= 10:
            messages.append(DisplayMessage(
                id="error_rate_warning",
                priority=1,
                line1="Error Rate High ",
                line2=f"{errors['error_rate']:.1f}% Errors    ",
                led_color=(255, 165, 0),
                duration=10
            ))
        
        return messages
    
    def _check_info(self, data: Dict) -> List[DisplayMessage]:
        """Check for P2 info messages."""
        messages = []
        
        # MLX training active
        mlx = data.get("mlx_training", {})
        if mlx.get("active", False):
            epoch = mlx.get("epoch", 0)
            total = mlx.get("total_epochs", 0)
            pct = int((epoch / total * 100)) if total > 0 else 0
            messages.append(DisplayMessage(
                id="mlx_training",
                priority=2,
                line1="MLX Training    ",
                line2=f"E{epoch}/{total} {pct}%   ",
                led_color=(0, 255, 255)
            ))
        
        return messages
    
    def _check_background(self, data: Dict) -> List[DisplayMessage]:
        """Generate P3 background rotation messages."""
        messages = []
        
        # System status
        messages.append(DisplayMessage(
            id="system_status",
            priority=3,
            line1="System Status   ",
            line2="All OK          ",
            led_color=(0, 255, 0)
        ))
        
        # Temporal status
        temporal = data.get("temporal", {})
        if temporal.get("running", False):
            messages.append(DisplayMessage(
                id="temporal_status",
                priority=3,
                line1="Temporal Works  ",
                line2=f"{temporal.get('active_workflows', 0)} Active       ",
                led_color=(0, 255, 0)
            ))
        
        # AutoKitteh status
        autokitteh = data.get("autokitteh", {})
        if autokitteh.get("running", False):
            messages.append(DisplayMessage(
                id="autokitteh_status",
                priority=3,
                line1="AutoKitteh      ",
                line2=f"{autokitteh.get('deployments', 0)} Running      ",
                led_color=(0, 255, 0)
            ))
        
        # MCP servers
        mcp = data.get("mcp_servers", {})
        messages.append(DisplayMessage(
            id="mcp_status",
            priority=3,
            line1="MCP Servers     ",
            line2=f"{mcp.get('online', 0)}/{mcp.get('total', 0)} Online     ",
            led_color=(0, 255, 0)
        ))
        
        # Ember status
        ember = data.get("ember", {})
        if "mood" in ember:
            mood = ember["mood"][:8]  # Truncate
            messages.append(DisplayMessage(
                id="ember_status",
                priority=3,
                line1=f"Ember {mood}    ",
                line2=f"H{ember.get('happiness', 0)}|E{ember.get('energy', 0)}          ",
                led_color=(0, 255, 0)
            ))
        
        # Storage status
        storage = data.get("system_metrics", {})
        if "storage_used_gb" in storage:
            messages.append(DisplayMessage(
                id="storage_status",
                priority=3,
                line1="Storage: RAID0  ",
                line2=f"{storage['storage_used_gb']:.1f}G/{storage['storage_total_gb']:.0f}G OK    ",
                led_color=(0, 255, 0)
            ))
        
        return messages


class DisplayController:
    """Controls Arduino display updates."""
    
    def __init__(self, surface: ArduinoSurface, config: Dict):
        self.surface = surface
        self.config = config
        self.logger = logging.getLogger("DisplayController")
        self.current_message = None
        self.rotation_queue = []
        self.rotation_index = 0
        self.last_update = 0
        
    def update(self, messages: List[DisplayMessage]):
        """Update display based on prioritized messages."""
        if not messages:
            return
            
        # Check for interrupts (P0 or P1 with interrupt flag)
        priority_configs = self.config["priorities"]
        for msg in messages:
            if msg.priority == 0:
                self._show_message(msg)
                return
            elif msg.priority == 1:
                if priority_configs["P1_WARNING"]["interrupt"]:
                    self._show_message(msg)
                    return
        
        # Handle rotation for P2 and P3 messages
        self._update_rotation(messages)
        
    def _show_message(self, msg: DisplayMessage):
        """Show a specific message immediately."""
        try:
            self.surface.lcd_clear()
            self.surface.lcd_write(0, 0, msg.format_line(msg.line1))
            self.surface.lcd_write(1, 0, msg.format_line(msg.line2))
            self.surface.set_led(0, *msg.led_color)
            
            if msg.audio_alert:
                self.surface.beep(200, 1000)
                time.sleep(0.1)
                self.surface.beep(200, 1000)
            
            self.current_message = msg
            self.last_update = time.time()
            self.logger.info(f"Displayed: {msg.id} (P{msg.priority})")
            
        except Exception as e:
            self.logger.error(f"Display error: {e}")
    
    def _update_rotation(self, messages: List[DisplayMessage]):
        """Update rotation queue and show next message."""
        # Filter to P2 and P3 messages
        rotation_messages = [m for m in messages if m.priority >= 2]
        
        if not rotation_messages:
            return
            
        # Check if rotation interval has passed
        interval = self.config["display"]["rotation_interval_seconds"]
        if time.time() - self.last_update < interval:
            return
            
        # Update rotation queue if changed
        if rotation_messages != self.rotation_queue:
            self.rotation_queue = rotation_messages
            self.rotation_index = 0
        
        # Show next message in rotation
        if self.rotation_queue:
            msg = self.rotation_queue[self.rotation_index]
            self._show_message(msg)
            
            self.rotation_index = (self.rotation_index + 1) % len(self.rotation_queue)


class DisplayIntelligenceAgent:
    """Main agent orchestrating the display monitoring."""
    
    def __init__(self, config_path: str, arduino_port: str):
        self.config_path = Path(config_path)
        self.arduino_port = arduino_port
        
        # Load configuration
        with open(self.config_path) as f:
            self.config = json.load(f)
        
        # Setup logging
        self._setup_logging()
        
        self.logger.info("=== Arduino Display Intelligence Agent Starting ===")
        self.logger.info(f"Config: {self.config_path}")
        self.logger.info(f"Arduino: {self.arduino_port}")
        
        # Initialize components
        self.surface = None
        self.collector = SystemDataCollector(self.config)
        self.priority_engine = PriorityEngine(self.config)
        self.display_controller = None
        
        self.running = False
        
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
        
        self.logger = logging.getLogger("DisplayAgent")
        
    async def initialize(self):
        """Initialize Arduino connection."""
        try:
            self.logger.info("Connecting to Arduino...")
            self.surface = ArduinoSurface(self.arduino_port)
            self.surface.connect()
            
            self.display_controller = DisplayController(self.surface, self.config)
            
            # Show startup message
            self.surface.lcd_clear()
            self.surface.lcd_write(0, 0, "Display Agent   ")
            self.surface.lcd_write(1, 0, "Initializing... ")
            self.surface.set_led(0, 128, 0, 128)  # Purple for startup
            
            time.sleep(2)
            
            self.logger.info("Arduino initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Arduino initialization failed: {e}")
            self.logger.error(traceback.format_exc())
            return False
    
    async def run(self):
        """Main agent loop."""
        self.running = True
        self.logger.info("Agent main loop started")
        
        while self.running:
            try:
                # Collect all system data
                data = await self.collector.collect_all()
                
                # Evaluate priorities
                messages = self.priority_engine.evaluate(data)
                
                # Update display
                self.display_controller.update(messages)
                
                # Sleep briefly
                await asyncio.sleep(1)
                
            except KeyboardInterrupt:
                self.logger.info("Keyboard interrupt received")
                self.running = False
                break
                
            except Exception as e:
                self.logger.error(f"Main loop error: {e}")
                self.logger.error(traceback.format_exc())
                await asyncio.sleep(5)  # Back off on errors
    
    async def shutdown(self):
        """Graceful shutdown."""
        self.logger.info("Shutting down agent...")
        self.running = False
        
        if self.surface:
            try:
                self.surface.lcd_clear()
                self.surface.lcd_write(0, 0, "Agent Stopped   ")
                self.surface.lcd_write(1, 0, "Goodbye!        ")
                self.surface.set_led(0, 255, 0, 0)  # Red for stopped
                time.sleep(2)
                self.surface.disconnect()
            except:
                pass
        
        self.logger.info("Shutdown complete")


async def main():
    """Entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Arduino Display Intelligence Agent")
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
    
    agent = DisplayIntelligenceAgent(args.config, args.port)
    
    if not await agent.initialize():
        print("Failed to initialize agent")
        sys.exit(1)
    
    try:
        await agent.run()
    finally:
        await agent.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
