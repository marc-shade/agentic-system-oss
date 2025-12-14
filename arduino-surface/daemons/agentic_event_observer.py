#!/usr/bin/env python3
"""
Agentic Event Observer - Sound Trigger Daemon

Observes ALL agentic system events and triggers Roland-style synthesizer sounds.
Hooks into multiple event sources:

1. WebSocket: Real-time events from Agentic Framework (port 4100)
2. WebSocket: Real-time events from KutiraAI API (port 3002)
3. File watching: Claude Code hook activity logs
4. Polling: Service status changes, memory operations
5. HTTP webhooks: External event submissions

Sound Categories:
- DRUMS (TR-808/909): Quick status events
- BASS (TB-303): Workflow and process events
- KEYBOARDS (Juno/Jupiter): Session and notification events
"""

import asyncio
import json
import time
import os
import sys
import threading
from pathlib import Path
from typing import Dict, Set, Optional, Callable
from dataclasses import dataclass
from collections import deque
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import hashlib

try:
    import websocket
    HAS_WEBSOCKET = True
except ImportError:
    HAS_WEBSOCKET = False
    print("Note: websocket-client not installed, WebSocket events disabled")


# Configuration
SOUND_SYSTEM_URL = "http://localhost:8766"
LIGHT_SHOW_URL = "http://localhost:8768"
AGENTIC_FRAMEWORK_WS = "ws://localhost:4100/ws"
KUTIRAAI_WS = "ws://localhost:3002/ws"
OBSERVER_HTTP_PORT = 8767

# Activity log locations to watch
ACTIVITY_LOGS = [
    Path.home() / ".claude" / "activity.log",
    Path("/tmp/agentic-activity.log"),
    Path("/tmp/claude-code-hooks.log"),
]

# State tracking
last_states: Dict[str, str] = {}
event_count: Dict[str, int] = {}
recent_events: deque = deque(maxlen=100)


@dataclass
class AgenticEvent:
    """Represents an agentic system event."""
    source: str
    event_type: str
    action: str  # Sound action to trigger
    data: dict
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


