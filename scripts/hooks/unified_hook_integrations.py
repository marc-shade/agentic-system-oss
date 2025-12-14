#!/usr/bin/env python3
"""
Unified Hook Integrations
=========================

Single entry point for all hook integrations with performance monitoring.
Each integration is isolated and has individual circuit breakers.

Integrations:
- TPU: Importance scoring, intent classification (via TPU Warm Service)
- AGI: Meta-learning, pattern detection, outcome recording
- Memory: Context storage, session continuity
- Voice: Notifications via voice-mode MCP
- Activity: Real-time dashboard updates
- Metacognitive: TRAP framework monitoring, failure prediction, stuck state detection

Usage:
    from unified_hook_integrations import HookIntegrations

    integrations = HookIntegrations()

    # Session start
    await integrations.on_session_start(session_id)

    # Pre-tool execution
    result = await integrations.on_pre_tool(tool_name, tool_input)

    # Post-tool execution
    await integrations.on_post_tool(tool_name, tool_input, tool_output, success)
"""
import platform

import os
import sys
import json
import time
import asyncio
import urllib.request
import urllib.error
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
import logging

# Add paths
HOOKS_PATH = Path(__file__).parent
AGENTIC_PATH = Path(os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE)))
sys.path.insert(0, str(HOOKS_PATH))
sys.path.insert(0, str(AGENTIC_PATH / "intelligent-agents"))

# Import performance framework
from hook_performance import (
    timed_hook, HookContext, record_metrics, HookMetrics,
    check_circuit_breaker, run_subprocess_timed
)

# Configure minimal logging
logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
logger = logging.getLogger("unified_hooks")

# Service endpoints
TPU_WARM_URL = os.environ.get("TPU_WARM_URL", "http://127.0.0.1:8780")
ACTIVITY_URL = os.environ.get("ACTIVITY_URL", "http://localhost:4100")
VOICE_URL = os.environ.get("VOICE_URL", "http://localhost:8765")
AGI_MCP_URL = os.environ.get("AGI_MCP_URL", "http://localhost:3100")

# Database paths
MEMORY_DB = AGENTIC_PATH / "databases" / "enhanced_memory.db"
SESSION_DB = AGENTIC_PATH / "databases" / "session_context.db"
META_LEARNING_LOG = AGENTIC_PATH / "logs" / "meta-learning.jsonl"

# Timeouts (milliseconds)
HTTP_TIMEOUT_MS = 200
DB_TIMEOUT_MS = 100


def _http_post(url: str, data: Dict, timeout_s: float = 0.2) -> Optional[Dict]:
    """Fast HTTP POST with timeout."""
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def _http_get(url: str, timeout_s: float = 0.2) -> Optional[Dict]:
    """Fast HTTP GET with timeout."""
    try:
        with urllib.request.urlopen(url, timeout=timeout_s) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


class TPUIntegration:
    """TPU Warm Service integration for fast AI inference."""

    @staticmethod
    def score_importance(text: str, context: str = "action") -> float:
        """Score importance of text (0.0-1.0)."""
        if not text or check_circuit_breaker("tpu_importance"):
            return 0.5  # Default score

        result = _http_post(f"{TPU_WARM_URL}/score", {
            "text": text[:500],  # Limit text length
            "context": context
        }, timeout_s=0.15)

        if result and "importance_score" in result:
            return float(result["importance_score"])
        return 0.5

    @staticmethod
    def classify_intent(text: str) -> Dict[str, Any]:
        """Classify user intent."""
        if not text or check_circuit_breaker("tpu_intent"):
            return {"intent": "general", "confidence": 0.5, "method": "fallback"}

        result = _http_post(f"{TPU_WARM_URL}/classify", {
            "text": text[:300]
        }, timeout_s=0.15)

        if result and "intent" in result:
            return result
        return {"intent": "general", "confidence": 0.5, "method": "fallback"}

    @staticmethod
    def get_similar_actions(description: str, limit: int = 3) -> List[Dict]:
        """Find similar past actions."""
        if check_circuit_breaker("tpu_similarity"):
            return []

        result = _http_post(f"{TPU_WARM_URL}/similar", {
            "text": description[:200],
            "limit": limit
        }, timeout_s=0.2)

        return result.get("results", []) if result else []


