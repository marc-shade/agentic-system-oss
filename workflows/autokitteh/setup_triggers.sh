#!/bin/bash
# AutoKitteh Triggers Setup Script
# Creates all necessary triggers for the autonomous_system project workflows
#
# Usage: ./setup_triggers.sh

set -e

AK="/Volumes/FILES/Marc-Data/Documents/Cline/MCP/autokitteh-source/bin/ak"
PROJECT="autonomous_system"

echo "========================================="
echo "AutoKitteh Triggers Setup"
echo "Project: $PROJECT"
echo "========================================="
echo ""

# AGI Workflows

echo "Creating AGI workflow triggers..."

# autonomous_goals.kitteh - detect_goals every 6 hours
echo "  ✓ Creating: detect_goals (every 6 hours)"
$AK trigger create \
  --name "detect_goals_6h" \
  --project "$PROJECT" \
  --schedule "0 */6 * * *" \
  --call "agi/autonomous_goals.kitteh:detect_goals" || echo "    Already exists or failed"

# memory_consolidation.kitteh - 3 triggers
echo "  ✓ Creating: consolidate_memories (daily 2 AM)"
$AK trigger create \
  --name "consolidate_memories_2am" \
  --project "$PROJECT" \
  --schedule "0 2 * * *" \
  --call "agi/memory_consolidation.kitteh:consolidate_memories" || echo "    Already exists or failed"

echo "  ✓ Creating: check_memory_health (every 6 hours)"
$AK trigger create \
  --name "memory_health_6h" \
  --project "$PROJECT" \
  --schedule "0 */6 * * *" \
  --call "agi/memory_consolidation.kitteh:check_memory_health" || echo "    Already exists or failed"

echo "  ✓ Creating: emergency_memory_backup (daily 3 AM)"
$AK trigger create \
  --name "memory_backup_3am" \
  --project "$PROJECT" \
  --schedule "0 3 * * *" \
  --call "agi/memory_consolidation.kitteh:emergency_memory_backup" || echo "    Already exists or failed"

echo ""

# Claude Performance Monitor

echo "Creating Claude performance monitoring triggers..."

echo "  ✓ Creating: monitor_claude_execution (every 15 minutes)"
$AK trigger create \
  --name "claude_monitor_15m" \
  --project "$PROJECT" \
  --schedule "*/15 * * * *" \
  --call "claude/claude_performance_monitor.kitteh:monitor_claude_execution" || echo "    Already exists or failed"

echo "  ✓ Creating: analyze_patterns (every hour)"
$AK trigger create \
  --name "claude_analyze_1h" \
  --project "$PROJECT" \
  --schedule "0 * * * *" \
  --call "claude/claude_performance_monitor.kitteh:analyze_patterns" || echo "    Already exists or failed"

echo "  ✓ Creating: deep_learning (every 6 hours)"
$AK trigger create \
  --name "claude_deeplearn_6h" \
  --project "$PROJECT" \
  --schedule "0 */6 * * *" \
  --call "claude/claude_performance_monitor.kitteh:deep_learning" || echo "    Already exists or failed"

echo ""

# System Workflows

echo "Creating system workflow triggers..."

echo "  ✓ Creating: overnight_automation (daily 10 PM)"
$AK trigger create \
  --name "overnight_automation_10pm" \
  --project "$PROJECT" \
  --schedule "0 22 * * *" \
  --call "system/overnight_automation.kitteh:orchestrate_overnight_automation" || echo "    Already exists or failed"

echo "  ✓ Creating: self_healing check (every 5 minutes)"
$AK trigger create \
  --name "self_healing_5m" \
  --project "$PROJECT" \
  --schedule "*/5 * * * *" \
  --call "system/self_healing.kitteh:check_config_integrity" || echo "    Already exists or failed"

echo "  ✓ Creating: self_healing webhook"
$AK trigger create \
  --name "self_healing_webhook" \
  --project "$PROJECT" \
  --webhook \
  --call "system/self_healing.kitteh:check_config_integrity" || echo "    Already exists or failed"

echo ""

# YouTube Workflows

echo "Creating YouTube workflow triggers..."

echo "  ✓ Creating: video_summary_report (weekly Monday 10 AM)"
$AK trigger create \
  --name "youtube_summary_weekly" \
  --project "$PROJECT" \
  --schedule "0 10 * * 1" \
  --call "youtube/video_analysis.kitteh:generate_video_summary_report" || echo "    Already exists or failed"

