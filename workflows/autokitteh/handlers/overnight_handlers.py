"""
Overnight Automation Orchestrator Handlers
Coordinates nightly research discovery, maintenance, and reporting
Integrates with Temporal workflow, improvement cycles, and research pipelines
"""
import json
import time
import requests
from datetime import datetime

# Import sibling handlers for coordination
try:
    from . import improvement_cycle_handlers
    from . import research_pipeline_handlers
except ImportError:
    improvement_cycle_handlers = None
    research_pipeline_handlers = None


def orchestrate_overnight_automation(event):
    """
    Orchestrate comprehensive overnight automation:
    1. Run research discovery pipeline
    2. Run improvement cycles
    3. Run memory consolidation
    4. Trigger Temporal long-running workflows
    5. Generate and send morning report
    """
    print("=" * 60)
    print(f"Starting Overnight Automation - {datetime.now()}")
    print("=" * 60)

    session_id = f"overnight-{datetime.now().strftime('%Y%m%d')}"
    results = {
        "session_id": session_id,
        "timestamp": datetime.now().isoformat(),
        "research": None,
        "improvement": None,
        "consolidation": None,
        "temporal": None,
        "success": True
    }

    # Step 1: Research Discovery
    print("\n[1/5] Running Research Discovery...")
    try:
        if research_pipeline_handlers:
            results["research"] = research_pipeline_handlers.run_research_discovery(event)
        else:
            results["research"] = run_research_fallback()
        print(f"✓ Research: {results['research'].get('papers_found', 0)} papers found")
    except Exception as e:
        print(f"⚠️ Research failed: {e}")
        results["research"] = {"status": "error", "error": str(e)}

    # Step 2: Improvement Cycle
    print("\n[2/5] Running Improvement Cycle...")
    try:
        if improvement_cycle_handlers:
            results["improvement"] = improvement_cycle_handlers.run_improvement_cycle(event)
        else:
            results["improvement"] = run_improvement_fallback()
        print(f"✓ Improvement: {results['improvement'].get('entities_created', 0)} entities created")
    except Exception as e:
        print(f"⚠️ Improvement failed: {e}")
        results["improvement"] = {"status": "error", "error": str(e)}

    # Step 3: Memory Consolidation
    print("\n[3/5] Running Memory Consolidation...")
    try:
        if improvement_cycle_handlers:
            results["consolidation"] = improvement_cycle_handlers.run_consolidation(event)
        else:
            results["consolidation"] = run_consolidation_fallback()
        print(f"✓ Consolidation complete")
    except Exception as e:
        print(f"⚠️ Consolidation failed: {e}")
        results["consolidation"] = {"status": "error", "error": str(e)}

    # Step 4: Trigger Temporal workflows for long-running tasks
    print("\n[4/5] Triggering Temporal workflows...")
    temporal_result = trigger_temporal_workflow(session_id)
    results["temporal"] = temporal_result
    if temporal_result["success"]:
        print(f"✓ Temporal workflow started: {temporal_result['workflow_id']}")
    else:
        print(f"⚠️ Temporal: {temporal_result.get('error')}")

    # Step 5: Generate and send morning report
    print("\n[5/5] Generating morning report...")
    send_morning_report(results)

    print("\n" + "=" * 60)
    print("Overnight Automation Complete")
    print("=" * 60)

    return results


def run_research_fallback():
    """Fallback research when handler not available"""
    try:
        response = requests.post(
            "http://localhost:9980/api/webhooks/research",
            json={},
            timeout=10
        )
        return {"status": "triggered", "via": "webhook"}
    except:
        return {"status": "skipped", "reason": "handler unavailable"}


def run_improvement_fallback():
    """Fallback improvement when handler not available"""
    try:
        response = requests.post(
            "http://localhost:9980/api/webhooks/improve",
            json={},
            timeout=10
        )
        return {"status": "triggered", "via": "webhook"}
    except:
        return {"status": "skipped", "reason": "handler unavailable"}


def run_consolidation_fallback():
    """Fallback consolidation when handler not available"""
    try:
        response = requests.post(
            "http://localhost:8101/consolidate",
            json={"time_window_hours": 24},
            timeout=120
        )
        return response.json() if response.status_code == 200 else {"status": "error"}
    except:
        return {"status": "skipped", "reason": "MCP unavailable"}


