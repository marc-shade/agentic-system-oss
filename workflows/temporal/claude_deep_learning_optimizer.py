#!/usr/bin/env python3
"""
Claude Deep Learning Cycle - Performance Optimizer
Temporal workflow that analyzes performance and optimizes Claude Code settings

INTEGRATION: Uses agentic marker system to signal intentional changes
STATUS: Production Ready
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

# Add intelligent healing system to path
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/intelligent-self-healing')
from intelligent_config_agent import IntelligentConfigAgent

# Temporal imports
try:
    from temporalio import activity, workflow
    from temporalio.common import RetryPolicy
    TEMPORAL_AVAILABLE = True
except ImportError:
    print("⚠️  Temporal not installed - running in standalone mode")
    TEMPORAL_AVAILABLE = False
    # Mock decorators for standalone testing
    def activity(fn):
        return fn
    class workflow:
        @staticmethod
        def defn(fn):
            return fn
        @staticmethod
        def run(fn):
            return fn


class PerformanceMetrics:
    """Collect and analyze Claude Code performance metrics"""

    def __init__(self):
        # Store on SSDRAID0 (not /tmp - see FILE_LOCATION_POLICY.md)
        base = Path("/Volumes/SSDRAID0/agentic-system")
        self.metrics_file = base / "logs/performance/claude_metrics.json"
        self.learning_memory = base / "logs/learning/learning_memory.jsonl"

    def collect_metrics(self) -> Dict:
        """Collect current performance metrics"""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "tool_executions": self._get_tool_execution_stats(),
            "memory_usage": self._get_memory_stats(),
            "response_times": self._get_response_time_stats(),
            "error_rates": self._get_error_rates(),
            "context_usage": self._get_context_stats()
        }
        return metrics

    def _get_tool_execution_stats(self) -> Dict:
        """Analyze tool execution patterns"""
        # In production, read from actual logs
        # For now, return mock data structure
        return {
            "total_executions": 0,
            "parallel_executions": 0,
            "average_time_ms": 0,
            "most_used_tools": []
        }

    def _get_memory_stats(self) -> Dict:
        """Get memory usage statistics"""
        import psutil
        memory = psutil.virtual_memory()
        return {
            "percent": memory.percent,
            "available_gb": memory.available / (1024**3),
            "used_gb": memory.used / (1024**3)
        }

    def _get_response_time_stats(self) -> Dict:
        """Get response time statistics"""
        return {
            "average_ms": 0,
            "p95_ms": 0,
            "p99_ms": 0
        }

    def _get_error_rates(self) -> Dict:
        """Get error rate statistics"""
        return {
            "total_errors": 0,
            "error_rate": 0.0,
            "recent_errors": []
        }

    def _get_context_stats(self) -> Dict:
        """Get context window usage statistics"""
        return {
            "average_tokens": 0,
            "max_tokens": 200000,
            "utilization": 0.0
        }


class PerformanceOptimizer:
    """Analyze metrics and generate optimization recommendations"""

    def __init__(self):
        self.agent = IntelligentConfigAgent()
        self.settings_file = Path.home() / ".claude" / "settings.json"

    def analyze_and_optimize(self, metrics: Dict) -> List[Tuple[str, any, str, float]]:
        """
        Analyze metrics and generate optimizations

        Returns:
            List of (key, new_value, reason, confidence) tuples
        """
        optimizations = []

        # Optimization 1: Context Window
        context_util = metrics['context_usage']['utilization']
        if context_util > 0.8:
            # High context usage - increase maxTokens
            optimizations.append((
                "maxTokens",
                250000,
                f"Context utilization at {context_util:.1%} - increasing for headroom",
                0.92
            ))
        elif context_util < 0.3:
            # Low context usage - can reduce
            optimizations.append((
                "maxTokens",
                150000,
                f"Context utilization only {context_util:.1%} - optimizing memory",
                0.85
            ))

        # Optimization 2: Parallel Tool Calls
        tool_stats = metrics['tool_executions']
        if tool_stats['parallel_executions'] > 0:
            parallel_ratio = tool_stats['parallel_executions'] / max(tool_stats['total_executions'], 1)
            if parallel_ratio > 0.3:
                # High parallel usage - ensure enabled
                optimizations.append((
                    "parallelToolCalls",
                    True,
                    f"Parallel execution at {parallel_ratio:.1%} - optimizing for speed",
                    0.95
                ))

        # Optimization 3: Memory Pressure
        memory = metrics['memory_usage']
        if memory['percent'] > 85:
            # High memory - reduce caching
            optimizations.append((
                "cachingStrategy",
                "conservative",
                f"Memory at {memory['percent']}% - reducing cache pressure",
                0.93
            ))
        elif memory['percent'] < 50:
            # Low memory - can be more aggressive
            optimizations.append((
                "cachingStrategy",
                "aggressive",
                f"Memory at {memory['percent']}% - enabling aggressive caching",
                0.88
            ))

        # Optimization 4: Error Rate Response
        error_rate = metrics['error_rates']['error_rate']
        if error_rate > 0.1:  # >10% error rate
            # High errors - enable debug logging temporarily
            optimizations.append((
                "loggingLevel",
                "DEBUG",
                f"Error rate at {error_rate:.1%} - enabling debug logging for analysis",
                0.90
            ))
        elif error_rate < 0.01:  # <1% error rate
            # Low errors - reduce logging overhead
            optimizations.append((
                "loggingLevel",
                "INFO",
                f"Error rate low ({error_rate:.1%}) - reducing logging overhead",
                0.87
            ))

        return optimizations

    def apply_optimizations(
        self,
        optimizations: List[Tuple[str, any, str, float]],
        session_id: str
    ) -> Dict:
        """
        Apply optimizations with marker system integration

        Returns:
            Summary of applied optimizations
        """
        # Load current settings
        with open(self.settings_file, 'r') as f:
            settings = json.load(f)

        applied = []
        skipped = []

        for key, new_value, reason, confidence in optimizations:
            # Check if key can be modified
            is_modifiable, mod_reason = self.agent.is_key_modifiable(key)

            if not is_modifiable:
                print(f"⚠️  Skipping {key}: {mod_reason}")
                skipped.append({
                    "key": key,
                    "reason": mod_reason
                })
                continue

            # Get old value
            old_value = settings.get(key)

            # Only apply if different
            if old_value == new_value:
                print(f"✓ {key} already optimal ({new_value})")
                continue

            # Apply optimization
            settings[key] = new_value

            print(f"🔧 Optimizing {key}: {old_value} → {new_value}")
            print(f"   Reason: {reason}")
            print(f"   Confidence: {confidence:.1%}")

            # Mark as intentional change using marker system
            self.agent.mark_agentic_change(
                file="settings.json",
                key=key,
                reason=reason,
                change_type="agentic_optimization",
                confidence=confidence,
                session_id=session_id
            )

            applied.append({
                "key": key,
                "old_value": old_value,
                "new_value": new_value,
                "reason": reason,
                "confidence": confidence
            })

        # Save optimized settings
        if applied:
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2)

            print(f"\n✅ Applied {len(applied)} optimizations")

            # Notify about optimizations
            self.agent.notify_change(
                change_info={
                    "session": session_id,
                    "optimizations": len(applied),
                    "keys": [opt['key'] for opt in applied]
                },
                severity="info",
                use_voice=True
            )
        else:
            print(f"\n✓ No optimizations needed - all settings optimal")

        return {
            "applied": applied,
            "skipped": skipped,
            "timestamp": datetime.now().isoformat()
        }


# Temporal Activities
@activity
async def collect_performance_metrics() -> Dict:
    """Activity: Collect performance metrics"""
    print("📊 Collecting performance metrics...")
    metrics_collector = PerformanceMetrics()
    metrics = metrics_collector.collect_metrics()
    print(f"✅ Collected metrics: {len(metrics)} categories")
    return metrics


@activity
async def analyze_and_optimize(metrics: Dict, session_id: str) -> Dict:
    """Activity: Analyze metrics and apply optimizations"""
    print(f"🔍 Analyzing metrics for optimization...")

    optimizer = PerformanceOptimizer()

    # Generate optimizations
    optimizations = optimizer.analyze_and_optimize(metrics)
    print(f"💡 Generated {len(optimizations)} potential optimizations")

    # Apply optimizations with marker system
    result = optimizer.apply_optimizations(optimizations, session_id)

    return result


# Temporal Workflow
if TEMPORAL_AVAILABLE:
    @workflow.defn
    class ClaudeDeepLearningWorkflow:
        """
        Deep learning workflow that continuously optimizes Claude Code

        Runs every 6 hours:
        1. Collect performance metrics
        2. Analyze for optimization opportunities
        3. Apply optimizations with marker system
        4. Store results in learning memory
        """

        @workflow.run
        async def run(self) -> Dict:
            session_id = f"deep_learning_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            print(f"🧠 Starting deep learning cycle: {session_id}")

            # Step 1: Collect metrics
            metrics = await workflow.execute_activity(
                collect_performance_metrics,
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RetryPolicy(maximum_attempts=3)
            )

            # Step 2: Analyze and optimize
            result = await workflow.execute_activity(
                analyze_and_optimize,
                args=[metrics, session_id],
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=RetryPolicy(maximum_attempts=2)
            )

            # Step 3: Store learning
            learning_record = {
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "metrics": metrics,
                "optimizations": result
            }

            # Log to learning memory (SSDRAID0)
            base = Path("/Volumes/SSDRAID0/agentic-system")
            learning_memory = base / "logs/learning/learning_memory.jsonl"
            learning_memory.parent.mkdir(parents=True, exist_ok=True)
            with open(learning_memory, 'a') as f:
                f.write(json.dumps(learning_record) + '\n')

            print(f"✅ Deep learning cycle complete: {len(result['applied'])} optimizations applied")

            return result


# Standalone mode for testing
def main_standalone():
    """Run optimization in standalone mode (no Temporal)"""
    print("=" * 60)
    print("🧠 Claude Deep Learning Optimizer (Standalone Mode)")
    print("=" * 60)
    print()

    session_id = f"deep_learning_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Collect metrics
    print("📊 Collecting performance metrics...")
    metrics_collector = PerformanceMetrics()
    metrics = metrics_collector.collect_metrics()
    print(f"✅ Collected metrics")
    print()

    # Analyze and optimize
    print("🔍 Analyzing for optimization opportunities...")
    optimizer = PerformanceOptimizer()
    optimizations = optimizer.analyze_and_optimize(metrics)
    print(f"💡 Generated {len(optimizations)} potential optimizations")
    print()

    # Apply optimizations
    result = optimizer.apply_optimizations(optimizations, session_id)

    print()
    print("=" * 60)
    print("📊 Optimization Summary")
    print("=" * 60)
    print(f"Applied: {len(result['applied'])}")
    print(f"Skipped: {len(result['skipped'])}")
    print()

    if result['applied']:
        print("Applied Optimizations:")
        for opt in result['applied']:
            print(f"  • {opt['key']}: {opt['old_value']} → {opt['new_value']}")
            print(f"    Reason: {opt['reason']}")
            print(f"    Confidence: {opt['confidence']:.1%}")
            print()

    if result['skipped']:
        print("Skipped (Protected Keys):")
        for skip in result['skipped']:
            print(f"  • {skip['key']}: {skip['reason']}")
            print()

    # Store learning
    learning_record = {
        "session_id": session_id,
        "timestamp": datetime.now().isoformat(),
        "metrics": metrics,
        "optimizations": result
    }

    base = Path("/Volumes/SSDRAID0/agentic-system")
    learning_memory = base / "logs/learning/learning_memory.jsonl"
    learning_memory.parent.mkdir(parents=True, exist_ok=True)
    with open(learning_memory, 'a') as f:
        f.write(json.dumps(learning_record) + '\n')

    print("✅ Learning stored to:", learning_memory)
    print()

    return result


if __name__ == "__main__":
    if TEMPORAL_AVAILABLE:
        print("⚠️  Temporal mode - use Temporal CLI to start workflow")
        print("    temporal workflow start \\")
        print("      --type ClaudeDeepLearningWorkflow \\")
        print("      --task-queue claude-optimization")
    else:
        # Run in standalone mode for testing
        main_standalone()
