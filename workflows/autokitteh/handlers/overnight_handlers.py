"""
Overnight Automation Orchestrator Handlers
Coordinates nightly research discovery, maintenance, and reporting
Integrates with Temporal workflow and KutiraAI service
"""
import json
import time
import requests
from datetime import datetime


def orchestrate_overnight_automation(event):
    """
    Orchestrate overnight automation:
    1. Trigger Temporal workflow
    2. Monitor progress
    3. Ensure completion by 7 AM
    4. Handle errors gracefully
    """
    print("=" * 60)
    print(f"Starting Overnight Automation - {datetime.now()}")
    print("=" * 60)

    session_id = f"session-{int(time.time())}"

    # Step 1: Trigger Temporal workflow
    print("\n[1/4] Triggering Temporal workflow...")
    temporal_result = trigger_temporal_workflow(session_id)

    if not temporal_result["success"]:
        print(f"⚠️ Temporal workflow failed to start: {temporal_result.get('error')}")
        send_alert("Overnight automation failed to start")
        return {"success": False, "error": "Workflow start failed"}

    print(f"✓ Temporal workflow started: {temporal_result['workflow_id']}")

    # Step 2: Monitor workflow progress
    print("\n[2/4] Monitoring workflow progress...")
    status = monitor_workflow_progress(temporal_result["workflow_id"])

    # Step 3: Verify completion
    print("\n[3/4] Verifying completion...")
    if status["completed"]:
        print("✓ Workflow completed successfully")
    else:
        print(f"⚠️ Workflow incomplete: {status.get('status')}")

    # Step 4: Send final status
    print("\n[4/4] Sending status notification...")
    send_completion_notification(session_id, status)

    print("\n" + "=" * 60)
    print("Overnight Automation Complete")
    print("=" * 60)

    return {
        "success": True,
        "session_id": session_id,
        "workflow_id": temporal_result["workflow_id"],
        "status": status
    }


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
