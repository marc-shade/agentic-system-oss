#!/usr/bin/env python3
"""
Latent Reasoning Monitor - Enhanced with AgentDebug Error Taxonomy
Phase 1 + Error Detection Integration

Based on:
1. Oxford/Buenos Aires research: Base models know how to reason
2. AgentDebug research (UIUC/Stanford/AMD): 5-module error taxonomy

This enhanced monitor tracks:
1. Execution patterns (agent spawn vs direct)
2. Error patterns using AgentDebug taxonomy
3. Error cascades and propagation
4. Quality metrics for steering optimization
5. Root cause analysis data
"""

import json
import sqlite3
import sys
import os
import re
from datetime import datetime
from pathlib import Path

# Database path
DB_PATH = Path.home() / ".claude" / "latent-reasoning-monitor.db"

class AgentDebugErrorTaxonomy:
    """AgentDebug 5-module error taxonomy"""

    ERROR_TAXONOMY = {
        'memory': {
            'over_simplification': {
                'severity': 'moderate',
                'description': 'Memory summary lost critical constraints or details',
                'patterns': ['too generic', 'missing context', 'lost constraint']
            },
            'hallucination': {
                'severity': 'critical',
                'description': 'Memory contains false or fabricated information',
                'patterns': ['not mentioned', 'fabricated', 'incorrect fact']
            },
            'retrieval_failure': {
                'severity': 'moderate',
                'description': 'Failed to retrieve relevant context',
                'patterns': ['missing context', 'forgot previous', 'context loss']
            }
        },
        'reflection': {
            'progress_misjudge': {
                'severity': 'moderate',
                'description': 'Incorrectly assessed task progress',
                'patterns': ['wrong assessment', 'misjudged progress']
            },
            'outcome_misinterpretation': {
                'severity': 'critical',
                'description': 'Misinterpreted action outcomes',
                'patterns': ['wrong interpretation', 'incorrect outcome']
            },
            'causal_misattribution': {
                'severity': 'moderate',
                'description': 'Attributed wrong causes to effects',
                'patterns': ['wrong cause', 'incorrect attribution']
            }
        },
        'planning': {
            'constraint_ignorance': {
                'severity': 'critical',
                'description': 'Planning ignored task constraints',
                'patterns': ['ignored constraint', 'violated requirement']
            },
            'impossible_action': {
                'severity': 'critical',
                'description': 'Planned action not in admissible set',
                'patterns': ['not possible', 'invalid action']
            },
            'inefficient_plan': {
                'severity': 'low',
                'description': 'Plan works but is inefficient',
                'patterns': ['inefficient', 'unnecessary steps']
            }
        },
        'action': {
            'format_error': {
                'severity': 'moderate',
                'description': 'Action output in wrong format',
                'patterns': ['wrong format', 'invalid syntax']
            },
            'parameter_error': {
                'severity': 'moderate',
                'description': 'Action parameters incorrect',
                'patterns': ['wrong parameter', 'missing argument']
            },
            'misalignment': {
                'severity': 'critical',
                'description': 'Action does not align with plan',
                'patterns': ['not aligned', 'different from plan']
            }
        },
        'system': {
            'step_limit': {
                'severity': 'high',
                'description': 'Exhausted maximum steps',
                'patterns': ['step limit', 'max iterations']
            },
            'tool_execution_error': {
                'severity': 'high',
                'description': 'Tool or API call failed',
                'patterns': ['tool failed', 'execution error', 'api error']
            },
            'llm_limit': {
                'severity': 'high',
                'description': 'Context length or output limit exceeded',
                'patterns': ['context limit', 'too long', 'token limit']
            }
        }
    }

    @classmethod
    def detect_error_in_text(cls, text, module_hint=None):
        """
        Detect errors in text using pattern matching
        Returns: (module, error_type, severity) or None
        """
        if not text:
            return None

        text_lower = text.lower()

        # Check specific module if hinted
        modules_to_check = [module_hint] if module_hint else cls.ERROR_TAXONOMY.keys()

        for module in modules_to_check:
            if module not in cls.ERROR_TAXONOMY:
                continue

            for error_type, error_info in cls.ERROR_TAXONOMY[module].items():
                for pattern in error_info['patterns']:
                    if pattern in text_lower:
                        return (module, error_type, error_info['severity'])

        return None


