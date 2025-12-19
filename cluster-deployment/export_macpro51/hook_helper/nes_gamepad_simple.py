#!/usr/bin/env python3
"""
Simple NES Gamepad Controller for Phoenix
==========================================

Simplified implementation focusing on core functionality:
- Button reading from USB HID device
- Direct voice integration (Start button)
- Agent navigation (D-Pad)
- Simple action dispatch

Author: Phoenix Dev Team
Status: Production-ready
"""

import hid
import time
import sys
from pathlib import Path
from typing import Set, Optional, Callable
from enum import Enum

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Use webcam microphone instead of Bluetooth (better audio levels)
from direct_voice_webcam import DirectVoiceWebcam as DirectVoice


class Button(Enum):
    """NES controller buttons"""
    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3
    A = 4
    B = 5
    SELECT = 6
    START = 7


class SimpleNESController:
    """Simple NES gamepad controller with direct integrations"""

    # Device IDs
    VENDOR_ID = 0x0810
    PRODUCT_ID = 0xE501

    def __init__(self):
        self.device: Optional[hid.device] = None
        self.running = False
        self.voice = DirectVoice(audio_feedback=True)

        # Agent state
        self.agents = []
        self.selected_idx = 0

        # Button state tracking
        self.button_states = {btn: False for btn in Button}
        self.hold_start_time = {}
        self.HOLD_THRESHOLD = 0.5  # 500ms for combinations

        print("🎮 Simple NES Controller initialized")

    def connect(self) -> bool:
        """Connect to NES gamepad"""
        try:
            self.device = hid.device()
            self.device.open(self.VENDOR_ID, self.PRODUCT_ID)

            product = self.device.get_product_string()
            print(f"✅ Connected to: {product}")

            self.device.set_nonblocking(1)
            return True

        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            return False

    def disconnect(self):
        """Disconnect from gamepad"""
        if self.device:
            self.device.close()
            self.device = None
            print("🔌 Disconnected")

    def read_buttons(self) -> Set[Button]:
        """Read current button states"""
        if not self.device:
            return set()

        try:
            data = self.device.read(64)
            if not data:
                return set()

            pressed = set()

            # Parse button bits (first 2 bytes)
            button_map = {
                0: Button.B,      # Bit 0
                1: Button.A,      # Bit 1
                2: Button.SELECT, # Bit 2
                3: Button.START,  # Bit 3
                4: Button.UP,     # Bit 4
                5: Button.DOWN,   # Bit 5
                6: Button.LEFT,   # Bit 6
                7: Button.RIGHT,  # Bit 7
            }

            for byte_idx in range(min(2, len(data))):
                for bit_idx in range(8):
                    button_num = byte_idx * 8 + bit_idx
                    if button_num in button_map:
                        if data[byte_idx] & (1 << bit_idx):
                            pressed.add(button_map[button_num])

            return pressed

        except Exception as e:
            print(f"❌ Read error: {e}")
            return set()

    def handle_start_button(self):
        """Start button: Activate voice listening"""
        print("\n🎤 START pressed - Activating voice...")
        text = self.voice.listen_only(duration=10.0)

        if text:
            print(f"✅ You said: {text}")
            # Process command
            self._process_voice_command(text)
        else:
            print("⚠️  No speech detected")

    def handle_select_button(self):
        """Select button: Show system status"""
        print("\n📊 SELECT pressed - System Status:")
        print("=" * 50)
        print(f"🤖 Active Agents: {len(self.agents)}")
        if self.agents:
            for i, agent in enumerate(self.agents):
                marker = "←" if i == self.selected_idx else " "
                print(f"  {i+1}. {agent['name']} [Pri: {agent['priority']}] {marker}")
        else:
            print("  No agents active")
        print("=" * 50)

    def handle_dpad_up(self):
        """D-Pad Up: Previous agent"""
        if self.agents:
            self.selected_idx = (self.selected_idx - 1) % len(self.agents)
            print(f"↑ Selected: {self.agents[self.selected_idx]['name']}")

    def handle_dpad_down(self):
        """D-Pad Down: Next agent"""
        if self.agents:
            self.selected_idx = (self.selected_idx + 1) % len(self.agents)
            print(f"↓ Selected: {self.agents[self.selected_idx]['name']}")

    def handle_dpad_left(self):
        """D-Pad Left: Decrease priority"""
        if self.agents and self.selected_idx < len(self.agents):
            agent = self.agents[self.selected_idx]
            agent['priority'] = max(1, agent['priority'] - 1)
            print(f"← Priority: {agent['priority']}")

    def handle_dpad_right(self):
        """D-Pad Right: Increase priority"""
        if self.agents and self.selected_idx < len(self.agents):
            agent = self.agents[self.selected_idx]
            agent['priority'] = min(10, agent['priority'] + 1)
            print(f"→ Priority: {agent['priority']}")

    def handle_a_button(self, held_buttons: Set[Button]):
        """A button: Execute or spawn (if combo)"""
        if Button.START in held_buttons:
            # Start + A: Spawn Worker
            print("🔧 START+A: Spawning Worker Agent...")
            self.agents.append({
                'name': f'Worker #{len(self.agents)+1}',
                'type': 'worker',
                'priority': 5
            })
        elif Button.SELECT in held_buttons:
            # Select + A: Spawn Dev
            print("💻 SELECT+A: Spawning Dev Agent...")
            self.agents.append({
                'name': f'Dev #{len(self.agents)+1}',
                'type': 'dev',
                'priority': 5
            })
        else:
            # Simple A: Execute
            if self.agents and self.selected_idx < len(self.agents):
                agent = self.agents[self.selected_idx]
                print(f"▶️  A: Executing {agent['name']}...")

    def handle_b_button(self, held_buttons: Set[Button]):
        """B button: Pause or emergency stop (if combo)"""
        if Button.START in held_buttons:
            # Start + B: Emergency Stop
            print("🚨 START+B: EMERGENCY STOP ALL AGENTS!")
            self.agents.clear()
            self.selected_idx = 0
        elif Button.SELECT in held_buttons:
            # Select + B: Spawn Analysis
            print("🔍 SELECT+B: Spawning Analysis Agent...")
            self.agents.append({
                'name': f'Analysis #{len(self.agents)+1}',
                'type': 'analysis',
                'priority': 5
            })
        else:
            # Simple B: Pause
            if self.agents and self.selected_idx < len(self.agents):
                agent = self.agents[self.selected_idx]
                print(f"⏸️  B: Pausing {agent['name']}...")

    def _process_voice_command(self, text: str):
        """Process voice command (simple implementation)"""
        text_lower = text.lower()

        if "status" in text_lower:
            self.handle_select_button()
        elif "worker" in text_lower or "spawn" in text_lower:
            print("🔧 Voice: Spawning Worker Agent...")
            self.agents.append({
                'name': f'Worker #{len(self.agents)+1}',
                'type': 'worker',
                'priority': 5
            })
        elif "stop" in text_lower or "halt" in text_lower:
            print("🛑 Voice: Stopping all agents...")
            self.agents.clear()
            self.selected_idx = 0
        else:
            print(f"💬 Voice command received: {text}")

    def run(self):
        """Main loop"""
        if not self.connect():
            return

        self.running = True
        print("\n🎮 NES Controller active!")
        print("=" * 50)
        print("Controls:")
        print("  START   = Voice listen (10s)")
        print("  SELECT  = System status")
        print("  ↑↓      = Navigate agents")
        print("  ←→      = Adjust priority")
        print("  A       = Execute")
        print("  B       = Pause")
        print("\nCombos:")
        print("  START+A = Spawn Worker")
        print("  START+B = Emergency Stop ALL")
        print("  SELECT+A = Spawn Dev")
        print("  SELECT+B = Spawn Analysis")
        print("=" * 50)
        print("\nPress Ctrl+C to exit\n")

        last_buttons = set()

        try:
            while self.running:
                current_buttons = self.read_buttons()

                # Detect button presses (edge detection)
                pressed = current_buttons - last_buttons

                for button in pressed:
                    # Check for combinations
                    if button == Button.START:
                        self.handle_start_button()
                    elif button == Button.SELECT:
                        self.handle_select_button()
                    elif button == Button.UP:
                        self.handle_dpad_up()
                    elif button == Button.DOWN:
                        self.handle_dpad_down()
                    elif button == Button.LEFT:
                        self.handle_dpad_left()
                    elif button == Button.RIGHT:
                        self.handle_dpad_right()
                    elif button == Button.A:
                        self.handle_a_button(current_buttons)
                    elif button == Button.B:
                        self.handle_b_button(current_buttons)

                last_buttons = current_buttons
                time.sleep(0.01)  # 100Hz polling

        except KeyboardInterrupt:
            print("\n\n👋 Shutting down...")

        finally:
            self.disconnect()


if __name__ == '__main__':
    controller = SimpleNESController()
    controller.run()
