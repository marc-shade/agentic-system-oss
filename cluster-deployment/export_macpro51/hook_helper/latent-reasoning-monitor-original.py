#!/usr/bin/env python3
"""
Latent Reasoning Monitor - Phase 1 Implementation
Tracks execution patterns to establish baseline for optimization

Based on Oxford/Buenos Aires research:
- Base models know how to reason
- Only 12% intervention rate needed
- 88% of time, base model runs unguided

This monitor tracks:
1. When agents are spawned vs direct execution
2. Success rates for each approach
3. Token usage and costs
4. Task completion times
5. Error patterns and retry counts
"""

import json
import sqlite3
import sys
import os
from datetime import datetime
from pathlib import Path

# Database path
DB_PATH = Path.home() / ".claude" / "latent-reasoning-monitor.db"

class LatentReasoningMonitor:
    """Monitor and analyze execution patterns"""

    def __init__(self):
        self.db_path = DB_PATH
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database for tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Task executions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                task_type TEXT NOT NULL,
                complexity INTEGER,
                execution_method TEXT NOT NULL,
                tool_name TEXT,
                success BOOLEAN,
                tokens_used INTEGER,
                duration_seconds REAL,
                error_count INTEGER DEFAULT 0,
                agent_type TEXT,
                description TEXT,
                confidence_score REAL,
                gpt5_used BOOLEAN DEFAULT 0,
                notes TEXT
            )
        """)

        # Reasoning mode activations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reasoning_activations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                mode_name TEXT NOT NULL,
                trigger_reason TEXT,
                success BOOLEAN,
                duration_seconds REAL
            )
        """)

        # Weekly aggregates table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weekly_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week_start TEXT NOT NULL,
                total_tasks INTEGER,
                direct_execution_count INTEGER,
                steering_prompt_count INTEGER,
                agent_spawn_count INTEGER,
                avg_success_rate REAL,
                total_tokens_used INTEGER,
                cost_savings_estimate REAL,
                notes TEXT
            )
        """)

        conn.commit()
        conn.close()

    def log_execution(self, execution_data):
        """Log a task execution"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO task_executions (
                timestamp, task_type, complexity, execution_method,
                tool_name, success, tokens_used, duration_seconds,
                error_count, agent_type, description, confidence_score,
                gpt5_used, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            execution_data.get('timestamp', datetime.now().isoformat()),
            execution_data.get('task_type', 'unknown'),
            execution_data.get('complexity', 5),
            execution_data.get('execution_method', 'direct'),
            execution_data.get('tool_name'),
            execution_data.get('success', True),
            execution_data.get('tokens_used', 0),
            execution_data.get('duration_seconds', 0.0),
            execution_data.get('error_count', 0),
            execution_data.get('agent_type'),
            execution_data.get('description'),
            execution_data.get('confidence_score'),
            execution_data.get('gpt5_used', False),
            execution_data.get('notes')
        ))

        conn.commit()
        conn.close()

    def classify_execution_method(self, tool_name, tool_args):
        """Classify execution method based on tool usage"""
        if tool_name == "Task":
            return "agent_spawn", tool_args.get("subagent_type", "unknown")
        elif tool_name in ["Write", "Edit", "MultiEdit", "Read", "Bash", "Grep", "Glob"]:
            return "direct_execution", None
        elif tool_name.startswith("mcp__"):
            return "mcp_tool", tool_name
        else:
            return "other", None

    def estimate_task_complexity(self, tool_name, tool_args):
        """Estimate task complexity on 1-10 scale"""
        # Simple heuristic - can be improved with ML later
        if tool_name == "Task":
            # Agent spawn suggests higher complexity
            description = tool_args.get("description", "")
            prompt = tool_args.get("prompt", "")
            combined = description + " " + prompt

            # Complexity indicators
            if any(word in combined.lower() for word in ["complex", "multi", "comprehensive", "full"]):
                return 8
            elif any(word in combined.lower() for word in ["simple", "quick", "basic"]):
                return 3
            else:
                return 6

        elif tool_name in ["Write", "Edit"]:
            return 2
        elif tool_name == "MultiEdit":
            return 4
        elif tool_name == "Bash":
            command = tool_args.get("command", "")
            if "&&" in command or ";" in command:
                return 5
            return 3
        elif tool_name.startswith("mcp__"):
            return 4

        return 5  # Default medium complexity

    def get_baseline_metrics(self, days=7):
        """Get baseline metrics for the last N days"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Calculate cutoff date
        cutoff = datetime.now().timestamp() - (days * 24 * 3600)
        cutoff_iso = datetime.fromtimestamp(cutoff).isoformat()

        # Total executions
        cursor.execute("""
            SELECT COUNT(*) FROM task_executions
            WHERE timestamp >= ?
        """, (cutoff_iso,))
        total_tasks = cursor.fetchone()[0]

        # By execution method
        cursor.execute("""
            SELECT execution_method, COUNT(*), AVG(success), AVG(tokens_used)
            FROM task_executions
            WHERE timestamp >= ?
            GROUP BY execution_method
        """, (cutoff_iso,))
        by_method = cursor.fetchall()

        # By complexity level
        cursor.execute("""
            SELECT complexity, COUNT(*), AVG(success)
            FROM task_executions
            WHERE timestamp >= ?
            GROUP BY complexity
            ORDER BY complexity
        """, (cutoff_iso,))
        by_complexity = cursor.fetchall()

        # Agent spawn rate
        cursor.execute("""
            SELECT
                SUM(CASE WHEN execution_method = 'agent_spawn' THEN 1 ELSE 0 END) as spawns,
                COUNT(*) as total
            FROM task_executions
            WHERE timestamp >= ?
        """, (cutoff_iso,))
        spawn_stats = cursor.fetchone()
        spawn_rate = spawn_stats[0] / spawn_stats[1] if spawn_stats[1] > 0 else 0

        conn.close()

        return {
            'total_tasks': total_tasks,
            'by_method': dict((m[0], {
                'count': m[1],
                'success_rate': m[2] or 0,
                'avg_tokens': m[3] or 0
            }) for m in by_method),
            'by_complexity': [(c[0], c[1], c[2]) for c in by_complexity],
            'agent_spawn_rate': spawn_rate,
            'target_spawn_rate': 0.12  # Research target: 12%
        }

    def generate_weekly_report(self):
        """Generate weekly analysis report"""
        metrics = self.get_baseline_metrics(days=7)

        report = {
            'timestamp': datetime.now().isoformat(),
            'period': 'last_7_days',
            'total_tasks': metrics['total_tasks'],
            'agent_spawn_rate': metrics['agent_spawn_rate'],
            'target_spawn_rate': metrics['target_spawn_rate'],
            'optimization_opportunity': metrics['agent_spawn_rate'] - metrics['target_spawn_rate'],
            'by_method': metrics['by_method'],
            'by_complexity': metrics['by_complexity']
        }

        # Save report
        report_path = Path.home() / ".claude" / "latent-reasoning-weekly-report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        return report

    def should_suggest_steering(self, tool_name, tool_args, complexity):
        """Heuristic: should we suggest using steering prompt instead of agent?"""
        if tool_name != "Task":
            return False

        # Medium complexity tasks are good candidates
        if 4 <= complexity <= 6:
            agent_type = tool_args.get("subagent_type", "")

            # Well-defined task types that might work with steering
            steering_candidates = [
                "research-coordinator",
                "documentation-researcher",
                "code-reviewer",
                "debugger"
            ]

            if any(candidate in agent_type for candidate in steering_candidates):
                return True

        return False


def main():
    """Hook integration point"""
    try:
        hook_input = json.loads(sys.stdin.read())
        tool_name = hook_input.get("tool", "")
        tool_args = hook_input.get("arguments", {})

        monitor = LatentReasoningMonitor()

        # Classify execution
        execution_method, agent_type = monitor.classify_execution_method(tool_name, tool_args)
        complexity = monitor.estimate_task_complexity(tool_name, tool_args)

        # Extract confidence if available
        confidence_score = None
        gpt5_used = False
        if tool_name == "Task":
            # Check for confidence annotations
            prompt = tool_args.get("prompt", "")
            if "confidence:" in prompt.lower():
                # Extract confidence percentage
                import re
                match = re.search(r'confidence:\s*(\d+)%', prompt.lower())
                if match:
                    confidence_score = float(match.group(1)) / 100

            # Check for GPT-5 annotations
            if "[GPT-5]" in prompt or "gpt5" in tool_args.get("description", "").lower():
                gpt5_used = True

        # Log execution
        execution_data = {
            'timestamp': datetime.now().isoformat(),
            'task_type': tool_name,
            'complexity': complexity,
            'execution_method': execution_method,
            'tool_name': tool_name,
            'agent_type': agent_type,
            'description': tool_args.get("description", ""),
            'confidence_score': confidence_score,
            'gpt5_used': gpt5_used,
            'success': True,  # Will be updated by post-hook
            'notes': f"Tool: {tool_name}"
        }

        monitor.log_execution(execution_data)

        # Check if steering prompt might be better
        if monitor.should_suggest_steering(tool_name, tool_args, complexity):
            # Store suggestion for later analysis
            execution_data['notes'] = f"STEERING_CANDIDATE: {agent_type}"
            monitor.log_execution({
                **execution_data,
                'execution_method': 'steering_suggestion'
            })

    except Exception as e:
        # Fail silently - monitoring should not break execution
        pass

    # Always allow execution
    return json.dumps({"allow": True})


if __name__ == "__main__":
    result = main()
    print(result)
