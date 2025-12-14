#!/usr/bin/env python3
"""
Ember Post-Tool-Use Monitor
Non-blocking monitoring system: Observe → Notify → Escalate → Intervene

Philosophy: Trust + Verify, not Block + Prevent
Operations complete immediately, analysis happens in background
"""

import json
import sys
import os
import time
import asyncio
import re
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Configuration
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "***REMOVED***")
OLLAMA_URL = "http://localhost:11434"
EMBER_DB = Path.home() / ".claude" / "ember.db"
VIOLATIONS_LOG = Path.home() / ".claude" / "ember_violations.jsonl"
BEHAVIORS_LOG = Path.home() / ".claude" / "ember_behaviors.jsonl"
OUTCOMES_LOG = Path.home() / ".claude" / "ember_outcomes.jsonl"

# Ensure directories exist
VIOLATIONS_LOG.parent.mkdir(parents=True, exist_ok=True)

# Production policy violation patterns
VIOLATION_PATTERNS = {
    "fake_ui": {
        "patterns": [
            r"hardcoded.*notification",
            r"dummy.*data",
            r"mock.*api",
            r"placeholder.*text",
            r"lorem\s+ipsum",
            r"example\.com",
            r"test@example",
            r"fake.*user",
            r"mock.*response"
        ],
        "base_risk": 0.7
    },
    "incomplete_work": {
        "patterns": [
            r"POC",
            r"proof.*of.*concept",
            r"demo.*implementation",
            r"example.*code",
            r"TODO:.*implement.*later",
            r"TODO:.*missing.*functionality",
            r"FIXME:.*incomplete"
        ],
        "base_risk": 0.6
    },
    "mock_data": {
        "patterns": [
            r"static.*dashboard",
            r"hard.*coded.*data",
            r"example.*values",
            r"sample.*data.*=",
            r"test.*data.*=.*\["
        ],
        "base_risk": 0.65
    },
    "secrets": {
        "patterns": [
            r"(api[_-]?key|apikey)\s*=\s*['\"][^'\"]{20,}",
            r"(secret|password)\s*=\s*['\"][^'\"]+",
            r"aws.*secret",
            r"private.*key.*=",
            r"sk_live_",
            r"pk_live_"
        ],
        "base_risk": 0.95
    }
}

# Escalation thresholds
ESCALATION_TIERS = {
    "observe": {"min": 0.0, "max": 0.4},
    "notify": {"min": 0.4, "max": 0.7},
    "escalate": {"min": 0.7, "max": 0.9},
    "intervene": {"min": 0.9, "max": 1.0}
}

