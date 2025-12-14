"""
Unified Eval System for Agentic Self-Improvement

This module provides eval tracking for all MCP servers, agents, and system components.
All evals feed into the enhanced-memory database for analysis and self-improvement.

Usage in MCP servers:
    from evals import track_tool_call, track_quality, EvalContext

    @track_tool_call
    async def my_tool(args):
        result = do_something()
        track_quality("relevance", 0.85)  # Optional quality metric
        return result

Usage for manual tracking:
    from evals import record_eval

    record_eval(
        component="research-paper",
        metric="extraction_quality",
        value=0.92,
        context={"paper_id": "arxiv:2401.12345"}
    )
"""

import time
import sqlite3
import json
import functools
import threading
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
import os

# Database path
DB_PATH = Path.home() / '.claude/enhanced_memories/memory.db'

# Thread-local storage for eval context
_eval_context = threading.local()


@dataclass
class EvalContext:
    """Context for tracking evals within a request/operation"""
    component: str
    operation: str
    start_time: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    quality_scores: Dict[str, float] = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None


def get_db_connection() -> sqlite3.Connection:
    """Get database connection with proper settings"""
    conn = sqlite3.connect(str(DB_PATH), timeout=5.0)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def ensure_eval_tables():
    """Ensure all eval tables exist"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # MCP tool call evals
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mcp_tool_evals (
            eval_id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_name TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            execution_time_ms REAL,
            success BOOLEAN DEFAULT 1,
            error_message TEXT,
            input_size_bytes INTEGER,
            output_size_bytes INTEGER,
            quality_scores TEXT,  -- JSON dict of quality metrics
            metadata TEXT,  -- JSON additional context
            session_id TEXT,
            node_id TEXT DEFAULT 'default',
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mcp_server ON mcp_tool_evals(server_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mcp_tool ON mcp_tool_evals(tool_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mcp_time ON mcp_tool_evals(recorded_at)")

    # Generic component evals (for anything not covered by specific tables)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS component_evals (
            eval_id INTEGER PRIMARY KEY AUTOINCREMENT,
            component TEXT NOT NULL,
            metric_name TEXT NOT NULL,
            metric_value REAL NOT NULL,
            metric_unit TEXT,
            context TEXT,  -- JSON
            session_id TEXT,
            node_id TEXT DEFAULT 'default',
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_comp_name ON component_evals(component)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_comp_metric ON component_evals(metric_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_comp_time ON component_evals(recorded_at)")

    # Self-improvement actions taken
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS improvement_actions (
            action_id INTEGER PRIMARY KEY AUTOINCREMENT,
            trigger_metric TEXT NOT NULL,
            trigger_value REAL,
            trigger_threshold REAL,
            action_type TEXT NOT NULL,  -- parameter_tune, alert, retrain, etc.
            action_details TEXT,  -- JSON
            outcome TEXT,  -- pending, success, failed
            outcome_metric_before REAL,
            outcome_metric_after REAL,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# Ensure tables exist on import
try:
    ensure_eval_tables()
except Exception as e:
    print(f"Warning: Could not initialize eval tables: {e}")


def record_eval(
    component: str,
    metric: str,
    value: float,
    unit: str = None,
    context: Dict[str, Any] = None,
    session_id: str = None
):
    """Record a generic eval metric"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO component_evals (component, metric_name, metric_value, metric_unit, context, session_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            component,
            metric,
            value,
            unit,
            json.dumps(context) if context else None,
            session_id or os.environ.get('CLAUDE_SESSION_ID', 'unknown')
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Eval recording failed: {e}")


