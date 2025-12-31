#!/usr/bin/env python3
"""
SysAdmin Auto-Recovery Workflow
Handles automatic service recovery with exponential backoff

Features:
- Processes recovery requests from watchdog
- Exponential backoff (30s, 60s, 120s, 240s)
- Service-specific recovery commands
- Notifies after 3 failed attempts
- Never blocks development work

STATUS: Production Ready
"""

import asyncio
import logging
import json
import os
import subprocess
from datetime import timedelta, datetime
from dataclasses import dataclass
from typing import Optional, Dict, List
from temporalio import workflow, activity
from temporalio.common import RetryPolicy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Recovery commands matching watchdog service names exactly
RECOVERY_COMMANDS = {
    # 1. KutiraAI Backend Services
    "frontend_dashboard": {
        "check": "curl -s http://localhost:3100/ > /dev/null",
        "start": "cd /Volumes/FILES/code/kutiraai/kutiraai-frontend && nohup python3 -m http.server 3100 > /tmp/kutiraai-frontend.log 2>&1 &",
        "stop": "pkill -f 'http.server 3100'",
    },
    "agentic_framework": {
        "check": "pm2 show agent-registry | grep -q online",
        "start": "pm2 start agent-registry",
        "stop": "pm2 stop agent-registry",
        "pm2": True,
    },
    "api_server": {
        "check": "pgrep -f api-server-real.js",
        "start": "cd /Volumes/FILES/code/kutiraai && nohup node api-server-real.js > /tmp/kutiraai-api.log 2>&1 &",
        "stop": "pkill -f api-server-real.js",
    },
    "port_manager": {
        "check": "pm2 show port-manager | grep -q online",
        "start": "pm2 start port-manager",
        "stop": "pm2 stop port-manager",
        "pm2": True,
    },
    "n8n_workflows": {
        "check": "pgrep -f 'n8n'",
        "start": "nohup n8n start > /tmp/n8n.log 2>&1 &",
        "stop": "pkill -f 'n8n'",
    },
    "autokitteh": {
        "check": "pgrep -f 'ak up'",
        "start": "cd /Volumes/SSDRAID0/agentic-system && nohup ak up --mode dev > /tmp/autokitteh.log 2>&1 &",
        "stop": "pkill -f 'ak up'",
    },

    # 2. Voice Mode Services
    "whisper_stt": {
        "check": "pgrep -f whisper-server",
        "start": "/Users/marc/.voicemode/services/whisper/start.sh",
        "stop": "pkill -f whisper-server",
    },
    "kokoro_tts": {
        "check": "pgrep -f 'uvicorn.*8880'",
        "start": "/Users/marc/.voicemode/services/kokoro/start-gpu_mac.sh",
        "stop": "pkill -f 'uvicorn.*8880'",
    },
    "voice_broker_main": {
        "check": "curl -s http://localhost:9091/health > /dev/null",
        "start": "cd /Users/marc/.voicemode && ./start-voice-broker.sh",
        "stop": "pkill -f voice-broker",
    },
    "voice_broker_admin": {
        "check": "curl -s http://localhost:9092/health > /dev/null",
        "start": "cd /Users/marc/.voicemode && ./start-voice-broker.sh",
        "stop": "pkill -f voice-broker",
    },
    "voice_cache": {
        "check": "curl -s http://localhost:9093/health > /dev/null",
        "start": "cd /Users/marc/.voicemode && ./start-voice-broker.sh",
        "stop": "pkill -f voice-broker",
    },
    "voice_feedback": {
        "check": "curl -s http://localhost:9050/health > /dev/null",
        "start": "cd /Users/marc/.voicemode && ./start-voice-broker.sh",
        "stop": "pkill -f voice-broker",
    },
    "livekit_server": {
        "check": "pgrep -f livekit-server",
        "start": "/Users/marc/.voicemode/services/livekit/start.sh",
        "stop": "pkill -f livekit-server",
    },

    # 3. Core Workflow Services
    "temporal": {
        "check": "pgrep -f 'temporal server'",
        "start": "cd /Volumes/SSDRAID0/agentic-system && nohup temporal server start-dev --namespace default --db-filename databases/temporal/temporal.db --ui-port 8233 > /tmp/temporal.log 2>&1 &",
        "stop": "pkill -f 'temporal server'",
    },

    # 4. Ember System
    "ember_mcp": {
        "check": "pgrep -f ember-mcp",
        "start": None,  # Started by Claude Code automatically
        "stop": None,
        "notify_only": True,
    },

    # 5. Core MCP Servers (most are started by Claude Code)
    "enhanced_memory": {
        "check": "pgrep -f enhanced-memory",
        "start": None,  # Started by Claude Code
        "stop": None,
        "notify_only": True,
    },
    "agent_runtime": {
        "check": "pgrep -f agent-runtime-mcp",
        "start": None,  # Started by Claude Code
        "stop": None,
        "notify_only": True,
    },
    "sequential_thinking": {
        "check": "pgrep -f sequential-thinking",
        "start": None,  # On-demand MCP
        "stop": None,
        "notify_only": True,
    },
    "voice_mode": {
        "check": "pgrep -f voicemode",
        "start": None,  # Started by Claude Code
        "stop": None,
        "notify_only": True,
    },
    "chrome_devtools": {
        "check": "pgrep -f chrome-devtools",
        "start": None,  # On-demand MCP
        "stop": None,
        "notify_only": True,
    },

    # 6. Database Services
    "postgresql": {
        "check": "pg_isready -h localhost -p 5432",
        "start": "brew services start postgresql@16",
        "stop": "brew services stop postgresql@16",
    },

    # 7. Hardware
    "arduino_surface": {
        "check": "curl -s http://macpro51:8200/status > /dev/null",
        "start": None,  # Cannot auto-start remote hardware
        "stop": None,
        "notify_only": True,
    },

    # Legacy PM2 services (not in verification but should be maintained)
    "mcp_orchestrator": {
        "check": "pm2 show mcp-orchestrator | grep -q online",
        "start": "pm2 start mcp-orchestrator",
        "stop": "pm2 stop mcp-orchestrator",
        "pm2": True,
    },
    "workflow_engine": {
        "check": "pm2 show workflow-engine | grep -q online",
        "start": "pm2 start workflow-engine",
        "stop": "pm2 stop workflow-engine",
        "pm2": True,
    },
    "system_monitor": {
        "check": "pm2 show system-monitor | grep -q online",
        "start": "pm2 start system-monitor",
        "stop": "pm2 stop system-monitor",
        "pm2": True,
    },
}

