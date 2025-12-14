#!/usr/bin/env python3
"""
Frontend Performance Optimizer

Analyzes and optimizes frontend performance across the agentic system:
1. Token usage optimization for LLM interactions
2. Query optimization for database operations
3. Cache tuning for semantic and vector search
4. API endpoint response time analysis
5. Real-time monitoring and alerting

Usage:
    ./optimize-frontend-performance.py --analyze     # Analyze current performance
    ./optimize-frontend-performance.py --optimize    # Apply optimizations
    ./optimize-frontend-performance.py --monitor     # Live monitoring mode

Author: AGI Development System
Created: 2025-12-05
Task: Frontend Performance Optimization (Task 42)
"""

import argparse
import json
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FrontendPerformanceOptimizer:
    """Main optimizer class for frontend performance."""

    def __init__(self):
        self.memory_db = Path('/mnt/agentic-system/mcp-servers/enhanced-memory-mcp/memory.db')
        self.cache_db = Path('/mnt/agentic-system/mcp-servers/enhanced-memory-mcp/semantic_cache.db')
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'optimizations': [],
            'metrics': {}
        }

    def analyze_token_usage(self) -> Dict:
        """Analyze token usage patterns and identify optimization opportunities."""
        logger.info("Analyzing token usage patterns...")

        try:
            if not self.memory_db.exists():
                return {'error': 'Memory database not found'}

            conn = sqlite3.connect(self.memory_db)
            cursor = conn.cursor()

            # Analyze entity content lengths
            cursor.execute("""
                SELECT
                    entityType,
                    COUNT(*) as count,
                    AVG(LENGTH(observations)) as avg_length,
                    MAX(LENGTH(observations)) as max_length,
                    MIN(LENGTH(observations)) as min_length
                FROM entities
                GROUP BY entityType
            """)

            type_analysis = []
            total_tokens_estimated = 0

            for row in cursor.fetchall():
                entity_type, count, avg_len, max_len, min_len = row
                # Rough token estimate: 4 characters per token
                avg_tokens = avg_len / 4 if avg_len else 0
                total_tokens = avg_tokens * count

                type_analysis.append({
                    'type': entity_type,
                    'count': count,
                    'avg_tokens': int(avg_tokens),
                    'max_tokens': int(max_len / 4) if max_len else 0,
                    'total_tokens_estimated': int(total_tokens)
                })

                total_tokens_estimated += total_tokens

            # Identify optimization opportunities
            optimizations = []

            # Check for oversized entities
            cursor.execute("""
                SELECT COUNT(*)
                FROM entities
                WHERE LENGTH(observations) > 4000
            """)
            oversized_count = cursor.fetchone()[0]

            if oversized_count > 0:
                optimizations.append({
                    'type': 'token_reduction',
                    'issue': f'{oversized_count} entities with >1000 tokens',
                    'recommendation': 'Enable compression for large entities',
                    'potential_savings': f'{oversized_count * 500} tokens'
                })

            # Check semantic cache effectiveness
            cursor.execute("""
                SELECT COUNT(DISTINCT query_hash) as cached_queries
                FROM semantic_cache
                WHERE last_accessed > datetime('now', '-7 days')
            """, ())

            conn.close()

            result = {
                'total_entities': sum(t['count'] for t in type_analysis),
                'total_tokens_estimated': int(total_tokens_estimated),
                'by_type': type_analysis,
                'optimizations': optimizations
            }

            self.results['metrics']['token_usage'] = result
            return result

        except Exception as e:
            logger.error(f"Error analyzing token usage: {e}")
            return {'error': str(e)}

    def analyze_query_performance(self) -> Dict:
        """Analyze database query performance."""
        logger.info("Analyzing query performance...")

        try:
            if not self.memory_db.exists():
                return {'error': 'Memory database not found'}

            conn = sqlite3.connect(self.memory_db)
            cursor = conn.cursor()

            queries = []

            # Test common query patterns
            test_queries = [
                ('SELECT COUNT(*) FROM entities', 'entity_count'),
                ('SELECT * FROM entities ORDER BY created_at DESC LIMIT 10', 'recent_entities'),
                ('SELECT * FROM entities WHERE entityType = "concept" LIMIT 20', 'concept_search'),
                ('SELECT * FROM working_memory WHERE expires_at > datetime("now") LIMIT 50', 'working_memory'),
                ('SELECT * FROM episodic_memory ORDER BY timestamp DESC LIMIT 20', 'recent_episodes'),
            ]

            for query, label in test_queries:
                start = time.time()
                try:
                    cursor.execute(query)
                    cursor.fetchall()
                    latency_ms = (time.time() - start) * 1000

                    queries.append({
                        'label': label,
                        'latency_ms': round(latency_ms, 2),
                        'status': 'ok' if latency_ms < 100 else 'slow'
                    })
                except Exception as e:
                    queries.append({
                        'label': label,
                        'error': str(e)
                    })

            conn.close()

            # Identify slow queries
            slow_queries = [q for q in queries if q.get('latency_ms', 0) > 100]

            optimizations = []
            if slow_queries:
                optimizations.append({
                    'type': 'query_optimization',
                    'issue': f'{len(slow_queries)} queries >100ms',
                    'recommendation': 'Add indexes or optimize query structure',
                    'affected_queries': [q['label'] for q in slow_queries]
                })

            result = {
                'queries': queries,
                'avg_latency_ms': round(sum(q.get('latency_ms', 0) for q in queries) / len(queries), 2),
                'slow_queries': len(slow_queries),
                'optimizations': optimizations
            }

            self.results['metrics']['query_performance'] = result
            return result

        except Exception as e:
            logger.error(f"Error analyzing query performance: {e}")
            return {'error': str(e)}

    def analyze_cache_efficiency(self) -> Dict:
        """Analyze cache hit rates and effectiveness."""
        logger.info("Analyzing cache efficiency...")

        try:
            if not self.cache_db.exists():
                return {'warning': 'Semantic cache database not found'}

            conn = sqlite3.connect(self.cache_db)
            cursor = conn.cursor()

            # Analyze cache statistics
            cursor.execute("""
                SELECT
                    COUNT(*) as total_entries,
                    SUM(access_count) as total_accesses,
                    AVG(access_count) as avg_accesses,
                    SUM(CASE WHEN last_accessed > datetime('now', '-1 hour') THEN 1 ELSE 0 END) as recent_accesses
                FROM semantic_cache
            """)

            row = cursor.fetchone()
            total_entries, total_accesses, avg_accesses, recent_accesses = row

            # Calculate hit rate (estimate)
            hit_rate = 0.0
            if total_accesses:
                # Entries accessed multiple times suggest cache hits
                hit_rate = min(1.0, (avg_accesses - 1) / avg_accesses)

            # Check for stale entries
            cursor.execute("""
                SELECT COUNT(*)
                FROM semantic_cache
                WHERE last_accessed < datetime('now', '-7 days')
            """)
            stale_entries = cursor.fetchone()[0]

            conn.close()

            optimizations = []

            # Low hit rate
            if hit_rate < 0.5:
                optimizations.append({
                    'type': 'cache_tuning',
                    'issue': f'Low cache hit rate: {hit_rate:.1%}',
                    'recommendation': 'Adjust similarity threshold or increase cache TTL'
                })

            # Too many stale entries
            if stale_entries > total_entries * 0.3:
                optimizations.append({
                    'type': 'cache_cleanup',
                    'issue': f'{stale_entries} stale cache entries',
                    'recommendation': 'Run cache cleanup to free resources'
                })

            result = {
                'total_entries': total_entries or 0,
                'total_accesses': total_accesses or 0,
                'hit_rate_estimated': round(hit_rate, 3),
                'recent_activity': recent_accesses or 0,
                'stale_entries': stale_entries,
                'optimizations': optimizations
            }

            self.results['metrics']['cache_efficiency'] = result
            return result

        except Exception as e:
            logger.error(f"Error analyzing cache efficiency: {e}")
            return {'error': str(e)}

    def apply_optimizations(self):
        """Apply performance optimizations."""
        logger.info("Applying performance optimizations...")

        applied = []

        try:
            # 1. Enable compression for large entities
            if self.memory_db.exists():
                conn = sqlite3.connect(self.memory_db)
                cursor = conn.cursor()

                # Check if compression is being used
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM entities
                    WHERE LENGTH(observations) > 4000
                    AND compression_ratio IS NULL
                """)
                uncompressed = cursor.fetchone()[0]

                if uncompressed > 0:
                    logger.info(f"Found {uncompressed} large entities that could benefit from compression")
                    applied.append({
                        'optimization': 'compression_recommendation',
                        'status': 'recommended',
                        'note': f'{uncompressed} entities >1000 tokens should use compression'
                    })

                conn.close()

            # 2. Cache cleanup
            if self.cache_db.exists():
                conn = sqlite3.connect(self.cache_db)
                cursor = conn.cursor()

                # Remove entries not accessed in 30 days
                cursor.execute("""
                    DELETE FROM semantic_cache
                    WHERE last_accessed < datetime('now', '-30 days')
                """)
                deleted = cursor.rowcount
                conn.commit()
                conn.close()

                if deleted > 0:
                    applied.append({
                        'optimization': 'cache_cleanup',
                        'status': 'applied',
                        'result': f'Removed {deleted} stale cache entries'
                    })

            # 3. Query optimization recommendations
            applied.append({
                'optimization': 'index_recommendations',
                'status': 'recommended',
                'note': 'Consider adding indexes on frequently queried columns'
            })

        except Exception as e:
            logger.error(f"Error applying optimizations: {e}")
            applied.append({
                'optimization': 'error',
                'status': 'failed',
                'error': str(e)
            })

        self.results['optimizations'] = applied
        return applied

    def generate_report(self) -> str:
        """Generate a performance optimization report."""
        logger.info("Generating performance report...")

        report = []
        report.append("=" * 70)
        report.append("FRONTEND PERFORMANCE OPTIMIZATION REPORT")
        report.append("=" * 70)
        report.append(f"Generated: {self.results['timestamp']}")
        report.append("")

        # Token Usage
        if 'token_usage' in self.results['metrics']:
            tu = self.results['metrics']['token_usage']
            report.append("TOKEN USAGE ANALYSIS")
            report.append("-" * 70)
            report.append(f"  Total Entities: {tu.get('total_entities', 0)}")
            report.append(f"  Estimated Total Tokens: {tu.get('total_tokens_estimated', 0):,}")
            report.append("")

            if 'by_type' in tu:
                report.append("  By Entity Type:")
                for t in tu['by_type']:
                    report.append(f"    - {t['type']}: {t['count']} entities, ~{t['avg_tokens']} avg tokens")
            report.append("")

        # Query Performance
        if 'query_performance' in self.results['metrics']:
            qp = self.results['metrics']['query_performance']
            report.append("QUERY PERFORMANCE ANALYSIS")
            report.append("-" * 70)
            report.append(f"  Average Query Latency: {qp.get('avg_latency_ms', 0):.2f} ms")
            report.append(f"  Slow Queries (>100ms): {qp.get('slow_queries', 0)}")
            report.append("")

            if 'queries' in qp:
                report.append("  Query Breakdown:")
                for q in qp['queries']:
                    status = q.get('status', 'error')
                    latency = q.get('latency_ms', 0)
                    report.append(f"    - {q['label']}: {latency:.2f}ms [{status}]")
            report.append("")

        # Cache Efficiency
        if 'cache_efficiency' in self.results['metrics']:
            ce = self.results['metrics']['cache_efficiency']
            report.append("CACHE EFFICIENCY ANALYSIS")
            report.append("-" * 70)
            report.append(f"  Total Cache Entries: {ce.get('total_entries', 0)}")
            report.append(f"  Estimated Hit Rate: {ce.get('hit_rate_estimated', 0):.1%}")
            report.append(f"  Recent Activity: {ce.get('recent_activity', 0)} accesses (last hour)")
            report.append(f"  Stale Entries: {ce.get('stale_entries', 0)}")
            report.append("")

        # Optimizations
        if self.results.get('optimizations'):
            report.append("OPTIMIZATIONS APPLIED")
            report.append("-" * 70)
            for opt in self.results['optimizations']:
                report.append(f"  [{opt['status']}] {opt['optimization']}")
                if 'result' in opt:
                    report.append(f"    Result: {opt['result']}")
                if 'note' in opt:
                    report.append(f"    Note: {opt['note']}")
            report.append("")

        # Recommendations
        report.append("RECOMMENDATIONS")
        report.append("-" * 70)

        all_optimizations = []
        for metric in self.results['metrics'].values():
            if 'optimizations' in metric:
                all_optimizations.extend(metric['optimizations'])

        if all_optimizations:
            for i, opt in enumerate(all_optimizations, 1):
                report.append(f"  {i}. [{opt['type']}]")
                report.append(f"     Issue: {opt['issue']}")
                report.append(f"     Recommendation: {opt['recommendation']}")
                if 'potential_savings' in opt:
                    report.append(f"     Potential Savings: {opt['potential_savings']}")
                report.append("")
        else:
            report.append("  No critical optimizations needed at this time.")
            report.append("")

        report.append("=" * 70)

        return "\n".join(report)

    def monitor_live(self, interval: int = 30):
        """Live monitoring mode."""
        logger.info(f"Starting live monitoring (interval: {interval}s)...")
        logger.info("Press Ctrl+C to stop")

        try:
            while True:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Running performance check...")

                token_result = self.analyze_token_usage()
                query_result = self.analyze_query_performance()
                cache_result = self.analyze_cache_efficiency()

                # Quick summary
                print(f"  Tokens: ~{token_result.get('total_tokens_estimated', 0):,}")
                print(f"  Avg Query Latency: {query_result.get('avg_latency_ms', 0):.2f}ms")
                print(f"  Cache Hit Rate: {cache_result.get('hit_rate_estimated', 0):.1%}")

                # Alert on issues
                if query_result.get('slow_queries', 0) > 0:
                    print(f"  ⚠️  WARNING: {query_result['slow_queries']} slow queries detected")

                if cache_result.get('hit_rate_estimated', 0) < 0.5:
                    print(f"  ⚠️  WARNING: Low cache hit rate")

                time.sleep(interval)

        except KeyboardInterrupt:
            print("\nMonitoring stopped.")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Frontend Performance Optimizer for AGI System'
    )
    parser.add_argument(
        '--analyze',
        action='store_true',
        help='Analyze current performance'
    )
    parser.add_argument(
        '--optimize',
        action='store_true',
        help='Apply performance optimizations'
    )
    parser.add_argument(
        '--monitor',
        action='store_true',
        help='Live monitoring mode'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=30,
        help='Monitoring interval in seconds (default: 30)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output file for report (default: stdout)'
    )

    args = parser.parse_args()

    optimizer = FrontendPerformanceOptimizer()

    if args.monitor:
        optimizer.monitor_live(interval=args.interval)
        return

    if args.analyze or args.optimize or not any([args.analyze, args.optimize, args.monitor]):
        # Run analysis
        optimizer.analyze_token_usage()
        optimizer.analyze_query_performance()
        optimizer.analyze_cache_efficiency()

    if args.optimize:
        # Apply optimizations
        optimizer.apply_optimizations()

    # Generate report
    report = optimizer.generate_report()

    if args.output:
        Path(args.output).write_text(report)
        logger.info(f"Report saved to: {args.output}")
    else:
        print(report)

    # Save JSON results
    results_file = Path('/mnt/agentic-system/performance-snapshots/frontend_performance_latest.json')
    results_file.parent.mkdir(parents=True, exist_ok=True)
    results_file.write_text(json.dumps(optimizer.results, indent=2))
    logger.info(f"Results saved to: {results_file}")


if __name__ == '__main__':
    main()
