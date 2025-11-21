#!/usr/bin/env python3
"""
Comprehensive System Info Daemon for Arduino
Displays: Ember status, system resources, MCP status, git info
"""

import sys
import time
import json
import psutil
import subprocess
from pathlib import Path
from datetime import datetime

# Add bridge to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'bridge'))
from arduino_client import ArduinoClient

# State files
TAMAGOTCHI_STATE = Path.home() / '.claude' / 'pets' / 'claude-pet-state.json'
CLAUDE_CONFIG = Path.home() / '.claude.json'

class SystemInfoDisplay:
    """Comprehensive system information display"""

    def __init__(self):
        self.client = ArduinoClient()
        self.display_mode = 0  # Cycle through different info screens

    def get_ember_state(self):
        """Get Ember's current status"""
        if TAMAGOTCHI_STATE.exists():
            try:
                with open(TAMAGOTCHI_STATE) as f:
                    state = json.load(f)
                    return {
                        'name': state.get('name', 'Ember'),
                        'hunger': state.get('hunger', 70),
                        'energy': state.get('energy', 90),
                        'happiness': state.get('happiness', 85),
                        'cleanliness': state.get('cleanliness', 100),
                        'health': state.get('health', 80)
                    }
            except:
                pass
        return None

    def get_system_stats(self):
        """Get system resource usage"""
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return {
            'cpu': cpu,
            'memory': mem.percent,
            'disk': disk.percent,
            'mem_available': mem.available // (1024**3),  # GB
            'disk_free': disk.free // (1024**3)  # GB
        }

    def get_mcp_status(self):
        """Get MCP server status"""
        if not CLAUDE_CONFIG.exists():
            return {'count': 0, 'servers': []}

        try:
            with open(CLAUDE_CONFIG) as f:
                config = json.load(f)
                servers = config.get('mcpServers', {})

                # Check which are actually running
                running = []
                for name in servers.keys():
                    # Simple heuristic: check if process exists
                    if self._is_server_running(name):
                        running.append(name)

                return {
                    'count': len(servers),
                    'running': len(running),
                    'servers': list(servers.keys())[:3]  # First 3
                }
        except:
            return {'count': 0, 'running': 0, 'servers': []}

    def _is_server_running(self, name):
        """Check if MCP server is running"""
        try:
            result = subprocess.run(
                ['pgrep', '-f', name],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except:
            return False

    def get_git_info(self):
        """Get git repository info"""
        try:
            # Get branch
            branch = subprocess.check_output(
                ['git', 'branch', '--show-current'],
                cwd=Path.home(),
                stderr=subprocess.DEVNULL,
                text=True
            ).strip()

            # Get status
            status = subprocess.check_output(
                ['git', 'status', '--porcelain'],
                cwd=Path.home(),
                stderr=subprocess.DEVNULL,
                text=True
            )
            changes = len(status.strip().split('\n')) if status.strip() else 0

            return {
                'branch': branch or 'main',
                'changes': changes
            }
        except:
            return {'branch': 'none', 'changes': 0}

    def get_mood_color(self, ember):
        """Determine LED color based on Ember's state"""
        if not ember:
            return (100, 100, 100)  # Gray

        h = ember['hunger']
        e = ember['energy']

        if h < 20 or e < 20:
            return (255, 0, 0)  # Red - critical
        elif h < 40 or e < 40:
            return (255, 100, 0)  # Orange - warning
        elif h > 80 and e > 80:
            return (0, 255, 0)  # Green - excellent
        else:
            return (255, 165, 0)  # Yellow - okay

    def format_screen_0(self, ember, system):
        """Screen 0: Ember Status"""
        if ember:
            line1 = f"🔥{ember['name']} H:{ember['hunger']}% E:{ember['energy']}%"
            line2 = f"❤️{ember['happiness']}% 🧼{ember['cleanliness']}%"
        else:
            line1 = "🔥 Ember"
            line2 = "Initializing..."
        return line1, line2

    def format_screen_1(self, system):
        """Screen 1: System Resources"""
        line1 = f"CPU:{system['cpu']:.0f}% MEM:{system['memory']:.0f}%"
        line2 = f"DISK:{system['disk']:.0f}% ({system['disk_free']}GB)"
        return line1, line2

    def format_screen_2(self, mcp, git):
        """Screen 2: MCP & Git"""
        line1 = f"MCP:{mcp['running']}/{mcp['count']} Git:{git['branch'][:8]}"
        line2 = f"Changes:{git['changes']}"
        return line1, line2

    def format_screen_3(self):
        """Screen 3: Time & Status"""
        now = datetime.now()
        line1 = now.strftime("%H:%M:%S %a")
        line2 = now.strftime("%Y-%m-%d")
        return line1, line2

    def update_display(self):
        """Update Arduino with current info"""
        if not self.client.connect():
            return False

        try:
            # Gather all information
            ember = self.get_ember_state()
            system = self.get_system_stats()
            mcp = self.get_mcp_status()
            git = self.get_git_info()

            # Determine LED color from Ember's mood
            led_color = self.get_mood_color(ember)

            # Format display based on current mode
            if self.display_mode == 0:
                line1, line2 = self.format_screen_0(ember, system)
            elif self.display_mode == 1:
                line1, line2 = self.format_screen_1(system)
            elif self.display_mode == 2:
                line1, line2 = self.format_screen_2(mcp, git)
            else:
                line1, line2 = self.format_screen_3()

            # Send to Arduino
            self.client.lcd(0, line1[:20])  # Max 20 chars per line
            self.client.lcd(1, line2[:20])
            self.client.led(tier=0, r=led_color[0], g=led_color[1], b=led_color[2])

            return True

        except Exception as e:
            print(f"Error updating display: {e}")
            return False
        finally:
            self.client.disconnect()

    def run(self, cycle_time=10, screen_duration=5):
        """Run continuous display updates

        Args:
            cycle_time: Seconds between updates within same screen
            screen_duration: Seconds before switching to next screen
        """
        print("System Info Daemon started", flush=True)
        print(f"Cycling screens every {screen_duration}s, updating every {cycle_time}s", flush=True)

        last_mode_change = time.time()
        update_count = 0

        while True:
            try:
                # Update display
                success = self.update_display()
                if success:
                    update_count += 1
                    print(f"Update {update_count}: Screen {self.display_mode} - OK", flush=True)
                else:
                    print(f"Update {update_count}: Failed to connect", flush=True)

                # Check if it's time to switch screens
                if time.time() - last_mode_change >= screen_duration:
                    self.display_mode = (self.display_mode + 1) % 4  # Cycle 0-3
                    last_mode_change = time.time()
                    print(f"Switching to screen {self.display_mode}")

                # Wait before next update
                time.sleep(cycle_time)

            except KeyboardInterrupt:
                print("\nShutting down...")
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                time.sleep(cycle_time)

if __name__ == '__main__':
    display = SystemInfoDisplay()
    display.run()
