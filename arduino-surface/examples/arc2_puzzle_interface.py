#!/usr/bin/env python3
"""
ARC-2 Puzzle Physical Verification Interface
Uses Arduino surface for human verification of ARC-2 puzzle solutions

ARC-2 (Abstraction and Reasoning Corpus) requires human-like reasoning.
This interface allows agents to present solutions for physical human verification.

Workflow:
1. Agent generates ARC-2 solution
2. Solution displayed on LCD (or via visual output to terminal)
3. Human reviews solution visually
4. Human uses buttons to verify: Confirm = Correct, Cancel = Incorrect
5. Potentiometer used to rate solution quality (0-100%)
6. Results stored for agent learning
"""

import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Optional

sys.path.append(str(Path(__file__).parent.parent / "bridge"))
from surface_bridge import ArduinoSurface


class ARC2VerificationInterface:
    """Physical interface for ARC-2 puzzle solution verification"""

    def __init__(self, surface: ArduinoSurface):
        self.surface = surface
        self.verification_log = []

    def display_puzzle_info(self, puzzle_id: str, grid_size: str):
        """Display puzzle identification"""
        self.surface.lcd_clear()
        self.surface.lcd_write(0, 0, f"ARC-2: {puzzle_id[:8]}")
        self.surface.lcd_write(1, 0, f"Grid: {grid_size}")

        # Blue LED for puzzle mode
        self.surface.set_led(0, 0, 0, 255)
        self.surface.beep(100, 1500)

        time.sleep(2)

    def request_verification(self, puzzle_id: str, solution_num: int,
                           timeout: int = 60) -> Optional[Dict]:
        """
        Request human verification of ARC-2 solution

        Args:
            puzzle_id: Puzzle identifier
            solution_num: Solution attempt number
            timeout: Seconds to wait for verification

        Returns:
            Dict with verification result or None if timeout
        """
        self.surface.lcd_clear()
        self.surface.lcd_write(0, 0, f"Solution #{solution_num}")
        self.surface.lcd_write(1, 0, "Review then vote")

        # Yellow LED for review mode
        self.surface.set_led(0, 255, 255, 0)
        self.surface.beep(200, 1000)

        print(f"\n🧩 ARC-2 Puzzle: {puzzle_id}")
        print(f"📊 Solution #{solution_num} ready for verification")
        print(f"👀 Review the solution visually, then:")
        print(f"   ✅ CONFIRM = Correct solution")
        print(f"   ❌ CANCEL = Incorrect solution")
        print(f"   ⏱️  Timeout in {timeout} seconds")

        start_time = time.time()

        # Wait for button press
        event = self.surface.wait_event(timeout=timeout)

        if event is None:
            # Timeout
            self.surface.lcd_clear()
            self.surface.lcd_write(0, 0, "Verification")
            self.surface.lcd_write(1, 0, "Timeout")
            self.surface.alert("warning")
            print("⏱️  Verification timeout")
            return None

        elif event.get("event") == "button":
            button = event.get("button")
            verification_time = time.time() - start_time

            if button == "confirm":
                # Correct solution
                self.surface.lcd_clear()
                self.surface.lcd_write(0, 0, "CORRECT!")
                self.surface.set_led(0, 0, 255, 0)  # Green
                self.surface.alert("success")

                result = {
                    "puzzle_id": puzzle_id,
                    "solution_num": solution_num,
                    "correct": True,
                    "verification_time_seconds": verification_time,
                    "timestamp": time.time()
                }

                print("✅ Solution verified as CORRECT")
                self.verification_log.append(result)
                return result

            else:  # cancel
                # Incorrect solution
                self.surface.lcd_clear()
                self.surface.lcd_write(0, 0, "INCORRECT")
                self.surface.set_led(0, 255, 0, 0)  # Red
                self.surface.alert("error")

                result = {
                    "puzzle_id": puzzle_id,
                    "solution_num": solution_num,
                    "correct": False,
                    "verification_time_seconds": verification_time,
                    "timestamp": time.time()
                }

                print("❌ Solution verified as INCORRECT")
                self.verification_log.append(result)
                return result

        return None

    def rate_solution_quality(self, duration: int = 10) -> float:
        """
        Get solution quality rating from potentiometer

        Args:
            duration: Seconds to allow rating adjustment

        Returns:
            Quality rating 0.0-1.0
        """
        self.surface.lcd_clear()
        self.surface.lcd_write(0, 0, "Rate quality:")

        # Purple LED for rating mode
        self.surface.set_led(0, 128, 0, 255)
        self.surface.beep(150, 1200)

        print(f"⭐ Rate solution quality using potentiometer")
        print(f"   0% (left) = Poor quality")
        print(f"   100% (right) = Perfect quality")
        print(f"   Press CONFIRM when done ({duration}s timeout)")

        start_time = time.time()
        last_quality = None

        while time.time() - start_time < duration:
            status = self.surface.get_status()
            if status:
                pot_raw = status.get("pot", 0)
                quality = pot_raw / 1023.0

                if last_quality is None or abs(quality - last_quality) > 0.01:
                    quality_percent = int(quality * 100)
                    self.surface.lcd_write(1, 0, f"Quality: {quality_percent}%    ")

                    # Servo shows rating visually
                    servo_pos = int(quality * 180)
                    self.surface.set_servo(servo_pos)

                    last_quality = quality

            # Check for confirm button
            event = self.surface.wait_event(timeout=0.1)
            if event and event.get("event") == "button" and event.get("button") == "confirm":
                self.surface.alert("success")
                print(f"⭐ Quality rating: {last_quality:.2f}")
                return last_quality

            time.sleep(0.1)

        # Timeout - use current value or 0.5
        if last_quality is not None:
            print(f"⏱️  Timeout - using rating: {last_quality:.2f}")
            return last_quality
        else:
            print(f"⚠️  No rating - using default: 0.5")
            return 0.5

    def display_statistics(self, stats: Dict):
        """Display verification statistics on LCD"""
        self.surface.lcd_clear()

        correct = stats.get("correct", 0)
        total = stats.get("total", 0)
        accuracy = stats.get("accuracy", 0.0)

        self.surface.lcd_write(0, 0, f"Score: {correct}/{total}")
        self.surface.lcd_write(1, 0, f"Acc: {accuracy:.1f}%")

        # LED color based on accuracy
        if accuracy >= 80:
            self.surface.set_led(0, 0, 255, 0)  # Green
        elif accuracy >= 50:
            self.surface.set_led(0, 255, 255, 0)  # Yellow
        else:
            self.surface.set_led(0, 255, 165, 0)  # Orange

        time.sleep(3)

    def get_verification_stats(self) -> Dict:
        """Calculate verification statistics"""
        if not self.verification_log:
            return {"correct": 0, "total": 0, "accuracy": 0.0}

        correct = sum(1 for v in self.verification_log if v["correct"])
        total = len(self.verification_log)
        accuracy = (correct / total * 100) if total > 0 else 0.0

        avg_time = sum(v["verification_time_seconds"] for v in self.verification_log) / total

        return {
            "correct": correct,
            "total": total,
            "accuracy": accuracy,
            "average_time_seconds": avg_time
        }

    def save_verification_log(self, filename: str):
        """Save verification log to JSON file"""
        with open(filename, 'w') as f:
            json.dump({
                "verifications": self.verification_log,
                "statistics": self.get_verification_stats()
            }, f, indent=2)

        print(f"💾 Verification log saved to {filename}")


