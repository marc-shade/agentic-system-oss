#!/usr/bin/env python3
"""
Metrics Collection for DSPy Optimization
=========================================

Performance tracking, analysis, and reporting for prompt optimization.
Integrates with enhanced-memory for persistent metrics storage.
"""

import json
import logging
import hashlib
import os
import platform
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path("/Volumes/SSDRAID0/agentic-system").exists():
            return Path("/Volumes/SSDRAID0/agentic-system")
        elif Path("/Volumes/FILES/agentic-system").exists():
            return Path("/Volumes/FILES/agentic-system")
    elif system == "Linux":
        if Path("/home/marc/agentic-system").exists():
            return Path("/home/marc/agentic-system")
        elif Path("/mnt/agentic-system").exists():
            return Path("/mnt/agentic-system")
    return Path(__file__).parent.parent.parent


_STORAGE_BASE = _get_storage_base()
DB_PATH = _STORAGE_BASE / "databases" / "dspy_optimizer.db"


@dataclass
class PromptPerformance:
    """Performance metrics for a single prompt execution"""
    execution_id: str
    prompt_id: str
    module_name: str
    latency_ms: float
    token_count: int
    success: bool
    score: float
    error_message: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        return {
            "execution_id": self.execution_id,
            "prompt_id": self.prompt_id,
            "module_name": self.module_name,
            "latency_ms": self.latency_ms,
            "token_count": self.token_count,
            "success": self.success,
            "score": self.score,
            "error_message": self.error_message,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class AggregatedMetrics:
    """Aggregated performance metrics"""
    module_name: str
    total_executions: int
    success_rate: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    avg_score: float
    avg_tokens: float
    total_tokens: int
    time_period: str
    timestamp: datetime = field(default_factory=datetime.now)


class MetricsCollector:
    """
    Collects and analyzes performance metrics for DSPy modules.

    Provides real-time tracking, historical analysis, and reporting.
    """

    def __init__(self):
        self._init_database()
        self._cache: Dict[str, List[PromptPerformance]] = defaultdict(list)
        self._cache_limit = 1000

    def _init_database(self):
        """Initialize metrics tables"""
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS prompt_metrics (
                    execution_id TEXT PRIMARY KEY,
                    prompt_id TEXT NOT NULL,
                    module_name TEXT NOT NULL,
                    latency_ms REAL,
                    token_count INTEGER,
                    success INTEGER,
                    score REAL,
                    error_message TEXT,
                    metadata TEXT,
                    timestamp TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_module
                ON prompt_metrics(module_name, timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_prompt
                ON prompt_metrics(prompt_id, timestamp)
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS aggregated_metrics (
                    id TEXT PRIMARY KEY,
                    module_name TEXT NOT NULL,
                    total_executions INTEGER,
                    success_rate REAL,
                    avg_latency_ms REAL,
                    p50_latency_ms REAL,
                    p95_latency_ms REAL,
                    p99_latency_ms REAL,
                    avg_score REAL,
                    avg_tokens REAL,
                    total_tokens INTEGER,
                    time_period TEXT,
                    timestamp TEXT
                )
            """)
            conn.commit()

    def record(self, performance: PromptPerformance):
        """Record a single performance metric"""
        # Add to cache
        self._cache[performance.module_name].append(performance)

        # Trim cache if needed
        if len(self._cache[performance.module_name]) > self._cache_limit:
            self._cache[performance.module_name] = \
                self._cache[performance.module_name][-self._cache_limit:]

        # Persist to database
        self._persist_metric(performance)

    def _persist_metric(self, performance: PromptPerformance):
        """Persist metric to database"""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("""
                    INSERT INTO prompt_metrics
                    (execution_id, prompt_id, module_name, latency_ms,
                     token_count, success, score, error_message, metadata, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    performance.execution_id,
                    performance.prompt_id,
                    performance.module_name,
                    performance.latency_ms,
                    performance.token_count,
                    1 if performance.success else 0,
                    performance.score,
                    performance.error_message,
                    json.dumps(performance.metadata),
                    performance.timestamp.isoformat()
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to persist metric: {e}")

    def record_execution(
        self,
        module_name: str,
        prompt_id: str,
        latency_ms: float,
        token_count: int,
        success: bool,
        score: float,
        error_message: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> PromptPerformance:
        """Convenience method to record an execution"""
        execution_id = hashlib.md5(
            f"{module_name}_{prompt_id}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]

        perf = PromptPerformance(
            execution_id=execution_id,
            prompt_id=prompt_id,
            module_name=module_name,
            latency_ms=latency_ms,
            token_count=token_count,
            success=success,
            score=score,
            error_message=error_message,
            metadata=metadata or {}
        )

        self.record(perf)
        return perf

    def get_aggregated_metrics(
        self,
        module_name: str,
        time_period: str = "1h"
    ) -> AggregatedMetrics:
        """Get aggregated metrics for a module"""
        # Parse time period
        hours = self._parse_time_period(time_period)
        cutoff = datetime.now() - timedelta(hours=hours)

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("""
                SELECT latency_ms, token_count, success, score
                FROM prompt_metrics
                WHERE module_name = ? AND timestamp > ?
                ORDER BY timestamp DESC
            """, (module_name, cutoff.isoformat()))

            rows = cursor.fetchall()

        if not rows:
            return AggregatedMetrics(
                module_name=module_name,
                total_executions=0,
                success_rate=0.0,
                avg_latency_ms=0.0,
                p50_latency_ms=0.0,
                p95_latency_ms=0.0,
                p99_latency_ms=0.0,
                avg_score=0.0,
                avg_tokens=0.0,
                total_tokens=0,
                time_period=time_period
            )

        latencies = [r[0] for r in rows if r[0] is not None]
        tokens = [r[1] for r in rows if r[1] is not None]
        successes = [r[2] for r in rows]
        scores = [r[3] for r in rows if r[3] is not None]

        latencies_sorted = sorted(latencies) if latencies else [0]

        return AggregatedMetrics(
            module_name=module_name,
            total_executions=len(rows),
            success_rate=sum(successes) / len(successes) if successes else 0.0,
            avg_latency_ms=statistics.mean(latencies) if latencies else 0.0,
            p50_latency_ms=self._percentile(latencies_sorted, 50),
            p95_latency_ms=self._percentile(latencies_sorted, 95),
            p99_latency_ms=self._percentile(latencies_sorted, 99),
            avg_score=statistics.mean(scores) if scores else 0.0,
            avg_tokens=statistics.mean(tokens) if tokens else 0.0,
            total_tokens=sum(tokens) if tokens else 0,
            time_period=time_period
        )

    def _parse_time_period(self, period: str) -> float:
        """Parse time period string to hours"""
        if period.endswith("h"):
            return float(period[:-1])
        elif period.endswith("d"):
            return float(period[:-1]) * 24
        elif period.endswith("w"):
            return float(period[:-1]) * 24 * 7
        else:
            return 1.0

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile"""
        if not data:
            return 0.0
        k = (len(data) - 1) * percentile / 100
        f = int(k)
        c = f + 1 if f + 1 < len(data) else f
        return data[f] + (k - f) * (data[c] - data[f])

    def compare_prompts(
        self,
        prompt_a_id: str,
        prompt_b_id: str,
        time_period: str = "24h"
    ) -> Dict:
        """Compare performance of two prompts"""
        hours = self._parse_time_period(time_period)
        cutoff = datetime.now() - timedelta(hours=hours)

        with sqlite3.connect(DB_PATH) as conn:
            def get_stats(prompt_id):
                cursor = conn.execute("""
                    SELECT latency_ms, token_count, success, score
                    FROM prompt_metrics
                    WHERE prompt_id = ? AND timestamp > ?
                """, (prompt_id, cutoff.isoformat()))
                rows = cursor.fetchall()

                if not rows:
                    return None

                latencies = [r[0] for r in rows if r[0]]
                scores = [r[3] for r in rows if r[3]]
                successes = [r[2] for r in rows]

                return {
                    "executions": len(rows),
                    "success_rate": sum(successes) / len(successes),
                    "avg_latency": statistics.mean(latencies) if latencies else 0,
                    "avg_score": statistics.mean(scores) if scores else 0
                }

            stats_a = get_stats(prompt_a_id)
            stats_b = get_stats(prompt_b_id)

        if not stats_a or not stats_b:
            return {"error": "Insufficient data for comparison"}

        winner = "a" if stats_a["avg_score"] > stats_b["avg_score"] else "b"
        score_diff = abs(stats_a["avg_score"] - stats_b["avg_score"])

        return {
            "prompt_a": {
                "id": prompt_a_id,
                **stats_a
            },
            "prompt_b": {
                "id": prompt_b_id,
                **stats_b
            },
            "winner": winner,
            "score_difference": score_diff,
            "confidence": min(stats_a["executions"], stats_b["executions"]) / 100
        }

    def get_performance_trend(
        self,
        module_name: str,
        time_period: str = "7d",
        interval: str = "1h"
    ) -> List[Dict]:
        """Get performance trend over time"""
        hours = self._parse_time_period(time_period)
        interval_hours = self._parse_time_period(interval)
        cutoff = datetime.now() - timedelta(hours=hours)

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("""
                SELECT timestamp, score, latency_ms, success
                FROM prompt_metrics
                WHERE module_name = ? AND timestamp > ?
                ORDER BY timestamp
            """, (module_name, cutoff.isoformat()))

            rows = cursor.fetchall()

        if not rows:
            return []

        # Group by interval
        buckets = defaultdict(list)
        for row in rows:
            ts = datetime.fromisoformat(row[0])
            bucket_key = ts.replace(
                minute=0, second=0, microsecond=0,
                hour=(ts.hour // int(interval_hours)) * int(interval_hours)
            )
            buckets[bucket_key].append({
                "score": row[1],
                "latency": row[2],
                "success": row[3]
            })

        # Aggregate buckets
        trend = []
        for bucket_time, entries in sorted(buckets.items()):
            scores = [e["score"] for e in entries if e["score"]]
            latencies = [e["latency"] for e in entries if e["latency"]]
            successes = [e["success"] for e in entries]

            trend.append({
                "timestamp": bucket_time.isoformat(),
                "executions": len(entries),
                "avg_score": statistics.mean(scores) if scores else 0,
                "avg_latency": statistics.mean(latencies) if latencies else 0,
                "success_rate": sum(successes) / len(successes) if successes else 0
            })

        return trend

    def get_top_performers(
        self,
        limit: int = 10,
        time_period: str = "7d"
    ) -> List[Dict]:
        """Get top performing prompts"""
        hours = self._parse_time_period(time_period)
        cutoff = datetime.now() - timedelta(hours=hours)

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("""
                SELECT prompt_id, module_name,
                       AVG(score) as avg_score,
                       COUNT(*) as executions,
                       AVG(latency_ms) as avg_latency
                FROM prompt_metrics
                WHERE timestamp > ? AND score IS NOT NULL
                GROUP BY prompt_id, module_name
                HAVING COUNT(*) >= 5
                ORDER BY avg_score DESC
                LIMIT ?
            """, (cutoff.isoformat(), limit))

            return [
                {
                    "prompt_id": row[0],
                    "module_name": row[1],
                    "avg_score": row[2],
                    "executions": row[3],
                    "avg_latency": row[4]
                }
                for row in cursor.fetchall()
            ]

    def export_metrics(
        self,
        module_name: Optional[str] = None,
        time_period: str = "7d",
        format: str = "json"
    ) -> str:
        """Export metrics data"""
        hours = self._parse_time_period(time_period)
        cutoff = datetime.now() - timedelta(hours=hours)

        with sqlite3.connect(DB_PATH) as conn:
            if module_name:
                cursor = conn.execute("""
                    SELECT * FROM prompt_metrics
                    WHERE module_name = ? AND timestamp > ?
                    ORDER BY timestamp DESC
                """, (module_name, cutoff.isoformat()))
            else:
                cursor = conn.execute("""
                    SELECT * FROM prompt_metrics
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC
                """, (cutoff.isoformat(),))

            columns = [desc[0] for desc in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

        if format == "json":
            return json.dumps(rows, indent=2)
        elif format == "csv":
            import csv
            import io
            output = io.StringIO()
            if rows:
                writer = csv.DictWriter(output, fieldnames=columns)
                writer.writeheader()
                writer.writerows(rows)
            return output.getvalue()
        else:
            return json.dumps(rows)


# Decorator for automatic metrics collection
def track_performance(collector: MetricsCollector, module_name: str):
    """Decorator to automatically track function performance"""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            import time
            prompt_id = kwargs.get("prompt_id", hashlib.md5(
                str(args).encode() + str(kwargs).encode()
            ).hexdigest()[:12])

            start = time.time()
            success = True
            error = None
            result = None
            score = 0.0

            try:
                result = func(*args, **kwargs)
                if hasattr(result, 'score'):
                    score = result.score
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                latency = (time.time() - start) * 1000
                collector.record_execution(
                    module_name=module_name,
                    prompt_id=prompt_id,
                    latency_ms=latency,
                    token_count=0,  # Would need LM integration
                    success=success,
                    score=score,
                    error_message=error
                )

            return result
        return wrapper
    return decorator
