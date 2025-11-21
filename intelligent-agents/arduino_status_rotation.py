#!/usr/bin/env python3
"""
Arduino Status Rotation Display

Implements Goal #3 from Agent Runtime: Persistent background task that
continuously rotates system status on Arduino LCD display.

Cycles through:
- Temporal workflows
- AutoKitteh deployments
- PM2 processes
- Qdrant vector DB
- MCP servers
- Port Manager
- System resources

Updates every 5 seconds with current health indicators using LED colors.
"""

import asyncio
import json
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Add Arduino bridge to path
<<<<<<< HEAD
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/arduino-surface/bridge')
=======
sys.path.insert(0, '/mnt/agentic-system/arduino-surface/bridge')
>>>>>>> origin/main

try:
    from surface_bridge import ArduinoSurface
    ARDUINO_AVAILABLE = True
except ImportError as e:
    ARDUINO_AVAILABLE = False
    print(f"Warning: Arduino bridge not available: {e}")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
<<<<<<< HEAD
        logging.FileHandler('/Volumes/SSDRAID0/agentic-system/logs/arduino_status_rotation.log'),
=======
        logging.FileHandler('/mnt/agentic-system/logs/arduino_status_rotation.log'),
>>>>>>> origin/main
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('arduino-status-rotation')

class ArduinoStatusDisplay:
    """Rotates system status on Arduino LCD"""

    def __init__(self, arduino_port: str = "/dev/tty.usbmodem8344401"):
        self.running = True
        self.rotation_interval = 5  # seconds
        self.current_screen = 0
        self.arduino_port = arduino_port
        self.arduino = None
        self.screens = [
            self.show_temporal_status,
            self.show_autokitteh_status,
            self.show_pm2_status,
            self.show_qdrant_status,
            self.show_mcp_status,
            self.show_port_manager,
            self.show_system_resources
        ]

        # Initialize Arduino connection
        if ARDUINO_AVAILABLE:
            try:
                self.arduino = ArduinoSurface(self.arduino_port)
                if self.arduino.connect():
                    logger.info(f"Connected to Arduino on {self.arduino_port}")
                else:
                    logger.error("Failed to connect to Arduino")
                    self.arduino = None
            except Exception as e:
                logger.error(f"Error initializing Arduino: {e}")
                self.arduino = None
        else:
            logger.warning("Arduino bridge not available - running in simulation mode")

    async def update_lcd(self, row0: str, row1: str):
        """Update both LCD rows"""
        if not self.arduino:
            logger.debug(f"Simulation: LCD: {row0} / {row1}")
            return

        try:
            # Use direct ArduinoSurface API
            self.arduino.lcd_write(0, 0, row0[:16])
            self.arduino.lcd_write(1, 0, row1[:16])
            logger.debug(f"LCD: {row0} / {row1}")
        except Exception as e:
            logger.error(f"LCD update error: {e}")

    async def set_led_color(self, r: int, g: int, b: int):
        """Set RGB LED color"""
        if not self.arduino:
            logger.debug(f"Simulation: LED: RGB({r},{g},{b})")
            return

        try:
            # Use direct ArduinoSurface API
            self.arduino.set_led(0, r, g, b)  # Tier 0
        except Exception as e:
            logger.error(f"LED update error: {e}")

    async def show_temporal_status(self):
        """Show Temporal workflow status"""
        try:
            result = subprocess.run(
                ['temporal', 'workflow', 'list', '--namespace', 'default', '--limit', '20'],
                capture_output=True, text=True, timeout=5
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                running = len([l for l in lines if 'Running' in l])
                await self.update_lcd(f"Temporal: {running}", "workflows ok")
                await self.set_led_color(0, 255, 0)  # Green
            else:
                await self.update_lcd("Temporal:", "ERROR")
                await self.set_led_color(255, 0, 0)  # Red

        except Exception as e:
            logger.error(f"Temporal status error: {e}")
            await self.update_lcd("Temporal:", "TIMEOUT")
            await self.set_led_color(255, 165, 0)  # Orange

    async def show_autokitteh_status(self):
        """Show AutoKitteh deployment status"""
        try:
            result = subprocess.run(
                ['/Volumes/FILES/Marc-Data/Documents/Cline/MCP/autokitteh-source/bin/ak', 'deployment', 'list'],
                capture_output=True, text=True, timeout=5
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                active = len([l for l in lines if 'ACTIVE' in l])
                await self.update_lcd(f"AutoKitteh:{active}", "deployments")
                await self.set_led_color(0, 255, 0)  # Green
            else:
                await self.update_lcd("AutoKitteh:", "ERROR")
                await self.set_led_color(255, 0, 0)  # Red

        except Exception as e:
            logger.error(f"AutoKitteh status error: {e}")
            await self.update_lcd("AutoKitteh:", "TIMEOUT")
            await self.set_led_color(255, 165, 0)  # Orange

    async def show_pm2_status(self):
        """Show PM2 process status"""
        try:
            result = subprocess.run(
                ['pm2', 'jlist'],
                capture_output=True, text=True, timeout=3
            )

            if result.returncode == 0:
                processes = json.loads(result.stdout)
                online = len([p for p in processes if p.get('pm2_env', {}).get('status') == 'online'])
                total = len(processes)
                await self.update_lcd(f"PM2: {online}/{total}", "processes ok")
                await self.set_led_color(0, 255, 0)  # Green
            else:
                await self.update_lcd("PM2:", "ERROR")
                await self.set_led_color(255, 0, 0)  # Red

        except Exception as e:
            logger.error(f"PM2 status error: {e}")
            await self.update_lcd("PM2:", "Not available")
            await self.set_led_color(128, 128, 128)  # Gray

    async def show_qdrant_status(self):
        """Show Qdrant vector DB status"""
        try:
            result = subprocess.run(
                ['curl', '-s', 'http://localhost:6333/'],
                capture_output=True, text=True, timeout=3
            )

            if result.returncode == 0 and 'qdrant' in result.stdout.lower():
                await self.update_lcd("Qdrant:", "Running OK")
                await self.set_led_color(0, 255, 0)  # Green
            else:
                await self.update_lcd("Qdrant:", "DOWN")
                await self.set_led_color(255, 0, 0)  # Red

        except Exception as e:
            logger.error(f"Qdrant status error: {e}")
            await self.update_lcd("Qdrant:", "TIMEOUT")
            await self.set_led_color(255, 165, 0)  # Orange

    async def show_mcp_status(self):
        """Show MCP server count"""
        try:
            with open(Path.home() / '.claude.json', 'r') as f:
                config = json.load(f)
                servers = config.get('mcpServers', {})
                enabled = len([s for s in servers.values() if not s.get('disabled', False)])
                total = len(servers)
                await self.update_lcd(f"MCP: {enabled}/{total}", "servers up")
                await self.set_led_color(0, 255, 0)  # Green

        except Exception as e:
            logger.error(f"MCP status error: {e}")
            await self.update_lcd("MCP:", "Config error")
            await self.set_led_color(255, 165, 0)  # Orange

    async def show_port_manager(self):
        """Show Port Manager status"""
        try:
            result = subprocess.run(
                ['curl', '-s', 'http://localhost:4102/api/ports'],
                capture_output=True, text=True, timeout=3
            )

            if result.returncode == 0:
                ports_data = json.loads(result.stdout)
                port_count = len(ports_data.get('ports', []))
                await self.update_lcd(f"PortMgr:{port_count}", "ports tracked")
                await self.set_led_color(0, 255, 0)  # Green
            else:
                await self.update_lcd("PortMgr:", "Unavailable")
                await self.set_led_color(128, 128, 128)  # Gray

        except Exception as e:
            logger.error(f"Port Manager status error: {e}")
            await self.update_lcd("PortMgr:", "TIMEOUT")
            await self.set_led_color(255, 165, 0)  # Orange

    async def show_system_resources(self):
        """Show system resource usage"""
        try:
            # Get CPU and memory usage
            result = subprocess.run(
                ['top', '-l', '1', '-n', '0'],
                capture_output=True, text=True, timeout=3
            )

            if result.returncode == 0:
                lines = result.stdout.split('\n')
                cpu_line = [l for l in lines if 'CPU usage' in l][0]
                cpu_idle = cpu_line.split('idle')[0].split()[-1].rstrip('%')
                cpu_used = 100 - float(cpu_idle)

                await self.update_lcd(f"System CPU:", f"{cpu_used:.1f}% used")

                if cpu_used < 70:
                    await self.set_led_color(0, 255, 0)  # Green
                elif cpu_used < 90:
                    await self.set_led_color(255, 165, 0)  # Orange
                else:
                    await self.set_led_color(255, 0, 0)  # Red
            else:
                await self.update_lcd("System:", "Status error")
                await self.set_led_color(128, 128, 128)  # Gray

        except Exception as e:
            logger.error(f"System resources error: {e}")
            await self.update_lcd("System:", "Read error")
            await self.set_led_color(255, 165, 0)  # Orange

    async def run(self):
        """Main rotation loop"""
        logger.info("Arduino Status Rotation starting...")

        while self.running:
            try:
                # Show current screen
                screen_func = self.screens[self.current_screen]
                await screen_func()

                # Move to next screen
                self.current_screen = (self.current_screen + 1) % len(self.screens)

                # Wait before next rotation
                await asyncio.sleep(self.rotation_interval)

            except KeyboardInterrupt:
                logger.info("Received shutdown signal")
                self.running = False
                break
            except Exception as e:
                logger.error(f"Error in rotation loop: {e}")
                await asyncio.sleep(self.rotation_interval)

        logger.info("Arduino Status Rotation stopped")

    def stop(self):
        """Stop the rotation"""
        self.running = False
        if self.arduino:
            try:
                self.arduino.disconnect()
                logger.info("Disconnected from Arduino")
            except Exception as e:
                logger.error(f"Error disconnecting from Arduino: {e}")

def main():
    """Entry point"""
    import sys

    # Get Arduino port from command line or use default
    arduino_port = sys.argv[1] if len(sys.argv) > 1 else "/dev/tty.usbmodem8344401"

    display = ArduinoStatusDisplay(arduino_port)

    try:
        asyncio.run(display.run())
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
        display.stop()

if __name__ == "__main__":
    main()
