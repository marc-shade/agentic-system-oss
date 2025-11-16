#!/usr/bin/env python3
"""
Arduino System Status Relay Daemon

Continuously updates Arduino Smart Surface with current system status.
Logs status updates that Arduino broker can pick up.
"""

import asyncio
import json
import sys
from pathlib import Path


class SystemStatusRelay:
    def __init__(self, status_file='/tmp/arduino-system-status.json'):
        self.status_file = status_file
        self.running = False

    async def connect(self):
        """Initialize status file"""
        print(f"✓ Initialized Arduino status relay (writing to {self.status_file})")

    async def get_system_status(self):
        """Get system status from status collector (via Node.js API)"""
        try:
            import urllib.request
            req = urllib.request.Request('http://localhost:3002/api/dashboard/stats')
            with urllib.request.urlopen(req, timeout=2) as response:
                data = json.loads(response.read().decode())
                if data.get('success'):
                    stats = data.get('stats', {})
                    # Count running services
                    services = stats.get('services', [])
                    total = len(services)
                    running = len([s for s in services if s.get('status') == 'active'])
                    percentage = round((running / total * 100) if total > 0 else 0)

                    return {
                        'running': running,
                        'total': total,
                        'percentage': percentage,
                        'status': stats.get('overall_status', 'unknown')
                    }
        except Exception as e:
            print(f"⚠ Error fetching system status: {e}")

        # Fallback - count manually if API fails
        return await self.count_services_manually()

    async def count_services_manually(self):
        """Manual service counting as fallback"""
        import subprocess

        ports_to_check = [
            3101, 4100, 4101, 4102, 4103, 4104,  # Backend
            2022, 8880, 9091, 9092, 9093, 9050, 7880,  # Voice
            8765, 5432, 3002  # Arduino MCP, PostgreSQL, API
        ]

        running = 0
        for port in ports_to_check:
            try:
                result = subprocess.run(
                    ['lsof', '-i', f':{port}'],
                    capture_output=True,
                    timeout=1
                )
                if result.returncode == 0:
                    running += 1
            except:
                pass

        # Add process checks
        processes = [
            'arduino_broker.py',
            'arduino_smart_agent.py',
            'tamagotchi-statusline'
        ]

        for proc in processes:
            try:
                result = subprocess.run(
                    ['pgrep', '-f', proc],
                    capture_output=True,
                    timeout=1
                )
                if result.returncode == 0:
                    running += 1
            except:
                pass

        total = len(ports_to_check) + len(processes) + 5  # +5 for MCP servers
        percentage = round((running / total * 100))

        return {
            'running': running,
            'total': total,
            'percentage': percentage,
            'status': 'manual_count'
        }

    async def update_arduino_display(self, status):
        """Write status to file for Arduino broker to pick up"""
        running = status['running']
        total = status['total']
        percentage = status['percentage']

        # Determine status icon
        if percentage >= 95:
            icon = "✓"
            color = "GREEN"
        elif percentage >= 80:
            icon = "⚠"
            color = "YELLOW"
        else:
            icon = "✗"
            color = "RED"

        # Format message for Arduino
        message = f"SYSTEM {icon}\n{running}/{total} ONLINE\n({percentage}%)"

        try:
            # Write to file for Arduino broker to read
            import json
            with open(self.status_file, 'w') as f:
                json.dump({
                    'type': 'system_status',
                    'message': message,
                    'color': color,
                    'running': running,
                    'total': total,
                    'percentage': percentage,
                    'timestamp': __import__('datetime').datetime.now().isoformat()
                }, f, indent=2)
            print(f"✓ Updated Arduino status: {running}/{total} services ({percentage}%)")
        except Exception as e:
            print(f"⚠ Error updating Arduino status file: {e}")

    async def run(self, interval=10):
        """Main relay loop"""
        self.running = True

        try:
            await self.connect()

            print(f"🔄 Starting system status relay (updating every {interval}s)")
            print("Press Ctrl+C to stop\n")

            while self.running:
                try:
                    # Get current system status
                    status = await self.get_system_status()

                    # Update Arduino display
                    await self.update_arduino_display(status)

                    # Wait before next update
                    await asyncio.sleep(interval)

                except KeyboardInterrupt:
                    print("\n⏹ Stopping system status relay...")
                    self.running = False
                except Exception as e:
                    print(f"⚠ Error in relay loop: {e}")
                    await asyncio.sleep(interval)

        except Exception as e:
            print(f"❌ Fatal error: {e}")
        finally:
            print("✓ System status relay stopped")

    async def stop(self):
        """Stop the relay"""
        self.running = False


async def main():
    relay = SystemStatusRelay()

    try:
        await relay.run(interval=10)  # Update every 10 seconds
    except KeyboardInterrupt:
        await relay.stop()


if __name__ == '__main__':
    asyncio.run(main())
