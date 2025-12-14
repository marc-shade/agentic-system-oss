#!/usr/bin/env python3
"""
Attention Daemon - The Focus Loop

Based on Free Energy Principle: Attention as precision-weighted prediction error.

This daemon maintains a Markov blanket around attention state and adjusts
focus when there's mismatch between task importance and allocated attention.

Key insight from Friston: Attention is precision - the confidence we place
in sensory signals. High-precision signals get more processing resources.

From Levin: Collective attention emerges from many agents attending to
different aspects. The system self-organizes attention allocation.

Markov Blanket:
- Internal: Current attention distribution, priority beliefs
- External: Task queue, node states, world events
- Sensory: Task updates, completion signals, urgency changes
- Active: Priority adjustments, resource allocation, focus shifts
"""

import asyncio
import json
import logging
import os
import signal
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import math

# Configuration
CONFIG = {
    "check_interval_seconds": 60,  # Check every minute
    "attention_decay_rate": 0.95,  # How fast attention decays
    "urgency_boost": 1.5,          # Multiplier for urgent tasks
    "memory_db_path": os.path.expanduser("~/.claude/enhanced_memories/memory.db"),
    "state_file": "/mnt/agentic-system/databases/attention_daemon_state.json",
    "log_file": "/var/log/attention-daemon.log",
    "max_focus_items": 10,         # Max items in active focus
    "salience_threshold": 0.5,     # Minimum salience to consider
    "prediction_horizon_hours": 4,  # How far ahead to predict needs
}

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(CONFIG["log_file"], mode='a')
        if os.access(os.path.dirname(CONFIG["log_file"]) or '.', os.W_OK)
        else logging.StreamHandler()
    ]
)
logger = logging.getLogger("AttentionDaemon")


@dataclass
class AttentionItem:
    """Something that needs attention"""
    id: str
    source: str  # task, goal, node_message, knowledge_gap, scheduled
    title: str
    raw_importance: float  # Base importance 0-1
    urgency: float  # Time-sensitivity 0-1
    current_attention: float  # How much attention it's getting
    last_attended: Optional[datetime]
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def computed_priority(self) -> float:
        """Priority = importance * urgency * decay factor"""
        decay = 1.0
        if self.last_attended:
            hours_since = (datetime.now() - self.last_attended).total_seconds() / 3600
            decay = min(2.0, 1.0 + (hours_since * 0.1))  # Grows if neglected
        return self.raw_importance * (1 + self.urgency) * decay


@dataclass
class AttentionBlanket:
    """
    Markov blanket for attention state.

    Internal states: What we believe about attention needs
    Sensory states: Observations from the environment
    Active states: Actions to adjust attention
    """
    # Current attention distribution (item_id -> attention_weight)
    attention_distribution: Dict[str, float] = field(default_factory=dict)

    # Predicted importance for each item
    predicted_importance: Dict[str, float] = field(default_factory=dict)

    # Free energy history (prediction errors)
    free_energy_history: List[float] = field(default_factory=list)

    def compute_free_energy(self, items: List[AttentionItem]) -> float:
        """
        Free energy = mismatch between attention allocation and importance.

        High free energy means we're attending to wrong things.
        """
        if not items:
            return 0.0

        total_error = 0.0
        for item in items:
            current = self.attention_distribution.get(item.id, 0.0)
            ideal = item.computed_priority

            # Squared error weighted by importance
            error = (current - ideal) ** 2 * item.raw_importance
            total_error += error

        # Normalize
        free_energy = math.sqrt(total_error / len(items))
        self.free_energy_history.append(free_energy)

        # Keep history bounded
        if len(self.free_energy_history) > 100:
            self.free_energy_history = self.free_energy_history[-100:]

        return free_energy

    def get_attention_gradient(self) -> float:
        """How is free energy changing? Negative = improving"""
        if len(self.free_energy_history) < 2:
            return 0.0
        return self.free_energy_history[-1] - self.free_energy_history[-2]


