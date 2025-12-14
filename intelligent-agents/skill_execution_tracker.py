#!/usr/bin/env python3
"""
Skill Execution Tracker - System-wide Failure Pattern Capture

Based on research:
- Agent Q: Learning from both success AND failure trajectories (DPO)
- ExACT: Contrastive reflection on success vs failure
- OS-Copilot: Skill accumulation from experience

This module provides:
1. Execution tracking for ALL skills across the AGI system
2. Failure pattern capture for learning
3. Contrastive analysis between success/failure trajectories
4. Automatic success rate updates
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable, Tuple
from functools import wraps
from contextlib import contextmanager
import traceback

# Configuration
EXECUTION_LOG_FILE = Path("/mnt/agentic-system/databases/skill_executions.jsonl")
FAILURE_PATTERNS_FILE = Path("/mnt/agentic-system/databases/skill_failure_patterns.jsonl")
CONTRASTIVE_ANALYSIS_FILE = Path("/mnt/agentic-system/databases/contrastive_analysis.json")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SkillExecutionTracker:
    """
    Tracks skill executions system-wide for AGI learning.
    Captures both success and failure trajectories per Agent Q research.
    """

    def __init__(self, skill_name: str, skill_category: str = "general"):
        self.skill_name = skill_name
        self.skill_category = skill_category
        self.execution_start: Optional[datetime] = None
        self.context: Dict[str, Any] = {}

    def __enter__(self):
        """Start tracking execution."""
        self.execution_start = datetime.now()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Complete tracking - record success or failure."""
        execution_end = datetime.now()
        duration_ms = (execution_end - self.execution_start).total_seconds() * 1000

        if exc_type is None:
            # Success
            self._record_execution(
                success=True,
                duration_ms=duration_ms,
                error=None,
                traceback_str=None
            )
        else:
            # Failure - capture for learning
            self._record_execution(
                success=False,
                duration_ms=duration_ms,
                error=str(exc_val),
                traceback_str=traceback.format_exc()
            )
            # Also capture detailed failure pattern
            self._capture_failure_pattern(
                error=str(exc_val),
                error_type=exc_type.__name__,
                traceback_str=traceback.format_exc()
            )

        # Don't suppress exceptions
        return False

    def set_context(self, **kwargs):
        """Set execution context for better analysis."""
        self.context.update(kwargs)
        return self

    def _record_execution(self, success: bool, duration_ms: float,
                         error: Optional[str], traceback_str: Optional[str]):
        """Record execution to log file."""
        record = {
            "timestamp": datetime.now().isoformat(),
            "skill_name": self.skill_name,
            "skill_category": self.skill_category,
            "success": success,
            "duration_ms": duration_ms,
            "error": error,
            "traceback": traceback_str[:500] if traceback_str else None,
            "context": self.context
        }

        try:
            EXECUTION_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(EXECUTION_LOG_FILE, 'a') as f:
                f.write(json.dumps(record, default=str) + '\n')
        except IOError as e:
            logger.error(f"Failed to record execution: {e}")

    def _capture_failure_pattern(self, error: str, error_type: str, traceback_str: str):
        """
        Capture detailed failure pattern for learning.
        Based on Agent Q: Learn from failure trajectories.
        """
        pattern = {
            "timestamp": datetime.now().isoformat(),
            "skill_name": self.skill_name,
            "skill_category": self.skill_category,
            "error_type": error_type,
            "error_message": error,
            "traceback_sample": traceback_str[:1000] if traceback_str else None,
            "context": self.context,
            "system_state": self._capture_system_state(),
            "potential_causes": self._analyze_potential_causes(error, traceback_str)
        }

        try:
            FAILURE_PATTERNS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(FAILURE_PATTERNS_FILE, 'a') as f:
                f.write(json.dumps(pattern, default=str) + '\n')
            logger.info(f"Captured failure pattern for {self.skill_name}: {error_type}")
        except IOError as e:
            logger.error(f"Failed to capture pattern: {e}")

    def _capture_system_state(self) -> dict:
        """Capture system state at time of failure."""
        state = {}
        try:
            with open('/proc/loadavg', 'r') as f:
                state['load_avg'] = f.read().strip()
        except:
            state['load_avg'] = 'unavailable'

        try:
            with open('/proc/meminfo', 'r') as f:
                lines = f.readlines()[:3]
                state['memory'] = ' '.join(l.strip() for l in lines)
        except:
            state['memory'] = 'unavailable'

        return state

    def _analyze_potential_causes(self, error: str, traceback_str: str) -> List[str]:
        """
        Analyze potential causes from error pattern.
        This is a heuristic analysis for learning.
        """
        causes = []
        error_lower = error.lower()
        tb_lower = traceback_str.lower() if traceback_str else ""

        # Common patterns
        if "timeout" in error_lower or "timed out" in error_lower:
            causes.append("network_timeout")
        if "connection" in error_lower:
            causes.append("connection_issue")
        if "memory" in error_lower or "oom" in error_lower:
            causes.append("memory_exhaustion")
        if "permission" in error_lower or "denied" in error_lower:
            causes.append("permission_error")
        if "not found" in error_lower or "does not exist" in error_lower:
            causes.append("resource_not_found")
        if "json" in error_lower or "decode" in error_lower:
            causes.append("serialization_error")
        if "database" in tb_lower or "sqlite" in tb_lower:
            causes.append("database_error")
        if "mcp" in tb_lower or "socket" in tb_lower:
            causes.append("mcp_communication")

        if not causes:
            causes.append("unknown_cause")

        return causes