RECOVERY_QUEUE_FILE = "/tmp/sysadmin_recovery_queue.json"
RECOVERY_STATE_FILE = "/tmp/sysadmin_recovery_state.json"


@dataclass
class RecoveryAttempt:
    service: str
    attempt_number: int
    success: bool
    error: Optional[str] = None
    timestamp: Optional[str] = None


@activity.defn
async def get_pending_recoveries() -> List[dict]:
    """Get list of services needing recovery"""
    try:
        if os.path.exists(RECOVERY_QUEUE_FILE):
            with open(RECOVERY_QUEUE_FILE, 'r') as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"Failed to read recovery queue: {e}")
        return []


@activity.defn
async def clear_recovery_request(service_name: str) -> bool:
    """Remove a service from recovery queue"""
    try:
        if os.path.exists(RECOVERY_QUEUE_FILE):
            with open(RECOVERY_QUEUE_FILE, 'r') as f:
                requests = json.load(f)

            requests = [r for r in requests if r.get('service') != service_name]

            with open(RECOVERY_QUEUE_FILE, 'w') as f:
                json.dump(requests, f)

        return True
    except Exception as e:
        logger.error(f"Failed to clear recovery request: {e}")
        return False


@activity.defn
async def get_recovery_state(service_name: str) -> dict:
    """Get current recovery state for a service"""
    try:
        state = {}
        if os.path.exists(RECOVERY_STATE_FILE):
            with open(RECOVERY_STATE_FILE, 'r') as f:
                state = json.load(f)

        return state.get(service_name, {
            "attempts": 0,
            "last_attempt": None,
            "backoff_seconds": 30
        })
    except Exception as e:
        logger.error(f"Failed to read recovery state: {e}")
        return {"attempts": 0, "last_attempt": None, "backoff_seconds": 30}


