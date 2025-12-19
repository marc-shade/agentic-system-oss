#!/usr/bin/env python3
"""
Latent Reasoning Memory Sync
Synchronizes monitoring data with enhanced-memory MCP for learning
"""

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DB_PATH = Path.home() / ".claude" / "latent-reasoning-monitor.db"

class MemorySyncService:
    """Sync monitoring data to enhanced-memory for long-term learning"""

    def __init__(self):
        self.db_path = DB_PATH

    def export_for_memory(self, days=7):
        """Export execution patterns for enhanced-memory storage"""
        if not self.db_path.exists():
            return []

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get recent high-value learnings
        cursor.execute("""
            SELECT
                task_type,
                execution_method,
                agent_type,
                complexity,
                AVG(success) as success_rate,
                AVG(tokens_used) as avg_tokens,
                COUNT(*) as frequency,
                AVG(confidence_score) as avg_confidence
            FROM task_executions
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
            GROUP BY task_type, execution_method, agent_type, complexity
            HAVING COUNT(*) >= 3
            ORDER BY frequency DESC
        """, (days,))

        patterns = cursor.fetchall()
        conn.close()

        # Convert to memory entities
        memory_entities = []

        for pattern in patterns:
            (task_type, exec_method, agent_type, complexity,
             success_rate, avg_tokens, frequency, avg_confidence) = pattern

            entity_name = f"latent-reasoning-pattern-{task_type}-{exec_method}-{datetime.now().strftime('%Y%m%d')}"

            observations = [
                f"task_type:{task_type}",
                f"execution_method:{exec_method}",
                f"complexity:{complexity}",
                f"success_rate:{success_rate:.2f}",
                f"avg_tokens:{int(avg_tokens)}",
                f"frequency:{frequency}",
                f"timestamp:{datetime.now().isoformat()}"
            ]

            if agent_type:
                observations.append(f"agent_type:{agent_type}")

            if avg_confidence:
                observations.append(f"avg_confidence:{avg_confidence:.2f}")

            # Determine if this is a steering candidate
            if exec_method == "agent_spawn" and 4 <= complexity <= 6 and frequency >= 5:
                observations.append("steering_candidate:true")
                observations.append(f"optimization_potential:high")

            memory_entities.append({
                "name": entity_name,
                "entityType": "execution_pattern",
                "observations": observations
            })

        return memory_entities

    def create_weekly_summary_entity(self):
        """Create weekly summary entity for memory"""
        if not self.db_path.exists():
            return None

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get weekly aggregates
        cursor.execute("""
            SELECT
                COUNT(*) as total_tasks,
                AVG(success) as success_rate,
                SUM(CASE WHEN execution_method = 'agent_spawn' THEN 1 ELSE 0 END) as spawns,
                SUM(tokens_used) as total_tokens
            FROM task_executions
            WHERE timestamp >= datetime('now', '-7 days')
        """)

        summary = cursor.fetchone()
        conn.close()

        if not summary or summary[0] == 0:
            return None

        total_tasks, success_rate, spawns, total_tokens = summary
        spawn_rate = spawns / total_tasks if total_tasks > 0 else 0

        entity_name = f"latent-reasoning-weekly-{datetime.now().strftime('%Y-W%W')}"

        observations = [
            f"period:weekly",
            f"total_tasks:{total_tasks}",
            f"success_rate:{success_rate:.2f}",
            f"agent_spawn_rate:{spawn_rate:.2f}",
            f"target_spawn_rate:0.12",
            f"spawn_rate_delta:{spawn_rate - 0.12:.2f}",
            f"total_tokens:{total_tokens}",
            f"timestamp:{datetime.now().isoformat()}"
        ]

        # Add optimization insights
        if spawn_rate > 0.20:
            observations.append("optimization_priority:high")
            observations.append("insight:spawn_rate_significantly_above_target")
        elif spawn_rate > 0.15:
            observations.append("optimization_priority:medium")
            observations.append("insight:spawn_rate_above_target")
        else:
            observations.append("optimization_priority:low")
            observations.append("insight:spawn_rate_near_target")

        return {
            "name": entity_name,
            "entityType": "weekly_summary",
            "observations": observations
        }

    def format_for_mcp(self):
        """Format data for MCP tool consumption"""
        patterns = self.export_for_memory(days=7)
        weekly = self.create_weekly_summary_entity()

        entities = patterns
        if weekly:
            entities.append(weekly)

        return {
            "entities": entities,
            "metadata": {
                "source": "latent_reasoning_monitor",
                "timestamp": datetime.now().isoformat(),
                "entity_count": len(entities)
            }
        }


def main():
    """Sync to enhanced-memory"""
    service = MemorySyncService()
    data = service.format_for_mcp()

    # Output for MCP consumption
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