def track_skill(skill_name: str, skill_category: str = "general"):
    """
    Decorator to track skill execution.

    Usage:
        @track_skill("my_skill", "coding")
        def my_function():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            with SkillExecutionTracker(skill_name, skill_category) as tracker:
                tracker.set_context(
                    function=func.__name__,
                    args_count=len(args),
                    kwargs_keys=list(kwargs.keys())
                )
                return func(*args, **kwargs)
        return wrapper
    return decorator


@contextmanager
def track_execution(skill_name: str, skill_category: str = "general", **context):
    """
    Context manager for tracking skill execution.

    Usage:
        with track_execution("cluster_coordination", "coordination", task_id=123):
            do_work()
    """
    tracker = SkillExecutionTracker(skill_name, skill_category)
    tracker.set_context(**context)
    with tracker:
        yield tracker


class ContrastiveAnalyzer:
    """
    Runs contrastive analysis on success vs failure patterns.
    Based on ExACT research: Compare what differentiates success from failure.
    """

    def __init__(self):
        self.executions = self._load_executions()
        self.failures = self._load_failures()

    def _load_executions(self) -> List[dict]:
        """Load recent executions."""
        executions = []
        if not EXECUTION_LOG_FILE.exists():
            return executions

        try:
            with open(EXECUTION_LOG_FILE, 'r') as f:
                for line in f:
                    try:
                        executions.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        continue
        except IOError:
            pass
        return executions[-1000:]  # Last 1000 executions

    def _load_failures(self) -> List[dict]:
        """Load failure patterns."""
        failures = []
        if not FAILURE_PATTERNS_FILE.exists():
            return failures

        try:
            with open(FAILURE_PATTERNS_FILE, 'r') as f:
                for line in f:
                    try:
                        failures.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        continue
        except IOError:
            pass
        return failures

    def analyze_skill(self, skill_name: str) -> dict:
        """
        Run contrastive analysis for a specific skill.
        Compares success vs failure trajectories.
        """
        skill_execs = [e for e in self.executions if e.get('skill_name') == skill_name]
        skill_failures = [f for f in self.failures if f.get('skill_name') == skill_name]

        if not skill_execs:
            return {"skill_name": skill_name, "error": "no_executions_found"}

        successes = [e for e in skill_execs if e.get('success', False)]
        failures = [e for e in skill_execs if not e.get('success', True)]

        total = len(skill_execs)
        success_rate = len(successes) / total if total > 0 else 0

        # Analyze duration differences
        success_durations = [e.get('duration_ms', 0) for e in successes if e.get('duration_ms')]
        failure_durations = [e.get('duration_ms', 0) for e in failures if e.get('duration_ms')]

        avg_success_duration = sum(success_durations) / len(success_durations) if success_durations else 0
        avg_failure_duration = sum(failure_durations) / len(failure_durations) if failure_durations else 0

        # Analyze error types from detailed failures
        error_types = {}
        potential_causes = {}
        for f in skill_failures:
            et = f.get('error_type', 'unknown')
            error_types[et] = error_types.get(et, 0) + 1
            for cause in f.get('potential_causes', []):
                potential_causes[cause] = potential_causes.get(cause, 0) + 1

        # Find patterns that differentiate success from failure
        differentiators = self._find_differentiators(successes, failures)

        analysis = {
            "skill_name": skill_name,
            "timestamp": datetime.now().isoformat(),
            "total_executions": total,
            "successes": len(successes),
            "failures": len(failures),
            "success_rate": success_rate,
            "avg_success_duration_ms": avg_success_duration,
            "avg_failure_duration_ms": avg_failure_duration,
            "duration_ratio": avg_failure_duration / avg_success_duration if avg_success_duration > 0 else 0,
            "error_type_distribution": error_types,
            "potential_cause_distribution": potential_causes,
            "most_common_error": max(error_types, key=error_types.get) if error_types else None,
            "most_common_cause": max(potential_causes, key=potential_causes.get) if potential_causes else None,
            "differentiators": differentiators,
            "recommendations": self._generate_recommendations(
                success_rate, error_types, potential_causes, differentiators
            )
        }

        return analysis

    def _find_differentiators(self, successes: List[dict], failures: List[dict]) -> dict:
        """
        Find context patterns that differentiate success from failure.
        """
        differentiators = {
            "context_patterns": {},
            "timing_patterns": {},
            "insights": []
        }

        # Analyze context keys present in successes vs failures
        success_context_keys = set()
        for s in successes:
            success_context_keys.update(s.get('context', {}).keys())

        failure_context_keys = set()
        for f in failures:
            failure_context_keys.update(f.get('context', {}).keys())

        differentiators["context_patterns"] = {
            "success_only_keys": list(success_context_keys - failure_context_keys),
            "failure_only_keys": list(failure_context_keys - success_context_keys),
            "common_keys": list(success_context_keys & failure_context_keys)
        }

        # Analyze timing patterns (hour of day)
        success_hours = [datetime.fromisoformat(s['timestamp']).hour for s in successes if 'timestamp' in s]
        failure_hours = [datetime.fromisoformat(f['timestamp']).hour for f in failures if 'timestamp' in f]

        if success_hours and failure_hours:
            from collections import Counter
            success_hour_dist = Counter(success_hours)
            failure_hour_dist = Counter(failure_hours)

            # Find hours with high failure rates
            high_failure_hours = []
            for hour in range(24):
                s_count = success_hour_dist.get(hour, 0)
                f_count = failure_hour_dist.get(hour, 0)
                total = s_count + f_count
                if total >= 5 and f_count / total > 0.3:  # >30% failure rate with enough samples
                    high_failure_hours.append(hour)

            differentiators["timing_patterns"]["high_failure_hours"] = high_failure_hours

        # Generate insights
        if differentiators["context_patterns"]["failure_only_keys"]:
            differentiators["insights"].append(
                f"Failures often occur with these context keys: {differentiators['context_patterns']['failure_only_keys']}"
            )
        if differentiators["timing_patterns"].get("high_failure_hours"):
            differentiators["insights"].append(
                f"Higher failure rates during hours: {differentiators['timing_patterns']['high_failure_hours']}"
            )

        return differentiators

    def _generate_recommendations(self, success_rate: float, error_types: dict,
                                   potential_causes: dict, differentiators: dict) -> List[str]:
        """
        Generate improvement recommendations based on analysis.
        """
        recommendations = []

        if success_rate < 0.9:
            recommendations.append(f"Success rate ({success_rate:.1%}) below target (90%). Focus on primary failure causes.")

        # Recommend based on common causes
        if potential_causes.get("network_timeout"):
            recommendations.append("Add retry logic with exponential backoff for network operations")
        if potential_causes.get("memory_exhaustion"):
            recommendations.append("Implement batch processing or streaming for large data")
        if potential_causes.get("database_error"):
            recommendations.append("Add database connection pooling and retry logic")
        if potential_causes.get("mcp_communication"):
            recommendations.append("Add MCP connection health checks before operations")
        if potential_causes.get("serialization_error"):
            recommendations.append("Add input validation and error handling for serialization")

        # Recommend based on error types
        if error_types:
            most_common = max(error_types, key=error_types.get)
            recommendations.append(f"Focus on handling {most_common} errors - most common failure type")

        # Recommend based on timing
        if differentiators.get("timing_patterns", {}).get("high_failure_hours"):
            recommendations.append("Consider scheduling non-urgent executions outside high-failure hours")

        return recommendations

    def run_all_skills_analysis(self) -> dict:
        """Run contrastive analysis on all tracked skills."""
        skill_names = set(e.get('skill_name') for e in self.executions if e.get('skill_name'))

        all_analysis = {
            "timestamp": datetime.now().isoformat(),
            "skills_analyzed": len(skill_names),
            "analyses": {}
        }

        for skill_name in skill_names:
            all_analysis["analyses"][skill_name] = self.analyze_skill(skill_name)

        # Sort by success rate to identify weakest skills
        all_analysis["skills_by_success_rate"] = sorted(
            [(name, a.get("success_rate", 0)) for name, a in all_analysis["analyses"].items()],
            key=lambda x: x[1]
        )

        # Save analysis
        try:
            with open(CONTRASTIVE_ANALYSIS_FILE, 'w') as f:
                json.dump(all_analysis, f, indent=2, default=str)
        except IOError as e:
            logger.error(f"Failed to save analysis: {e}")

        return all_analysis


def update_skill_success_rates():
    """
    Update skill success rates in enhanced-memory MCP based on tracked executions.
    Syncs the tracking data with the MCP skill storage.
    """
    import urllib.request

    analyzer = ContrastiveAnalyzer()
    analysis = analyzer.run_all_skills_analysis()

    updated_skills = []
    for skill_name, skill_analysis in analysis.get("analyses", {}).items():
        if skill_analysis.get("total_executions", 0) < 5:
            continue  # Skip skills with too few executions

        success_rate = skill_analysis.get("success_rate", 0)
        total_executions = skill_analysis.get("total_executions", 0)
        avg_duration = skill_analysis.get("avg_success_duration_ms", 0)

        # Call MCP to update skill
        try:
            payload = {
                "skill_name": skill_name,
                "success": True,  # Recording aggregate update
                "execution_time_ms": int(avg_duration) if avg_duration else 0
            }
            req = urllib.request.Request(
                "http://localhost:8765/record_skill_execution",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read())
                updated_skills.append(skill_name)
        except Exception as e:
            logger.warning(f"Failed to update skill {skill_name}: {e}")

    return {
        "updated_skills": updated_skills,
        "total_skills_analyzed": len(analysis.get("analyses", {})),
        "weakest_skills": analysis.get("skills_by_success_rate", [])[:5]
    }


if __name__ == "__main__":
    # Run contrastive analysis and print results
    analyzer = ContrastiveAnalyzer()

    print("=" * 60)
    print("Skill Contrastive Analysis Report")
    print("=" * 60)

    # Analyze specific skill (cluster_coordination)
    cluster_analysis = analyzer.analyze_skill("cluster_coordination")
    print(f"\nCluster Coordination Analysis:")
    print(f"  Success Rate: {cluster_analysis.get('success_rate', 0):.1%}")
    print(f"  Total Executions: {cluster_analysis.get('total_executions', 0)}")
    print(f"  Most Common Error: {cluster_analysis.get('most_common_error', 'N/A')}")
    print(f"  Most Common Cause: {cluster_analysis.get('most_common_cause', 'N/A')}")
    print(f"\n  Recommendations:")
    for rec in cluster_analysis.get('recommendations', []):
        print(f"    - {rec}")

    # Run full analysis
    print("\n" + "=" * 60)
    print("Full System Analysis")
    print("=" * 60)

    full_analysis = analyzer.run_all_skills_analysis()
    print(f"\nSkills Analyzed: {full_analysis.get('skills_analyzed', 0)}")
    print(f"\nSkills by Success Rate (lowest first):")
    for skill, rate in full_analysis.get("skills_by_success_rate", [])[:10]:
        print(f"  {skill}: {rate:.1%}")

    print(f"\nAnalysis saved to: {CONTRASTIVE_ANALYSIS_FILE}")
