#!/usr/bin/env python3
"""
Arduino Ready Watcher v2
Automatically starts display intelligence agent when Arduino is ready

This daemon:
1. Monitors Arduino serial port
2. Actively checks if Arduino is ready
3. Starts display_intelligence_agent when Arduino is operational
4. Ensures agent stays running while Arduino is connected
"""

import serial
import time
import json
import subprocess
import sys
import signal
from pathlib import Path
from typing import Optional
import logging

# Setup logging
LOG_FILE = Path(__file__).parent.parent / "logs" / "ready_watcher.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("arduino_ready_watcher")

# Configuration
ARDUINO_PORT = "/dev/tty.usbmodem8344401"
BAUD_RATE = 115200
AGENT_SCRIPT = Path(__file__).parent / "intelligent_display_agent.py"
CONFIG_FILE = Path(__file__).parent.parent / "config" / "display-agent.json"

class ArduinoReadyWatcher:
    """Watches for Arduino and manages display agent"""

    def __init__(self, port: str, agent_script: Path, config_file: Path):
        self.port = port
        self.agent_script = agent_script
        self.config_file = config_file
        self.serial = None
        self.agent_process = None
        self.running = True

        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        self.stop_agent()
        if self.serial and self.serial.is_open:
            self.serial.close()
        sys.exit(0)

    def connect_arduino(self) -> bool:
        """Connect to Arduino and verify it's ready"""
        try:
            if self.serial and self.serial.is_open:
                self.serial.close()

            logger.info(f"Connecting to Arduino on {self.port}...")
            self.serial = serial.Serial(self.port, BAUD_RATE, timeout=2)
            time.sleep(3)  # Wait for Arduino reset

            # Clear any pending data
            self.serial.reset_input_buffer()
            
            # Send STATUS command to check if Arduino is ready
            logger.info("Checking Arduino status...")
            self.serial.write(b"STATUS\n")
            self.serial.flush()
            
            # Wait for response
            start_time = time.time()
            while time.time() - start_time < 5:
                if self.serial.in_waiting:
                    line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        logger.info(f"Arduino response: {line}")
                        try:
                            data = json.loads(line)
                            # Check for valid Arduino responses
                            if (data.get("status") in ["ok", "ready"] or
                                data.get("cmd") == "status" or
                                "device" in data or
                                "pot" in data):
                                logger.info(f"✓ Arduino is ready")
                                return True
                        except json.JSONDecodeError:
                            pass
                time.sleep(0.1)
            
            logger.warning("No valid status response from Arduino")
            return False

        except serial.SerialException as e:
            logger.error(f"Failed to connect: {e}")
            return False
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False

    def start_agent(self) -> bool:
        """Start the display intelligence agent"""
        if self.agent_process and self.agent_process.poll() is None:
            logger.info("Agent already running")
            return True

        try:
            logger.info(f"Starting display intelligence agent...")
            
            # Start agent process
            self.agent_process = subprocess.Popen(
                [
                    sys.executable,
                    str(self.agent_script),
                    "--config", str(self.config_file),
                    "--port", self.port
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL
            )
            
            # Give it a moment to start
            time.sleep(2)
            
            # Check if it's running
            if self.agent_process.poll() is None:
                logger.info(f"✓ Display agent started (PID: {self.agent_process.pid})")
                return True
            else:
                stderr = self.agent_process.stderr.read().decode() if self.agent_process.stderr else ""
                logger.error(f"Agent process exited immediately: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start agent: {e}")
            return False

    def stop_agent(self):
        """Stop the display intelligence agent"""
        if self.agent_process:
            try:
                logger.info("Stopping display agent...")
                self.agent_process.terminate()
                
                # Wait for graceful shutdown
                try:
                    self.agent_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning("Agent didn't stop gracefully, killing...")
                    self.agent_process.kill()
                    self.agent_process.wait()
                
                logger.info("Display agent stopped")
                
            except Exception as e:
                logger.error(f"Error stopping agent: {e}")
            
            self.agent_process = None

    def monitor_agent(self):
        """Monitor agent and restart if it dies"""
        if not self.agent_process:
            return

        # Check if agent is still running
        if self.agent_process.poll() is not None:
            logger.warning("Display agent died, restarting...")
            time.sleep(5)  # Brief delay before restart
            self.start_agent()

    def run(self):
        """Main watch loop"""
        logger.info("Arduino Ready Watcher v2 starting...")
        
        retry_count = 0
        max_retries = 5
        
        while self.running:
            try:
                # Try to connect and verify Arduino is ready
                if self.connect_arduino():
                    retry_count = 0  # Reset on success
                    
                    # Start display agent
                    if self.start_agent():
                        logger.info("✓ System ready - monitoring...")
                        
                        # Monitor both agent and Arduino connection
                        while self.running:
                            time.sleep(5)  # Check every 5 seconds
                            
                            # Check if Arduino is still connected
                            if not self.serial or not self.serial.is_open:
                                logger.warning("Arduino disconnected")
                                self.stop_agent()
                                break
                            
                            # Monitor agent health
                            self.monitor_agent()
                    else:
                        logger.error("Failed to start agent, retrying...")
                        time.sleep(10)
                else:
                    # Connection failed
                    retry_count += 1
                    if retry_count >= max_retries:
                        logger.error("Max retries reached, waiting 60s before reset...")
                        time.sleep(60)
                        retry_count = 0
                    else:
                        logger.info(f"Retrying in 10s... ({retry_count}/{max_retries})")
                        time.sleep(10)
                    
            except KeyboardInterrupt:
                logger.info("Interrupted by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                time.sleep(10)
        
        # Cleanup
        self.stop_agent()
        if self.serial and self.serial.is_open:
            self.serial.close()
        
        logger.info("Arduino Ready Watcher stopped")

def main():
    """Entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Arduino Ready Watcher v2")
    parser.add_argument("--port", default=ARDUINO_PORT, help="Arduino serial port")
    parser.add_argument("--config", default=CONFIG_FILE, help="Agent config file")
    
    args = parser.parse_args()
    
    # Verify files exist
    if not AGENT_SCRIPT.exists():
        logger.error(f"Agent script not found: {AGENT_SCRIPT}")
        sys.exit(1)
    
    if not Path(args.config).exists():
        logger.error(f"Config file not found: {args.config}")
        sys.exit(1)
    
    # Start watcher
    watcher = ArduinoReadyWatcher(
        port=args.port,
        agent_script=AGENT_SCRIPT,
        config_file=Path(args.config)
    )
    
    watcher.run()

if __name__ == "__main__":
    main()
