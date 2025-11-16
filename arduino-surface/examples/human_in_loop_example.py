#!/usr/bin/env python3
"""
Human-in-the-Loop Agent Workflow Example
Demonstrates agent requesting human confirmation via Arduino physical interface

Use Cases:
- Destructive operations (delete, modify critical files)
- High-cost decisions (expensive API calls, resource allocation)
- Ethical decisions (content filtering, user data handling)
- Parameter tuning (real-time adjustment via potentiometer)
"""

import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "bridge"))
from surface_bridge import ArduinoSurface


class HumanInLoopAgent:
    """Agent that requests human confirmation for critical decisions"""

    def __init__(self, surface: ArduinoSurface):
        self.surface = surface

    def ask_confirmation(self, question: str, timeout: int = 30) -> bool:
        """
        Ask human for confirmation via physical buttons

        Args:
            question: Question to display (max 32 chars, will wrap to 2 lines)
            timeout: Seconds to wait for response

        Returns:
            True if confirmed, False if cancelled or timeout
        """
        # Clear display and show question
        self.surface.lcd_clear()

        # Split question into two lines if needed
        if len(question) <= 16:
            self.surface.lcd_write(0, 0, question)
            self.surface.lcd_write(1, 0, "Confirm=Yes")
        else:
            # Split at word boundary if possible
            split_pos = question[:16].rfind(' ')
            if split_pos == -1:
                split_pos = 16
            line1 = question[:split_pos]
            line2 = question[split_pos:split_pos+16].strip()

            self.surface.lcd_write(0, 0, line1)
            self.surface.lcd_write(1, 0, line2)

        # Visual indication: yellow LED
        self.surface.set_led(0, 255, 255, 0)

        # Beep to get attention
        self.surface.beep(100, 1000)

        print(f"❓ Waiting for human decision: {question}")
        print(f"   Timeout in {timeout} seconds...")

        # Wait for button press
        event = self.surface.wait_event(timeout=timeout)

        if event is None:
            # Timeout
            self.surface.lcd_clear()
            self.surface.lcd_write(0, 0, "Timeout!")
            self.surface.set_led(0, 255, 0, 0)  # Red
            self.surface.alert("warning")
            print("⏱️  Timeout - defaulting to NO")
            return False

        elif event.get("event") == "button":
            button = event.get("button")

            if button == "confirm":
                # Confirmed
                self.surface.lcd_clear()
                self.surface.lcd_write(0, 0, "Confirmed!")
                self.surface.set_led(0, 0, 255, 0)  # Green
                self.surface.alert("success")
                print("✅ Confirmed by human")
                return True

            else:  # cancel
                # Cancelled
                self.surface.lcd_clear()
                self.surface.lcd_write(0, 0, "Cancelled!")
                self.surface.set_led(0, 255, 0, 0)  # Red
                self.surface.alert("error")
                print("❌ Cancelled by human")
                return False

        return False

    def get_parameter(self, param_name: str, min_val: float, max_val: float,
                     duration: int = 10) -> float:
        """
        Get parameter value from potentiometer

        Args:
            param_name: Name of parameter (max 16 chars)
            min_val: Minimum value
            max_val: Maximum value
            duration: Seconds to allow adjustment

        Returns:
            Selected parameter value
        """
        self.surface.lcd_clear()
        self.surface.lcd_write(0, 0, f"Adjust: {param_name[:8]}")

        # Blue LED for parameter mode
        self.surface.set_led(0, 0, 0, 255)
        self.surface.beep(200, 1500)

        print(f"🎚️  Adjust {param_name} using potentiometer")
        print(f"   Range: {min_val} - {max_val}")
        print(f"   Press CONFIRM when ready ({duration}s timeout)")

        start_time = time.time()
        last_value = None

        while time.time() - start_time < duration:
            # Get current potentiometer value
            status = self.surface.get_status()
            if status:
                pot_raw = status.get("pot", 0)
                # Map 0-1023 to min_val-max_val
                value = min_val + (pot_raw / 1023.0) * (max_val - min_val)

                # Only update display if value changed significantly
                if last_value is None or abs(value - last_value) > (max_val - min_val) * 0.01:
                    self.surface.lcd_write(1, 0, f"Val: {value:.2f}      ")

                    # Update servo to show position
                    servo_pos = int((pot_raw / 1023.0) * 180)
                    self.surface.set_servo(servo_pos)

                    last_value = value

            # Check for confirm button
            event = self.surface.wait_event(timeout=0.1)
            if event and event.get("event") == "button" and event.get("button") == "confirm":
                # Confirmed value
                self.surface.alert("success")
                print(f"✅ Parameter set: {param_name} = {last_value:.2f}")
                return last_value

            time.sleep(0.1)

        # Timeout - use current value
        if last_value is not None:
            self.surface.alert("info")
            print(f"⏱️  Timeout - using value: {last_value:.2f}")
            return last_value
        else:
            # No reading, use midpoint
            midpoint = (min_val + max_val) / 2
            print(f"⚠️  No reading - using midpoint: {midpoint:.2f}")
            return midpoint

    def monitor_emergency_stop(self, callback):
        """
        Monitor tilt switch for emergency stop

        Args:
            callback: Function to call when emergency stop triggered
        """
        print("🛑 Emergency stop monitoring active")
        print("   Tilt the Arduino to trigger emergency stop")

        self.surface.start_event_listener()

        def tilt_handler(event):
            if event.get("triggered"):
                print("🚨 EMERGENCY STOP TRIGGERED!")
                self.surface.lcd_clear()
                self.surface.lcd_write(0, 0, "EMERGENCY STOP!")

                # All LEDs red
                for tier in range(3):
                    self.surface.set_led(tier, 255, 0, 0)

                # Loud alert
                for _ in range(5):
                    self.surface.beep(200, 500)
                    time.sleep(0.1)

                # Execute callback
                callback()

        self.surface.register_handler("tilt", tilt_handler)


