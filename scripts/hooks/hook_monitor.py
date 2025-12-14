#!/usr/bin/env python3
"""
Hook Performance Monitor - Real-time dashboard for hook metrics.

Displays:
- Hook execution times and status
- Circuit breaker states
- Prometheus metrics summary
- Integration health
"""

import sqlite3
import json
import time
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import argparse

# Performance thresholds (ms)
THRESHOLD_GOOD = 50
THRESHOLD_WARNING = 100
THRESHOLD_CRITICAL = 200
THRESHOLD_TIMEOUT = 500

# Database path
DB_PATH = Path("/home/marc/agentic-system/databases/hook_metrics.db")
CIRCUIT_BREAKER_FILE = Path("/home/marc/agentic-system/databases/circuit_breaker_states.json")

# Service health endpoints
# NOTE: Activity Dashboard (4100) and AGI MCP (3100) were aspirational - never implemented
# See: docs/ASPIRATIONAL_DOCUMENTATION_AUDIT.md
SERVICES = {
    "TPU Warm": "http://localhost:8780/health",
    # "Activity Dashboard": "http://localhost:4100/health",  # Aspirational - not implemented
    "Voice Mode": "http://localhost:8765/health",
    # "AGI MCP": "http://localhost:3100/health",  # Aspirational - not implemented
    "Enhanced Memory": "http://localhost:8101/health",
}


def get_db_connection() -> sqlite3.Connection:
    """Get database connection, creating schema if needed."""
    db_path = DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Create schema if not exists (matching existing schema)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hook_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hook_type TEXT NOT NULL,
            integration_name TEXT NOT NULL,
            execution_time_ms REAL NOT NULL,
            success INTEGER NOT NULL,
            timeout INTEGER DEFAULT 0,
            error TEXT,
            timestamp REAL NOT NULL,
            node_id TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_hook_metrics_timestamp
        ON hook_metrics(timestamp DESC)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_hook_metrics_hook_type
        ON hook_metrics(hook_type)
    """)
    conn.commit()
    return conn


def get_recent_metrics(hours: int = 24, limit: int = 100) -> List[Dict]:
    """Get recent hook metrics."""
    conn = get_db_connection()
    import time
    cutoff_ts = time.time() - (hours * 3600)

    cursor = conn.execute("""
        SELECT id, hook_type, integration_name as integration,
               execution_time_ms as duration_ms, success, timeout,
               error as error_message, timestamp,
               datetime(timestamp, 'unixepoch', 'localtime') as timestamp_str
        FROM hook_metrics
        WHERE timestamp > ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (cutoff_ts, limit))

    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_hook_stats(hours: int = 24) -> Dict:
    """Get aggregated hook statistics."""
    conn = get_db_connection()
    import time
    cutoff_ts = time.time() - (hours * 3600)

    # Get stats by hook type
    cursor = conn.execute("""
        SELECT
            hook_type,
            COUNT(*) as count,
            AVG(execution_time_ms) as avg_duration,
            MAX(execution_time_ms) as max_duration,
            MIN(execution_time_ms) as min_duration,
            SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
            SUM(CASE WHEN timeout = 1 THEN 1 ELSE 0 END) as timeout_count
        FROM hook_metrics
        WHERE timestamp > ?
        GROUP BY hook_type
        ORDER BY count DESC
    """, (cutoff_ts,))

    stats = {}
    for row in cursor.fetchall():
        stats[row['hook_type']] = {
            'count': row['count'],
            'avg_duration': round(row['avg_duration'], 2) if row['avg_duration'] else 0,
            'max_duration': row['max_duration'] or 0,
            'min_duration': row['min_duration'] or 0,
            'success_rate': round(row['success_count'] / row['count'] * 100, 1) if row['count'] > 0 else 0,
            'timeout_rate': round(row['timeout_count'] / row['count'] * 100, 1) if row['count'] > 0 else 0,
        }

    conn.close()
    return stats


