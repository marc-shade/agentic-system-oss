#!/usr/bin/env python3
"""
Latent Reasoning Analyzer - Baseline Metrics and Reporting
Generates insights from monitored execution patterns
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

DB_PATH = Path.home() / ".claude" / "latent-reasoning-monitor.db"

class LatentReasoningAnalyzer:
    """Analyze execution patterns and generate reports"""

    def __init__(self):
        self.db_path = DB_PATH

    def get_comprehensive_metrics(self, days=7):
        """Get comprehensive baseline metrics"""
        if not self.db_path.exists():
            return {
                'error': 'No monitoring data available yet',
                'message': 'Run some tasks first to collect baseline data'
            }

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        # Overall statistics
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
                AVG(tokens_used) as avg_tokens,
                AVG(duration_seconds) as avg_duration,
                SUM(tokens_used) as total_tokens
            FROM task_executions
            WHERE timestamp >= ?
        """, (cutoff,))
        overall = cursor.fetchone()

        # Execution method breakdown
        cursor.execute("""
            SELECT
                execution_method,
                COUNT(*) as count,
                AVG(success) as success_rate,
                AVG(tokens_used) as avg_tokens,
                AVG(complexity) as avg_complexity
            FROM task_executions
            WHERE timestamp >= ?
            GROUP BY execution_method
            ORDER BY count DESC
        """, (cutoff,))
        by_method = cursor.fetchall()

        # Agent spawn analysis
        cursor.execute("""
            SELECT
                agent_type,
                COUNT(*) as count,
                AVG(success) as success_rate,
                AVG(confidence_score) as avg_confidence,
                AVG(tokens_used) as avg_tokens
            FROM task_executions
            WHERE timestamp >= ? AND execution_method = 'agent_spawn'
            GROUP BY agent_type
            ORDER BY count DESC
        """, (cutoff,))
        by_agent = cursor.fetchall()

        # Complexity analysis
        cursor.execute("""
            SELECT
                complexity,
                COUNT(*) as count,
                AVG(success) as success_rate,
                execution_method,
                AVG(tokens_used) as avg_tokens
            FROM task_executions
            WHERE timestamp >= ?
            GROUP BY complexity, execution_method
            ORDER BY complexity, count DESC
        """, (cutoff,))
        by_complexity = cursor.fetchall()

        # Steering candidates
        cursor.execute("""
            SELECT COUNT(*)
            FROM task_executions
            WHERE timestamp >= ? AND notes LIKE '%STEERING_CANDIDATE%'
        """, (cutoff,))
        steering_candidates = cursor.fetchone()[0]

        # GPT-5 usage
        cursor.execute("""
            SELECT
                COUNT(*) as gpt5_count,
                AVG(success) as gpt5_success_rate,
                AVG(tokens_used) as gpt5_avg_tokens
            FROM task_executions
            WHERE timestamp >= ? AND gpt5_used = 1
        """, (cutoff,))
        gpt5_stats = cursor.fetchone()

        conn.close()

        # Calculate agent spawn rate
        total_tasks = overall[0]
        agent_spawns = sum(m[1] for m in by_method if m[0] == 'agent_spawn')
        spawn_rate = agent_spawns / total_tasks if total_tasks > 0 else 0
        target_rate = 0.12

        # Calculate optimization opportunity
        current_spawn_cost = agent_spawns * (overall[2] or 0)  # spawns * avg tokens
        target_spawn_cost = (total_tasks * target_rate) * (overall[2] or 0)
        potential_savings = current_spawn_cost - target_spawn_cost

        return {
            'period': f'Last {days} days',
            'timestamp': datetime.now().isoformat(),
            'overall': {
                'total_tasks': total_tasks,
                'success_rate': overall[1] / total_tasks if total_tasks > 0 else 0,
                'avg_tokens_per_task': overall[2] or 0,
                'avg_duration_seconds': overall[3] or 0,
                'total_tokens_used': overall[4] or 0
            },
            'execution_methods': [{
                'method': m[0],
                'count': m[1],
                'percentage': (m[1] / total_tasks * 100) if total_tasks > 0 else 0,
                'success_rate': m[2] or 0,
                'avg_tokens': m[3] or 0,
                'avg_complexity': m[4] or 0
            } for m in by_method],
            'agent_analysis': [{
                'agent_type': a[0],
                'count': a[1],
                'success_rate': a[2] or 0,
                'avg_confidence': a[3] or 0,
                'avg_tokens': a[4] or 0
            } for a in by_agent],
            'complexity_patterns': [{
                'complexity': c[0],
                'count': c[1],
                'success_rate': c[2] or 0,
                'method': c[3],
                'avg_tokens': c[4] or 0
            } for c in by_complexity],
            'optimization': {
                'current_spawn_rate': spawn_rate,
                'target_spawn_rate': target_rate,
                'spawn_rate_difference': spawn_rate - target_rate,
                'percentage_over_target': ((spawn_rate - target_rate) / target_rate * 100) if target_rate > 0 else 0,
                'steering_candidates_identified': steering_candidates,
                'estimated_token_savings': potential_savings
            },
            'gpt5_usage': {
                'count': gpt5_stats[0] or 0,
                'success_rate': gpt5_stats[1] or 0,
                'avg_tokens': gpt5_stats[2] or 0
            }
        }

    def generate_insights(self, metrics):
        """Generate actionable insights from metrics"""
        insights = []

        # Spawn rate analysis
        spawn_diff = metrics['optimization']['spawn_rate_difference']
        if spawn_diff > 0.10:
            insights.append({
                'type': 'optimization_opportunity',
                'severity': 'high',
                'message': f"Agent spawn rate is {spawn_diff:.1%} above target. Research suggests 88% of tasks could run directly.",
                'recommendation': "Consider implementing steering prompts for medium-complexity tasks"
            })

        # Steering candidates
        candidates = metrics['optimization']['steering_candidates_identified']
        if candidates > 0:
            insights.append({
                'type': 'steering_ready',
                'severity': 'medium',
                'message': f"Found {candidates} tasks that are good candidates for steering prompts",
                'recommendation': "Begin Phase 2: Create reasoning mode library for these task types"
            })

        # Complexity patterns
        complexity_patterns = metrics.get('complexity_patterns', [])
        medium_complexity_spawns = sum(
            c['count'] for c in complexity_patterns
            if 4 <= c['complexity'] <= 6 and c['method'] == 'agent_spawn'
        )

        if medium_complexity_spawns > 5:
            insights.append({
                'type': 'pattern_identified',
                'severity': 'medium',
                'message': f"{medium_complexity_spawns} medium-complexity tasks using agents",
                'recommendation': "These tasks are prime candidates for steering prompt optimization"
            })

        # Success rate analysis
        overall_success = metrics['overall']['success_rate']
        if overall_success < 0.8:
            insights.append({
                'type': 'quality_concern',
                'severity': 'high',
                'message': f"Overall success rate is {overall_success:.1%}",
                'recommendation': "Investigate failure patterns before implementing optimization"
            })

        # Token savings potential
        savings = metrics['optimization']['estimated_token_savings']
        if savings > 10000:
            insights.append({
                'type': 'cost_opportunity',
                'severity': 'high',
                'message': f"Potential savings: /home/marc{int(savings)} tokens per week",
                'recommendation': f"Estimated cost reduction: ${savings * 0.000003:.2f}/week if optimized"
            })

        return insights

    def create_dashboard_data(self):
        """Create data for visual dashboard"""
        metrics = self.get_comprehensive_metrics(days=7)

        if 'error' in metrics:
            return metrics

        insights = self.generate_insights(metrics)

        dashboard = {
            'generated_at': datetime.now().isoformat(),
            'metrics': metrics,
            'insights': insights,
            'recommendations': self._generate_recommendations(metrics, insights)
        }

        # Save dashboard data
        dashboard_path = Path.home() / ".claude" / "latent-reasoning-dashboard.json"
        with open(dashboard_path, 'w') as f:
            json.dump(dashboard, f, indent=2)

        return dashboard

    def _generate_recommendations(self, metrics, insights):
        """Generate prioritized recommendations"""
        recommendations = []

        spawn_rate = metrics['optimization']['current_spawn_rate']
        target_rate = metrics['optimization']['target_spawn_rate']

        if spawn_rate > target_rate + 0.05:
            recommendations.append({
                'priority': 1,
                'action': 'Implement Phase 2: Reasoning Mode Library',
                'reason': f'Spawn rate {spawn_rate:.1%} is significantly above research target {target_rate:.1%}',
                'expected_impact': '20-30% reduction in agent spawning',
                'effort': 'Medium (1-2 weeks)'
            })

        # Agent-specific recommendations
        agent_analysis = metrics.get('agent_analysis', [])
        high_volume_agents = [a for a in agent_analysis if a['count'] > 5]

        for agent in high_volume_agents[:3]:  # Top 3
            recommendations.append({
                'priority': 2,
                'action': f"Create steering prompt for {agent['agent_type']}",
                'reason': f"High volume: {agent['count']} spawns in analysis period",
                'expected_impact': f"Could reduce {agent['count']} spawns to /home/marc{int(agent['count'] * 0.3)} with steering",
                'effort': 'Low (1-2 days)'
            })

        # Data collection recommendation
        if metrics['overall']['total_tasks'] < 50:
            recommendations.append({
                'priority': 0,
                'action': 'Continue baseline data collection',
                'reason': f"Only {metrics['overall']['total_tasks']} tasks logged. Need more data for reliable analysis.",
                'expected_impact': 'Better insights with 100+ tasks',
                'effort': 'Passive (1-2 weeks)'
            })

        return sorted(recommendations, key=lambda x: x['priority'])


def main():
    """Generate and display analysis"""
    analyzer = LatentReasoningAnalyzer()
    dashboard = analyzer.create_dashboard_data()

    print(json.dumps(dashboard, indent=2))


if __name__ == "__main__":
    main()