echo "  ✓ Creating: detect_trending_topics (daily 8 PM)"
$AK trigger create \
  --name "youtube_trending_8pm" \
  --project "$PROJECT" \
  --schedule "0 20 * * *" \
  --call "youtube/video_analysis.kitteh:detect_trending_topics" || echo "    Already exists or failed"

echo ""

# Additional TBD Workflows

echo "Creating Ember monitoring triggers..."

echo "  ✓ Creating: check_ember_status (every 2 minutes)"
$AK trigger create \
  --name "ember_check_2m" \
  --project "$PROJECT" \
  --schedule "*/2 * * * *" \
  --call "system/ember_monitoring.kitteh:check_ember_status" || echo "    Already exists or failed"

echo ""

echo "Creating service health monitoring triggers..."

echo "  ✓ Creating: check_all_services (every 1 minute)"
$AK trigger create \
  --name "service_health_1m" \
  --project "$PROJECT" \
  --schedule "* * * * *" \
  --call "system/service_health_monitor.kitteh:check_all_services" || echo "    Already exists or failed"

echo "  ✓ Creating: generate_health_report (every 6 hours)"
$AK trigger create \
  --name "health_report_6h" \
  --project "$PROJECT" \
  --schedule "0 */6 * * *" \
  --call "system/service_health_monitor.kitteh:generate_health_report" || echo "    Already exists or failed"

echo ""

echo "Creating cache management triggers..."

echo "  ✓ Creating: monitor_cache_size (daily 11 PM)"
$AK trigger create \
  --name "cache_monitor_11pm" \
  --project "$PROJECT" \
  --schedule "0 23 * * *" \
  --call "youtube/cache_management.kitteh:monitor_cache_size" || echo "    Already exists or failed"

echo "  ✓ Creating: optimize_cache (monthly 1st at 5 AM)"
$AK trigger create \
  --name "cache_optimize_monthly" \
  --project "$PROJECT" \
  --schedule "0 5 1 * *" \
  --call "youtube/cache_management.kitteh:optimize_cache" || echo "    Already exists or failed"

echo "  ✓ Creating: rebuild_cache_index (weekly Tuesday 3 AM)"
$AK trigger create \
  --name "cache_index_tuesday" \
  --project "$PROJECT" \
  --schedule "0 3 * * 2" \
  --call "youtube/cache_management.kitteh:rebuild_cache_index" || echo "    Already exists or failed"

echo "  ✓ Creating: verify_cache_integrity (weekly Wednesday 2 AM)"
$AK trigger create \
  --name "cache_verify_wednesday" \
  --project "$PROJECT" \
  --schedule "0 2 * * 3" \
  --call "youtube/cache_management.kitteh:verify_cache_integrity" || echo "    Already exists or failed"

echo ""

echo "Creating metrics dashboard triggers..."

echo "  ✓ Creating: generate_daily_metrics (daily 9 AM)"
$AK trigger create \
  --name "metrics_daily_9am" \
  --project "$PROJECT" \
  --schedule "0 9 * * *" \
  --call "agi/metrics_dashboard.kitteh:generate_daily_metrics" || echo "    Already exists or failed"

echo "  ✓ Creating: generate_weekly_summary (Sunday 6 PM)"
$AK trigger create \
  --name "metrics_weekly_sunday" \
  --project "$PROJECT" \
  --schedule "0 18 * * 0" \
  --call "agi/metrics_dashboard.kitteh:generate_weekly_summary" || echo "    Already exists or failed"

echo "  ✓ Creating: alert_on_performance_degradation (every 2 hours)"
$AK trigger create \
  --name "metrics_perf_2h" \
  --project "$PROJECT" \
  --schedule "0 */2 * * *" \
  --call "agi/metrics_dashboard.kitteh:alert_on_performance_degradation" || echo "    Already exists or failed"

echo ""
echo "========================================="
echo "Triggers setup complete!"
echo "========================================="
echo ""
echo "Verify triggers with:"
echo "  $AK trigger list --project $PROJECT"
echo ""
echo "Check sessions with:"
echo "  $AK session list --project $PROJECT"
echo ""
echo "View logs:"
echo "  tail -f /Volumes/SSDRAID0/agentic-system/logs/autokitteh.log"
echo ""