class AttentionDaemon:
    """
    Attention allocation daemon.
    Minimizes free energy by aligning attention with importance.
    """

    def __init__(self):
        self.running = True
        self.blanket = AttentionBlanket()
        self.state = self._load_state()

        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGUSR1, self._handle_rebalance)

    def _load_state(self) -> Dict:
        state_path = Path(CONFIG["state_file"])
        if state_path.exists():
            try:
                data = json.loads(state_path.read_text())
                # Restore blanket state
                self.blanket.attention_distribution = data.get("attention_distribution", {})
                self.blanket.predicted_importance = data.get("predicted_importance", {})
                return data
            except:
                pass
        return {
            "total_rebalances": 0,
            "items_promoted": 0,
            "items_demoted": 0,
            "last_rebalance": None,
            "attention_distribution": {},
            "predicted_importance": {},
        }

    def _save_state(self):
        state_path = Path(CONFIG["state_file"])
        state_path.parent.mkdir(parents=True, exist_ok=True)

        self.state["attention_distribution"] = self.blanket.attention_distribution
        self.state["predicted_importance"] = self.blanket.predicted_importance

        state_path.write_text(json.dumps(self.state, indent=2, default=str))

    def _handle_shutdown(self, signum, frame):
        logger.info("Shutting down attention daemon")
        self.running = False

    def _handle_rebalance(self, signum, frame):
        logger.info("Forcing attention rebalance (SIGUSR1)")
        asyncio.create_task(self._attention_cycle(force=True))

    # ═══════════════════════════════════════════════════════════════════
    # SENSORY - Observe what needs attention
    # ═══════════════════════════════════════════════════════════════════

    async def sense_attention_items(self) -> List[AttentionItem]:
        """Sense all items that might need attention"""
        items = []

        # Sense from different sources
        items.extend(await self._sense_pending_tasks())
        items.extend(await self._sense_active_goals())
        items.extend(await self._sense_knowledge_gaps())
        items.extend(await self._sense_high_salience_memories())
        items.extend(await self._sense_node_requests())

        return items

    async def _sense_pending_tasks(self) -> List[AttentionItem]:
        """Get pending tasks from agent-runtime"""
        items = []
        try:
            db_path = Path(CONFIG["memory_db_path"]).parent / "agent_runtime.db"
            if not db_path.exists():
                # Try the main memory db
                db_path = Path(CONFIG["memory_db_path"])

            if db_path.exists():
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()

                # Check if tasks table exists
                cursor.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='tasks'
                """)
                if cursor.fetchone():
                    cursor.execute("""
                        SELECT id, title, description, priority, status, created_at
                        FROM tasks
                        WHERE status IN ('pending', 'in_progress')
                        ORDER BY priority DESC
                        LIMIT 20
                    """)

                    for row in cursor.fetchall():
                        priority = row[3] / 10.0 if row[3] else 0.5  # Normalize to 0-1
                        created = datetime.fromisoformat(row[5]) if row[5] else datetime.now()
                        age_hours = (datetime.now() - created).total_seconds() / 3600

                        # Urgency increases with age
                        urgency = min(1.0, age_hours / 24)

                        items.append(AttentionItem(
                            id=f"task_{row[0]}",
                            source="task",
                            title=row[1] or "Untitled task",
                            raw_importance=priority,
                            urgency=urgency,
                            current_attention=self.blanket.attention_distribution.get(f"task_{row[0]}", 0.0),
                            last_attended=None,
                            metadata={"description": row[2], "status": row[4]}
                        ))

                conn.close()
        except Exception as e:
            logger.debug(f"Failed to sense tasks: {e}")
        return items

    async def _sense_active_goals(self) -> List[AttentionItem]:
        """Get active goals"""
        items = []
        try:
            db_path = Path(CONFIG["memory_db_path"]).parent / "agent_runtime.db"
            if db_path.exists():
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='goals'
                """)
                if cursor.fetchone():
                    cursor.execute("""
                        SELECT id, name, description, status, created_at
                        FROM goals
                        WHERE status = 'active'
                        ORDER BY created_at DESC
                        LIMIT 10
                    """)

                    for row in cursor.fetchall():
                        items.append(AttentionItem(
                            id=f"goal_{row[0]}",
                            source="goal",
                            title=row[1] or "Untitled goal",
                            raw_importance=0.8,  # Goals are high importance
                            urgency=0.3,  # But typically not urgent
                            current_attention=self.blanket.attention_distribution.get(f"goal_{row[0]}", 0.0),
                            last_attended=None,
                            metadata={"description": row[2]}
                        ))

                conn.close()
        except Exception as e:
            logger.debug(f"Failed to sense goals: {e}")
        return items

    async def _sense_knowledge_gaps(self) -> List[AttentionItem]:
        """Get open knowledge gaps"""
        items = []
        try:
            db_path = Path(CONFIG["memory_db_path"])
            if db_path.exists():
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='knowledge_gaps'
                """)
                if cursor.fetchone():
                    cursor.execute("""
                        SELECT id, domain, gap_description, severity, status
                        FROM knowledge_gaps
                        WHERE status IN ('open', 'learning')
                        AND severity >= ?
                        ORDER BY severity DESC
                        LIMIT 10
                    """, (CONFIG["salience_threshold"],))

                    for row in cursor.fetchall():
                        items.append(AttentionItem(
                            id=f"gap_{row[0]}",
                            source="knowledge_gap",
                            title=f"{row[1]}: {row[2][:50]}",
                            raw_importance=row[3],
                            urgency=0.2,  # Knowledge gaps aren't usually urgent
                            current_attention=self.blanket.attention_distribution.get(f"gap_{row[0]}", 0.0),
                            last_attended=None,
                            metadata={"domain": row[1], "full_description": row[2]}
                        ))

                conn.close()
        except Exception as e:
            logger.debug(f"Failed to sense knowledge gaps: {e}")
        return items

    async def _sense_high_salience_memories(self) -> List[AttentionItem]:
        """Get high-salience memories that need attention"""
        items = []
        try:
            db_path = Path(CONFIG["memory_db_path"])
            if db_path.exists():
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='emotional_tags'
                """)
                if cursor.fetchone():
                    cursor.execute("""
                        SELECT entity_id, salience_score, primary_emotion, context_type
                        FROM emotional_tags
                        WHERE salience_score >= ?
                        ORDER BY salience_score DESC, created_at DESC
                        LIMIT 5
                    """, (0.7,))  # Only very high salience

                    for row in cursor.fetchall():
                        items.append(AttentionItem(
                            id=f"salience_{row[0]}",
                            source="salience",
                            title=f"High salience memory ({row[2] or 'neutral'})",
                            raw_importance=row[1],
                            urgency=0.4 if row[3] == "failure" else 0.2,
                            current_attention=self.blanket.attention_distribution.get(f"salience_{row[0]}", 0.0),
                            last_attended=None,
                            metadata={"emotion": row[2], "context": row[3]}
                        ))

                conn.close()
        except Exception as e:
            logger.debug(f"Failed to sense salience: {e}")
        return items

    async def _sense_node_requests(self) -> List[AttentionItem]:
        """Get pending inter-node communication requests"""
        items = []
        try:
            # Check node-chat database
            db_path = Path(os.path.expanduser("~/.claude/node_chat.db"))
            if db_path.exists():
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='messages'
                """)
                if cursor.fetchone():
                    cursor.execute("""
                        SELECT id, from_node, subject, priority, created_at
                        FROM messages
                        WHERE status = 'pending'
                        AND to_node = ?
                        ORDER BY priority DESC, created_at ASC
                        LIMIT 5
                    """, ("macpro51",))

                    for row in cursor.fetchall():
                        priority_map = {"low": 0.3, "normal": 0.5, "high": 0.7, "urgent": 0.9}
                        importance = priority_map.get(row[3], 0.5)

                        items.append(AttentionItem(
                            id=f"node_{row[0]}",
                            source="node_message",
                            title=f"From {row[1]}: {row[2][:30]}",
                            raw_importance=importance,
                            urgency=0.8 if row[3] == "urgent" else 0.4,
                            current_attention=self.blanket.attention_distribution.get(f"node_{row[0]}", 0.0),
                            last_attended=None,
                            metadata={"from_node": row[1], "subject": row[2]}
                        ))

                conn.close()
        except Exception as e:
            logger.debug(f"Failed to sense node requests: {e}")
        return items

    # ═══════════════════════════════════════════════════════════════════
    # PREDICTION - Predict optimal attention allocation
    # ═══════════════════════════════════════════════════════════════════

    def predict_attention_needs(self, items: List[AttentionItem]) -> Dict[str, float]:
        """
        Predict optimal attention distribution.

        Uses softmax over computed priorities to get a probability distribution.
        """
        if not items:
            return {}

        # Compute priorities
        priorities = {item.id: item.computed_priority for item in items}

        # Softmax normalization
        max_priority = max(priorities.values())
        exp_priorities = {
            k: math.exp(v - max_priority)  # Subtract max for numerical stability
            for k, v in priorities.items()
        }
        total = sum(exp_priorities.values())

        # Normalized attention distribution
        predicted = {k: v / total for k, v in exp_priorities.items()}

        # Store prediction
        self.blanket.predicted_importance = predicted

        return predicted

    # ═══════════════════════════════════════════════════════════════════
    # ACTIVE - Adjust attention to minimize free energy
    # ═══════════════════════════════════════════════════════════════════

    async def rebalance_attention(self, items: List[AttentionItem]) -> Dict[str, Any]:
        """
        Rebalance attention distribution to minimize free energy.

        This is the active inference step - taking action to reduce prediction error.
        """
        result = {
            "items_processed": len(items),
            "promotions": 0,
            "demotions": 0,
            "free_energy_before": 0.0,
            "free_energy_after": 0.0,
        }

        if not items:
            return result

        # Compute current free energy
        result["free_energy_before"] = self.blanket.compute_free_energy(items)

        # Predict optimal distribution
        predicted = self.predict_attention_needs(items)

        # Gradually shift attention toward prediction (learning rate)
        learning_rate = 0.3
        new_distribution = {}

        for item in items:
            current = self.blanket.attention_distribution.get(item.id, 0.0)
            target = predicted.get(item.id, 0.0)

            # Smooth update
            new_value = current + learning_rate * (target - current)
            new_distribution[item.id] = new_value

            # Track promotions/demotions
            if new_value > current + 0.05:
                result["promotions"] += 1
            elif new_value < current - 0.05:
                result["demotions"] += 1

        # Update blanket
        self.blanket.attention_distribution = new_distribution

        # Compute new free energy
        for item in items:
            item.current_attention = new_distribution.get(item.id, 0.0)
        result["free_energy_after"] = self.blanket.compute_free_energy(items)

        # Log significant items
        top_items = sorted(items, key=lambda x: x.current_attention, reverse=True)[:5]
        if top_items:
            logger.info("Top attention items:")
            for item in top_items:
                logger.info(f"  [{item.source}] {item.title[:40]}: {item.current_attention:.3f}")

        # Update state
        self.state["total_rebalances"] += 1
        self.state["items_promoted"] += result["promotions"]
        self.state["items_demoted"] += result["demotions"]
        self.state["last_rebalance"] = datetime.now().isoformat()

        return result

    async def should_alert_bootstrap(self, items: List[AttentionItem]) -> Optional[str]:
        """
        Check if any attention item is urgent enough to wake the bootstrap daemon.

        Returns a prompt if awakening is needed, None otherwise.
        """
        # Find items with high urgency AND high importance
        critical_items = [
            item for item in items
            if item.urgency > 0.8 and item.raw_importance > 0.7
        ]

        if not critical_items:
            return None

        # Build alert prompt
        top_critical = sorted(critical_items, key=lambda x: x.computed_priority, reverse=True)[0]

        prompt = f"""ATTENTION ALERT: Critical item requires immediate processing