def get_integration_stats(hours: int = 24) -> Dict:
    """Get stats by integration."""
    conn = get_db_connection()
    import time
    cutoff_ts = time.time() - (hours * 3600)

    cursor = conn.execute("""
        SELECT
            integration_name as integration,
            COUNT(*) as count,
            AVG(execution_time_ms) as avg_duration,
            SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count
        FROM hook_metrics
        WHERE timestamp > ? AND integration_name IS NOT NULL
        GROUP BY integration_name
        ORDER BY count DESC
    """, (cutoff_ts,))

    stats = {}
    for row in cursor.fetchall():
        if row['integration']:
            stats[row['integration']] = {
                'count': row['count'],
                'avg_duration': round(row['avg_duration'], 2) if row['avg_duration'] else 0,
                'success_rate': round(row['success_count'] / row['count'] * 100, 1) if row['count'] > 0 else 0,
            }

    conn.close()
    return stats


def get_circuit_breaker_states() -> Dict:
    """Get current circuit breaker states."""
    if CIRCUIT_BREAKER_FILE.exists():
        try:
            with open(CIRCUIT_BREAKER_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def check_service_health(url: str, timeout: float = 0.5) -> bool:
    """Check if a service is healthy."""
    try:
        import urllib.request
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status == 200
    except Exception:
        return False


def format_duration(ms: float) -> str:
    """Format duration with color coding."""
    if ms < THRESHOLD_GOOD:
        return f"\033[92m{ms:.0f}ms\033[0m"  # Green
    elif ms < THRESHOLD_WARNING:
        return f"\033[93m{ms:.0f}ms\033[0m"  # Yellow
    elif ms < THRESHOLD_CRITICAL:
        return f"\033[91m{ms:.0f}ms\033[0m"  # Red
    else:
        return f"\033[95m{ms:.0f}ms\033[0m"  # Purple (critical)


def format_percentage(pct: float, invert: bool = False) -> str:
    """Format percentage with color coding."""
    threshold_good = 95 if not invert else 5
    threshold_warning = 80 if not invert else 20

    if invert:
        if pct < threshold_good:
            return f"\033[92m{pct:.1f}%\033[0m"
        elif pct < threshold_warning:
            return f"\033[93m{pct:.1f}%\033[0m"
        else:
            return f"\033[91m{pct:.1f}%\033[0m"
    else:
        if pct >= threshold_good:
            return f"\033[92m{pct:.1f}%\033[0m"
        elif pct >= threshold_warning:
            return f"\033[93m{pct:.1f}%\033[0m"
        else:
            return f"\033[91m{pct:.1f}%\033[0m"


def print_dashboard(hours: int = 24, show_recent: bool = True):
    """Print the full monitoring dashboard."""
    print("\033[2J\033[H")  # Clear screen
    print("=" * 70)
    print(f"  Hook Performance Monitor - Last {hours}h")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Hook Statistics
    print("\n\033[1m--- Hook Statistics ---\033[0m")
    stats = get_hook_stats(hours)

    if stats:
        print(f"{'Hook Type':<20} {'Count':<8} {'Avg':<12} {'Max':<12} {'Success':<10} {'Timeout':<10}")
        print("-" * 70)

        for hook_type, data in sorted(stats.items(), key=lambda x: x[1]['count'], reverse=True):
            avg = format_duration(data['avg_duration'])
            max_d = format_duration(data['max_duration'])
            success = format_percentage(data['success_rate'])
            timeout = format_percentage(data['timeout_rate'], invert=True)
            print(f"{hook_type:<20} {data['count']:<8} {avg:<20} {max_d:<20} {success:<18} {timeout:<10}")
    else:
        print("  No metrics recorded yet")

    # Integration Statistics
    print("\n\033[1m--- Integration Statistics ---\033[0m")
    int_stats = get_integration_stats(hours)

    if int_stats:
        print(f"{'Integration':<20} {'Count':<8} {'Avg Duration':<15} {'Success Rate':<12}")
        print("-" * 55)

        for integration, data in sorted(int_stats.items(), key=lambda x: x[1]['count'], reverse=True):
            avg = format_duration(data['avg_duration'])
            success = format_percentage(data['success_rate'])
            print(f"{integration:<20} {data['count']:<8} {avg:<23} {success:<12}")
    else:
        print("  No integration metrics yet")

    # Circuit Breaker States
    print("\n\033[1m--- Circuit Breaker States ---\033[0m")
    cb_states = get_circuit_breaker_states()

    if cb_states:
        for name, state in cb_states.items():
            is_open = state.get('open', False)
            failures = state.get('failures', 0)
            status = "\033[91mOPEN\033[0m" if is_open else "\033[92mCLOSED\033[0m"
            print(f"  {name}: {status} (failures: {failures})")
    else:
        print("  All circuits closed (healthy)")

    # Service Health
    print("\n\033[1m--- Service Health ---\033[0m")
    for name, url in SERVICES.items():
        healthy = check_service_health(url)
        status = "\033[92m OK \033[0m" if healthy else "\033[91mDOWN\033[0m"
        print(f"  {name}: [{status}] {url}")

    # Recent Events
    if show_recent:
        print("\n\033[1m--- Recent Events (last 10) ---\033[0m")
        recent = get_recent_metrics(hours=1, limit=10)

        if recent:
            print(f"{'Time':<12} {'Hook':<18} {'Duration':<12} {'Status':<10}")
            print("-" * 52)

            for event in recent:
                ts = event.get('timestamp_str', '')[-8:-3] if event.get('timestamp_str') else "?"
                hook = event['hook_type'][:17]
                duration = format_duration(event.get('duration_ms', 0))

                if event['timeout']:
                    status = "\033[95mTIMEOUT\033[0m"
                elif event['success']:
                    status = "\033[92mOK\033[0m"
                else:
                    status = "\033[91mFAIL\033[0m"

                print(f"{ts:<12} {hook:<18} {duration:<20} {status:<10}")
        else:
            print("  No recent events")

    print("\n" + "=" * 70)
    print("  Thresholds: Good <50ms | Warning <100ms | Critical <200ms | Timeout >=500ms")
    print("=" * 70)


def export_metrics(hours: int = 24, format: str = 'json') -> str:
    """Export metrics in specified format."""
    stats = get_hook_stats(hours)
    int_stats = get_integration_stats(hours)
    recent = get_recent_metrics(hours, limit=1000)

    data = {
        'exported_at': datetime.now().isoformat(),
        'period_hours': hours,
        'hook_stats': stats,
        'integration_stats': int_stats,
        'circuit_breakers': get_circuit_breaker_states(),
        'recent_events': recent,
    }

    if format == 'json':
        return json.dumps(data, indent=2)
    else:
        # Simple text format
        lines = [
            f"Hook Metrics Export - {data['exported_at']}",
            f"Period: {hours} hours",
            "",
            "Hook Statistics:",
        ]
        for hook, s in stats.items():
            lines.append(f"  {hook}: count={s['count']}, avg={s['avg_duration']}ms, success={s['success_rate']}%")
        return "\n".join(lines)


def run_continuous(interval: int = 5, hours: int = 1):
    """Run continuous monitoring."""
    print("Starting continuous monitoring (Ctrl+C to stop)...")
    try:
        while True:
            print_dashboard(hours=hours, show_recent=True)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")


def main():
    parser = argparse.ArgumentParser(description='Hook Performance Monitor')
    parser.add_argument('--hours', type=int, default=24, help='Time window in hours')
    parser.add_argument('--continuous', '-c', action='store_true', help='Continuous monitoring mode')
    parser.add_argument('--interval', type=int, default=5, help='Refresh interval in seconds')
    parser.add_argument('--export', type=str, choices=['json', 'text'], help='Export metrics')
    parser.add_argument('--no-recent', action='store_true', help='Hide recent events')

    args = parser.parse_args()

    if args.export:
        print(export_metrics(args.hours, args.export))
    elif args.continuous:
        run_continuous(args.interval, args.hours)
    else:
        print_dashboard(args.hours, not args.no_recent)


if __name__ == '__main__':
    main()