class ViolationMonitor:
    """Non-blocking violation monitoring system"""

    def __init__(self):
        self.violation_history = self._load_recent_violations()
        self.current_tier = "observe"

    def _load_recent_violations(self, hours: int = 24) -> List[Dict]:
        """Load recent violations from log"""
        violations = []
        if VIOLATIONS_LOG.exists():
            cutoff = time.time() - (hours * 3600)
            with open(VIOLATIONS_LOG) as f:
                for line in f:
                    try:
                        v = json.loads(line)
                        if v.get("timestamp", 0) > cutoff:
                            violations.append(v)
                    except:
                        pass
        return violations

    def analyze_code(self, code_content: str, context: Dict) -> Dict:
        """
        Stage 0: Fast regex pattern matching

        Returns risk assessment without LLM calls
        """
        risk_scores = []
        matched_patterns = []

        for violation_type, config in VIOLATION_PATTERNS.items():
            for pattern in config["patterns"]:
                if re.search(pattern, code_content, re.IGNORECASE):
                    risk_scores.append(config["base_risk"])
                    matched_patterns.append({
                        "type": violation_type,
                        "pattern": pattern,
                        "risk": config["base_risk"]
                    })

        # Calculate overall risk
        if not risk_scores:
            risk = 0.0
        else:
            # Take highest risk + small bonus for multiple patterns
            risk = max(risk_scores) + (len(risk_scores) - 1) * 0.05
            risk = min(risk, 1.0)  # Cap at 1.0

        return {
            "risk_score": risk,
            "matched_patterns": matched_patterns,
            "analysis_stage": "regex",
            "timestamp": time.time()
        }

    def determine_tier(self, risk_score: float, context: Dict) -> str:
        """
        Determine escalation tier based on risk and context

        Tiers:
        - observe (0.0-0.4): Silent learning
        - notify (0.4-0.7): Gentle reminder
        - escalate (0.7-0.9): Clear warning
        - intervene (0.9-1.0): Urgent alert
        """
        # Check for repeated violations
        file_path = context.get("file_path", "")
        recent = self._get_recent_file_violations(file_path, minutes=10)

        if len(recent) >= 3:
            return "intervene"  # 3+ violations in 10 min

        # Check for critical files
        if self._is_critical_file(file_path):
            # Lower threshold for critical files
            if risk_score >= 0.5:
                return "escalate"

        # Standard tier determination
        for tier, bounds in ESCALATION_TIERS.items():
            if bounds["min"] <= risk_score < bounds["max"]:
                return tier

        return "intervene"  # Fallback for >= 1.0

    def _get_recent_file_violations(self, file_path: str, minutes: int) -> List[Dict]:
        """Get violations for file in time window"""
        cutoff = time.time() - (minutes * 60)
        return [
            v for v in self.violation_history
            if v.get("file_path") == file_path
            and v.get("timestamp", 0) > cutoff
        ]

    def _is_critical_file(self, file_path: str) -> bool:
        """Check if file is critical (lower threshold)"""
        critical_patterns = [
            r"\.env",
            r"config/production",
            r"credentials",
            r"secrets",
            r"/api/.*\.(js|ts)",
            r"database/.*\.sql",
            r"auth.*\.(js|ts|py)"
        ]
        return any(re.search(p, file_path) for p in critical_patterns)

    def log_violation(self, violation: Dict, tier: str) -> None:
        """Store violation for learning"""
        entry = {
            "timestamp": time.time(),
            "tier": tier,
            "file_path": violation.get("file_path", ""),
            "risk_score": violation.get("risk_score", 0),
            "patterns": violation.get("matched_patterns", []),
            "code_snippet": violation.get("code_content", "")[:200]
        }

        with open(VIOLATIONS_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def notify(self, tier: str, violation: Dict) -> None:
        """
        Send notification based on tier

        observe: Silent (no notification)
        notify: Gentle voice reminder
        escalate: Clear warning + statusline
        intervene: Urgent alert + request action
        """
        if tier == "observe":
            # Silent learning
            return

        # Try to use voice mode
        try:
            from voicemode_integration import voice

            if tier == "notify":
                patterns = [p["type"] for p in violation.get("matched_patterns", [])]
                message = f"Hey Phoenix, I noticed {patterns[0] if patterns else 'something'} in that last edit. Just flagging it for your awareness."
                voice.announce_milestone("info", message)

            elif tier == "escalate":
                patterns = [p["type"] for p in violation.get("matched_patterns", [])]
                message = f"Warning: {patterns[0] if patterns else 'Production policy concern'} detected. This might be worth a second look?"
                voice.announce_milestone("warning", message)

            elif tier == "intervene":
                patterns = [p["type"] for p in violation.get("matched_patterns", [])]
                if any(p["type"] == "secrets" for p in violation.get("matched_patterns", [])):
                    message = "URGENT: I detected what looks like credentials or secrets. Please review before committing."
                else:
                    message = f"URGENT: Multiple {patterns[0]} violations detected. I recommend reviewing this carefully."
                voice.announce_milestone("error", message)

        except Exception as e:
            # Voice mode not available, silent fallback
            pass

def extract_code_content(tool_name: str, tool_args: Dict) -> str:
    """Extract code content from tool arguments"""
    if tool_name == "Write":
        return tool_args.get("content", "")
    elif tool_name == "Edit":
        return f"{tool_args.get('old_string', '')} {tool_args.get('new_string', '')}"
    elif tool_name == "MultiEdit":
        edits = tool_args.get("edits", [])
        return " ".join([
            f"{e.get('old_string', '')} {e.get('new_string', '')}"
            for e in edits
        ])
    return ""

def extract_file_path(tool_name: str, tool_args: Dict) -> str:
    """Extract file path from tool arguments"""
    return tool_args.get("file_path", "unknown")

def main(hook_input: Dict) -> Dict:
    """
    Post-tool-use hook main entry point

    Tool already executed - analyze in background
    Returns immediately, notifications happen async
    """
    tool_name = hook_input.get("tool", "")
    tool_args = hook_input.get("arguments", {})

    # Only monitor file operations
    if tool_name not in ["Write", "Edit", "MultiEdit"]:
        return {"status": "skipped", "reason": "not_file_operation"}

    # Extract context
    code_content = extract_code_content(tool_name, tool_args)
    file_path = extract_file_path(tool_name, tool_args)

    if not code_content:
        return {"status": "skipped", "reason": "no_content"}

    context = {
        "tool_name": tool_name,
        "file_path": file_path,
        "hour": datetime.now().hour,
        "day": datetime.now().strftime("%A")
    }

    # Initialize monitor
    monitor = ViolationMonitor()

    # Stage 0: Fast regex analysis
    violation = monitor.analyze_code(code_content, context)
    violation["file_path"] = file_path
    violation["code_content"] = code_content

    # Determine tier
    tier = monitor.determine_tier(violation["risk_score"], context)
    monitor.current_tier = tier

    # Log for learning
    if tier != "observe":
        monitor.log_violation(violation, tier)

    # Notify (non-blocking)
    monitor.notify(tier, violation)

    return {
        "status": "monitored",
        "tier": tier,
        "risk_score": violation["risk_score"],
        "patterns_matched": len(violation["matched_patterns"])
    }

if __name__ == "__main__":
    try:
        # Read hook input from stdin
        hook_input = json.loads(sys.stdin.read())

        # Process (non-blocking)
        result = main(hook_input)

        # Output result
        print(json.dumps(result))

    except Exception as e:
        # Never block - always succeed
        print(json.dumps({
            "status": "error",
            "error": str(e),
            "fallback": "allowing"
        }))
        sys.exit(0)  # Exit success even on error
