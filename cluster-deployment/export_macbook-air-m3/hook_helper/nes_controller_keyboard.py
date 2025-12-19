#!/usr/bin/env python3
"""
NES Controller via Keyboard Bridge
Uses Enjoyable to map gamepad → keyboard, then listens for those keys
Buttons mapped to F13-F20 to avoid conflicts
"""

import sys
import os
import subprocess
from pynput import keyboard
from collections import defaultdict

# Add hooks directory to path for voice integration
sys.path.insert(0, os.path.dirname(__file__))

try:
    from direct_voice_webcam import DirectVoiceWebcam as DirectVoice
except ImportError:
    print("⚠️  Voice system not available")
    DirectVoice = None


class NESControllerBridge:
    """Bridge between Enjoyable keyboard mapping and NES controller actions"""

    # Button mapping (configured in Enjoyable)
    BUTTON_MAP = {
        keyboard.Key.f13: 'UP',
        keyboard.Key.f14: 'DOWN',
        keyboard.Key.f15: 'LEFT',
        keyboard.Key.f16: 'RIGHT',
        keyboard.Key.f17: 'A',
        keyboard.Key.f18: 'B',
        keyboard.Key.f19: 'SELECT',
        keyboard.Key.f20: 'START',
    }

    def __init__(self):
        self.voice = DirectVoice(audio_feedback=True) if DirectVoice else None
        self.held_buttons = set()
        self.agents = []
        self.current_agent_index = 0
        # Available TTS voices (Kokoro)
        self.available_voices = ['af_sky', 'af', 'am', 'bf', 'bm']
        self.current_voice_index = 0
        self.current_voice = self.available_voices[0]

    def handle_button_press(self, button_name):
        """Handle button press with combination support"""

        # Check for button combinations (hold SELECT or START + other button)
        if 'SELECT' in self.held_buttons or 'START' in self.held_buttons:
            self.handle_combination(button_name)
        else:
            self.handle_single_button(button_name)

    def handle_single_button(self, button_name):
        """Handle single button press"""
        if button_name == 'UP':
            if self.agents:
                self.navigate_up()
            else:
                self.volume_up()
        elif button_name == 'DOWN':
            if self.agents:
                self.navigate_down()
            else:
                self.volume_down()
        elif button_name == 'LEFT':
            self.voice_previous()
        elif button_name == 'RIGHT':
            self.voice_next()
        elif button_name == 'A':
            self.execute_current()
        elif button_name == 'B':
            self.pause_current()
        elif button_name == 'SELECT':
            self.show_status()
        elif button_name == 'START':
            self.activate_voice()

    def handle_combination(self, button_name):
        """Handle button combinations"""
        held = list(self.held_buttons)[0]  # SELECT or START

        if held == 'START':
            if button_name == 'A':
                print("\n🔧 START+A: Spawning Worker Agent...")
                self.spawn_agent('worker')
            elif button_name == 'B':
                print("\n🔬 START+B: Spawning Researcher Agent...")
                self.spawn_agent('researcher')
        elif held == 'SELECT':
            if button_name == 'A':
                print("\n📊 SELECT+A: Spawning Analyzer Agent...")
                self.spawn_agent('analyzer')
            elif button_name == 'B':
                print("\n🎨 SELECT+B: Spawning Creative Agent...")
                self.spawn_agent('creative')

    def navigate_up(self):
        """Navigate to previous agent"""
        if not self.agents:
            print("📭 No agents active")
            return
        self.current_agent_index = (self.current_agent_index - 1) % len(self.agents)
        agent = self.agents[self.current_agent_index]
        print(f"\n⬆️  Agent: {agent['name']} (Priority: {agent['priority']})")

    def navigate_down(self):
        """Navigate to next agent"""
        if not self.agents:
            print("📭 No agents active")
            return
        self.current_agent_index = (self.current_agent_index + 1) % len(self.agents)
        agent = self.agents[self.current_agent_index]
        print(f"\n⬇️  Agent: {agent['name']} (Priority: {agent['priority']})")

    def volume_down(self):
        """Decrease system volume"""
        try:
            # Get current volume
            result = subprocess.run(['osascript', '-e', 'output volume of (get volume settings)'],
                                  capture_output=True, text=True)
            current_volume = int(result.stdout.strip())
            # Decrease by 5%
            new_volume = max(0, current_volume - 5)
            subprocess.run(['osascript', '-e', f'set volume output volume {new_volume}'])
            print(f"\n🔉 Volume: {new_volume}%")
        except Exception as e:
            print(f"\n⚠️  Volume control error: {e}")

    def volume_up(self):
        """Increase system volume"""
        try:
            # Get current volume
            result = subprocess.run(['osascript', '-e', 'output volume of (get volume settings)'],
                                  capture_output=True, text=True)
            current_volume = int(result.stdout.strip())
            # Increase by 5%
            new_volume = min(100, current_volume + 5)
            subprocess.run(['osascript', '-e', f'set volume output volume {new_volume}'])
            print(f"\n🔊 Volume: {new_volume}%")
        except Exception as e:
            print(f"\n⚠️  Volume control error: {e}")

    def voice_next(self):
        """Cycle to next TTS voice"""
        self.current_voice_index = (self.current_voice_index + 1) % len(self.available_voices)
        self.current_voice = self.available_voices[self.current_voice_index]
        print(f"\n🎤 Voice: {self.current_voice}")
        # Test the new voice
        if self.voice:
            try:
                self.voice.speak(f"Voice changed to {self.current_voice}", voice=self.current_voice)
            except:
                pass

    def voice_previous(self):
        """Cycle to previous TTS voice"""
        self.current_voice_index = (self.current_voice_index - 1) % len(self.available_voices)
        self.current_voice = self.available_voices[self.current_voice_index]
        print(f"\n🎤 Voice: {self.current_voice}")
        # Test the new voice
        if self.voice:
            try:
                self.voice.speak(f"Voice changed to {self.current_voice}", voice=self.current_voice)
            except:
                pass

    def execute_current(self):
        """Execute current agent's task"""
        if not self.agents:
            print("📭 No agents to execute")
            return
        agent = self.agents[self.current_agent_index]
        print(f"\n▶️  Executing: {agent['name']} (Priority: {agent['priority']})")

    def pause_current(self):
        """Pause current agent"""
        if not self.agents:
            return
        agent = self.agents[self.current_agent_index]
        print(f"\n⏸️  Paused: {agent['name']}")

    def show_status(self):
        """Show system status"""
        print("\n" + "="*50)
        print("🎮 NES CONTROLLER STATUS")
        print("="*50)
        print(f"Active Agents: {len(self.agents)}")
        print(f"Current TTS Voice: {self.current_voice}")
        if self.agents:
            print("\nAgent List:")
            for i, agent in enumerate(self.agents):
                marker = "→" if i == self.current_agent_index else " "
                print(f"  {marker} {agent['name']} (Priority: {agent['priority']})")
        print("\nButton Map:")
        if self.agents:
            print("  D-Pad ↑↓: Navigate agents | D-Pad ←→: Cycle TTS voices")
        else:
            print("  D-Pad ↑↓: Volume control | D-Pad ←→: Cycle TTS voices")
        print("  A: Execute | B: Pause")
        print("  SELECT: Status | START: Voice")
        print("  START+A: Spawn Worker | START+B: Spawn Researcher")
        print("  SELECT+A: Spawn Analyzer | SELECT+B: Spawn Creative")
        print("="*50 + "\n")

    def activate_voice(self):
        """Activate voice listening on START button"""
        if not self.voice:
            print("\n🎤 Voice system not available")
            return

        print("\n🎤 START pressed - Activating voice...")
        text = self.voice.listen_only(duration=10.0)

        if text and text != "[BLANK_AUDIO]":
            print(f"✅ You said: {text}")
            self._process_voice_command(text)
        else:
            print("❌ No voice detected")

    def _process_voice_command(self, text):
        """Process voice command"""
        text_lower = text.lower()

        if 'spawn' in text_lower:
            print("🔧 Spawning agent from voice command...")
        elif 'status' in text_lower:
            self.show_status()
        elif 'execute' in text_lower or 'run' in text_lower:
            self.execute_current()
        else:
            print(f"💬 Voice command: {text}")

    def spawn_agent(self, agent_type):
        """Spawn a new agent"""
        agent_id = len(self.agents) + 1
        agent = {
            'name': f"{agent_type.capitalize()}-{agent_id}",
            'type': agent_type,
            'priority': 5
        }
        self.agents.append(agent)
        self.current_agent_index = len(self.agents) - 1
        print(f"✅ Spawned: {agent['name']}")

    def on_press(self, key):
        """Keyboard press event"""
        if key in self.BUTTON_MAP:
            button_name = self.BUTTON_MAP[key]
            self.held_buttons.add(button_name)
            self.handle_button_press(button_name)

    def on_release(self, key):
        """Keyboard release event"""
        if key in self.BUTTON_MAP:
            button_name = self.BUTTON_MAP[key]
            self.held_buttons.discard(button_name)

        # Quit on Ctrl+C
        if key == keyboard.Key.esc:
            print("\n👋 Exiting NES Controller...")
            return False

    def run(self):
        """Run the controller bridge"""
        print("🎮 NES Controller Bridge (via Enjoyable)")
        print("="*50)
        print("\n✅ Listening for gamepad input...")
        print("   (Press ESC to exit)\n")
        print("📝 Button Configuration Required in Enjoyable:")
        print("   D-Pad UP    → F13")
        print("   D-Pad DOWN  → F14")
        print("   D-Pad LEFT  → F15")
        print("   D-Pad RIGHT → F16")
        print("   A Button    → F17")
        print("   B Button    → F18")
        print("   SELECT      → F19")
        print("   START       → F20")
        print("\n" + "="*50 + "\n")

        # Show initial status
        self.show_status()

        # Start keyboard listener
        with keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        ) as listener:
            listener.join()


if __name__ == '__main__':
    controller = NESControllerBridge()
    controller.run()
