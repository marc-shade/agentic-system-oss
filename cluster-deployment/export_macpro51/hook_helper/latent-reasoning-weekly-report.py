#!/usr/bin/env python3
"""
Latent Reasoning Weekly Report Generator
Automated weekly analysis and recommendations
Run via cron or manually for weekly insights
"""

import json
import sys
import subprocess
from datetime import datetime
from pathlib import Path

def generate_weekly_report():
    """Generate comprehensive weekly report"""

    # Run analyzer
    analyzer_script = Path.home() / ".claude" / "hooks" / "latent-reasoning-analyzer.py"
    result = subprocess.run([sys.executable, str(analyzer_script)], capture_output=True, text=True)

    if result.returncode != 0:
        return {
            'error': 'Failed to generate report',
            'details': result.stderr
        }

    dashboard_data = json.loads(result.stdout)
    metrics = dashboard_data['metrics']
    insights = dashboard_data['insights']
    recommendations = dashboard_data['recommendations']

    # Create formatted report
    report = {
        'report_date': datetime.now().isoformat(),
        'report_type': 'weekly_latent_reasoning_analysis',
        'period': metrics['period'],
        'executive_summary': generate_executive_summary(metrics, insights),
        'key_metrics': extract_key_metrics(metrics),
        'optimization_status': metrics['optimization'],
        'top_insights': insights[:3],  # Top 3 insights
        'priority_recommendations': recommendations[:3],  # Top 3 recommendations
        'phase_2_readiness': assess_phase_2_readiness(metrics),
        'action_items': generate_action_items(metrics, insights, recommendations)
    }

    # Save report
    report_dir = Path.home() / ".claude" / "reports"
    report_dir.mkdir(exist_ok=True)

    report_file = report_dir / f"latent-reasoning-weekly-{datetime.now().strftime('%Y-W%W')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    # Also save as latest
    latest_file = report_dir / "latent-reasoning-latest.json"
    with open(latest_file, 'w') as f:
        json.dump(report, f, indent=2)

    return report

def generate_executive_summary(metrics, insights):
    """Create executive summary"""
    overall = metrics['overall']
    opt = metrics['optimization']

    summary = []

    # Overall performance
    summary.append(f"Analyzed {overall['total_tasks']} tasks with {overall['success_rate']*100:.1f}% success rate")

    # Spawn rate status
    if opt['current_spawn_rate'] > opt['target_spawn_rate']:
        diff = opt['current_spawn_rate'] - opt['target_spawn_rate']
        summary.append(f"Agent spawn rate {opt['current_spawn_rate']*100:.1f}% is {diff*100:.1f}% above research target")
        summary.append(f"Optimization opportunity: {opt['percentage_over_target']:.0f}% reduction possible")
    else:
        summary.append(f"Agent spawn rate at or below research target of {opt['target_spawn_rate']*100:.1f}%")

    # Steering candidates
    if opt['steering_candidates_identified'] > 0:
        summary.append(f"Identified {opt['steering_candidates_identified']} tasks as steering prompt candidates")

    # High severity insights
    high_severity = [i for i in insights if i['severity'] == 'high']
    if high_severity:
        summary.append(f"{len(high_severity)} high-priority optimization opportunities identified")

    return summary

def extract_key_metrics(metrics):
    """Extract most important metrics"""
    return {
        'total_tasks': metrics['overall']['total_tasks'],
        'success_rate': metrics['overall']['success_rate'],
        'current_spawn_rate': metrics['optimization']['current_spawn_rate'],
        'target_spawn_rate': metrics['optimization']['target_spawn_rate'],
        'over_target_percentage': metrics['optimization']['percentage_over_target'],
        'steering_candidates': metrics['optimization']['steering_candidates_identified'],
        'token_savings_potential': metrics['optimization']['estimated_token_savings']
    }

def assess_phase_2_readiness(metrics):
    """Determine if ready for Phase 2"""
    overall = metrics['overall']
    opt = metrics['optimization']

    # Readiness criteria
    criteria = {
        'sufficient_data': overall['total_tasks'] >= 100,
        'spawn_rate_above_target': opt['current_spawn_rate'] > opt['target_spawn_rate'] + 0.05,
        'steering_candidates_found': opt['steering_candidates_identified'] >= 5,
        'patterns_clear': len(metrics.get('agent_analysis', [])) >= 3
    }

    ready_count = sum(criteria.values())
    total_count = len(criteria)

    readiness = {
        'is_ready': ready_count >= 3,  # 3 out of 4 criteria
        'readiness_percentage': (ready_count / total_count) * 100,
        'criteria_met': criteria,
        'recommendation': ''
    }

    if readiness['is_ready']:
        readiness['recommendation'] = 'READY: Proceed to Phase 2 - Reasoning Mode Library'
    elif overall['total_tasks'] < 50:
        readiness['recommendation'] = 'WAIT: Continue collecting baseline data (need 100+ tasks)'
    elif opt['steering_candidates_identified'] < 5:
        readiness['recommendation'] = 'WAIT: Need more steering candidates identified'
    else:
        readiness['recommendation'] = 'ALMOST: Review criteria and consider starting Phase 2 soon'

    return readiness

