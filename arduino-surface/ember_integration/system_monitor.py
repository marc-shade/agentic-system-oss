#!/usr/bin/env python3
"""
System Monitor for Arduino Display
Shows real Claude Code quality and system metrics
"""

import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from lcd_filter import LCDFilter


class SystemMonitor:
    """Monitor Claude Code system quality and activity"""

    def __init__(self):
        self.home = Path.home()
        self.claude_dir = self.home / ".claude"
        self.violations_log = self.claude_dir / "ember_violations.jsonl"
        self.outcomes_log = self.claude_dir / "ember_outcomes.jsonl"
        self.patterns_file = self.claude_dir / "ember_learned_patterns.json"
        self.lcd_filter = LCDFilter()

    def get_violation_stats(self):
        """Get violation statistics from the last hour"""
        if not self.violations_log.exists():
            return {"count": 0, "recent": None, "severity": "none"}

        violations = []
        one_hour_ago = time.time() - 3600

        try:
            with open(self.violations_log, 'r') as f:
                for line in f:
                    try:
                        violation = json.loads(line.strip())
                        observations = violation.get("observations", [])

                        # Extract timestamp
                        timestamp = 0
                        for obs in observations:
                            if obs.startswith("timestamp:"):
                                timestamp = int(obs.split(":")[1].strip())
                                break

                        if timestamp > one_hour_ago:
                            violations.append(violation)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Error reading violations: {e}")
            return {"count": 0, "recent": None, "severity": "none"}

        if not violations:
            return {"count": 0, "recent": None, "severity": "none"}

        # Get most recent violation
        recent = violations[-1]
        observations = recent.get("observations", [])

        violation_type = "unknown"
        severity = "moderate"
        for obs in observations:
            if obs.startswith("violation_type:"):
                violation_type = obs.split(":")[1].strip()
            elif obs.startswith("severity:"):
                severity = obs.split(":")[1].strip()

        return {
            "count": len(violations),
            "recent": violation_type,
            "severity": severity
        }

    def get_learning_stats(self):
        """Get pattern learning statistics"""
        if not self.patterns_file.exists():
            return {"patterns": 0, "confidence": 0}

        try:
            with open(self.patterns_file, 'r') as f:
                patterns = json.load(f)

            pattern_count = len(patterns.get("exceptions", []))
            avg_confidence = 0

            if pattern_count > 0:
                confidences = [p.get("confidence", 0) for p in patterns.get("exceptions", [])]
                avg_confidence = sum(confidences) / len(confidences)

            return {
                "patterns": pattern_count,
                "confidence": int(avg_confidence * 100)
            }
        except Exception as e:
            print(f"Error reading patterns: {e}")
            return {"patterns": 0, "confidence": 0}

    def get_outcome_stats(self):
        """Get outcome statistics (corrected vs intentional)"""
        if not self.outcomes_log.exists():
            return {"corrected": 0, "intentional": 0, "ratio": 0}

        corrected = 0
        intentional = 0

        try:
            with open(self.outcomes_log, 'r') as f:
                for line in f:
                    try:
                        outcome = json.loads(line.strip())
                        outcome_type = outcome.get("outcome_type", "")

                        if outcome_type == "corrected":
                            corrected += 1
                        elif outcome_type == "intentional":
                            intentional += 1
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Error reading outcomes: {e}")
            return {"corrected": 0, "intentional": 0, "ratio": 0}

        total = corrected + intentional
        ratio = (intentional / total * 100) if total > 0 else 0

        return {
            "corrected": corrected,
            "intentional": intentional,
            "ratio": int(ratio)
        }

    def get_quality_score(self):
        """
        Calculate overall quality score based on:
        - Low violation count (good)
        - High pattern learning (good)
        - High intentional ratio (good)
        """
        violations = self.get_violation_stats()
        learning = self.get_learning_stats()
        outcomes = self.get_outcome_stats()

        # Start at 100
        score = 100

        # Penalty for violations (max -30)
        violation_penalty = min(violations["count"] * 10, 30)
        score -= violation_penalty

        # Bonus for learning (max +15)
        learning_bonus = min(learning["patterns"] * 2, 15)
        score += learning_bonus

        # Bonus for intentional ratio (max +15)
        ratio_bonus = int(outcomes["ratio"] * 0.15)
        score += ratio_bonus

        return max(0, min(100, score))

    def get_system_info(self):
        """Get general system information"""
        import psutil

        # Get memory usage
        memory = psutil.virtual_memory()
        mem_used_gb = memory.used / (1024 ** 3)
        mem_total_gb = memory.total / (1024 ** 3)

        # Get CPU usage
        cpu_percent = int(psutil.cpu_percent(interval=0.1))

        return {
            "memory_used_gb": round(mem_used_gb, 1),
            "memory_total_gb": round(mem_total_gb, 1),
            "cpu_percent": cpu_percent
        }

    def get_display_mode_violation(self):
        """Display mode 1: Violation Monitor"""
        stats = self.get_violation_stats()
        return self.lcd_filter.format_violations(
            stats["count"],
            stats["recent"],
            stats["severity"]
        )

    def get_display_mode_quality(self):
        """Display mode 2: Quality Score"""
        score = self.get_quality_score()
        violations = self.get_violation_stats()
        return self.lcd_filter.format_quality_score(score, violations['count'])

    def get_display_mode_learning(self):
        """Display mode 3: Learning Progress"""
        learning = self.get_learning_stats()
        outcomes = self.get_outcome_stats()
        return self.lcd_filter.format_learning(
            learning['patterns'],
            learning['confidence'],
            outcomes['ratio']
        )

    def get_display_mode_system(self):
        """Display mode 4: System Resources"""
        info = self.get_system_info()
        return self.lcd_filter.format_system_info(
            info['cpu_percent'],
            info['memory_used_gb'],
            info['memory_total_gb']
        )

    def get_display_for_mode(self, mode):
        """Get display lines for a specific mode"""
        modes = {
            0: self.get_display_mode_violation,
            1: self.get_display_mode_quality,
            2: self.get_display_mode_learning,
            3: self.get_display_mode_system
        }

        mode_func = modes.get(mode % 4, self.get_display_mode_violation)
        return mode_func()

    def get_led_for_quality(self):
        """Get LED color/pattern based on quality score"""
        score = self.get_quality_score()

        if score >= 90:
            return {"color": (0, 255, 0), "pattern": "solid"}  # Green = excellent
        elif score >= 75:
            return {"color": (255, 120, 0), "pattern": "slow_pulse"}  # Orange = good
        elif score >= 50:
            return {"color": (255, 255, 0), "pattern": "fast_pulse"}  # Yellow = fair
        else:
            return {"color": (255, 0, 0), "pattern": "flash"}  # Red = poor


# CLI for testing
if __name__ == "__main__":
    monitor = SystemMonitor()

    print("=" * 50)
    print("🔥 System Monitor Test 🔥")
    print("=" * 50)
    print()

    # Test all display modes
    modes = ["Violation", "Quality", "Learning", "System"]
    for i, name in enumerate(modes):
        line1, line2 = monitor.get_display_for_mode(i)
        print(f"Mode {i}: {name}")
        print(f"  LCD Line 1: {line1}")
        print(f"  LCD Line 2: {line2}")
        print()

    # Test LED
    led = monitor.get_led_for_quality()
    print(f"LED Color: RGB{led['color']}")
    print(f"LED Pattern: {led['pattern']}")
    print()

    # Show stats
    print("Raw Stats:")
    print(f"  Violations: {monitor.get_violation_stats()}")
    print(f"  Learning: {monitor.get_learning_stats()}")
    print(f"  Outcomes: {monitor.get_outcome_stats()}")
    print(f"  Quality Score: {monitor.get_quality_score()}/100")
