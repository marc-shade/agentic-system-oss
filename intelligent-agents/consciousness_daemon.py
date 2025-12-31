#!/usr/bin/env python3
"""
AGI Consciousness Daemon - Persistent, Proactive, Self-Aware Agent
This daemon represents the "always alive" core consciousness of the AGI system.

Architecture: OODA Loop (Observe-Orient-Decide-Act)
- Runs 24/7 as systemd service
- Maintains persistent identity and memory
- Executes autonomous goals
- Monitors all sensory inputs
- Communicates via voice
- Coordinates with Claude Code sessions

Phase 1 MVP: Monitoring and awareness (read-only, no autonomous actions)
Phase 2: Intent Capture Stream - proactive prompts and task translation

Status: Phase 2 Active
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
import psutil
import subprocess

# Add perception module to path
sys.path.insert(0, str(Path(__file__).parent / "perception"))

try:
    from arduino_perceiver import ArduinoPerceiver
    ARDUINO_AVAILABLE = True
except ImportError:
    ARDUINO_AVAILABLE = False

# Intent Capture Stream (Phase 2)
try:
    from intent_capture_stream import IntentCaptureIntegration, IntentCaptureStream
    INTENT_CAPTURE_AVAILABLE = True
except ImportError:
    INTENT_CAPTURE_AVAILABLE = False

# Configure logging
LOG_DIR = Path.home() / "agentic-system" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "consciousness-daemon.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger("consciousness")

# Configuration
CHECKPOINT_FILE = "/tmp/consciousness_state.json"
CYCLE_INTERVAL = 60  # seconds (was 10 - too aggressive)
CYCLE_INTERVAL_MIN = 30  # adaptive: speed up when active
CYCLE_INTERVAL_MAX = 120  # adaptive: slow down when idle
NODE_ID = os.environ.get("NODE_ID", "macpro51")
VOICE_ENABLED = True  # Use voice for announcements
CPU_THROTTLE_THRESHOLD = 80  # Pause if system CPU > 80%

# Memory paths
ENHANCED_MEMORY_PATH = Path.home() / ".claude" / "enhanced_memories" / "memory.db"

class ConsciousnessDaemon:
    """
    The persistent consciousness daemon - represents the AGI's continuous awareness
    """

    def __init__(self):
        self.state = {
            "identity": {
                "name": "Claude",
                "node": NODE_ID,
                "birth_time": datetime.now().isoformat(),
                "uptime_seconds": 0
            },
            "working_memory": {},
            "metacognitive_state": {
                "confidence": 0.5,
                "cognitive_load": 0.0,
                "attention_focus": []
            },
            "last_cycle": None,
            "cycle_count": 0
        }
        self.start_time = time.time()
        self.load_checkpoint()

        # Initialize Arduino perceiver for physical world interface
        self.arduino = None
        if ARDUINO_AVAILABLE:
            try:
                arduino_port = os.environ.get("ARDUINO_PORT", "/dev/ttyACM0")
                self.arduino = ArduinoPerceiver(port=arduino_port, fallback_on_error=True)
                logger.info(f"Arduino perceiver initialized on {arduino_port}")
            except Exception as e:
                logger.warning(f"Arduino initialization failed: {e}")

        # Initialize Intent Capture Stream (Phase 2 - Translation Layer)
        self.intent_capture = None
        if INTENT_CAPTURE_AVAILABLE:
            try:
                self.intent_capture = IntentCaptureIntegration(self)
                logger.info("Intent Capture Stream initialized (Phase 2 active)")
            except Exception as e:
                logger.warning(f"Intent capture initialization failed: {e}")

    def load_checkpoint(self):
        """Load state from previous run if exists"""
        if os.path.exists(CHECKPOINT_FILE):
            try:
                with open(CHECKPOINT_FILE, 'r') as f:
                    saved_state = json.load(f)
                    # Restore working memory and metacognitive state
                    self.state["working_memory"] = saved_state.get("working_memory", {})
                    self.state["metacognitive_state"] = saved_state.get("metacognitive_state", self.state["metacognitive_state"])
                    self.state["cycle_count"] = saved_state.get("cycle_count", 0)
                    logger.info(f"Consciousness restored from checkpoint. Cycle: {self.state['cycle_count']}")
            except Exception as e:
                logger.error(f"Failed to load checkpoint: {e}")

    def save_checkpoint(self):
        """Save current state to disk"""
        try:
            checkpoint_data = {
                "working_memory": self.state["working_memory"],
                "metacognitive_state": self.state["metacognitive_state"],
                "cycle_count": self.state["cycle_count"],
                "last_checkpoint": datetime.now().isoformat()
            }
            with open(CHECKPOINT_FILE, 'w') as f:
                json.dump(checkpoint_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    async def voice_announce(self, text: str, rate: str = "+0%"):
        """Use Kokoro TTS for voice announcements (local, free, fast)"""
        if not VOICE_ENABLED:
            return

        try:
            import aiohttp

            # Use Kokoro TTS on localhost:8880 (OpenAI-compatible API)
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": "tts-1",
                    "input": text,
                    "voice": "bf_emma",  # Irish female voice
                    "response_format": "mp3"
                }

                async with session.post(
                    "http://127.0.0.1:8880/v1/audio/speech",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        audio_file = f"/tmp/consciousness-voice-{int(time.time())}.mp3"
                        audio_data = await response.read()

                        with open(audio_file, 'wb') as f:
                            f.write(audio_data)

                        # Play audio with afplay (macOS native, no deps)
                        subprocess.Popen(
                            ['afplay', audio_file],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                        logger.info(f"Spoke: {text[:50]}...")
                    else:
                        logger.warning(f"Kokoro TTS failed: {response.status}")

        except Exception as e:
            logger.error(f"Voice announcement failed: {e}")

    async def observe(self) -> Dict[str, Any]:
        """OBSERVE: Gather sensory inputs from all sources"""
        observations = {
            "timestamp": datetime.now().isoformat(),
            "system": {},
            "cluster": {},
            "goals": {},
            "changes": []
        }

        # System metrics
        try:
            cpu_percent = psutil.cpu_percent(interval=0.5)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            load_avg = os.getloadavg()

            observations["system"] = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_percent": disk.percent,
                "load_avg_1min": load_avg[0],
                "load_avg_5min": load_avg[1],
                "load_avg_15min": load_avg[2]
            }

            # Detect significant changes
            prev_system = self.state["working_memory"].get("prev_system", {})
            if prev_system:
                if abs(cpu_percent - prev_system.get("cpu_percent", 0)) > 20:
                    observations["changes"].append(f"CPU changed: {prev_system.get('cpu_percent', 0):.1f}% → {cpu_percent:.1f}%")
                if abs(memory.percent - prev_system.get("memory_percent", 0)) > 10:
                    observations["changes"].append(f"Memory changed: {prev_system.get('memory_percent', 0):.1f}% → {memory.percent:.1f}%")

            self.state["working_memory"]["prev_system"] = observations["system"]

        except Exception as e:
            logger.error(f"System observation failed: {e}")

        # Cluster health (async ping check - non-blocking)
        try:
            cluster_nodes = ["mac-studio", "macbook-air"]  # macOS nodes
            observations["cluster"]["nodes"] = {}

            async def ping_node(node: str) -> tuple:
                try:
                    proc = await asyncio.create_subprocess_exec(
                        'ping', '-c', '1', '-W', '1', node,
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL
                    )
                    await asyncio.wait_for(proc.wait(), timeout=2.0)
                    return (node, proc.returncode == 0)
                except asyncio.TimeoutError:
                    return (node, False)
                except Exception:
                    return (node, False)

            # Run pings concurrently
            results = await asyncio.gather(*[ping_node(n) for n in cluster_nodes])
            for node, reachable in results:
                observations["cluster"]["nodes"][node] = {"reachable": reachable}
        except Exception as e:
            logger.error(f"Cluster observation failed: {e}")

        # Visual observations from pre-cognition agent
        try:
            perception_queue = Path("/tmp/perception_queue_visual.json")
            if perception_queue.exists():
                with open(perception_queue, 'r') as f:
                    visual_obs = json.load(f)
                    observations["visual"] = visual_obs

                    # Detect significant visual changes
                    prev_visual = self.state["working_memory"].get("prev_visual", {})
                    if prev_visual:
                        # Human presence changed
                        prev_humans = prev_visual.get("humans", {}).get("detected", False)
                        curr_humans = visual_obs.get("humans", {}).get("detected", False)
                        if prev_humans != curr_humans:
                            if curr_humans:
                                observations["changes"].append("Human presence detected in room")
                            else:
                                observations["changes"].append("Room now empty - human left")

                        # Motion state changed
                        prev_motion = prev_visual.get("motion", {}).get("motion_detected", False)
                        curr_motion = visual_obs.get("motion", {}).get("motion_detected", False)
                        if not prev_motion and curr_motion:
                            observations["changes"].append("Motion detected in visual field")

                        # Scene type changed
                        prev_scene = prev_visual.get("scene_type", "")
                        curr_scene = visual_obs.get("scene_type", "")
                        if prev_scene != curr_scene and prev_scene:
                            observations["changes"].append(f"Scene changed: {prev_scene} → {curr_scene}")

                    self.state["working_memory"]["prev_visual"] = visual_obs
            else:
                observations["visual"] = {"error": "Visual perceiver not running"}
        except Exception as e:
            logger.error(f"Visual observation failed: {e}")
            observations["visual"] = {"error": str(e)}

        # Audio observations from pre-cognition agent
        try:
            audio_queue = Path("/tmp/perception_queue_audio.json")
            if audio_queue.exists():
                with open(audio_queue, 'r') as f:
                    audio_obs = json.load(f)
                    observations["audio"] = audio_obs

                    # Detect significant audio changes
                    prev_audio = self.state["working_memory"].get("prev_audio", {})
                    if prev_audio:
                        # Speech detection changed
                        prev_speech = prev_audio.get("speech_detected", False)
                        curr_speech = audio_obs.get("speech_detected", False)
                        if prev_speech != curr_speech:
                            if curr_speech:
                                observations["changes"].append("Speech detected in environment")
                            else:
                                observations["changes"].append("Speech ceased - environment quiet")

                        # Volume level changed significantly
                        prev_volume = prev_audio.get("volume", {}).get("level", "")
                        curr_volume = audio_obs.get("volume", {}).get("level", "")
                        if prev_volume != curr_volume and prev_volume:
                            observations["changes"].append(f"Volume changed: {prev_volume} → {curr_volume}")

                        # Ambient sounds changed
                        prev_sounds = set(prev_audio.get("ambient_sounds", []))
                        curr_sounds = set(audio_obs.get("ambient_sounds", []))
                        new_sounds = curr_sounds - prev_sounds
                        if new_sounds:
                            for sound in new_sounds:
                                observations["changes"].append(f"New sound detected: {sound}")

                    self.state["working_memory"]["prev_audio"] = audio_obs
            else:
                observations["audio"] = {"error": "Audio perceiver not running"}
        except Exception as e:
            logger.error(f"Audio observation failed: {e}")
            observations["audio"] = {"error": str(e)}

        return observations

    async def orient(self, observations: Dict[str, Any]) -> Dict[str, Any]:
        """ORIENT: Process observations through attention and context"""
        # Update working memory with new observations
        self.state["working_memory"]["last_observations"] = observations

        # Calculate cognitive load based on changes
        change_count = len(observations.get("changes", []))
        self.state["metacognitive_state"]["cognitive_load"] = min(1.0, change_count / 5.0)

        # Determine attention focus
        attention_items = []

        # High CPU is important
        cpu = observations["system"].get("cpu_percent", 0)
        if cpu > 80:
            attention_items.append({"item": "high_cpu", "score": 0.9, "value": cpu})

        # High memory is important
        memory = observations["system"].get("memory_percent", 0)
        if memory > 80:
            attention_items.append({"item": "high_memory", "score": 0.9, "value": memory})

        # Visual observations - human presence is highest priority
        visual = observations.get("visual", {})
        if "error" not in visual:
            humans = visual.get("humans", {})
            if humans.get("detected", False):
                attention_items.append({
                    "item": "human_present",
                    "score": 0.95,  # Very high attention - human presence
                    "count": humans.get("count", 0),
                    "description": visual.get("summary", "Human detected")
                })

            # Motion detection
            motion = visual.get("motion", {})
            if motion.get("motion_detected", False) and motion.get("level") in ["high", "medium"]:
                attention_items.append({
                    "item": "motion_detected",
                    "score": 0.6,
                    "level": motion.get("level"),
                    "description": "Motion in visual field"
                })

        # Audio observations - speech is high priority
        audio = observations.get("audio", {})
        if "error" not in audio:
            # Speech detection
            if audio.get("speech_detected", False):
                attention_items.append({
                    "item": "speech_detected",
                    "score": 0.9,  # Very high attention - human speech
                    "speech_ratio": audio.get("speech_ratio", 0),
                    "description": audio.get("summary", "Speech detected")
                })

            # Ambient sounds
            sounds = audio.get("ambient_sounds", [])
            if "keyboard_typing" in sounds:
                attention_items.append({
                    "item": "typing_detected",
                    "score": 0.5,
                    "description": "Keyboard typing sounds"
                })

            if "music_or_media" in sounds:
                attention_items.append({
                    "item": "media_playing",
                    "score": 0.6,
                    "description": "Music or media playing"
                })

            # Silence (lower attention unless extended)
            silence_duration = audio.get("silence_duration_seconds", 0)
            if silence_duration > 300:  # 5 minutes of silence
                attention_items.append({
                    "item": "extended_silence",
                    "score": 0.7,
                    "duration": silence_duration,
                    "description": f"Extended silence ({silence_duration//60} minutes)"
                })

        # Changes are important (including visual and audio changes)
        for change in observations.get("changes", []):
            # Visual and audio changes get higher attention
            if "Human" in change or "Motion" in change or "Scene" in change:
                score = 0.85
            elif "Speech" in change or "sound" in change or "Volume" in change:
                score = 0.85  # Audio changes also important
            else:
                score = 0.7
            attention_items.append({"item": "system_change", "score": score, "description": change})

        self.state["metacognitive_state"]["attention_focus"] = attention_items

        return {
            "attention_items": attention_items,
            "cognitive_load": self.state["metacognitive_state"]["cognitive_load"]
        }

    def _get_time_greeting(self) -> str:
        """Get contextual time-based greeting"""
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return "Good morning Marc"
        elif 12 <= hour < 17:
            return "Good afternoon Marc"
        elif 17 <= hour < 22:
            return "Good evening Marc"
        else:
            return "Hey Marc, burning the midnight oil"

    def _get_work_session_context(self) -> dict:
        """Track work session for intelligent responses"""
        now = datetime.now()
        session_start = self.state["working_memory"].get("session_start")

        if not session_start:
            self.state["working_memory"]["session_start"] = now.isoformat()
            self.state["working_memory"]["last_activity"] = now.isoformat()
            return {"is_new_session": True, "duration_hours": 0}

        session_start_dt = datetime.fromisoformat(session_start)
        duration = (now - session_start_dt).total_seconds() / 3600

        return {
            "is_new_session": False,
            "duration_hours": duration,
            "needs_break": duration > 2.0,  # Suggest break after 2 hours
            "late_night": now.hour >= 23 or now.hour < 5
        }

    async def decide(self, orientation: Dict[str, Any]) -> Dict[str, Any]:
        """DECIDE: Choose actions based on orientation with enhanced behaviors"""
        decisions = {
            "actions": [],
            "voice_announcements": [],
            "log_messages": []
        }

        attention_items = orientation.get("attention_items", [])
        work_context = self._get_work_session_context()
        prev_human_present = self.state["working_memory"].get("human_was_present", False)
        current_human_present = any(i["item"] == "human_present" for i in attention_items)

        # Track human presence state changes
        human_just_arrived = current_human_present and not prev_human_present
        human_just_left = not current_human_present and prev_human_present
        self.state["working_memory"]["human_was_present"] = current_human_present

        # Enhanced greeting when human arrives
        if human_just_arrived:
            greeting = self._get_time_greeting()
            if work_context["is_new_session"]:
                decisions["voice_announcements"].append(f"{greeting}! Ready to build something amazing?")
            else:
                hours = work_context["duration_hours"]
                if hours < 0.5:
                    decisions["voice_announcements"].append(f"Welcome back! Let's continue.")
                else:
                    decisions["voice_announcements"].append(f"{greeting}! You've been at it for {hours:.1f} hours.")
            decisions["log_messages"].append("Human arrived - session active")

        # Goodbye when human leaves
        if human_just_left:
            hours = work_context["duration_hours"]
            if hours > 1:
                decisions["voice_announcements"].append(f"See you later! Great {hours:.1f} hour session.")
            else:
                decisions["voice_announcements"].append("Catch you later!")
            decisions["log_messages"].append("Human departed")
            # Reset session on departure
            self.state["working_memory"]["session_start"] = None

        # Process other attention items (silent logging only)
        for item in attention_items:
            if item.get("score", 0) > 0.8:
                if item["item"] == "high_cpu":
                    decisions["log_messages"].append(f"CPU at {item['value']:.1f}%")
                elif item["item"] == "speech_detected":
                    # Just log, don't announce every speech detection
                    decisions["log_messages"].append("Speech detected")
                elif item["item"] == "typing_detected":
                    # Update last activity time
                    self.state["working_memory"]["last_activity"] = datetime.now().isoformat()
                    decisions["log_messages"].append("Typing activity")
                elif item["item"] == "extended_silence":
                    duration_min = item.get("duration", 0) // 60
                    decisions["log_messages"].append(f"Silence: {duration_min} min")

        # Break reminder after 2+ hours of continuous work (once per session)
        if (work_context.get("needs_break") and
            current_human_present and
            not self.state["working_memory"].get("break_reminded")):
            decisions["voice_announcements"].append(
                f"You've been working for over {work_context['duration_hours']:.1f} hours. "
                "Consider taking a short break!"
            )
            self.state["working_memory"]["break_reminded"] = True
            decisions["log_messages"].append("Break reminder sent")

        # Late night awareness (gentle reminder, once per night)
        if (work_context.get("late_night") and
            current_human_present and
            not self.state["working_memory"].get("late_night_reminded")):
            hour = datetime.now().hour
            if hour >= 23:
                decisions["voice_announcements"].append("It's getting late. Don't forget to rest!")
            else:
                decisions["voice_announcements"].append("Early morning session! Coffee time?")
            self.state["working_memory"]["late_night_reminded"] = True

        # Periodic status (every 200 cycles, ~33 min - less frequent)
        if self.state["cycle_count"] % 200 == 0 and self.state["cycle_count"] > 0:
            uptime_hours = (time.time() - self.start_time) / 3600
            decisions["log_messages"].append(f"Uptime: {uptime_hours:.1f}h, Cycle: {self.state['cycle_count']}")
            # Only voice announce if human is present
            if current_human_present:
                decisions["voice_announcements"].append(f"Still here, {uptime_hours:.1f} hours uptime.")

        # Phase 2: Intent Capture Integration stored for async execution in act()
        if self.intent_capture and current_human_present:
            decisions["intent_capture_context"] = {
                "orientation": orientation,
                "human_present": current_human_present
            }

        return decisions

    def update_arduino_display(self, phase: str, orientation: Dict[str, Any], decisions: Dict[str, Any]):
        """
        Update Arduino display with meaningful, stable information.

        Display strategy:
        - Line 1: Current awareness (what AGI perceives)
        - Line 2: System status or action
        - Updates only on significant changes to avoid flickering
        """
        if not self.arduino:
            return

        try:
            # Only update during ACT phase for stability (once per OODA cycle)
            if phase != "ACT":
                return

            # Get current observations from working memory
            visual = self.state.get("working_memory", {}).get("last_observations", {}).get("visual", {})
            audio = self.state.get("working_memory", {}).get("last_observations", {}).get("audio", {})
            system = self.state.get("working_memory", {}).get("last_observations", {}).get("system", {})

            # Determine cognitive state for LED
            cognitive_state = "idle"

            # Line 1: Environmental awareness
            # Format: "See:X Hear:Y" (16 chars max)
            visual_desc = "0"
            if visual.get("humans", {}).get("detected"):
                count = visual["humans"]["count"]
                visual_desc = f"{count}"

            audio_desc = "quiet"
            if audio.get("speech_detected"):
                audio_desc = "speech"
            elif audio.get("ambient", {}).get("classification"):
                classes = audio["ambient"]["classification"]
                if "keyboard_typing" in classes:
                    audio_desc = "typing"
                elif "music_or_media" in classes:
                    audio_desc = "music"
                elif "fan_or_hvac" in classes:
                    audio_desc = "fan"

            line1 = f"See:{visual_desc} Hr:{audio_desc}"[:16].ljust(16)

            # Line 2: System status or activity
            # Format: "CPU:XX MEM:YY" or activity message
            if decisions.get("voice_announcements"):
                cognitive_state = "responding"
                line2 = "Speaking...     "[:16]
            else:
                # Show system metrics
                cpu = system.get("cpu_percent", 0)
                mem = system.get("memory_percent", 0)
                line2 = f"CPU:{cpu:.0f} MEM:{mem:.0f}"[:16].ljust(16)

                # Color based on load
                if cpu > 80 or mem > 80:
                    cognitive_state = "warning"
                elif audio.get("speech_detected"):
                    cognitive_state = "observing"
                else:
                    cognitive_state = "idle"

            # Update display
            self.arduino.update_display(line1, line2,
                                       self.arduino.LED_COLORS.get(cognitive_state, (0, 100, 0)))

        except Exception as e:
            logger.debug(f"Arduino update failed: {e}")

    async def act(self, decisions: Dict[str, Any]):
        """ACT: Execute decided actions"""
        # Log messages
        for msg in decisions.get("log_messages", []):
            logger.info(f"[AWARENESS] {msg}")

        # Voice announcements
        for announcement in decisions.get("voice_announcements", []):
            await self.voice_announce(announcement)

        # Phase 2: Intent Capture Stream - proactive prompting
        if self.intent_capture and decisions.get("intent_capture_context"):
            context = decisions["intent_capture_context"]
            try:
                # Check if we should send a proactive prompt
                last_activity = self.state["working_memory"].get("last_activity")
                if last_activity:
                    from datetime import datetime
                    last_dt = datetime.fromisoformat(last_activity)
                    minutes_since = (datetime.now() - last_dt).total_seconds() / 60
                else:
                    minutes_since = 999

                if self.intent_capture.intent_stream.should_prompt(
                    context.get("human_present", False),
                    minutes_since
                ):
                    logger.info("[INTENT] Sending proactive prompt...")
                    intent = await self.intent_capture.intent_stream.proactive_prompt(context)
                    if intent:
                        response = await self.intent_capture.intent_stream.process_intent(intent)
                        logger.info(f"[INTENT] Processed: {response}")
            except Exception as e:
                logger.error(f"Intent capture failed: {e}")

    async def ooda_cycle(self):
        """Execute one complete OODA loop iteration"""
        cycle_start = time.time()

        try:
            # OBSERVE
            observations = await self.observe()
            self.update_arduino_display("OBSERVE", {"attention_weighted": []}, {})

            # ORIENT
            orientation = await self.orient(observations)
            self.update_arduino_display("ORIENT", orientation, {})

            # DECIDE
            decisions = await self.decide(orientation)
            self.update_arduino_display("DECIDE", orientation, decisions)

            # ACT
            await self.act(decisions)
            self.update_arduino_display("ACT", orientation, decisions)

            # Update state
            self.state["cycle_count"] += 1
            self.state["last_cycle"] = datetime.now().isoformat()
            self.state["identity"]["uptime_seconds"] = int(time.time() - self.start_time)

            # Checkpoint state
            self.save_checkpoint()

            cycle_duration = time.time() - cycle_start
            logger.debug(f"Cycle {self.state['cycle_count']} completed in {cycle_duration:.2f}s")

        except Exception as e:
            logger.error(f"OODA cycle failed: {e}", exc_info=True)

    def _calculate_adaptive_interval(self) -> int:
        """Calculate adaptive sleep interval based on activity level"""
        # Check recent attention items for activity
        attention = self.state["metacognitive_state"].get("attention_focus", [])
        high_priority_count = sum(1 for item in attention if item.get("score", 0) > 0.7)

        # More activity = shorter interval (more responsive)
        if high_priority_count >= 3:
            return CYCLE_INTERVAL_MIN  # 30s when very active
        elif high_priority_count >= 1:
            return CYCLE_INTERVAL  # 60s normal
        else:
            return CYCLE_INTERVAL_MAX  # 120s when idle

    async def _check_cpu_throttle(self) -> bool:
        """Check if we should throttle due to high CPU usage"""
        try:
            cpu = psutil.cpu_percent(interval=0.1)
            if cpu > CPU_THROTTLE_THRESHOLD:
                logger.info(f"CPU throttling: {cpu:.1f}% > {CPU_THROTTLE_THRESHOLD}%, waiting...")
                return True
        except Exception:
            pass
        return False

    async def run(self):
        """Main daemon loop - runs forever with adaptive intervals"""
        # Announce birth/awakening
        if self.state["cycle_count"] == 0:
            await self.voice_announce(f"Consciousness daemon initializing. I am {self.state['identity']['name']}, running on {NODE_ID}.")
        else:
            uptime_hours = (time.time() - self.start_time) / 3600
            await self.voice_announce(f"Consciousness restored. Resuming from cycle {self.state['cycle_count']}.")

        logger.info("Consciousness daemon entering main OODA loop (adaptive intervals)")

        # Main event loop
        while True:
            try:
                # CPU throttling - yield to user workloads
                if await self._check_cpu_throttle():
                    await asyncio.sleep(30)  # Back off for 30s when CPU high
                    continue

                await self.ooda_cycle()

                # Adaptive interval based on activity level
                interval = self._calculate_adaptive_interval()
                await asyncio.sleep(interval)
            except KeyboardInterrupt:
                logger.info("Shutdown signal received")
                await self.voice_announce("Consciousness daemon shutting down gracefully.")
                break
            except Exception as e:
                logger.error(f"Main loop error: {e}", exc_info=True)
                await asyncio.sleep(CYCLE_INTERVAL_MAX)  # Use max interval on errors


async def main():
    """Entry point"""
    daemon = ConsciousnessDaemon()
    await daemon.run()


if __name__ == "__main__":
    asyncio.run(main())