def generate_action_items(metrics, insights, recommendations):
    """Generate prioritized action items"""
    actions = []

    # Data collection action
    if metrics['overall']['total_tasks'] < 100:
        actions.append({
            'priority': 'high',
            'action': 'Continue baseline data collection',
            'target': f"{100 - metrics['overall']['total_tasks']} more tasks needed",
            'timeline': '1-2 weeks'
        })

    # High severity insights become actions
    for insight in insights:
        if insight['severity'] == 'high':
            actions.append({
                'priority': 'high',
                'action': insight['recommendation'],
                'reason': insight['message'],
                'timeline': 'immediate'
            })

    # Top recommendation becomes action
    if recommendations:
        top_rec = recommendations[0]
        actions.append({
            'priority': 'medium',
            'action': top_rec['action'],
            'reason': top_rec['reason'],
            'timeline': top_rec['effort']
        })

    return actions

def send_to_enhanced_memory(report):
    """Send weekly report to enhanced-memory"""
    try:
        # Create memory entity for this week
        entity = {
            "name": f"latent-reasoning-weekly-report-{datetime.now().strftime('%Y-W%W')}",
            "entityType": "weekly_report",
            "observations": [
                f"period:{report['period']}",
                f"total_tasks:{report['key_metrics']['total_tasks']}",
                f"success_rate:{report['key_metrics']['success_rate']:.2f}",
                f"spawn_rate:{report['key_metrics']['current_spawn_rate']:.2f}",
                f"over_target:{report['key_metrics']['over_target_percentage']:.0f}%",
                f"steering_candidates:{report['key_metrics']['steering_candidates']}",
                f"phase2_ready:{report['phase_2_readiness']['is_ready']}",
                f"timestamp:{report['report_date']}"
            ]
        }

        print(json.dumps({"memory_entity": entity}, indent=2))
        return entity

    except Exception as e:
        return None

def main():
    """Generate and display report"""
    print("\n" + "=" * 70)
    print("  LATENT REASONING - WEEKLY REPORT")
    print("  " + datetime.now().strftime("%Y Week %W"))
    print("=" * 70 + "\n")

    report = generate_weekly_report()

    if 'error' in report:
        print(f"ERROR: {report['error']}")
        if 'details' in report:
            print(f"Details: {report['details']}")
        return

    # Display executive summary
    print("EXECUTIVE SUMMARY")
    print("-" * 70)
    for item in report['executive_summary']:
        print(f"  • {item}")
    print()

    # Display key metrics
    print("KEY METRICS")
    print("-" * 70)
    km = report['key_metrics']
    print(f"  Total Tasks: {km['total_tasks']}")
    print(f"  Success Rate: {km['success_rate']*100:.1f}%")
    print(f"  Current Spawn Rate: {km['current_spawn_rate']*100:.1f}%")
    print(f"  Target Spawn Rate: {km['target_spawn_rate']*100:.1f}%")
    print(f"  Over Target: {km['over_target_percentage']:.0f}%")
    print(f"  Steering Candidates: {km['steering_candidates']}")
    print()

    # Display Phase 2 readiness
    print("PHASE 2 READINESS")
    print("-" * 70)
    p2 = report['phase_2_readiness']
    print(f"  Status: {'✓ READY' if p2['is_ready'] else '○ NOT READY'} ({p2['readiness_percentage']:.0f}%)")
    print(f"  Recommendation: {p2['recommendation']}")
    print("\n  Criteria:")
    for criterion, met in p2['criteria_met'].items():
        status = "✓" if met else "○"
        print(f"    {status} {criterion.replace('_', ' ').title()}")
    print()

    # Display top insights
    if report['top_insights']:
        print("TOP INSIGHTS")
        print("-" * 70)
        for insight in report['top_insights']:
            print(f"  {insight['severity'].upper()}: {insight['message']}")
            print(f"    → {insight['recommendation']}")
            print()

    # Display action items
    if report['action_items']:
        print("ACTION ITEMS")
        print("-" * 70)
        for i, action in enumerate(report['action_items'], 1):
            print(f"  {i}. [{action['priority'].upper()}] {action['action']}")
            if 'reason' in action:
                print(f"     Reason: {action['reason']}")
            if 'target' in action:
                print(f"     Target: {action['target']}")
            print(f"     Timeline: {action['timeline']}")
            print()

    print("=" * 70)
    print(f"  Report saved to: /home/marc/.claude/reports/latent-reasoning-latest.json")
    print("=" * 70 + "\n")

    # Send to enhanced-memory
    send_to_enhanced_memory(report)

if __name__ == "__main__":
    main()