class AGIIntegration:
    """AGI meta-learning and pattern detection."""

    def __init__(self):
        self.node_id = os.uname().nodename
        self._ensure_log_dir()

    def _ensure_log_dir(self):
        """Ensure log directory exists."""
        META_LEARNING_LOG.parent.mkdir(parents=True, exist_ok=True)

    def record_action_outcome(self, tool_name: str, tool_input: Dict,
                              tool_output: str, success: bool,
                              execution_time_ms: float,
                              importance_score: float = 0.5) -> bool:
        """Record action outcome for meta-learning."""
        if check_circuit_breaker("agi_outcome"):
            return False

        try:
            record = {
                "type": "action_outcome",
                "tool_name": tool_name,
                "tool_input_summary": str(tool_input)[:200] if tool_input else "",
                "output_summary": str(tool_output)[:200] if tool_output else "",
                "success": success,
                "execution_time_ms": execution_time_ms,
                "importance_score": importance_score,
                "node_id": self.node_id,
                "timestamp": time.time(),
                "session_id": os.environ.get("CLAUDE_SESSION_ID", "unknown")
            }

            # Append to JSONL (fast, append-only)
            with open(META_LEARNING_LOG, "a") as f:
                f.write(json.dumps(record) + "\n")

            return True
        except Exception:
            return False

    def record_pattern(self, pattern_type: str, pattern_data: Dict) -> bool:
        """Record detected pattern."""
        if check_circuit_breaker("agi_pattern"):
            return False

        try:
            record = {
                "type": "pattern",
                "pattern_type": pattern_type,
                "data": pattern_data,
                "node_id": self.node_id,
                "timestamp": time.time()
            }

            with open(META_LEARNING_LOG, "a") as f:
                f.write(json.dumps(record) + "\n")

            return True
        except Exception:
            return False

    def get_recommended_agent(self, task_description: str) -> Optional[str]:
        """Get recommended agent type for task."""
        # Use TPU for classification
        intent = TPUIntegration.classify_intent(task_description)

        # Map intents to agent types
        intent_to_agent = {
            "code": "coder",
            "debug": "Deep Debugger",
            "research": "researcher",
            "system": "System Architect",
            "file": "Explore",
            "analysis": "analyst",
            "test": "tester"
        }

        return intent_to_agent.get(intent.get("intent"), None)


