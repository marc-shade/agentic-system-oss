#!/usr/bin/env python3
"""
AGI Bridge - Connect Hooks to AGI MCP Tools
============================================

This module bridges Claude Code hooks with the AGI MCP server,
enabling full meta-learning, pattern detection, and self-improvement
capabilities from hook events.

Capabilities enabled:
1. Meta-learning: Record action outcomes for learning
2. Pattern detection: Identify patterns in tool usage
3. Agent recommendation: Get optimal agent for tasks
4. Skill evolution: Track and improve skills over time
5. Goal tracking: Update progress on decomposed goals

Part of the AGI Development System - Building toward artificial general intelligence.
"""

import json
import sys
import os
import subprocess
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import urllib.request
import urllib.error

# AGI MCP Server configuration
AGI_MCP_HOST = os.environ.get('AGI_MCP_HOST', 'localhost')
AGI_MCP_PORT = int(os.environ.get('AGI_MCP_PORT', '3100'))

# Memory database
MEMORY_DB_PATH = Path("/mnt/agentic-system/.claude/enhanced_memories/memory.db")

# Meta-learning log
META_LEARNING_LOG = Path("/mnt/agentic-system/logs/meta-learning.jsonl")


class AGIBridge:
    """
    Bridge between Claude Code hooks and AGI MCP server.

    Provides synchronous methods that hooks can call to enable
    AGI capabilities without blocking Claude Code execution.
    """

    def __init__(self):
        self.node_id = os.uname().nodename
        self.session_id = os.environ.get('CLAUDE_SESSION_ID', 'unknown')

    def record_outcome(self, task_id: str, task_type: str, agent_used: str,
                       success: bool, execution_time_ms: int,
                       quality_score: float = None, error_message: str = None,
                       context: Dict[str, Any] = None) -> bool:
        """
        Record task outcome for AGI meta-learning.

        This feeds into the meta-learning system to improve:
        - Agent selection for future tasks
        - Execution strategy optimization
        - Error pattern detection
        """
        try:
            outcome_record = {
                "timestamp": datetime.now().isoformat(),
                "task_id": task_id,
                "task_type": task_type,
                "agent_used": agent_used,
                "success": success,
                "execution_time_ms": execution_time_ms,
                "quality_score": quality_score,
                "error_message": error_message,
                "context": context or {},
                "node": self.node_id,
                "session_id": self.session_id
            }

            # Write to meta-learning log
            META_LEARNING_LOG.parent.mkdir(parents=True, exist_ok=True)
            with open(META_LEARNING_LOG, 'a') as f:
                f.write(json.dumps(outcome_record) + '\n')

            # Store in memory database for pattern analysis
            self._store_learning_memory(outcome_record)

            # Try to call AGI MCP server (non-blocking attempt)
            self._call_agi_mcp('agi_record_outcome', {
                'task_id': task_id,
                'task_type': task_type,
                'agent_used': agent_used,
                'success': success,
                'execution_time_ms': execution_time_ms,
                'quality_score': quality_score,
                'error_message': error_message,
                'context': context
            })

            return True

        except Exception as e:
            print(f"AGI Bridge: record_outcome error: {e}", file=sys.stderr)
            return False

    def detect_patterns(self, window_hours: int = 24, min_occurrences: int = 3) -> Dict[str, Any]:
        """
        Detect patterns in recent task execution for optimization opportunities.
        """
        try:
            # Read recent meta-learning records
            patterns = {
                "tool_frequency": {},
                "success_rates": {},
                "avg_durations": {},
                "failure_patterns": [],
                "optimization_opportunities": []
            }

            if not META_LEARNING_LOG.exists():
                return patterns

            # Analyze recent records
            from datetime import timedelta
            cutoff = datetime.now() - timedelta(hours=window_hours)

            tool_success = {}
            tool_durations = {}

            with open(META_LEARNING_LOG, 'r') as f:
                for line in f:
                    try:
                        record = json.loads(line.strip())
                        record_time = datetime.fromisoformat(record['timestamp'])

                        if record_time < cutoff:
                            continue

                        task_type = record.get('task_type', 'unknown')
                        success = record.get('success', False)
                        duration = record.get('execution_time_ms', 0)

                        # Track frequency
                        patterns['tool_frequency'][task_type] = patterns['tool_frequency'].get(task_type, 0) + 1

                        # Track success/failure
                        if task_type not in tool_success:
                            tool_success[task_type] = {'success': 0, 'failure': 0}
                        if success:
                            tool_success[task_type]['success'] += 1
                        else:
                            tool_success[task_type]['failure'] += 1
                            patterns['failure_patterns'].append({
                                'task_type': task_type,
                                'error': record.get('error_message'),
                                'timestamp': record['timestamp']
                            })

                        # Track durations
                        if task_type not in tool_durations:
                            tool_durations[task_type] = []
                        if duration > 0:
                            tool_durations[task_type].append(duration)

                    except (json.JSONDecodeError, KeyError):
                        continue

            # Calculate success rates
            for task_type, counts in tool_success.items():
                total = counts['success'] + counts['failure']
                if total >= min_occurrences:
                    rate = counts['success'] / total
                    patterns['success_rates'][task_type] = round(rate, 2)

                    # Flag low success rate as optimization opportunity
                    if rate < 0.8:
                        patterns['optimization_opportunities'].append({
                            'task_type': task_type,
                            'success_rate': rate,
                            'suggestion': f"Investigate {task_type} failures - {counts['failure']} failures in last {window_hours}h"
                        })

            # Calculate average durations
            for task_type, durations in tool_durations.items():
                if len(durations) >= min_occurrences:
                    patterns['avg_durations'][task_type] = round(sum(durations) / len(durations), 2)

            return patterns

        except Exception as e:
            print(f"AGI Bridge: detect_patterns error: {e}", file=sys.stderr)
            return {}

    def recommend_agent(self, task_type: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get AGI recommendation for best agent to handle a task type.
        """
        try:
            # Analyze historical performance
            patterns = self.detect_patterns(window_hours=168)  # Last week

            recommendation = {
                "task_type": task_type,
                "recommended_agent": "general-purpose",  # Default
                "confidence": 0.5,
                "reasoning": "Default recommendation"
            }

            # Check success rates for this task type
            if task_type in patterns.get('success_rates', {}):
                success_rate = patterns['success_rates'][task_type]

                if success_rate >= 0.9:
                    recommendation['confidence'] = 0.9
                    recommendation['reasoning'] = f"High success rate ({success_rate}) for {task_type}"
                elif success_rate < 0.7:
                    recommendation['confidence'] = 0.6
                    recommendation['reasoning'] = f"Low success rate ({success_rate}) - consider alternative approach"

            # Try AGI MCP for more sophisticated recommendation
            mcp_response = self._call_agi_mcp('agi_recommend_agent', {
                'task_type': task_type,
                'context': context
            })

            if mcp_response and mcp_response.get('success'):
                return mcp_response.get('recommendation', recommendation)

            return recommendation

        except Exception as e:
            print(f"AGI Bridge: recommend_agent error: {e}", file=sys.stderr)
            return {"task_type": task_type, "recommended_agent": "general-purpose", "confidence": 0.5}

    def identify_knowledge_gap(self, topic: str, severity: float = 0.5,
                                context: str = None) -> bool:
        """
        Record a knowledge gap for future learning.
        """
        try:
            gap_record = {
                "timestamp": datetime.now().isoformat(),
                "topic": topic,
                "severity": severity,
                "context": context,
                "node": self.node_id,
                "session_id": self.session_id,
                "status": "identified"
            }

            # Store in memory database
            self._store_knowledge_gap(gap_record)

            # Log for research prioritization
            gaps_log = Path("/mnt/agentic-system/logs/knowledge-gaps.jsonl")
            gaps_log.parent.mkdir(parents=True, exist_ok=True)
            with open(gaps_log, 'a') as f:
                f.write(json.dumps(gap_record) + '\n')

            return True

        except Exception as e:
            print(f"AGI Bridge: identify_knowledge_gap error: {e}", file=sys.stderr)
            return False

    def record_metacognitive_state(self, confidence: float, uncertainty_areas: List[str],
                                    cognitive_load: str = "normal") -> bool:
        """
        Record metacognitive state for self-awareness tracking.
        """
        try:
            state_record = {
                "timestamp": datetime.now().isoformat(),
                "confidence": confidence,
                "uncertainty_areas": uncertainty_areas,
                "cognitive_load": cognitive_load,
                "node": self.node_id,
                "session_id": self.session_id
            }

            # Store metacognitive state
            metacog_log = Path("/mnt/agentic-system/logs/metacognitive-states.jsonl")
            metacog_log.parent.mkdir(parents=True, exist_ok=True)
            with open(metacog_log, 'a') as f:
                f.write(json.dumps(state_record) + '\n')

            return True

        except Exception as e:
            print(f"AGI Bridge: record_metacognitive_state error: {e}", file=sys.stderr)
            return False

    def _store_learning_memory(self, record: Dict[str, Any]) -> bool:
        """Store learning record in enhanced memory database."""
        try:
            import zlib

            if not MEMORY_DB_PATH.exists():
                return False

            conn = sqlite3.connect(str(MEMORY_DB_PATH), timeout=5)
            cursor = conn.cursor()

            memory_name = f"learning_{record['task_type']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            content = json.dumps(record)
            compressed = zlib.compress(content.encode('utf-8'))

            cursor.execute("""
                INSERT INTO entities (name, entity_type, compressed_data, tier, original_size, compressed_size, compression_ratio, last_accessed, created_at)
                VALUES (?, 'meta_learning', ?, 'episodic', ?, ?, ?, datetime('now'), datetime('now'))
            """, (memory_name, compressed, len(content), len(compressed), len(compressed)/len(content)))

            conn.commit()
            conn.close()
            return True

        except Exception:
            return False

    def _store_knowledge_gap(self, record: Dict[str, Any]) -> bool:
        """Store knowledge gap in enhanced memory database."""
        try:
            import zlib

            if not MEMORY_DB_PATH.exists():
                return False

            conn = sqlite3.connect(str(MEMORY_DB_PATH), timeout=5)
            cursor = conn.cursor()

            memory_name = f"knowledge_gap_{record['topic'][:30]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            content = json.dumps(record)
            compressed = zlib.compress(content.encode('utf-8'))

            cursor.execute("""
                INSERT INTO entities (name, entity_type, compressed_data, tier, original_size, compressed_size, compression_ratio, last_accessed, created_at)
                VALUES (?, 'knowledge_gap', ?, 'semantic', ?, ?, ?, datetime('now'), datetime('now'))
            """, (memory_name, compressed, len(content), len(compressed), len(compressed)/len(content)))

            conn.commit()
            conn.close()
            return True

        except Exception:
            return False

    def _call_agi_mcp(self, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Call AGI MCP server method.
        Non-blocking with timeout - returns None if unavailable.
        """
        try:
            # Build JSON-RPC request
            request_data = json.dumps({
                "jsonrpc": "2.0",
                "method": f"tools/{method}",
                "params": params,
                "id": 1
            }).encode('utf-8')

            # Make HTTP request with short timeout
            req = urllib.request.Request(
                f"http://{AGI_MCP_HOST}:{AGI_MCP_PORT}/",
                data=request_data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )

            with urllib.request.urlopen(req, timeout=2) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get('result')

        except (urllib.error.URLError, TimeoutError, Exception):
            # AGI MCP not available - that's OK, we logged locally
            return None


def main():
    """CLI interface for AGI Bridge."""
    import argparse

    parser = argparse.ArgumentParser(description="AGI Bridge - Hook to AGI MCP integration")
    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # record-outcome command
    record_parser = subparsers.add_parser('record-outcome', help='Record task outcome')
    record_parser.add_argument('--task-id', required=True)
    record_parser.add_argument('--task-type', required=True)
    record_parser.add_argument('--agent', default='claude-code')
    record_parser.add_argument('--success', action='store_true')
    record_parser.add_argument('--duration-ms', type=int, default=0)
    record_parser.add_argument('--quality', type=float)
    record_parser.add_argument('--error')

    # detect-patterns command
    patterns_parser = subparsers.add_parser('detect-patterns', help='Detect execution patterns')
    patterns_parser.add_argument('--hours', type=int, default=24)
    patterns_parser.add_argument('--min-occurrences', type=int, default=3)

    # recommend-agent command
    recommend_parser = subparsers.add_parser('recommend-agent', help='Get agent recommendation')
    recommend_parser.add_argument('--task-type', required=True)

    # knowledge-gap command
    gap_parser = subparsers.add_parser('knowledge-gap', help='Record knowledge gap')
    gap_parser.add_argument('--topic', required=True)
    gap_parser.add_argument('--severity', type=float, default=0.5)
    gap_parser.add_argument('--context')

    # metacognitive command
    meta_parser = subparsers.add_parser('metacognitive', help='Record metacognitive state')
    meta_parser.add_argument('--confidence', type=float, required=True)
    meta_parser.add_argument('--uncertainties', nargs='*', default=[])
    meta_parser.add_argument('--load', default='normal')

    args = parser.parse_args()
    bridge = AGIBridge()

    if args.command == 'record-outcome':
        result = bridge.record_outcome(
            task_id=args.task_id,
            task_type=args.task_type,
            agent_used=args.agent,
            success=args.success,
            execution_time_ms=args.duration_ms,
            quality_score=args.quality,
            error_message=args.error
        )
        print(f"Outcome recorded: {result}")

    elif args.command == 'detect-patterns':
        patterns = bridge.detect_patterns(
            window_hours=args.hours,
            min_occurrences=args.min_occurrences
        )
        print(json.dumps(patterns, indent=2))

    elif args.command == 'recommend-agent':
        recommendation = bridge.recommend_agent(args.task_type)
        print(json.dumps(recommendation, indent=2))

    elif args.command == 'knowledge-gap':
        result = bridge.identify_knowledge_gap(
            topic=args.topic,
            severity=args.severity,
            context=args.context
        )
        print(f"Knowledge gap recorded: {result}")

    elif args.command == 'metacognitive':
        result = bridge.record_metacognitive_state(
            confidence=args.confidence,
            uncertainty_areas=args.uncertainties,
            cognitive_load=args.load
        )
        print(f"Metacognitive state recorded: {result}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
