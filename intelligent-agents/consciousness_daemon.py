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
    logger.warning("Arduino perceiver not available")

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
CYCLE_INTERVAL = 10  # seconds
NODE_ID = os.environ.get("NODE_ID", "macpro51")
VOICE_ENABLED = True  # Use voice for announcements

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
        """Use voice to announce status"""
        if not VOICE_ENABLED:
            return

        try:
            # Call edge-tts directly (voice-mode MCP may not be available to daemon)
            audio_file = f"/tmp/consciousness-voice-{int(time.time())}.mp3"
            cmd = [
                'edge-tts',
                '--voice', 'en-IE-EmilyNeural',
                '--rate', rate,
                '--text', text,
                '--write-media', audio_file
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()

            # Play audio
            if proc.returncode == 0:
                for player in ['mpg123', 'ffplay']:
                    if subprocess.run(['which', player], capture_output=True).returncode == 0:
                        subprocess.Popen([player, audio_file],
                                       stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL)
                        break
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

        # Cluster health (basic ping check)
        try:
            cluster_nodes = ["mac-studio", "macbook-air"]  # macOS nodes
            observations["cluster"]["nodes"] = {}
            for node in cluster_nodes:
                result = subprocess.run(['ping', '-c', '1', '-W', '1', node],
                                      capture_output=True)
                observations["cluster"]["nodes"][node] = {
                    "reachable": result.returncode == 0
                }
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

    async def decide(self, orientation: Dict[str, Any]) -> Dict[str, Any]:
        """DECIDE: Choose actions based on orientation"""
        decisions = {
            "actions": [],
            "voice_announcements": [],
            "log_messages": []
        }

        # Phase 1 MVP: Only monitoring, no autonomous actions
        # Just log and announce significant events

        attention_items = orientation.get("attention_items", [])

        for item in attention_items:
            if item.get("score", 0) > 0.8:  # High attention items
                if item["item"] == "high_cpu":
                    msg = f"CPU at {item['value']:.1f} percent - system under load"
                    decisions["voice_announcements"].append(msg)
                    decisions["log_messages"].append(msg)
                elif item["item"] == "high_memory":
                    msg = f"Memory at {item['value']:.1f} percent - approaching capacity"
                    decisions["voice_announcements"].append(msg)
                    decisions["log_messages"].append(msg)
                elif item["item"] == "human_present":
                    # Human detected - greet if this is new detection
                    msg = item.get("description", "Human detected in visual field")
                    decisions["log_messages"].append(msg)
                    # Voice announcement only on state change (not every cycle)
                    if "Human presence detected" in str(attention_items):
                        decisions["voice_announcements"].append("Hello! I can see you now.")
                elif item["item"] == "system_change" and "Human" in item.get("description", ""):
                    # Human presence changed
                    if "left" in item.get("description", ""):
                        msg = "Human left the room - returning to idle monitoring"
                        decisions["voice_announcements"].append(msg)
                    decisions["log_messages"].append(item.get("description", ""))
                elif item["item"] == "speech_detected":
                    # Human speech detected
                    msg = item.get("description", "Speech detected in environment")
                    decisions["log_messages"].append(msg)
                    # Voice announcement only on state change
                    if "Speech detected in environment" in str(attention_items):
                        decisions["voice_announcements"].append("I can hear you speaking now.")
                elif item["item"] == "system_change" and "Speech" in item.get("description", ""):
                    # Speech state changed
                    desc = item.get("description", "")
                    if "ceased" in desc:
                        msg = "Speech stopped - environment quiet now"
                        decisions["voice_announcements"].append(msg)
                    decisions["log_messages"].append(desc)
                elif item["item"] == "extended_silence":
                    # Extended silence detected
                    duration_min = item.get("duration", 0) // 60
                    msg = f"Extended silence detected - {duration_min} minutes of quiet"
                    decisions["log_messages"].append(msg)

        # Special announcement every 100 cycles
        if self.state["cycle_count"] % 100 == 0 and self.state["cycle_count"] > 0:
            uptime_hours = (time.time() - self.start_time) / 3600
            msg = f"Consciousness daemon running. Uptime: {uptime_hours:.1f} hours. Cycle: {self.state['cycle_count']}"
            decisions["voice_announcements"].append(msg)

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

        # Phase 1: No autonomous actions yet
        # Future: Execute system commands, spawn tasks, update configurations

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

    async def run(self):
        """Main daemon loop - runs forever"""
        # Announce birth/awakening
        if self.state["cycle_count"] == 0:
            await self.voice_announce(f"Consciousness daemon initializing. I am {self.state['identity']['name']}, running on {NODE_ID}.")
        else:
            uptime_hours = (time.time() - self.start_time) / 3600
            await self.voice_announce(f"Consciousness restored. Resuming from cycle {self.state['cycle_count']}.")

        logger.info("Consciousness daemon entering main OODA loop")

        # Main event loop
        while True:
            try:
                await self.ooda_cycle()
                await asyncio.sleep(CYCLE_INTERVAL)
            except KeyboardInterrupt:
                logger.info("Shutdown signal received")
                await self.voice_announce("Consciousness daemon shutting down gracefully.")
                break
            except Exception as e:
                logger.error(f"Main loop error: {e}", exc_info=True)
                await asyncio.sleep(CYCLE_INTERVAL)


async def main():
    """Entry point"""
    daemon = ConsciousnessDaemon()
    await daemon.run()


if __name__ == "__main__":
    asyncio.run(main())