def simulate_arc2_workflow(interface: ARC2VerificationInterface):
    """Simulate ARC-2 puzzle solving workflow with physical verification"""

    # Example puzzles (in real use, these would be actual ARC-2 grids)
    puzzles = [
        {"id": "f8ff0b80", "grid_size": "3x3", "expected_correct": True},
        {"id": "1cf80156", "grid_size": "5x5", "expected_correct": False},
        {"id": "445eab21", "grid_size": "4x4", "expected_correct": True},
        {"id": "a8c38be5", "grid_size": "6x6", "expected_correct": True},
        {"id": "bda2d7a6", "grid_size": "3x4", "expected_correct": False},
    ]

    print("\n" + "="*60)
    print("ARC-2 PUZZLE VERIFICATION WORKFLOW")
    print("="*60)

    for idx, puzzle in enumerate(puzzles, 1):
        print(f"\n--- Puzzle {idx}/{len(puzzles)} ---")

        # Display puzzle info
        interface.display_puzzle_info(puzzle["id"], puzzle["grid_size"])

        # In real workflow:
        # 1. Agent generates solution
        # 2. Solution visualized on screen
        # 3. Human reviews visual output

        print(f"\n🤖 Agent generating solution for {puzzle['id']}...")
        print(f"📐 Grid size: {puzzle['grid_size']}")
        print(f"\n[Solution would be displayed visually here]")
        print(f"[Imagine a {puzzle['grid_size']} colored grid pattern]")

        # Request verification
        verification = interface.request_verification(
            puzzle_id=puzzle["id"],
            solution_num=1,
            timeout=60
        )

        if verification:
            # If solution verified as correct, optionally get quality rating
            if verification["correct"]:
                time.sleep(1)
                quality = interface.rate_solution_quality(duration=10)
                verification["quality_rating"] = quality
                print(f"⭐ Quality: {quality:.2f}")

        time.sleep(2)

        # Show running statistics
        stats = interface.get_verification_stats()
        interface.display_statistics(stats)
        print(f"\n📊 Current Stats: {stats['correct']}/{stats['total']} correct ({stats['accuracy']:.1f}%)")

    # Final statistics
    print("\n" + "="*60)
    print("VERIFICATION SESSION COMPLETE")
    print("="*60)

    final_stats = interface.get_verification_stats()
    print(f"\n📊 Final Statistics:")
    print(f"   Total Solutions: {final_stats['total']}")
    print(f"   Correct: {final_stats['correct']}")
    print(f"   Accuracy: {final_stats['accuracy']:.1f}%")
    print(f"   Avg Verification Time: {final_stats['average_time_seconds']:.1f}s")

    # Save log
    log_file = f"/tmp/arc2_verification_{int(time.time())}.json"
    interface.save_verification_log(log_file)

    # Final display
    interface.surface.lcd_clear()
    interface.surface.lcd_write(0, 0, "Session done")
    interface.surface.lcd_write(1, 0, f"{final_stats['accuracy']:.0f}% accuracy")

    if final_stats['accuracy'] >= 80:
        interface.surface.alert("success")
    else:
        interface.surface.alert("info")


def main():
    if len(sys.argv) < 2:
        print("Usage: arc2_puzzle_interface.py <serial_port>")
        print("Example: arc2_puzzle_interface.py /dev/tty.usbmodem14101")
        sys.exit(1)

    port = sys.argv[1]

    surface = ArduinoSurface(port)

    if not surface.connect():
        print("❌ Failed to connect to Arduino")
        sys.exit(1)

    # Startup display
    surface.lcd_clear()
    surface.lcd_write(0, 0, "ARC-2 Interface")
    surface.lcd_write(1, 0, "Initializing...")
    surface.alert("info")
    time.sleep(2)

    interface = ARC2VerificationInterface(surface)

    try:
        simulate_arc2_workflow(interface)

    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")

    finally:
        surface.lcd_clear()
        surface.lcd_write(0, 0, "Goodbye!")
        time.sleep(1)
        surface.disconnect()


if __name__ == "__main__":
    main()