@activity.defn
async def update_recovery_state(service_name: str, attempts: int, success: bool) -> bool:
    """Update recovery state for a service"""
    try:
        state = {}
        if os.path.exists(RECOVERY_STATE_FILE):
            with open(RECOVERY_STATE_FILE, 'r') as f:
                state = json.load(f)

        if success:
            # Clear state on success
            if service_name in state:
                del state[service_name]
        else:
            # Update with exponential backoff
            backoff = min(30 * (2 ** attempts), 240)  # Max 4 minutes
            state[service_name] = {
                "attempts": attempts,
                "last_attempt": datetime.utcnow().isoformat(),
                "backoff_seconds": backoff
            }

        with open(RECOVERY_STATE_FILE, 'w') as f:
            json.dump(state, f)

        return True
    except Exception as e:
        logger.error(f"Failed to update recovery state: {e}")
        return False


@activity.defn
async def attempt_service_recovery(service_name: str) -> RecoveryAttempt:
    """Attempt to recover a service"""
    commands = RECOVERY_COMMANDS.get(service_name)

    if not commands:
        return RecoveryAttempt(
            service=service_name,
            attempt_number=0,
            success=False,
            error=f"No recovery commands defined for {service_name}",
            timestamp=datetime.utcnow().isoformat()
        )

    # Handle notify-only services (like hardware that can't be auto-recovered)
    if commands.get("notify_only"):
        return RecoveryAttempt(
            service=service_name,
            attempt_number=1,
            success=False,
            error=f"Service {service_name} requires manual intervention (notify-only)",
            timestamp=datetime.utcnow().isoformat()
        )

    try:
        # First check if service is actually down
        check_result = subprocess.run(
            commands["check"],
            shell=True,
            capture_output=True,
            timeout=10
        )

        if check_result.returncode == 0:
            # Service is actually running
            return RecoveryAttempt(
                service=service_name,
                attempt_number=0,
                success=True,
                error=None,
                timestamp=datetime.utcnow().isoformat()
            )

        # Try to stop first (clean slate)
        if "stop" in commands:
            try:
                subprocess.run(
                    commands["stop"],
                    shell=True,
                    capture_output=True,
                    timeout=10
                )
                await asyncio.sleep(2)  # Wait for clean shutdown
            except:
                pass

        # Start the service
        logger.info(f"[Recovery] Starting {service_name}...")
        start_result = subprocess.run(
            commands["start"],
            shell=True,
            capture_output=True,
            timeout=30
        )

        # Wait for service to come up
        await asyncio.sleep(5)

        # Verify it started
        verify_result = subprocess.run(
            commands["check"],
            shell=True,
            capture_output=True,
            timeout=10
        )

        success = verify_result.returncode == 0

        return RecoveryAttempt(
            service=service_name,
            attempt_number=1,
            success=success,
            error=None if success else f"Service failed to start: {start_result.stderr.decode()[:200]}",
            timestamp=datetime.utcnow().isoformat()
        )

    except Exception as e:
        return RecoveryAttempt(
            service=service_name,
            attempt_number=1,
            success=False,
            error=str(e)[:200],
            timestamp=datetime.utcnow().isoformat()
        )


@activity.defn
async def send_recovery_notification(service_name: str, success: bool, attempts: int, error: Optional[str] = None) -> bool:
    """Send notification about recovery status"""
    try:
        if success:
            message = f"Service {service_name} recovered successfully after {attempts} attempt(s)."
            level = "info"
        elif attempts >= 3:
            message = f"ALERT: Service {service_name} failed to recover after {attempts} attempts. Manual intervention required. Error: {error}"
            level = "error"
        else:
            message = f"Recovery attempt {attempts} for {service_name} failed. Will retry. Error: {error}"
            level = "warning"

        logger.log(getattr(logging, level.upper()), f"[Recovery] {message}")

        # For critical failures, try voice notification
        if attempts >= 3 and not success:
            try:
                import aiohttp
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(
                        "http://localhost:8880/synthesize",
                        json={"text": f"Attention: {service_name} service requires manual intervention.", "voice": "default"}
                    ) as response:
                        pass
            except:
                pass

        return True
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        return False


