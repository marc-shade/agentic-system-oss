#!/usr/bin/env python3
"""
Agentic Light Show - Arduino Visual Event Display

Syncs with the agentic event system to create a visual light show
using the Arduino's RGB LED and 16x2 LCD display.

Colors and patterns match the Roland-style sound system:
- DRUMS (TR-808): Fast flashes, warm colors
- BASS (TB-303): Pulsing, acid greens
- KEYBOARDS (Juno): Smooth fades, cool colors
"""

import serial
import time
import json
import sys
import threading
import queue
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Optional
from dataclasses import dataclass
from collections import deque

# Configuration
ARDUINO_PORT = "/dev/ttyACM0"
ARDUINO_BAUD = 115200
HTTP_PORT = 8768

# Event to visual mapping - colors as (R, G, B)
EVENT_VISUALS = {
    # === DRUMS - Warm, punchy colors ===
    'agent_spawn': {'color': (255, 100, 0), 'pattern': 'flash', 'lcd': 'AGENT SPAWN'},
    'agent_terminate': {'color': (100, 0, 100), 'pattern': 'fade', 'lcd': 'AGENT DONE'},
    'task_start': {'color': (0, 255, 100), 'pattern': 'pulse', 'lcd': 'TASK START'},
    'task_complete': {'color': (0, 255, 0), 'pattern': 'flash', 'lcd': 'TASK DONE'},
    'error': {'color': (255, 0, 0), 'pattern': 'strobe', 'lcd': '!! ERROR !!'},
    'warning': {'color': (255, 200, 0), 'pattern': 'pulse', 'lcd': 'WARNING'},
    'memory_store': {'color': (0, 100, 255), 'pattern': 'fade', 'lcd': 'MEM WRITE'},
    'memory_retrieve': {'color': (100, 200, 255), 'pattern': 'flash', 'lcd': 'MEM READ'},
    'api_call': {'color': (255, 255, 100), 'pattern': 'flash', 'lcd': 'API CALL'},
    'cluster_sync': {'color': (255, 0, 255), 'pattern': 'sweep', 'lcd': 'CLUSTER SYNC'},
    'health_check': {'color': (50, 50, 50), 'pattern': 'tick', 'lcd': 'HEALTH OK'},
    'heartbeat': {'color': (30, 0, 30), 'pattern': 'heartbeat', 'lcd': None},  # No LCD for heartbeat

    # === BASS - Acid greens and deep colors ===
    'workflow_start': {'color': (0, 255, 50), 'pattern': 'acid', 'lcd': 'WORKFLOW'},
    'workflow_end': {'color': (0, 100, 50), 'pattern': 'fade', 'lcd': 'FLOW DONE'},
    'ai_inference': {'color': (150, 255, 0), 'pattern': 'pulse', 'lcd': 'AI THINK'},
    'model_load': {'color': (200, 255, 100), 'pattern': 'sweep', 'lcd': 'MODEL LOAD'},
    'database_query': {'color': (0, 150, 100), 'pattern': 'flash', 'lcd': 'DB QUERY'},
    'mcp_call': {'color': (100, 255, 50), 'pattern': 'acid', 'lcd': 'MCP CALL'},
    'thinking': {'color': (50, 200, 100), 'pattern': 'pulse', 'lcd': 'THINKING...'},

    # === KEYBOARDS - Cool, smooth colors ===
    'session_start': {'color': (100, 150, 255), 'pattern': 'fade_in', 'lcd': 'SESSION START'},
    'session_end': {'color': (50, 50, 150), 'pattern': 'fade_out', 'lcd': 'SESSION END'},
    'success': {'color': (0, 255, 100), 'pattern': 'celebration', 'lcd': '** SUCCESS **'},
    'notification': {'color': (200, 200, 255), 'pattern': 'bell', 'lcd': 'NOTIFY'},
    'reasoning': {'color': (100, 100, 255), 'pattern': 'wave', 'lcd': 'REASONING'},
    'voice_activity': {'color': (255, 150, 200), 'pattern': 'pulse', 'lcd': 'VOICE'},
    'cluster_message': {'color': (255, 200, 100), 'pattern': 'flash', 'lcd': 'CLUSTER MSG'},
    'goal_achieved': {'color': (255, 255, 0), 'pattern': 'celebration', 'lcd': 'GOAL MET!'},
    'learning': {'color': (150, 100, 255), 'pattern': 'wave', 'lcd': 'LEARNING'},
}