# Example workflows
def example_destructive_operation(agent: HumanInLoopAgent):
    """Example: Delete operation requiring confirmation"""
    print("\n=== Example 1: Destructive Operation ===")

    confirmed = agent.ask_confirmation("Delete all logs?", timeout=30)

    if confirmed:
        print("🗑️  Proceeding with deletion...")
        # Actual deletion would happen here
        agent.surface.lcd_clear()
        agent.surface.lcd_write(0, 0, "Logs deleted")
    else:
        print("💾 Keeping logs")


def example_parameter_tuning(agent: HumanInLoopAgent):
    """Example: Real-time parameter adjustment"""
    print("\n=== Example 2: Parameter Tuning ===")

    confidence_threshold = agent.get_parameter(
        param_name="Confidence",
        min_val=0.0,
        max_val=1.0,
        duration=15
    )

    print(f"🎯 Using confidence threshold: {confidence_threshold:.2f}")

    # Agent would use this threshold in decision-making
    agent.surface.lcd_clear()
    agent.surface.lcd_write(0, 0, "Threshold set")
    agent.surface.lcd_write(1, 0, f"{confidence_threshold:.2f}")


def example_cost_gating(agent: HumanInLoopAgent):
    """Example: Expensive API call requiring approval"""
    print("\n=== Example 3: Cost Gating ===")

    # Show estimated cost
    estimated_cost = 125.50
    agent.surface.lcd_clear()
    agent.surface.lcd_write(0, 0, f"Cost: ${estimated_cost:.2f}")
    time.sleep(2)

    confirmed = agent.ask_confirmation("Proceed w/ API?", timeout=30)

    if confirmed:
        print(f"💸 Executing ${estimated_cost:.2f} API call...")
        # API call would happen here
        agent.surface.lcd_clear()
        agent.surface.lcd_write(0, 0, "API call done")
    else:
        print("💰 API call cancelled")


def example_emergency_monitoring(agent: HumanInLoopAgent):
    """Example: Emergency stop monitoring"""
    print("\n=== Example 4: Emergency Stop ===")

    def emergency_callback():
        """Called when emergency stop triggered"""
        print("🛑 Stopping all operations...")
        # Stop all running tasks
        # Close connections
        # Save state
        print("💾 State saved, operations halted")

    agent.monitor_emergency_stop(emergency_callback)

    # Simulate agent doing work
    agent.surface.lcd_clear()
    agent.surface.lcd_write(0, 0, "Agent working...")

    for i in range(30):
        agent.surface.lcd_write(1, 0, f"Step {i+1}/30")
        agent.surface.set_servo((i * 6) % 180)
        time.sleep(1)

        # Check events (emergency stop would be handled by callback)
        event = agent.surface.wait_event(timeout=0.1)
        if event and event.get("event") == "tilt":
            break

    agent.surface.lcd_clear()
    agent.surface.lcd_write(0, 0, "Work complete")


def main():
    if len(sys.argv) < 2:
        print("Usage: human_in_loop_example.py <serial_port> [example_number]")
        print("Examples:")
        print("  1 - Destructive operation")
        print("  2 - Parameter tuning")
        print("  3 - Cost gating")
        print("  4 - Emergency monitoring")
        print("  all - Run all examples")
        sys.exit(1)

    port = sys.argv[1]
    example = sys.argv[2] if len(sys.argv) > 2 else "all"

    surface = ArduinoSurface(port)

    if not surface.connect():
        print("❌ Failed to connect to Arduino")
        sys.exit(1)

    # Startup display
    surface.lcd_clear()
    surface.lcd_write(0, 0, "Human-in-Loop")
    surface.lcd_write(1, 0, "Examples")
    surface.alert("info")
    time.sleep(2)

    agent = HumanInLoopAgent(surface)

    try:
        if example == "1":
            example_destructive_operation(agent)
        elif example == "2":
            example_parameter_tuning(agent)
        elif example == "3":
            example_cost_gating(agent)
        elif example == "4":
            example_emergency_monitoring(agent)
        elif example == "all":
            example_destructive_operation(agent)
            time.sleep(2)
            example_parameter_tuning(agent)
            time.sleep(2)
            example_cost_gating(agent)
            time.sleep(2)
            example_emergency_monitoring(agent)
        else:
            print(f"❌ Unknown example: {example}")

    except KeyboardInterrupt:
        print("\n👋 Interrupted by user")

    finally:
        surface.lcd_clear()
        surface.lcd_write(0, 0, "Examples done")
        time.sleep(1)
        surface.disconnect()


if __name__ == "__main__":
    main()