@workflow.defn
class SysAdminAutoRecoveryWorkflow:
    """
    Auto-recovery workflow that handles service failures.
    Runs continuously, processing recovery requests from watchdog.
    Uses exponential backoff to avoid hammering failing services.
    """

    def __init__(self):
        self.running = True
        self.recovery_stats: Dict[str, dict] = {}

    @workflow.run
    async def run(self, poll_interval_seconds: int = 15) -> str:
        """Main recovery loop"""

        while self.running:
            # Get pending recovery requests
            pending = await workflow.execute_activity(
                get_pending_recoveries,
                start_to_close_timeout=timedelta(seconds=10)
            )

            for request in pending:
                service_name = request.get("service")
                if not service_name:
                    continue

                # Get current recovery state
                state = await workflow.execute_activity(
                    get_recovery_state,
                    args=[service_name],
                    start_to_close_timeout=timedelta(seconds=5)
                )

                attempts = state.get("attempts", 0)
                backoff = state.get("backoff_seconds", 30)
                last_attempt = state.get("last_attempt")

                # Check if we should skip this service (backoff period)
                if last_attempt and attempts > 0:
                    try:
                        last_time = datetime.fromisoformat(last_attempt)
                        elapsed = (datetime.utcnow() - last_time).total_seconds()
                        if elapsed < backoff:
                            continue  # Still in backoff period
                    except:
                        pass

                # Stop trying after 5 attempts
                if attempts >= 5:
                    # Clear from queue, notify, and give up
                    await workflow.execute_activity(
                        clear_recovery_request,
                        args=[service_name],
                        start_to_close_timeout=timedelta(seconds=5)
                    )
                    await workflow.execute_activity(
                        send_recovery_notification,
                        args=[service_name, False, attempts, "Max attempts reached"],
                        start_to_close_timeout=timedelta(seconds=10)
                    )
                    continue

                # Attempt recovery
                result = await workflow.execute_activity(
                    attempt_service_recovery,
                    args=[service_name],
                    start_to_close_timeout=timedelta(seconds=60),
                    retry_policy=RetryPolicy(maximum_attempts=1)
                )

                new_attempts = attempts + 1

                # Update state
                await workflow.execute_activity(
                    update_recovery_state,
                    args=[service_name, new_attempts, result.success],
                    start_to_close_timeout=timedelta(seconds=5)
                )

                if result.success:
                    # Clear from queue and notify
                    await workflow.execute_activity(
                        clear_recovery_request,
                        args=[service_name],
                        start_to_close_timeout=timedelta(seconds=5)
                    )
                    await workflow.execute_activity(
                        send_recovery_notification,
                        args=[service_name, True, new_attempts, None],
                        start_to_close_timeout=timedelta(seconds=10)
                    )
                else:
                    # Notify about failure (especially after 3 attempts)
                    if new_attempts >= 3:
                        await workflow.execute_activity(
                            send_recovery_notification,
                            args=[service_name, False, new_attempts, result.error],
                            start_to_close_timeout=timedelta(seconds=10)
                        )

                # Track stats
                self.recovery_stats[service_name] = {
                    "last_attempt": result.timestamp,
                    "attempts": new_attempts,
                    "last_success": result.success
                }

            # Wait before next poll
            await asyncio.sleep(poll_interval_seconds)

        return "Auto-recovery stopped"

    @workflow.signal
    async def stop(self):
        """Signal to stop the workflow"""
        self.running = False

    @workflow.signal
    async def force_recovery(self, service_name: str):
        """Signal to force immediate recovery attempt"""
        # Reset state and add to queue
        await workflow.execute_activity(
            update_recovery_state,
            args=[service_name, 0, False],
            start_to_close_timeout=timedelta(seconds=5)
        )

    @workflow.query
    def get_stats(self) -> dict:
        """Query for recovery statistics"""
        return self.recovery_stats


# Activities list for worker registration
recovery_activities = [
    get_pending_recoveries,
    clear_recovery_request,
    get_recovery_state,
    update_recovery_state,
    attempt_service_recovery,
    send_recovery_notification,
]