# Default visual for unknown events
DEFAULT_VISUAL = {'color': (100, 100, 100), 'pattern': 'flash', 'lcd': 'EVENT'}


class ArduinoLightShow:
    """Controls Arduino RGB LED and LCD for visual event display."""

    def __init__(self, port: str = ARDUINO_PORT, baud: int = ARDUINO_BAUD):
        self.port = port
        self.baud = baud
        self.serial: Optional[serial.Serial] = None
        self.connected = False
        self.event_queue = queue.Queue()
        self.running = False
        self.current_color = (0, 0, 0)
        self.animation_thread = None
        self.stats = {'events': 0, 'errors': 0}
        self.last_lcd_update = 0
        self.lcd_min_interval = 0.3  # Minimum time between LCD updates

    def connect(self) -> bool:
        """Connect to Arduino."""
        try:
            self.serial = serial.Serial(self.port, self.baud, timeout=2)
            time.sleep(3)  # Wait for Arduino reset

            # Clear startup messages
            while self.serial.in_waiting:
                self.serial.readline()

            # Test connection
            self._send_command("PING")
            self.connected = True
            print(f"[OK] Connected to Arduino at {self.port}")

            # Show startup message
            self._send_command("CLEAR")
            self._send_command("LCD 0 0 AGENTIC LIGHT")
            self._send_command("LCD 1 0 SHOW READY!")
            self._send_command("LED 0 0 255 0")  # Green
            time.sleep(1)

            return True
        except Exception as e:
            print(f"[ERROR] Arduino connection failed: {e}")
            self.connected = False
            return False

    def _send_command(self, cmd: str) -> Optional[dict]:
        """Send command to Arduino."""
        if not self.serial:
            return None
        try:
            self.serial.write(f"{cmd}\n".encode())
            time.sleep(0.05)
            if self.serial.in_waiting:
                response = self.serial.readline().decode('utf-8', errors='ignore').strip()
                try:
                    return json.loads(response)
                except:
                    return {'raw': response}
            return {'status': 'ok'}
        except Exception as e:
            self.stats['errors'] += 1
            return None

    def set_led(self, r: int, g: int, b: int):
        """Set RGB LED color."""
        r, g, b = max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))
        self._send_command(f"LED 0 {r} {g} {b}")
        self.current_color = (r, g, b)

    def set_lcd(self, line1: str, line2: str = ""):
        """Set LCD text (16 chars per line)."""
        now = time.time()
        if now - self.last_lcd_update < self.lcd_min_interval:
            return
        self.last_lcd_update = now

        self._send_command("CLEAR")
        if line1:
            self._send_command(f"LCD 0 0 {line1[:16]}")
        if line2:
            self._send_command(f"LCD 1 0 {line2[:16]}")

    def flash(self, color: tuple, times: int = 1, duration: float = 0.1):
        """Flash LED."""
        r, g, b = color
        for _ in range(times):
            self.set_led(r, g, b)
            time.sleep(duration)
            self.set_led(0, 0, 0)
            time.sleep(duration / 2)

    def pulse(self, color: tuple, duration: float = 0.5):
        """Pulse LED (fade in and out)."""
        r, g, b = color
        steps = 10
        for i in range(steps):
            factor = i / steps
            self.set_led(int(r * factor), int(g * factor), int(b * factor))
            time.sleep(duration / steps / 2)
        for i in range(steps, 0, -1):
            factor = i / steps
            self.set_led(int(r * factor), int(g * factor), int(b * factor))
            time.sleep(duration / steps / 2)

    def strobe(self, color: tuple, times: int = 5):
        """Rapid strobe for errors."""
        r, g, b = color
        for _ in range(times):
            self.set_led(r, g, b)
            time.sleep(0.05)
            self.set_led(0, 0, 0)
            time.sleep(0.05)

    def show_char(self, row: int, col: int, char_index: int):
        """Display a custom character.

        Characters: 0=armsDown, 1=armsUp, 2=heart, 3=smiley,
                    4=thinking, 5=bolt, 6=wave, 7=check
        """
        self._send_command(f"CHAR {row} {col} {char_index}")

    def dance(self, duration_ms: int = 3000):
        """Run the dancing man animation."""
        self._send_command(f"DANCE START {duration_ms}")

    def celebration(self, base_color: tuple):
        """Celebration pattern for success with dancing man!"""
        # Show celebration text with heart
        self._send_command("CLEAR")
        self._send_command("LCD 0 0 ** SUCCESS **")
        self.show_char(0, 14, 2)  # Heart at end

        # Color celebration while dancing
        colors = [
            base_color,
            (255, 255, 0),
            (0, 255, 255),
            base_color,
        ]

        # Start dancing (non-blocking via thread)
        self._send_command("DANCE START 2000")

        # Flash colors during dance
        for color in colors:
            self.set_led(*color)
            time.sleep(0.4)

    def heartbeat(self):
        """Subtle heartbeat pulse."""
        # Very dim purple pulse
        for brightness in [10, 20, 30, 20, 10, 5]:
            self.set_led(brightness, 0, brightness)
            time.sleep(0.1)
        self.set_led(0, 0, 0)

    def trigger_event(self, action: str, source: str = "", extra: str = ""):
        """Trigger visual for an event."""
        self.stats['events'] += 1
        visual = EVENT_VISUALS.get(action, DEFAULT_VISUAL)

        color = visual['color']
        pattern = visual['pattern']
        lcd_text = visual.get('lcd')

        # Update LCD if text specified
        if lcd_text:
            line2 = source[:16] if source else extra[:16] if extra else ""
            self.set_lcd(lcd_text, line2)

            # Add special icons for certain events
            if action in ('thinking', 'ai_inference', 'reasoning'):
                self.show_char(0, 15, 4)  # Thinking face
            elif action == 'success':
                self.show_char(0, 15, 7)  # Checkmark
            elif action == 'goal_achieved':
                self.show_char(0, 15, 2)  # Heart
            elif action in ('mcp_call', 'api_call'):
                self.show_char(0, 15, 5)  # Lightning bolt
            elif action == 'learning':
                self.show_char(0, 15, 3)  # Smiley

        # Execute pattern
        if pattern == 'flash':
            self.flash(color)
        elif pattern == 'pulse':
            self.pulse(color, 0.3)
        elif pattern == 'strobe':
            self.strobe(color)
        elif pattern == 'celebration':
            self.celebration(color)
        elif pattern == 'heartbeat':
            self.heartbeat()
        elif pattern == 'fade':
            self.pulse(color, 0.5)
        elif pattern == 'acid':
            # Acid pattern: rapid green variations
            for _ in range(3):
                self.set_led(0, 255, 50)
                time.sleep(0.08)
                self.set_led(100, 255, 0)
                time.sleep(0.08)
        elif pattern == 'wave':
            # Smooth wave
            for i in range(20):
                factor = abs(10 - i) / 10
                self.set_led(int(color[0] * factor), int(color[1] * factor), int(color[2] * factor))
                time.sleep(0.03)
        elif pattern == 'sweep':
            # Color sweep
            self.set_led(color[0], 0, 0)
            time.sleep(0.1)
            self.set_led(0, color[1], 0)
            time.sleep(0.1)
            self.set_led(0, 0, color[2])
            time.sleep(0.1)
            self.set_led(*color)
            time.sleep(0.1)
        elif pattern == 'tick':
            # Quick tick for health checks
            self.set_led(*color)
            time.sleep(0.05)
            self.set_led(0, 0, 0)
        elif pattern == 'bell':
            # Bell pattern
            self.flash(color)
            time.sleep(0.1)
            self.flash((color[0]//2, color[1]//2, color[2]//2))
        elif pattern in ('fade_in', 'fade_out'):
            self.pulse(color, 0.8)
        else:
            self.flash(color)

        # Return to idle (dim)
        self.set_led(5, 0, 5)

    def start_http_server(self):
        """Start HTTP server for receiving events."""
        light_show = self

        class EventHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # Suppress logging

            def do_POST(self):
                if self.path == '/event':
                    content_length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(content_length).decode()
                    try:
                        data = json.loads(body)
                        action = data.get('action', '')
                        source = data.get('source', '')
                        extra = data.get('extra', '')
                        if action:
                            # Run in thread to not block
                            threading.Thread(
                                target=light_show.trigger_event,
                                args=(action, source, extra),
                                daemon=True
                            ).start()
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({'success': True}).encode())
                    except Exception as e:
                        self.send_response(400)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({'error': str(e)}).encode())
                else:
                    self.send_response(404)
                    self.end_headers()

            def do_GET(self):
                if self.path == '/health':
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'status': 'running',
                        'connected': light_show.connected,
                        'events_processed': light_show.stats['events'],
                        'errors': light_show.stats['errors']
                    }).encode())
                elif self.path == '/test':
                    # Test all patterns
                    threading.Thread(target=light_show.run_test_sequence, daemon=True).start()
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'status': 'test_started'}).encode())
                else:
                    self.send_response(404)
                    self.end_headers()

        server = HTTPServer(('0.0.0.0', HTTP_PORT), EventHandler)
        print(f"[OK] HTTP server listening on port {HTTP_PORT}")
        server.serve_forever()

    def run_test_sequence(self):
        """Run through all visual patterns."""
        self.set_lcd("TEST SEQUENCE", "STARTING...")
        time.sleep(1)

        test_events = [
            'agent_spawn', 'task_start', 'mcp_call', 'success',
            'error', 'heartbeat', 'cluster_sync', 'learning'
        ]

        for event in test_events:
            visual = EVENT_VISUALS.get(event, DEFAULT_VISUAL)
            lcd_text = visual.get('lcd') or ''
            self.set_lcd(f"TEST: {event[:10]}", lcd_text[:16])
            time.sleep(0.5)
            self.trigger_event(event, "test")
            time.sleep(0.5)

        self.set_lcd("TEST COMPLETE", "READY!")
        time.sleep(1)
        self.set_led(0, 255, 0)
        time.sleep(0.5)
        self.set_led(5, 0, 5)

    def run(self):
        """Main run loop."""
        if not self.connect():
            print("[ERROR] Cannot start - Arduino not connected")
            return

        self.running = True

        print("=" * 60)
        print("AGENTIC LIGHT SHOW - READY")
        print("=" * 60)
        print(f"  Arduino: {self.port}")
        print(f"  HTTP API: http://localhost:{HTTP_PORT}")
        print()
        print("  POST /event  - Trigger visual event")
        print("  GET  /health - Health check")
        print("  GET  /test   - Run test sequence")
        print("=" * 60)

        # Start HTTP server (blocks)
        self.start_http_server()


def main():
    light_show = ArduinoLightShow()
    try:
        light_show.run()
    except KeyboardInterrupt:
        print("\nShutting down...")
        if light_show.serial:
            light_show.set_lcd("LIGHT SHOW", "OFFLINE")
            light_show.set_led(0, 0, 0)
            light_show.serial.close()


if __name__ == "__main__":
    main()