Source: {top_critical.source}
Title: {top_critical.title}
Importance: {top_critical.raw_importance:.2f}
Urgency: {top_critical.urgency:.2f}
Priority Score: {top_critical.computed_priority:.2f}

Metadata: {json.dumps(top_critical.metadata, default=str)}

Please address this item immediately."""

        logger.warning(f"Critical attention item detected: {top_critical.title}")
        return prompt

    # ═══════════════════════════════════════════════════════════════════
    # MAIN LOOP - Attention allocation cycle
    # ═══════════════════════════════════════════════════════════════════

    async def _attention_cycle(self, force: bool = False):
        """Execute one attention cycle"""
        # Sense all items
        items = await self.sense_attention_items()

        if not items:
            logger.debug("No items requiring attention")
            return

        logger.info(f"Processing {len(items)} attention items")

        # Rebalance attention
        result = await self.rebalance_attention(items)

        logger.info(
            f"Attention rebalanced: {result['promotions']} promoted, "
            f"{result['demotions']} demoted, "
            f"free energy: {result['free_energy_before']:.3f} -> {result['free_energy_after']:.3f}"
        )

        # Check for critical items
        alert_prompt = await self.should_alert_bootstrap(items)
        if alert_prompt:
            await self._send_bootstrap_alert(alert_prompt)

        self._save_state()

    async def _send_bootstrap_alert(self, prompt: str):
        """Send alert to bootstrap daemon via file signal"""
        try:
            alert_path = Path("/mnt/agentic-system/databases/bootstrap_alerts")
            alert_path.mkdir(parents=True, exist_ok=True)

            alert_file = alert_path / f"attention_alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            alert_file.write_text(json.dumps({
                "source": "attention_daemon",
                "timestamp": datetime.now().isoformat(),
                "trigger": "critical_attention_item",
                "prompt": prompt,
                "priority": 0.9
            }, indent=2))

            logger.info(f"Sent bootstrap alert: {alert_file}")
        except Exception as e:
            logger.error(f"Failed to send bootstrap alert: {e}")

    async def run(self):
        """Main daemon loop"""
        logger.info("═══ ATTENTION DAEMON STARTING ═══")
        logger.info("Focus allocation active")
        logger.info(f"Check interval: {CONFIG['check_interval_seconds']}s")
        logger.info(f"Salience threshold: {CONFIG['salience_threshold']}")

        while self.running:
            try:
                await self._attention_cycle()
                await asyncio.sleep(CONFIG["check_interval_seconds"])

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in attention cycle: {e}")
                await asyncio.sleep(60)

        logger.info("═══ ATTENTION DAEMON STOPPED ═══")


def main():
    daemon = AttentionDaemon()
    try:
        asyncio.run(daemon.run())
    except KeyboardInterrupt:
        logger.info("Interrupted")
    except Exception as e:
        logger.error(f"Crashed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
