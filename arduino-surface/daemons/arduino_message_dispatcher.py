#!/usr/bin/env python3
"""
Arduino Message Dispatcher with Sound Integration

Central hub that collects information from ALL agentic systems and agents,
prioritizes messages, dispatches them to the Arduino display, AND triggers
Roland-style synthesizer sounds for different agentic actions.

Data Sources:
- KutiraAI Dashboard API (services, agents, health)
- Agentic Framework API (ecosystem status)
- Enhanced Memory MCP (memory status)
- Ember MCP (quality guardian status)
- Cluster Nodes (node heartbeats)
- Voice Mode (STT activity)
- Claude Code hooks (activity events)
- System health (CPU, memory, disk)

Output:
- Writes to /tmp/arduino-messages.json for the display agent to consume
- HTTP endpoint for external systems to submit messages
- Triggers sounds via Agentic Sound System (port 8766)
"""

import asyncio
import json
import time
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from collections import deque
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import subprocess


# Sound system integration
SOUND_SYSTEM_URL = "http://localhost:8766"


def trigger_sound(action: str):
    """Trigger a sound via the Agentic Sound System."""
    try:
        data = json.dumps({"action": action}).encode()
        req = urllib.request.Request(
            f"{SOUND_SYSTEM_URL}/action",
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        urllib.request.urlopen(req, timeout=1)
    except Exception:
        pass  # Don't block on sound failures


@dataclass
class ArduinoMessage:
    """A message to display on Arduino."""
    id: str
    source: str  # Source system (kutiraai, ember, memory, cluster, etc.)
    priority: int  # 0=critical, 1=warning, 2=info, 3=background
    headline: str  # Line 1 (16 chars max for LCD)
    detail: str    # Line 2 (16 chars max for LCD)
    led_color: tuple = (0, 255, 0)  # RGB color
    audio_alert: bool = False
    ttl: int = 30  # Time to live in seconds
    timestamp: float = field(default_factory=time.time)

    def to_dict(self):
        return asdict(self)

    def is_expired(self):
        return time.time() - self.timestamp > self.ttl


class DataSource:
    """Base class for data sources."""

    def __init__(self, name: str, url: str, interval: int = 10):
        self.name = name
        self.url = url
        self.interval = interval
        self.last_data = None
        self.last_fetch = 0
        self.error_count = 0

    async def fetch(self) -> Optional[Dict]:
        """Fetch data from source."""
        try:
            req = urllib.request.Request(self.url, headers={'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                self.last_data = data
                self.last_fetch = time.time()
                self.error_count = 0
                return data
        except Exception as e:
            self.error_count += 1
            return None

    def generate_messages(self, data: Dict) -> List[ArduinoMessage]:
        """Generate messages from data. Override in subclasses."""
        return []


class KutiraAISource(DataSource):
    """KutiraAI Dashboard stats."""

    def __init__(self):
        super().__init__("kutiraai", "http://localhost:3002/api/dashboard/stats", 10)

    def generate_messages(self, data: Dict) -> List[ArduinoMessage]:
        messages = []
        if not data or not data.get('success'):
            return messages

        stats = data.get('stats', {})
        services = stats.get('services', [])
        total = len(services)
        running = len([s for s in services if s.get('status') == 'active'])

        # Only generate message if status changed significantly
        pct = round((running / total * 100) if total > 0 else 0)

        if pct < 80:
            messages.append(ArduinoMessage(
                id=f"kutiraai_health_{int(time.time())}",
                source="kutiraai",
                priority=1 if pct < 50 else 2,
                headline=f"SERVICES {pct}%",
                detail=f"{running}/{total} ACTIVE",
                led_color=(255, 165, 0) if pct >= 50 else (255, 0, 0),
                ttl=30
            ))

        return messages


class AgenticFrameworkSource(DataSource):
    """Agentic Framework ecosystem status."""

    def __init__(self):
        super().__init__("agentic", "http://localhost:4100/api/v1/ecosystem/overview", 10)

    def generate_messages(self, data: Dict) -> List[ArduinoMessage]:
        messages = []
        if not data:
            return messages

        # Check agent count
        agents = data.get('agents', {})
        active_count = agents.get('active', 0)

        if active_count > 0:
            messages.append(ArduinoMessage(
                id=f"agents_active_{int(time.time())}",
                source="agentic",
                priority=3,
                headline="AGENTS ACTIVE",
                detail=f"{active_count} RUNNING",
                led_color=(0, 255, 128),
                ttl=15
            ))

        # Check for alerts
        alerts = data.get('alerts', [])
        for alert in alerts[:3]:  # Only first 3 alerts
            severity = alert.get('severity', 'info')
            messages.append(ArduinoMessage(
                id=f"alert_{alert.get('id', int(time.time()))}",
                source="agentic",
                priority=0 if severity == 'critical' else 1 if severity == 'warning' else 2,
                headline=alert.get('title', 'ALERT')[:16],
                detail=alert.get('message', '')[:16],
                led_color=(255, 0, 0) if severity == 'critical' else (255, 165, 0),
                audio_alert=severity == 'critical',
                ttl=60
            ))

        return messages


class EmberSource(DataSource):
    """Ember quality guardian status."""

    def __init__(self):
        super().__init__("ember", "http://localhost:8300/mcp/ember_get_mood", 30)

    def generate_messages(self, data: Dict) -> List[ArduinoMessage]:
        messages = []
        if not data:
            return messages

        mood = data.get('mood', 'neutral')
        quality_score = data.get('averageQualityScore', 0)

        # Only show if mood is notable
        if mood in ['frustrated', 'concerned', 'delighted']:
            emoji = {'frustrated': ':(', 'concerned': '!?', 'delighted': ':)'}
            messages.append(ArduinoMessage(
                id=f"ember_mood_{int(time.time())}",
                source="ember",
                priority=2 if mood != 'delighted' else 3,
                headline=f"EMBER {emoji.get(mood, '')}",
                detail=f"QUALITY: {quality_score}%",
                led_color=(255, 0, 0) if mood == 'frustrated' else (255, 165, 0) if mood == 'concerned' else (0, 255, 0),
                ttl=45
            ))

        return messages


class MemorySource(DataSource):
    """Enhanced Memory MCP status."""

    def __init__(self):
        super().__init__("memory", "http://localhost:4002/mcp/get_memory_status", 30)

    def generate_messages(self, data: Dict) -> List[ArduinoMessage]:
        messages = []
        if not data:
            return messages

        total_memories = data.get('total_entities', 0)

        # Show memory count periodically
        if total_memories > 0:
            messages.append(ArduinoMessage(
                id=f"memory_count_{int(time.time())}",
                source="memory",
                priority=3,
                headline="MEMORIES",
                detail=f"{total_memories} STORED",
                led_color=(128, 0, 255),
                ttl=60
            ))

        return messages


class ClusterSource(DataSource):
    """Cluster node status."""

    def __init__(self):
        super().__init__("cluster", "http://localhost:4100/api/v1/cluster/nodes", 15)

    def generate_messages(self, data: Dict) -> List[ArduinoMessage]:
        messages = []
        if not data:
            return messages

        nodes = data.get('nodes', [])
        online = len([n for n in nodes if n.get('status') == 'online'])
        total = len(nodes)

        if total > 0 and online < total:
            messages.append(ArduinoMessage(
                id=f"cluster_nodes_{int(time.time())}",
                source="cluster",
                priority=1 if online < total / 2 else 2,
                headline="CLUSTER",
                detail=f"{online}/{total} ONLINE",
                led_color=(255, 165, 0) if online < total else (0, 255, 0),
                ttl=30
            ))

        return messages


class SystemHealthSource(DataSource):
    """Local system health (CPU, Memory)."""

    def __init__(self):
        super().__init__("system", "", 10)

    async def fetch(self) -> Optional[Dict]:
        """Get system stats locally."""
        try:
            # Get CPU usage
            cpu_result = subprocess.run(
                ['top', '-l', '1', '-n', '0'],
                capture_output=True, text=True, timeout=5
            )
            cpu_line = [l for l in cpu_result.stdout.split('\n') if 'CPU usage' in l]
            cpu_idle = 100
            if cpu_line:
                import re
                match = re.search(r'(\d+\.?\d*)% idle', cpu_line[0])
                if match:
                    cpu_idle = float(match.group(1))

            cpu_usage = round(100 - cpu_idle)

            # Get memory (macOS)
            mem_result = subprocess.run(
                ['vm_stat'],
                capture_output=True, text=True, timeout=5
            )

            self.last_data = {'cpu_usage': cpu_usage}
            self.last_fetch = time.time()
            return self.last_data
        except:
            return None

    def generate_messages(self, data: Dict) -> List[ArduinoMessage]:
        messages = []
        if not data:
            return messages

        cpu = data.get('cpu_usage', 0)

        if cpu > 80:
            messages.append(ArduinoMessage(
                id=f"cpu_high_{int(time.time())}",
                source="system",
                priority=1 if cpu > 90 else 2,
                headline="HIGH CPU",
                detail=f"{cpu}% USAGE",
                led_color=(255, 0, 0) if cpu > 90 else (255, 165, 0),
                ttl=15
            ))

        return messages


class ArduinoMessageDispatcher:
    """Main dispatcher that collects and manages messages."""

    def __init__(self, output_file: str = '/tmp/arduino-messages.json'):
        self.output_file = output_file
        self.message_queue: deque = deque(maxlen=100)  # Rolling buffer
        self.current_messages: List[ArduinoMessage] = []
        self.running = False

        # Data sources
        self.sources = [
            KutiraAISource(),
            AgenticFrameworkSource(),
            EmberSource(),
            MemorySource(),
            ClusterSource(),
            SystemHealthSource(),
        ]

        # HTTP server for external submissions
        self.http_server = None
        self.http_port = 8765

    def add_message(self, message: ArduinoMessage):
        """Add a message to the queue."""
        self.message_queue.append(message)

    def get_current_message(self) -> Optional[ArduinoMessage]:
        """Get highest priority non-expired message."""
        # Clean expired messages
        self.current_messages = [m for m in self.current_messages if not m.is_expired()]

        # Add new messages from queue
        while self.message_queue:
            msg = self.message_queue.popleft()
            if not msg.is_expired():
                self.current_messages.append(msg)

        if not self.current_messages:
            return None

        # Sort by priority (lower is higher priority)
        self.current_messages.sort(key=lambda m: (m.priority, -m.timestamp))
        return self.current_messages[0]

    def write_output(self):
        """Write current messages to output file."""
        msg = self.get_current_message()

        output = {
            'timestamp': datetime.now().isoformat(),
            'current_message': msg.to_dict() if msg else None,
            'queue_size': len(self.current_messages),
            'sources_status': {
                s.name: {
                    'last_fetch': s.last_fetch,
                    'error_count': s.error_count
                } for s in self.sources
            }
        }

        try:
            with open(self.output_file, 'w') as f:
                json.dump(output, f, indent=2)
        except Exception as e:
            print(f"Error writing output: {e}")

    async def poll_sources(self):
        """Poll all data sources and generate messages."""
        for source in self.sources:
            # Check if it's time to fetch
            if time.time() - source.last_fetch >= source.interval:
                try:
                    data = await source.fetch()
                    if data:
                        messages = source.generate_messages(data)
                        for msg in messages:
                            self.add_message(msg)
                except Exception as e:
                    print(f"Error polling {source.name}: {e}")

    def start_http_server(self):
        """Start HTTP server for external message submissions."""
        dispatcher = self

        class MessageHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path == '/message':
                    content_length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(content_length).decode()
                    try:
                        data = json.loads(body)
                        msg = ArduinoMessage(
                            id=data.get('id', f"external_{int(time.time())}"),
                            source=data.get('source', 'external'),
                            priority=data.get('priority', 2),
                            headline=data.get('headline', 'MESSAGE')[:16],
                            detail=data.get('detail', '')[:16],
                            led_color=tuple(data.get('led_color', [0, 255, 0])),
                            audio_alert=data.get('audio_alert', False),
                            ttl=data.get('ttl', 30)
                        )
                        dispatcher.add_message(msg)
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({'success': True}).encode())
                    except Exception as e:
                        self.send_response(400)
                        self.end_headers()
                        self.wfile.write(json.dumps({'error': str(e)}).encode())
                else:
                    self.send_response(404)
                    self.end_headers()

            def do_GET(self):
                if self.path == '/status':
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    msg = dispatcher.get_current_message()
                    self.wfile.write(json.dumps({
                        'current_message': msg.to_dict() if msg else None,
                        'queue_size': len(dispatcher.current_messages)
                    }).encode())
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, format, *args):
                pass  # Suppress logging

        def run_server():
            self.http_server = HTTPServer(('0.0.0.0', self.http_port), MessageHandler)
            self.http_server.serve_forever()

        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        print(f"HTTP server started on port {self.http_port}")

    async def run(self):
        """Main run loop."""
        self.running = True

        # Start HTTP server
        self.start_http_server()

        print("Arduino Message Dispatcher started")
        print(f"Output file: {self.output_file}")
        print(f"HTTP endpoint: http://localhost:{self.http_port}/message")
        print(f"Sources: {', '.join(s.name for s in self.sources)}")
        print("")

        # Initial idle message
        self.add_message(ArduinoMessage(
            id="startup",
            source="dispatcher",
            priority=3,
            headline="AGENTIC SYS",
            detail="READY",
            led_color=(0, 255, 0),
            ttl=10
        ))

        while self.running:
            try:
                # Poll all sources
                await self.poll_sources()

                # Write current state
                self.write_output()

                # Small delay between cycles
                await asyncio.sleep(2)

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                await asyncio.sleep(5)

        print("Dispatcher stopped")


async def main():
    dispatcher = ArduinoMessageDispatcher()
    await dispatcher.run()


if __name__ == '__main__':
    asyncio.run(main())