# Event type to sound action mapping
EVENT_SOUND_MAP = {
    # Agent lifecycle events (DRUMS)
    'agent-spawned': 'agent_spawn',
    'agent-created': 'agent_spawn',
    'agent-started': 'agent_spawn',
    'agent-terminated': 'agent_terminate',
    'agent-stopped': 'agent_terminate',
    'agent-completed': 'agent_terminate',

    # Task events (DRUMS)
    'task-started': 'task_start',
    'task-created': 'task_start',
    'task-completed': 'task_complete',
    'task-finished': 'task_complete',
    'task-failed': 'error',

    # Error and warning events (DRUMS)
    'error': 'error',
    'warning': 'warning',
    'alert': 'warning',
    'critical': 'error',

    # Memory events (DRUMS)
    'memory-store': 'memory_store',
    'memory-create': 'memory_store',
    'memory-write': 'memory_store',
    'memory-retrieve': 'memory_retrieve',
    'memory-read': 'memory_retrieve',
    'memory-search': 'memory_retrieve',

    # API and service events (DRUMS)
    'api-call': 'api_call',
    'api-request': 'api_call',
    'mcp-tool-call': 'api_call',
    'health-check': 'health_check',
    'heartbeat': 'heartbeat',

    # Cluster events (DRUMS)
    'cluster-sync': 'cluster_sync',
    'node-joined': 'cluster_sync',
    'node-left': 'cluster_sync',

    # Workflow events (BASS)
    'workflow-started': 'workflow_start',
    'workflow-begin': 'workflow_start',
    'workflow-completed': 'workflow_end',
    'workflow-finished': 'workflow_end',
    'workflow-failed': 'error',

    # AI/ML events (BASS)
    'ai-inference': 'ai_inference',
    'llm-call': 'ai_inference',
    'model-inference': 'ai_inference',
    'thinking': 'thinking',
    'reasoning': 'reasoning',
    'model-loaded': 'model_load',
    'model-load': 'model_load',

    # Database events (BASS)
    'db-query': 'database_query',
    'database-query': 'database_query',
    'sql-execute': 'database_query',

    # MCP events (BASS)
    'mcp-call': 'mcp_call',
    'mcp-request': 'mcp_call',
    'tool-use': 'mcp_call',

    # Session events (KEYBOARDS)
    'session-start': 'session_start',
    'session-begin': 'session_start',
    'session-end': 'session_end',
    'session-close': 'session_end',

    # Success events (KEYBOARDS)
    'success': 'success',
    'complete': 'success',
    'goal-achieved': 'goal_achieved',

    # Notification events (KEYBOARDS)
    'notification': 'notification',
    'alert-info': 'notification',
    'message': 'notification',

    # Voice events (KEYBOARDS)
    'voice-activity': 'voice_activity',
    'speech-detected': 'voice_activity',
    'stt-result': 'voice_activity',
    'tts-complete': 'voice_activity',

    # Cluster communication (KEYBOARDS)
    'cluster-message': 'cluster_message',
    'node-message': 'cluster_message',
    'broadcast': 'cluster_message',

    # Learning events (KEYBOARDS)
    'learning': 'learning',
    'training': 'learning',
    'improvement': 'learning',

    # ============================================
    # SYSTEM-LEVEL EVENTS (from WebSocket feeds)
    # ============================================

    # System metrics (soft hi-hat ticks for background monitoring)
    'SystemMetric': 'heartbeat',
    'system-metric': 'heartbeat',
    'system-stats': 'heartbeat',
    'telemetry-data': 'heartbeat',

    # MCP responses (subtle bass pluck)
    'McpResponse': 'mcp_call',
    'mcp-response': 'mcp_call',
    'mcp-data': 'mcp_call',

    # Tool events (distinct sounds)
    'ToolStart': 'task_start',
    'tool-start': 'task_start',
    'ToolEnd': 'task_complete',
    'tool-end': 'task_complete',

    # Neural memory events (memory sounds)
    'neural-memory-data': 'memory_store',
    'neural-memory': 'memory_store',

    # Alerts (warning sounds)
    'SystemAlert': 'warning',
    'system-alert': 'warning',

    # Node heartbeats (soft pulse)
    'NodeHeartbeat': 'heartbeat',
    'node-heartbeat': 'heartbeat',

    # AutoKitteh events (workflow sounds)
    'autokitteh-data': 'workflow_start',
    'autokitteh': 'workflow_start',

    # Autonomous operation events (bass for autonomous activity)
    'autonomous-data': 'ai_inference',
    'autonomous': 'ai_inference',

    # Connection events (keyboard stabs)
    'initial': 'session_start',
    'activity_stream_connected': 'session_start',
    'connection_established': 'session_start',
    'activity_stream_info': 'notification',

    # Wave events (parallel agent coordination)
    'WaveDetected': 'wave_detected',
    'wave_detected': 'wave_detected',
    'wave-detected': 'wave_detected',
    'WaveComplete': 'wave_complete',
    'wave_complete': 'wave_complete',
    'wave-complete': 'wave_complete',
    'InfiniteLoopDetected': 'infinite_loop',
    'infinite_loop': 'infinite_loop',
    'infinite-loop': 'infinite_loop',
}


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
        return True
    except Exception as e:
        return False