class LatentReasoningMonitor:
    """Enhanced monitor with error taxonomy tracking"""

    def __init__(self):
        self.db_path = DB_PATH
        self.error_taxonomy = AgentDebugErrorTaxonomy()
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database with error tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Enhanced task executions table with error taxonomy
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
                notes TEXT,
                -- AgentDebug error tracking
                error_module TEXT,
                error_type TEXT,
                error_severity TEXT,
                error_evidence TEXT,
                is_cascade BOOLEAN DEFAULT 0,
                root_cause_step INTEGER
            )
        """)

        # Error patterns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS error_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                agent_type TEXT,
                execution_method TEXT,
                error_module TEXT NOT NULL,
                error_type TEXT NOT NULL,
                error_severity TEXT NOT NULL,
                frequency INTEGER DEFAULT 1,
                last_seen TEXT NOT NULL
            )
        """)

        # Quality metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quality_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                agent_type TEXT,
                execution_method TEXT,
                total_executions INTEGER,
                success_count INTEGER,
                error_count INTEGER,
                critical_error_count INTEGER,
                cascade_count INTEGER,
                avg_tokens INTEGER,
                success_rate REAL,
                error_rate REAL,
                critical_error_rate REAL
            )
        """)

        # Existing tables
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
        """Log a task execution with error detection"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Detect errors in notes/description
        error_info = None
        notes = execution_data.get('notes', '')
        description = execution_data.get('description', '')
        combined_text = f"{notes} {description}"

        if combined_text.strip():
            error_info = self.error_taxonomy.detect_error_in_text(combined_text)

        # Extract error details
        error_module = execution_data.get('error_module')
        error_type = execution_data.get('error_type')
        error_severity = execution_data.get('error_severity')

        # Use detected errors if not explicitly provided
        if not error_module and error_info:
            error_module, error_type, error_severity = error_info

        cursor.execute("""
            INSERT INTO task_executions (
                timestamp, task_type, complexity, execution_method,
                tool_name, success, tokens_used, duration_seconds,
                error_count, agent_type, description, confidence_score,
                gpt5_used, notes,
                error_module, error_type, error_severity, error_evidence,
                is_cascade, root_cause_step
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            execution_data.get('notes'),
            error_module,
            error_type,
            error_severity,
            execution_data.get('error_evidence'),
            execution_data.get('is_cascade', False),
            execution_data.get('root_cause_step')
        ))

        # Update error patterns if error detected
        if error_module and error_type:
            self._update_error_patterns(
                cursor,
                execution_data.get('agent_type'),
                execution_data.get('execution_method'),
                error_module,
                error_type,
                error_severity
            )

        conn.commit()
        conn.close()

    def _update_error_patterns(self, cursor, agent_type, execution_method,
                               error_module, error_type, error_severity):
        """Update error pattern frequency"""
        cursor.execute("""
            SELECT id, frequency FROM error_patterns
            WHERE agent_type = ? AND execution_method = ?
            AND error_module = ? AND error_type = ?
        """, (agent_type, execution_method, error_module, error_type))

        result = cursor.fetchone()

        if result:
            # Update existing pattern
            cursor.execute("""
                UPDATE error_patterns
                SET frequency = frequency + 1, last_seen = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), result[0]))
        else:
            # Create new pattern
            cursor.execute("""
                INSERT INTO error_patterns (
                    timestamp, agent_type, execution_method,
                    error_module, error_type, error_severity,
                    frequency, last_seen
                ) VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """, (
                datetime.now().isoformat(),
                agent_type,
                execution_method,
                error_module,
                error_type,
                error_severity,
                datetime.now().isoformat()
            ))

    def get_error_rate_for_type(self, agent_type, execution_method, days=30):
        """Calculate error rate from historical data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff = datetime.now().timestamp() - (days * 24 * 3600)
        cutoff_iso = datetime.fromtimestamp(cutoff).isoformat()

        cursor.execute("""
            SELECT
                SUM(CASE WHEN error_module IS NOT NULL THEN 1 ELSE 0 END) as errors,
                SUM(CASE WHEN error_severity = 'critical' THEN 1 ELSE 0 END) as critical_errors,
                COUNT(*) as total
            FROM task_executions
            WHERE agent_type = ? AND execution_method = ?
            AND timestamp >= ?
        """, (agent_type, execution_method, cutoff_iso))

        result = cursor.fetchone()
        conn.close()

        errors, critical_errors, total = result

        return {
            'error_rate': errors / total if total > 0 else 0,
            'critical_error_rate': critical_errors / total if total > 0 else 0,
            'total': total
        }

    def should_suggest_steering(self, tool_name, tool_args, complexity):
        """Enhanced heuristic with error rate checking"""
        if tool_name != "Task":
            return False

        # Medium complexity tasks are candidates
        if 4 <= complexity <= 6:
            agent_type = tool_args.get("subagent_type", "")

            # Check historical error rates
            steering_stats = self.get_error_rate_for_type(agent_type, 'steering_suggestion')
            agent_stats = self.get_error_rate_for_type(agent_type, 'agent_spawn')

            # Quality gates
            QUALITY_THRESHOLDS = {
                'max_error_rate': 0.10,
                'max_critical_error_rate': 0.02,
                'min_samples': 50
            }

            # Only suggest if we have enough data and quality is good
            if steering_stats['total'] < QUALITY_THRESHOLDS['min_samples']:
                return False

            if steering_stats['error_rate'] > QUALITY_THRESHOLDS['max_error_rate']:
                return False

            if steering_stats['critical_error_rate'] > QUALITY_THRESHOLDS['max_critical_error_rate']:
                return False

            # Steering must be comparable to agent spawn
            if steering_stats['error_rate'] > agent_stats['error_rate'] * 1.1:
                return False

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
        if tool_name == "Task":
            description = tool_args.get("description", "")
            prompt = tool_args.get("prompt", "")
            combined = description + " " + prompt

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

        return 5

    def get_baseline_metrics(self, days=7):
        """Get baseline metrics with error analysis"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff = datetime.now().timestamp() - (days * 24 * 3600)
        cutoff_iso = datetime.fromtimestamp(cutoff).isoformat()

        # Total executions
        cursor.execute("""
            SELECT COUNT(*) FROM task_executions
            WHERE timestamp >= ?
        """, (cutoff_iso,))
        total_tasks = cursor.fetchone()[0]

        # By execution method with error rates
        cursor.execute("""
            SELECT
                execution_method,
                COUNT(*) as count,
                AVG(success) as success_rate,
                AVG(tokens_used) as avg_tokens,
                SUM(CASE WHEN error_module IS NOT NULL THEN 1 ELSE 0 END) as errors,
                SUM(CASE WHEN error_severity = 'critical' THEN 1 ELSE 0 END) as critical_errors
            FROM task_executions
            WHERE timestamp >= ?
            GROUP BY execution_method
        """, (cutoff_iso,))
        by_method = cursor.fetchall()

        # Error breakdown by module
        cursor.execute("""
            SELECT error_module, error_type, COUNT(*) as count
            FROM task_executions
            WHERE timestamp >= ? AND error_module IS NOT NULL
            GROUP BY error_module, error_type
            ORDER BY count DESC
        """, (cutoff_iso,))
        error_breakdown = cursor.fetchall()

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
                'avg_tokens': m[3] or 0,
                'error_rate': (m[4] / m[1]) if m[1] > 0 else 0,
                'critical_error_rate': (m[5] / m[1]) if m[1] > 0 else 0
            }) for m in by_method),
            'error_breakdown': [(e[0], e[1], e[2]) for e in error_breakdown],
            'agent_spawn_rate': spawn_rate,
            'target_spawn_rate': 0.12
        }


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
            prompt = tool_args.get("prompt", "")
            if "confidence:" in prompt.lower():
                match = re.search(r'confidence:\s*(\d+)%', prompt.lower())
                if match:
                    confidence_score = float(match.group(1)) / 100

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
            'success': True,
            'notes': f"Tool: {tool_name}"
        }

        monitor.log_execution(execution_data)

        # Check if steering prompt might be better (with quality gates)
        if monitor.should_suggest_steering(tool_name, tool_args, complexity):
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