def send_morning_report(results):
    """Generate and send comprehensive morning report"""
    report = []
    report.append("=" * 50)
    report.append("OVERNIGHT AUTOMATION REPORT")
    report.append(f"Session: {results['session_id']}")
    report.append("=" * 50)

    # Research summary
    research = results.get("research", {})
    report.append(f"\n📚 RESEARCH DISCOVERY:")
    report.append(f"   Papers found: {research.get('papers_found', 0)}")
    report.append(f"   Insights extracted: {research.get('insights_extracted', 0)}")

    # Improvement summary
    improvement = results.get("improvement", {})
    report.append(f"\n🔧 IMPROVEMENT CYCLE:")
    report.append(f"   Entities created: {improvement.get('entities_created', 0)}")
    report.append(f"   Causal links: {improvement.get('causal_links', 0)}")

    # Consolidation summary
    consolidation = results.get("consolidation", {})
    report.append(f"\n🧠 MEMORY CONSOLIDATION:")
    report.append(f"   Patterns promoted: {consolidation.get('patterns_promoted', 0)}")

    report_text = "\n".join(report)
    print(report_text)

    # Send voice notification
    send_completion_notification(results['session_id'], results)


def trigger_temporal_workflow(session_id):
    """Trigger Temporal workflow via API"""
    try:
        # Start workflow via Temporal API
        response = requests.post(
            "http://localhost:7233/api/v1/workflows/start",
            json={
                "workflow_id": f"overnight-automation-{session_id}",
                "workflow_type": "OvernightAutomationWorkflow",
                "task_queue": "overnight-automation-queue",
                "input": {
                    "session_id": session_id,
                    "triggered_by": "autokitteh"
                }
            },
            timeout=10
        )

        if response.status_code in [200, 201]:
            return {
                "success": True,
                "workflow_id": f"overnight-automation-{session_id}"
            }
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}"
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def monitor_workflow_progress(workflow_id, max_wait_hours=9):
    """
    Monitor workflow until completion or timeout
    Max wait: 9 hours (10 PM - 7 AM)
    """
    start_time = time.time()
    max_wait_seconds = max_wait_hours * 60 * 60
    check_interval = 5 * 60  # Check every 5 minutes

    while time.time() - start_time < max_wait_seconds:
        try:
            # Query workflow status
            response = requests.get(
                f"http://localhost:7233/api/v1/workflows/{workflow_id}",
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                status = data.get("status", "unknown")

                if status in ["completed", "failed", "terminated"]:
                    return {
                        "completed": status == "completed",
                        "status": status,
                        "result": data.get("result")
                    }

            # Wait before next check
            time.sleep(check_interval)

        except Exception as e:
            print(f"Status check error: {e}")
            time.sleep(check_interval)

    # Timeout
    return {
        "completed": False,
        "status": "timeout",
        "error": "Workflow exceeded 9-hour limit"
    }


def send_completion_notification(session_id, status):
    """Send voice notification via Voice Mode MCP"""
    # Build notification message
    if status["completed"]:
        result = status.get("result", {})

        discoveries = result.get("discoveries", {})
        papers = discoveries.get("papers", 0)
        repos = discoveries.get("repos", 0)

        message = f"Good morning! Overnight automation completed successfully. "
        message += f"Discovered {papers} research papers and {repos} repositories. "

        maintenance = result.get("maintenance", {})
        if maintenance.get("issues", 0) > 0:
            message += f"Alert: {maintenance['issues']} maintenance issues detected."
    else:
        message = f"Overnight automation encountered issues. Status: {status['status']}. Please review logs."

    try:
        # Send via Voice Mode
        response = requests.post(
            "http://localhost:3000/api/voice/notify",
            json={"message": message},
            timeout=10
        )

        print(f"Voice notification sent: {message}")
        return {"success": True, "message": message}

    except Exception as e:
        print(f"Voice notification failed: {e}")
        return {"success": False, "error": str(e)}


def send_alert(alert_message):
    """Send critical alert immediately"""
    try:
        response = requests.post(
            "http://localhost:3000/api/voice/notify",
            json={
                "message": f"Critical alert: {alert_message}",
                "priority": "high"
            },
            timeout=10
        )

        print(f"Alert sent: {alert_message}")

    except Exception as e:
        print(f"Failed to send alert: {e}")