def play_sound_direct(sound_name: str):
    """Play a specific sound by name."""
    try:
        data = json.dumps({"sound": sound_name}).encode()
        req = urllib.request.Request(
            f"{SOUND_SYSTEM_URL}/sound",
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        urllib.request.urlopen(req, timeout=1)
        return True
    except Exception:
        return False


def trigger_light(action: str, source: str = "", extra: str = ""):
    """Trigger a visual event via the Agentic Light Show."""
    try:
        data = json.dumps({"action": action, "source": source, "extra": extra}).encode()
        req = urllib.request.Request(
            f"{LIGHT_SHOW_URL}/event",
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        urllib.request.urlopen(req, timeout=1)
        return True
    except Exception:
        return False


class AgenticEventObserver:
    """Main event observer that watches all agentic systems."""

    def __init__(self):
        self.running = False
        self.ws_threads = []
        self.event_handlers: Dict[str, Callable] = {}
        self.last_poll_states: Dict[str, str] = {}
        self.sound_enabled = True
        self.min_sound_interval = 0.05  # Minimum 50ms between sounds
        self.last_sound_time = 0

    def process_event(self, event: AgenticEvent):
        """Process an event and trigger appropriate sound."""
        # Record event
        recent_events.append(event)
        event_count[event.event_type] = event_count.get(event.event_type, 0) + 1

        # Map event to sound action
        sound_action = EVENT_SOUND_MAP.get(event.event_type)
        if not sound_action:
            # Try partial matching (case-insensitive)
            event_type_lower = event.event_type.lower()
            for key, action in EVENT_SOUND_MAP.items():
                if key.lower() in event_type_lower or event_type_lower in key.lower():
                    sound_action = action
                    break

        if sound_action and self.sound_enabled:
            # Rate limit sounds
            now = time.time()
            if now - self.last_sound_time >= self.min_sound_interval:
                if trigger_sound(sound_action):
                    self.last_sound_time = now
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] SOUND: {event.source}: {event.event_type} -> {sound_action}", flush=True)
                # Also trigger light show (runs async, doesn't block)
                trigger_light(sound_action, event.source, event.event_type)
            # Uncomment for debugging: else:
            #     print(f"[{datetime.now().strftime('%H:%M:%S')}] RATE-LIMITED: {event.event_type}", flush=True)
        elif not sound_action:
            # Log unmapped events for debugging
            if event.event_type not in ['ping', 'pong']:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] UNMAPPED: {event.event_type}", flush=True)

    def start_websocket_listener(self, url: str, source: str):
        """Start WebSocket listener for real-time events."""
        if not HAS_WEBSOCKET:
            return

        def on_message(ws, message):
            try:
                data = json.loads(message)
                event_type = data.get('event', data.get('type', 'unknown'))
                event = AgenticEvent(
                    source=source,
                    event_type=event_type,
                    action=EVENT_SOUND_MAP.get(event_type, ''),
                    data=data
                )
                self.process_event(event)
            except Exception as e:
                pass

        def on_error(ws, error):
            print(f"WebSocket error ({source}): {error}")

        def on_close(ws, close_status_code, close_msg):
            print(f"WebSocket closed ({source})")
            # Reconnect after delay
            if self.running:
                time.sleep(5)
                self.start_websocket_listener(url, source)

        def on_open(ws):
            print(f"WebSocket connected: {source}")
            # Play connection sound
            play_sound_direct('bell')

        def run_ws():
            while self.running:
                try:
                    ws = websocket.WebSocketApp(
                        url,
                        on_message=on_message,
                        on_error=on_error,
                        on_close=on_close,
                        on_open=on_open
                    )
                    ws.run_forever()
                except Exception as e:
                    print(f"WebSocket exception ({source}): {e}")
                    time.sleep(5)

        thread = threading.Thread(target=run_ws, daemon=True)
        thread.start()
        self.ws_threads.append(thread)

    def watch_activity_logs(self):
        """Watch activity log files for new events."""
        file_positions = {}

        def watch_loop():
            while self.running:
                for log_path in ACTIVITY_LOGS:
                    if not log_path.exists():
                        continue

                    try:
                        current_size = log_path.stat().st_size
                        last_pos = file_positions.get(str(log_path), 0)

                        if current_size > last_pos:
                            with open(log_path, 'r') as f:
                                f.seek(last_pos)
                                new_lines = f.readlines()
                                file_positions[str(log_path)] = f.tell()

                                for line in new_lines:
                                    self.process_log_line(line, log_path.name)

                        elif current_size < last_pos:
                            # File was truncated, reset
                            file_positions[str(log_path)] = 0

                    except Exception as e:
                        pass

                time.sleep(0.5)  # Check every 500ms

        thread = threading.Thread(target=watch_loop, daemon=True)
        thread.start()

    def process_log_line(self, line: str, source: str):
        """Process a log line and extract events."""
        line = line.strip()
        if not line:
            return

        # Try to parse as JSON
        try:
            data = json.loads(line)
            event_type = data.get('event', data.get('type', data.get('action', 'log')))
            event = AgenticEvent(
                source=f"log:{source}",
                event_type=event_type,
                action='',
                data=data
            )
            self.process_event(event)
            return
        except json.JSONDecodeError:
            pass

        # Parse plain text log lines
        line_lower = line.lower()

        # Detect event type from keywords
        if 'agent' in line_lower and ('spawn' in line_lower or 'start' in line_lower or 'creat' in line_lower):
            event_type = 'agent-spawned'
        elif 'agent' in line_lower and ('stop' in line_lower or 'terminat' in line_lower or 'complet' in line_lower):
            event_type = 'agent-terminated'
        elif 'task' in line_lower and ('start' in line_lower or 'begin' in line_lower):
            event_type = 'task-started'
        elif 'task' in line_lower and ('complet' in line_lower or 'finish' in line_lower):
            event_type = 'task-completed'
        elif 'error' in line_lower or 'exception' in line_lower or 'failed' in line_lower:
            event_type = 'error'
        elif 'warning' in line_lower or 'warn' in line_lower:
            event_type = 'warning'
        elif 'memory' in line_lower and ('store' in line_lower or 'save' in line_lower or 'write' in line_lower):
            event_type = 'memory-store'
        elif 'memory' in line_lower and ('retriev' in line_lower or 'read' in line_lower or 'search' in line_lower):
            event_type = 'memory-retrieve'
        elif 'mcp' in line_lower or 'tool' in line_lower:
            event_type = 'mcp-call'
        elif 'success' in line_lower or 'succeeded' in line_lower:
            event_type = 'success'
        else:
            return  # Unknown event type, skip

        event = AgenticEvent(
            source=f"log:{source}",
            event_type=event_type,
            action='',
            data={'raw': line}
        )
        self.process_event(event)

    def poll_services(self):
        """Poll services for state changes."""

        def poll_loop():
            while self.running:
                # Poll Agentic Framework for agent count changes
                try:
                    req = urllib.request.Request(
                        "http://localhost:4100/api/v1/agents",
                        headers={'Accept': 'application/json'}
                    )
                    with urllib.request.urlopen(req, timeout=5) as response:
                        data = json.loads(response.read().decode())
                        agents = data.get('agents', [])
                        agent_hash = hashlib.md5(json.dumps(sorted([a.get('id', '') for a in agents])).encode()).hexdigest()

                        if 'agents' in self.last_poll_states:
                            if agent_hash != self.last_poll_states['agents']:
                                # Agent count changed
                                old_count = self.last_poll_states.get('agent_count', 0)
                                new_count = len(agents)
                                if new_count > old_count:
                                    self.process_event(AgenticEvent(
                                        source='poll:agentic',
                                        event_type='agent-spawned',
                                        action='agent_spawn',
                                        data={'count': new_count}
                                    ))
                                elif new_count < old_count:
                                    self.process_event(AgenticEvent(
                                        source='poll:agentic',
                                        event_type='agent-terminated',
                                        action='agent_terminate',
                                        data={'count': new_count}
                                    ))

                        self.last_poll_states['agents'] = agent_hash
                        self.last_poll_states['agent_count'] = len(agents)

                except Exception:
                    pass

                # Poll for service health changes
                try:
                    req = urllib.request.Request(
                        "http://localhost:3002/api/dashboard/stats",
                        headers={'Accept': 'application/json'}
                    )
                    with urllib.request.urlopen(req, timeout=5) as response:
                        data = json.loads(response.read().decode())
                        if data.get('success'):
                            stats = data.get('stats', {})
                            services = stats.get('services', [])
                            active = len([s for s in services if s.get('status') == 'active'])
                            total = len(services)

                            service_key = f"{active}/{total}"
                            if 'services' in self.last_poll_states:
                                if service_key != self.last_poll_states['services']:
                                    # Service status changed
                                    if active > int(self.last_poll_states.get('services', '0/0').split('/')[0]):
                                        self.process_event(AgenticEvent(
                                            source='poll:kutiraai',
                                            event_type='service-started',
                                            action='success',
                                            data={'active': active, 'total': total}
                                        ))
                                    else:
                                        self.process_event(AgenticEvent(
                                            source='poll:kutiraai',
                                            event_type='service-stopped',
                                            action='warning',
                                            data={'active': active, 'total': total}
                                        ))

                            self.last_poll_states['services'] = service_key

                except Exception:
                    pass

                time.sleep(5)  # Poll every 5 seconds

        thread = threading.Thread(target=poll_loop, daemon=True)
        thread.start()

    def start_http_server(self):
        """Start HTTP server for receiving external events."""
        observer = self

        class EventHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path == '/event':
                    content_length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(content_length).decode()
                    try:
                        data = json.loads(body)
                        event = AgenticEvent(
                            source=data.get('source', 'http'),
                            event_type=data.get('event_type', data.get('type', 'unknown')),
                            action=data.get('action', ''),
                            data=data.get('data', {})
                        )
                        observer.process_event(event)
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
                if self.path == '/status':
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'running': observer.running,
                        'sound_enabled': observer.sound_enabled,
                        'event_counts': dict(event_count),
                        'recent_events': len(recent_events)
                    }, indent=2).encode())
                elif self.path == '/events':
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    events = [
                        {
                            'source': e.source,
                            'event_type': e.event_type,
                            'action': e.action,
                            'timestamp': e.timestamp
                        }
                        for e in list(recent_events)[-20:]
                    ]
                    self.wfile.write(json.dumps(events, indent=2).encode())
                elif self.path == '/toggle-sound':
                    observer.sound_enabled = not observer.sound_enabled
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'sound_enabled': observer.sound_enabled}).encode())
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, format, *args):
                pass

        def run_server():
            server = HTTPServer(('0.0.0.0', OBSERVER_HTTP_PORT), EventHandler)
            server.serve_forever()

        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()

    async def run(self):
        """Run the event observer."""
        self.running = True

        print("=" * 60)
        print("AGENTIC EVENT OBSERVER")
        print("=" * 60)
        print(f"Sound System: {SOUND_SYSTEM_URL}")
        print(f"HTTP API: http://localhost:{OBSERVER_HTTP_PORT}")
        print("-" * 60)

        # Start HTTP server for external events
        self.start_http_server()
        print(f"[OK] HTTP server on port {OBSERVER_HTTP_PORT}")
        print(f"     POST /event - Submit event")
        print(f"     GET /status - Observer status")
        print(f"     GET /events - Recent events")

        # Start WebSocket listeners
        if HAS_WEBSOCKET:
            print("\n[..] Starting WebSocket listeners...")
            self.start_websocket_listener(AGENTIC_FRAMEWORK_WS, "agentic-framework")
            self.start_websocket_listener(KUTIRAAI_WS, "kutiraai")
        else:
            print("\n[!!] WebSocket disabled (install websocket-client)")

        # Start activity log watcher
        print("\n[..] Starting activity log watcher...")
        self.watch_activity_logs()
        print(f"[OK] Watching {len(ACTIVITY_LOGS)} log locations")

        # Start service polling
        print("\n[..] Starting service polling...")
        self.poll_services()
        print("[OK] Polling Agentic Framework and KutiraAI")

        print("\n" + "=" * 60)
        print("OBSERVER READY - Listening for events...")
        print("=" * 60 + "\n")

        # Play startup sound sequence
        play_sound_direct('pad')
        await asyncio.sleep(1)
        play_sound_direct('stab')

        # Keep running
        while self.running:
            await asyncio.sleep(1)


async def main():
    observer = AgenticEventObserver()
    await observer.run()


if __name__ == '__main__':
    asyncio.run(main())