def record_mcp_tool_eval(
    server_name: str,
    tool_name: str,
    execution_time_ms: float,
    success: bool = True,
    error_message: str = None,
    input_size: int = 0,
    output_size: int = 0,
    quality_scores: Dict[str, float] = None,
    metadata: Dict[str, Any] = None
):
    """Record MCP tool execution eval"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO mcp_tool_evals
            (server_name, tool_name, execution_time_ms, success, error_message,
             input_size_bytes, output_size_bytes, quality_scores, metadata, session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            server_name,
            tool_name,
            execution_time_ms,
            success,
            error_message,
            input_size,
            output_size,
            json.dumps(quality_scores) if quality_scores else None,
            json.dumps(metadata) if metadata else None,
            os.environ.get('CLAUDE_SESSION_ID', 'unknown')
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"MCP eval recording failed: {e}")


def track_tool_call(server_name: str):
    """Decorator to track MCP tool calls with timing and success/failure"""
    def decorator(func: Callable):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            success = True
            error_msg = None
            result = None

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_msg = str(e)
                raise
            finally:
                elapsed_ms = (time.time() - start) * 1000

                # Get quality scores from context if available
                quality = getattr(_eval_context, 'quality_scores', {})

                # Calculate input/output sizes
                input_size = len(json.dumps(kwargs)) if kwargs else 0
                output_size = len(json.dumps(result)) if result else 0

                record_mcp_tool_eval(
                    server_name=server_name,
                    tool_name=func.__name__,
                    execution_time_ms=elapsed_ms,
                    success=success,
                    error_message=error_msg,
                    input_size=input_size,
                    output_size=output_size,
                    quality_scores=quality if quality else None
                )

                # Clear context
                if hasattr(_eval_context, 'quality_scores'):
                    _eval_context.quality_scores = {}

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            success = True
            error_msg = None
            result = None

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_msg = str(e)
                raise
            finally:
                elapsed_ms = (time.time() - start) * 1000
                quality = getattr(_eval_context, 'quality_scores', {})
                input_size = len(json.dumps(kwargs)) if kwargs else 0
                output_size = len(json.dumps(result)) if result else 0

                record_mcp_tool_eval(
                    server_name=server_name,
                    tool_name=func.__name__,
                    execution_time_ms=elapsed_ms,
                    success=success,
                    error_message=error_msg,
                    input_size=input_size,
                    output_size=output_size,
                    quality_scores=quality if quality else None
                )

                if hasattr(_eval_context, 'quality_scores'):
                    _eval_context.quality_scores = {}

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def track_quality(metric_name: str, value: float):
    """Track a quality metric within current eval context"""
    if not hasattr(_eval_context, 'quality_scores'):
        _eval_context.quality_scores = {}
    _eval_context.quality_scores[metric_name] = value


@contextmanager
def eval_context(component: str, operation: str, **metadata):
    """Context manager for tracking an operation with evals"""
    ctx = EvalContext(component=component, operation=operation, metadata=metadata)
    start = time.time()

    try:
        yield ctx
    except Exception as e:
        ctx.success = False
        ctx.error = str(e)
        raise
    finally:
        elapsed_ms = (time.time() - start) * 1000

        record_eval(
            component=component,
            metric=f"{operation}_execution_time",
            value=elapsed_ms,
            unit="ms",
            context={
                "success": ctx.success,
                "error": ctx.error,
                "quality_scores": ctx.quality_scores,
                **ctx.metadata
            }
        )

        # Record individual quality scores
        for metric, value in ctx.quality_scores.items():
            record_eval(
                component=component,
                metric=f"{operation}_{metric}",
                value=value,
                context=ctx.metadata
            )


# Convenience functions for specific eval types
def record_memory_retrieval(
    query: str,
    results_count: int,
    relevance_score: float,
    latency_ms: float,
    retrieval_type: str = "hybrid"
):
    """Record memory retrieval quality"""
    record_eval("enhanced-memory", "retrieval_relevance", relevance_score,
                context={"query_length": len(query), "results": results_count, "type": retrieval_type})
    record_eval("enhanced-memory", "retrieval_latency", latency_ms, unit="ms",
                context={"results": results_count, "type": retrieval_type})


def record_agent_execution(
    agent_type: str,
    task_description: str,
    execution_time_ms: float,
    success: bool,
    quality_score: float = None,
    tokens_used: int = None
):
    """Record agent task execution"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO agent_evals
            (agent_type, task_description, execution_time_ms, success, quality_score, tokens_used, parent_session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            agent_type,
            task_description[:500] if task_description else None,
            execution_time_ms,
            success,
            quality_score,
            tokens_used,
            os.environ.get('CLAUDE_SESSION_ID', 'unknown')
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Agent eval recording failed: {e}")


def record_research_extraction(
    source_type: str,  # arxiv, semantic_scholar, youtube
    source_id: str,
    concepts_extracted: int,
    insights_extracted: int,
    quality_score: float,
    latency_ms: float
):
    """Record research/video extraction quality"""
    record_eval("research-extraction", f"{source_type}_quality", quality_score,
                context={"source_id": source_id, "concepts": concepts_extracted, "insights": insights_extracted})
    record_eval("research-extraction", f"{source_type}_latency", latency_ms, unit="ms",
                context={"source_id": source_id})


def record_voice_transcription(
    duration_seconds: float,
    transcription_length: int,
    confidence: float,
    latency_ms: float,
    model: str = "whisper"
):
    """Record voice transcription quality"""
    record_eval("voice-mode", "transcription_confidence", confidence,
                context={"duration": duration_seconds, "length": transcription_length, "model": model})
    record_eval("voice-mode", "transcription_latency", latency_ms, unit="ms",
                context={"duration": duration_seconds, "model": model})


def record_node_communication(
    from_node: str,
    to_node: str,
    message_type: str,
    delivery_success: bool,
    latency_ms: float
):
    """Record inter-node communication"""
    record_eval("node-chat", "delivery_success", 1.0 if delivery_success else 0.0,
                context={"from": from_node, "to": to_node, "type": message_type})
    record_eval("node-chat", "delivery_latency", latency_ms, unit="ms",
                context={"from": from_node, "to": to_node})


# Export public API
__all__ = [
    'record_eval',
    'record_mcp_tool_eval',
    'track_tool_call',
    'track_quality',
    'eval_context',
    'record_memory_retrieval',
    'record_agent_execution',
    'record_research_extraction',
    'record_voice_transcription',
    'record_node_communication',
    'EvalContext',
]