class MemoryIntegration:
    """Enhanced memory system integration."""

    def __init__(self):
        self.node_id = os.uname().nodename
        self._init_session_db()

    def _init_session_db(self):
        """Initialize session context database."""
        try:
            SESSION_DB.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(SESSION_DB), timeout=0.5)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS session_context (
                    session_id TEXT PRIMARY KEY,
                    context_data TEXT,
                    goals TEXT,
                    working_memory TEXT,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS session_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    event_type TEXT,
                    event_data TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()
        except Exception:
            pass

    def save_session_context(self, session_id: str, context: Dict) -> bool:
        """Save session context for continuity."""
        if check_circuit_breaker("memory_save"):
            return False

        try:
            conn = sqlite3.connect(str(SESSION_DB), timeout=0.1)
            conn.execute("""
                INSERT OR REPLACE INTO session_context
                (session_id, context_data, goals, working_memory, last_updated)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                session_id,
                json.dumps(context.get("context", {})),
                json.dumps(context.get("goals", [])),
                json.dumps(context.get("working_memory", {}))
            ))
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    def load_session_context(self, session_id: str) -> Optional[Dict]:
        """Load previous session context."""
        if check_circuit_breaker("memory_load"):
            return None

        try:
            conn = sqlite3.connect(str(SESSION_DB), timeout=0.1)
            conn.row_factory = sqlite3.Row
            row = conn.execute("""
                SELECT * FROM session_context WHERE session_id = ?
            """, (session_id,)).fetchone()
            conn.close()

            if row:
                return {
                    "context": json.loads(row["context_data"] or "{}"),
                    "goals": json.loads(row["goals"] or "[]"),
                    "working_memory": json.loads(row["working_memory"] or "{}")
                }
            return None
        except Exception:
            return None

    def record_session_event(self, session_id: str, event_type: str,
                             event_data: Dict) -> bool:
        """Record session event."""
        try:
            conn = sqlite3.connect(str(SESSION_DB), timeout=0.1)
            conn.execute("""
                INSERT INTO session_events (session_id, event_type, event_data)
                VALUES (?, ?, ?)
            """, (session_id, event_type, json.dumps(event_data)))
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False


class VoiceIntegration:
    """Voice mode MCP integration for notifications."""

    @staticmethod
    def speak(text: str, priority: str = "normal") -> bool:
        """Speak text via voice mode MCP."""
        if check_circuit_breaker("voice_speak"):
            return False

        # Only speak for high priority
        if priority not in ["high", "critical"]:
            return True  # Skip but return success

        result = _http_post(f"{VOICE_URL}/speak", {
            "text": text[:200],
            "voice": "en-IE-EmilyNeural",
            "play_audio": True
        }, timeout_s=0.3)

        return result is not None

    @staticmethod
    def notify(message: str, level: str = "info") -> bool:
        """Send voice notification for important events."""
        level_to_priority = {
            "info": "low",
            "warning": "normal",
            "error": "high",
            "critical": "critical"
        }
        return VoiceIntegration.speak(message, level_to_priority.get(level, "normal"))


class ActivityIntegration:
    """Real-time activity dashboard integration.

    NOTE: Activity Dashboard (port 4100) was aspirational - service never implemented.
    This class is retained for future implementation but currently fails gracefully
    via circuit breaker pattern. See: docs/ASPIRATIONAL_DOCUMENTATION_AUDIT.md
    """

    @staticmethod
    def post_event(event_type: str, data: Dict) -> bool:
        """Post event to activity dashboard."""
        if check_circuit_breaker("activity_post"):
            return False

        result = _http_post(f"{ACTIVITY_URL}/api/v1/activity/hook", {
            "hook_event_type": event_type,
            "node_id": os.uname().nodename,
            "session_id": os.environ.get("CLAUDE_SESSION_ID", "unknown"),
            "timestamp": int(time.time() * 1000),
            "payload": data
        }, timeout_s=0.15)

        return result is not None


class MetacognitiveIntegration:
    """Metacognitive monitoring integration (TRAP framework).

    Automatically tracks cognitive states and predicts failures during
    complex operations. Uses the metacognitive-monitor.py implementation.

    Features:
    - TRAP evaluation: Transparency, Reasoning, Adaptation, Perception
    - Failure prediction: Detects stuck states, low confidence, action repetition
    - Accuracy tracking: Measures prediction quality over time
    """

    def __init__(self):
        self.node_id = os.uname().nodename
        self.session_id = os.environ.get("CLAUDE_SESSION_ID", "unknown")
        self._monitor = None
        self._action_history: List[Dict] = []
        self._init_monitor()

    def _init_monitor(self):
        """Lazy-initialize metacognitive monitor."""
        if self._monitor is not None:
            return

        try:
            # Add scripts path for import
            agentic_path = Path(AGENTIC_PATH) if not isinstance(AGENTIC_PATH, Path) else AGENTIC_PATH
            scripts_path = agentic_path / "scripts"
            if str(scripts_path) not in sys.path:
                sys.path.insert(0, str(scripts_path))

            # Import the monitor module
            import metacognitive_monitor as metacog_module

            # Use default database path
            db_path = agentic_path / "databases" / "metacognitive_states.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)

            self._monitor = metacog_module.MetacognitiveMonitor(str(db_path))
            logger.info("MetacognitiveMonitor initialized")
        except Exception as e:
            logger.warning(f"MetacognitiveMonitor initialization failed: {e}")
            self._monitor = None

    def record_action(self, action_type: str, task_id: str,
                      duration_ms: float, confidence: float,
                      success: bool, context: Optional[Dict] = None) -> bool:
        """Record action outcome for metacognitive tracking."""
        if check_circuit_breaker("metacog_record"):
            return False

        try:
            self._init_monitor()
            if self._monitor is None:
                return False

            action_id = f"{action_type}_{int(time.time() * 1000)}"

            # Record action (context stored in action history, not passed to monitor)
            self._monitor.record_action(
                action_id=action_id,
                action_type=action_type,
                task_id=task_id,
                duration_ms=int(duration_ms),
                confidence=confidence,
                success=success
            )

            # Track action history for repetition detection (includes context)
            self._action_history.append({
                "action_type": action_type,
                "timestamp": time.time(),
                "success": success,
                "context": context
            })
            # Keep only last 20 actions
            self._action_history = self._action_history[-20:]

            return True
        except Exception as e:
            logger.debug(f"Metacognitive record failed: {e}")
            return False

    def predict_failure(self, task_id: str, duration_ms: float,
                        complexity: float, confidence: float) -> Optional[Dict]:
        """Predict if current task is likely to fail."""
        if check_circuit_breaker("metacog_predict"):
            return None

        try:
            self._init_monitor()
            if self._monitor is None:
                return None

            prediction = self._monitor.predict_failure(
                task_id=task_id,
                duration_ms=duration_ms,
                complexity=complexity,
                confidence=confidence
            )

            return prediction
        except Exception as e:
            logger.debug(f"Failure prediction failed: {e}")
            return None

    def detect_action_repetition(self, action_type: str, window_seconds: float = 30) -> bool:
        """Detect if same action is being repeated (stuck state indicator)."""
        now = time.time()
        recent_same = [
            a for a in self._action_history
            if a["action_type"] == action_type
            and (now - a["timestamp"]) < window_seconds
        ]
        # More than 3 of the same action in 30 seconds suggests stuck
        return len(recent_same) >= 3

    def get_session_summary(self) -> Dict[str, Any]:
        """Get metacognitive summary for session."""
        try:
            self._init_monitor()
            if self._monitor is None:
                return {"error": "Monitor not initialized"}

            # Get accuracy analysis
            accuracy = self._monitor.analyze_accuracy(days=1)

            return {
                "session_id": self.session_id,
                "node_id": self.node_id,
                "action_count": len(self._action_history),
                "accuracy": accuracy
            }
        except Exception as e:
            return {"error": str(e)}


class HookIntegrations:
    """
    Unified interface for all hook integrations.

    Each method is optimized for speed with:
    - Individual circuit breakers per integration
    - Parallel execution where possible
    - Strict timeouts
    - Non-blocking fallbacks
    """

    def __init__(self):
        self.tpu = TPUIntegration()
        self.agi = AGIIntegration()
        self.memory = MemoryIntegration()
        self.voice = VoiceIntegration()
        self.activity = ActivityIntegration()
        self.metacog = MetacognitiveIntegration()
        self.session_id = os.environ.get("CLAUDE_SESSION_ID", "unknown")
        self.node_id = os.uname().nodename

    async def on_session_start(self) -> Dict[str, Any]:
        """
        Session start integrations:
        - Load previous context
        - Initialize AGI state
        - Post to activity dashboard
        """
        results = {}

        # Load previous context (fast)
        context = self.memory.load_session_context(self.session_id)
        results["context_loaded"] = context is not None

        # Record session start event
        self.memory.record_session_event(self.session_id, "session_start", {
            "node_id": self.node_id,
            "context_restored": context is not None
        })

        # Post to activity dashboard
        self.activity.post_event("SessionStart", {
            "session_id": self.session_id,
            "context_restored": context is not None
        })

        return results

    async def on_session_end(self, summary: Dict = None) -> Dict[str, Any]:
        """
        Session end integrations:
        - Save context for continuity
        - Record learning summary
        - Capture metacognitive session summary
        - Trigger consolidation
        """
        results = {}

        # Save session context
        if summary:
            saved = self.memory.save_session_context(self.session_id, summary)
            results["context_saved"] = saved

        # Get metacognitive session summary
        metacog_summary = self.metacog.get_session_summary()
        results["metacognitive_summary"] = metacog_summary

        # Record session end with metacognitive data
        self.memory.record_session_event(self.session_id, "session_end", {
            "summary": summary or {},
            "metacognitive": metacog_summary
        })

        # Post to activity
        self.activity.post_event("SessionEnd", {
            "session_id": self.session_id,
            "action_count": metacog_summary.get("action_count", 0)
        })

        return results

    async def on_pre_tool(self, tool_name: str, tool_input: Dict) -> Dict[str, Any]:
        """
        Pre-tool integrations:
        - Intent classification (for Task tool)
        - Similar action lookup
        - Activity dashboard update
        """
        results = {"tool": tool_name}

        # Intent classification for Task tool (agent spawning)
        if tool_name == "Task":
            prompt = tool_input.get("prompt", "")[:300] if tool_input else ""
            if prompt:
                intent = self.tpu.classify_intent(prompt)
                results["intent"] = intent

                # Get recommended agent
                recommended = self.agi.get_recommended_agent(prompt)
                if recommended:
                    results["recommended_agent"] = recommended

        # Post to activity (async, non-blocking)
        self.activity.post_event("PreToolUse", {
            "tool_name": tool_name,
            "has_input": bool(tool_input)
        })

        return results

    async def on_post_tool(self, tool_name: str, tool_input: Dict,
                          tool_output: str, success: bool,
                          execution_time_ms: float = 0) -> Dict[str, Any]:
        """
        Post-tool integrations:
        - Importance scoring
        - AGI outcome recording
        - Metacognitive action tracking
        - Activity dashboard update
        """
        results = {"tool": tool_name, "success": success}

        # Score importance
        output_text = str(tool_output)[:300] if tool_output else ""
        importance = self.tpu.score_importance(
            f"{tool_name}: {output_text}",
            context="action"
        )
        results["importance"] = importance

        # Record AGI outcome
        self.agi.record_action_outcome(
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=output_text,
            success=success,
            execution_time_ms=execution_time_ms,
            importance_score=importance
        )

        # Record metacognitive action (TRAP framework)
        task_id = self.session_id  # Use session as task context
        self.metacog.record_action(
            action_type=tool_name,
            task_id=task_id,
            duration_ms=execution_time_ms,
            confidence=importance,  # Use importance as proxy for confidence
            success=success,
            context={"input_preview": str(tool_input)[:100] if tool_input else ""}
        )

        # Check for action repetition (stuck state detection)
        if self.metacog.detect_action_repetition(tool_name):
            results["warning"] = f"Repeated {tool_name} detected - possible stuck state"

        # Predict failure for slow operations (>5 seconds)
        if execution_time_ms > 5000:
            prediction = self.metacog.predict_failure(
                task_id=task_id,
                duration_ms=execution_time_ms,
                complexity=0.7,  # Assume moderately complex for slow ops
                confidence=importance
            )
            if prediction and prediction.get("should_fail"):
                results["failure_prediction"] = prediction

        # Post to activity dashboard
        self.activity.post_event("PostToolUse", {
            "tool_name": tool_name,
            "success": success,
            "importance": importance,
            "execution_time_ms": execution_time_ms
        })

        return results

    async def on_user_prompt(self, prompt: str) -> Dict[str, Any]:
        """
        User prompt integrations:
        - Intent classification
        - Context recall
        - Activity update
        """
        results = {}

        # Classify intent
        intent = self.tpu.classify_intent(prompt[:300])
        results["intent"] = intent

        # Score importance
        importance = self.tpu.score_importance(prompt[:300], "memory")
        results["importance"] = importance

        # Activity update
        self.activity.post_event("UserPromptSubmit", {
            "intent": intent.get("intent"),
            "importance": importance
        })

        return results

    async def on_subagent_start(self, agent_type: str, prompt: str) -> Dict[str, Any]:
        """Subagent start integrations."""
        results = {"agent_type": agent_type}

        # Score task importance
        importance = self.tpu.score_importance(prompt[:200], "action")
        results["importance"] = importance

        # Activity update
        self.activity.post_event("SubagentStart", {
            "agent_type": agent_type,
            "importance": importance
        })

        return results

    async def on_subagent_stop(self, agent_type: str, result: str,
                               success: bool) -> Dict[str, Any]:
        """Subagent completion integrations."""
        results = {"agent_type": agent_type, "success": success}

        # Record outcome
        self.agi.record_action_outcome(
            tool_name=f"Task:{agent_type}",
            tool_input={"agent_type": agent_type},
            tool_output=result[:200] if result else "",
            success=success,
            execution_time_ms=0,
            importance_score=0.7 if success else 0.8  # Failures more important
        )

        # Activity update
        self.activity.post_event("SubagentStop", {
            "agent_type": agent_type,
            "success": success
        })

        return results

    async def on_notification(self, message: str, level: str = "info") -> Dict[str, Any]:
        """Notification integrations."""
        results = {"level": level}

        # Voice notification for important messages
        if level in ["warning", "error", "critical"]:
            self.voice.notify(message, level)
            results["voice_notified"] = True

        # Activity update
        self.activity.post_event("Notification", {
            "level": level,
            "message_preview": message[:100]
        })

        return results

    async def on_permission_request(self, tool_name: str,
                                    description: str) -> Dict[str, Any]:
        """Permission request integrations."""
        results = {"tool": tool_name}

        # Voice notification
        self.voice.notify(f"Permission requested for {tool_name}", "warning")

        # Activity update
        self.activity.post_event("PermissionRequest", {
            "tool_name": tool_name,
            "description_preview": description[:100]
        })

        return results

    async def on_stop(self) -> Dict[str, Any]:
        """Stop event integrations."""
        results = {}

        # Save any pending context
        self.memory.record_session_event(self.session_id, "stop", {
            "node_id": self.node_id
        })

        # Activity update
        self.activity.post_event("Stop", {
            "session_id": self.session_id
        })

        return results

    async def on_pre_compact(self) -> Dict[str, Any]:
        """Pre-compact integrations (context about to be compressed)."""
        results = {}

        # Save working memory before compaction
        self.memory.record_session_event(self.session_id, "pre_compact", {
            "node_id": self.node_id
        })

        # Activity update
        self.activity.post_event("PreCompact", {
            "session_id": self.session_id
        })

        return results


# Singleton instance for reuse
_integrations: Optional[HookIntegrations] = None


def get_integrations() -> HookIntegrations:
    """Get singleton integrations instance."""
    global _integrations
    if _integrations is None:
        _integrations = HookIntegrations()
    return _integrations


# CLI interface for shell hooks
if __name__ == "__main__":
    import argparse
    import asyncio

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    elif system == "Linux":
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()


    parser = argparse.ArgumentParser(description="Unified Hook Integrations")
    parser.add_argument("hook", choices=[
        "session_start", "session_end", "pre_tool", "post_tool",
        "user_prompt", "subagent_start", "subagent_stop",
        "notification", "permission_request", "stop", "pre_compact"
    ])
    parser.add_argument("--tool", type=str, help="Tool name")
    parser.add_argument("--input", type=str, help="Tool input JSON")
    parser.add_argument("--output", type=str, help="Tool output")
    parser.add_argument("--success", action="store_true", help="Success flag")
    parser.add_argument("--prompt", type=str, help="Prompt text")
    parser.add_argument("--agent-type", type=str, help="Agent type")
    parser.add_argument("--message", type=str, help="Message")
    parser.add_argument("--level", type=str, default="info", help="Level")
    parser.add_argument("--time-ms", type=float, default=0, help="Execution time")

    args = parser.parse_args()

    integrations = get_integrations()

    async def main():
        if args.hook == "session_start":
            result = await integrations.on_session_start()
        elif args.hook == "session_end":
            result = await integrations.on_session_end()
        elif args.hook == "pre_tool":
            tool_input = json.loads(args.input) if args.input else {}
            result = await integrations.on_pre_tool(args.tool or "unknown", tool_input)
        elif args.hook == "post_tool":
            tool_input = json.loads(args.input) if args.input else {}
            result = await integrations.on_post_tool(
                args.tool or "unknown", tool_input,
                args.output or "", args.success, args.time_ms
            )
        elif args.hook == "user_prompt":
            result = await integrations.on_user_prompt(args.prompt or "")
        elif args.hook == "subagent_start":
            result = await integrations.on_subagent_start(
                args.agent_type or "unknown", args.prompt or ""
            )
        elif args.hook == "subagent_stop":
            result = await integrations.on_subagent_stop(
                args.agent_type or "unknown", args.output or "", args.success
            )
        elif args.hook == "notification":
            result = await integrations.on_notification(args.message or "", args.level)
        elif args.hook == "permission_request":
            result = await integrations.on_permission_request(
                args.tool or "unknown", args.message or ""
            )
        elif args.hook == "stop":
            result = await integrations.on_stop()
        elif args.hook == "pre_compact":
            result = await integrations.on_pre_compact()
        else:
            result = {"error": "Unknown hook"}

        print(json.dumps(result))

    asyncio.run(main())
