#!/usr/bin/env python3
"""
Epistemic Flexibility Daemon
Continuous monitoring and challenge scheduling for agent belief systems

Runs as a background service to:
1. Periodically audit all agents' epistemic flexibility
2. Schedule counterfactual challenges for low-scoring agents
3. Run Probability Reversal Tasks for calibration
4. Report metrics to Prometheus

Based on Stanford CICL research and Reflection-Bench methodology.
"""

import asyncio
import logging
import signal
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add MCP server paths
sys.path.insert(0, str(Path(__file__).parent.parent / "mcp-servers" / "enhanced-memory-mcp"))
sys.path.insert(0, str(Path(__file__).parent.parent / "mcp-servers" / "enhanced-memory-mcp" / "agi"))

from epistemic_scheduler import (
    EpistemicScheduler,
    run_scheduler_cycle,
    get_system_epistemic_health
)
from counterfactual_testing import CounterfactualTester, run_flexibility_audit
from probability_reversal_task import run_quick_calibration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path.home() / ".claude" / "logs" / "epistemic-daemon.log")
    ]
)
logger = logging.getLogger("epistemic-daemon")

# Configuration
AUDIT_INTERVAL_MINUTES = 60  # Full audit every hour
CHALLENGE_CHECK_MINUTES = 15  # Check for pending challenges every 15 min
CRITICAL_THRESHOLD = 0.2  # Agents below this get immediate attention
WARNING_THRESHOLD = 0.4  # Agents below this get regular challenges
HEALTHY_THRESHOLD = 0.6  # Target for healthy epistemic flexibility

# Prometheus metrics (if available)
try:
    from prometheus_client import Gauge, Counter, start_http_server
    METRICS_ENABLED = True

    # Define metrics
    FLEXIBILITY_SCORE = Gauge(
        'epistemic_flexibility_score',
        'Current epistemic flexibility score',
        ['agent_id']
    )
    CHALLENGES_SCHEDULED = Counter(
        'epistemic_challenges_scheduled_total',
        'Total counterfactual challenges scheduled',
        ['agent_id', 'priority']
    )
    AUDIT_RUNS = Counter(
        'epistemic_audit_runs_total',
        'Total epistemic audits run'
    )
    PRT_SESSIONS = Counter(
        'prt_sessions_completed_total',
        'Probability Reversal Task sessions completed',
        ['agent_id']
    )
except ImportError:
    METRICS_ENABLED = False
    logger.warning("prometheus_client not available - metrics disabled")


class EpistemicFlexibilityDaemon:
    """Background daemon for epistemic flexibility monitoring"""

    def __init__(self):
        self.running = False
        self.scheduler = EpistemicScheduler()
        self.last_audit = None
        self.last_challenge_check = None

    async def start(self):
        """Start the daemon"""
        self.running = True
        logger.info("Epistemic Flexibility Daemon starting...")

        # Start Prometheus metrics server if available
        if METRICS_ENABLED:
            try:
                start_http_server(9710)  # Unique port for this daemon
                logger.info("Prometheus metrics available on :9710")
            except Exception as e:
                logger.warning(f"Could not start metrics server: {e}")

        # Initial audit
        await self.run_audit()

        # Main loop
        while self.running:
            try:
                await self.tick()
                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in daemon tick: {e}")
                await asyncio.sleep(60)

        logger.info("Epistemic Flexibility Daemon stopped")

    def stop(self):
        """Stop the daemon gracefully"""
        self.running = False
        logger.info("Shutdown requested...")

    async def tick(self):
        """Single daemon tick - check what needs to be done"""
        now = datetime.now()

        # Check if full audit is due
        if (self.last_audit is None or
            now - self.last_audit > timedelta(minutes=AUDIT_INTERVAL_MINUTES)):
            await self.run_audit()
            self.last_audit = now

        # Check for pending challenges
        if (self.last_challenge_check is None or
            now - self.last_challenge_check > timedelta(minutes=CHALLENGE_CHECK_MINUTES)):
            await self.process_pending_challenges()
            self.last_challenge_check = now

    async def run_audit(self):
        """Run full epistemic flexibility audit"""
        logger.info("Running epistemic flexibility audit...")

        try:
            # Run the audit
            audit_result = run_flexibility_audit()

            if METRICS_ENABLED:
                AUDIT_RUNS.inc()

                # Update per-agent metrics
                for agent_id, result in audit_result.get('per_agent_results', {}).items():
                    score = result.get('composite_flexibility_score', 0.5)
                    FLEXIBILITY_SCORE.labels(agent_id=agent_id).set(score)

            # Log summary
            cluster_avg = audit_result.get('cluster_average_flexibility', 0)
            agents_count = audit_result.get('agents_audited', 0)
            attention_needed = audit_result.get('agents_needing_attention', [])

            logger.info(
                f"Audit complete: {agents_count} agents, "
                f"cluster avg: {cluster_avg:.2f}, "
                f"{len(attention_needed)} need attention"
            )

            # Schedule challenges for low-scoring agents
            for agent_id in attention_needed:
                agent_result = audit_result['per_agent_results'].get(agent_id, {})
                score = agent_result.get('composite_flexibility_score', 0)

                if score < CRITICAL_THRESHOLD:
                    # Critical - schedule immediate PRT
                    await self.schedule_prt_session(agent_id, "critical")
                    if METRICS_ENABLED:
                        CHALLENGES_SCHEDULED.labels(
                            agent_id=agent_id, priority="critical"
                        ).inc()
                elif score < WARNING_THRESHOLD:
                    # Warning - schedule counterfactual challenge
                    await self.schedule_counterfactual(agent_id, "warning")
                    if METRICS_ENABLED:
                        CHALLENGES_SCHEDULED.labels(
                            agent_id=agent_id, priority="warning"
                        ).inc()

            return audit_result

        except Exception as e:
            logger.error(f"Audit failed: {e}")
            return None

    async def process_pending_challenges(self):
        """Process any pending scheduled challenges"""
        logger.debug("Checking for pending challenges...")

        try:
            # Run scheduler cycle (async function)
            cycle_result = await run_scheduler_cycle()

            processed = cycle_result.get('challenges_processed', 0)
            if processed > 0:
                logger.info(f"Processed {processed} pending challenges")

            return cycle_result

        except Exception as e:
            logger.error(f"Challenge processing failed: {e}")
            return None

    async def schedule_prt_session(self, agent_id: str, priority: str):
        """Schedule a Probability Reversal Task session for an agent"""
        logger.info(f"Scheduling PRT session for {agent_id} (priority: {priority})")

        try:
            # Create PRT session (returns session setup, agent completes trials separately)
            result = run_quick_calibration(agent_id)

            if METRICS_ENABLED:
                PRT_SESSIONS.labels(agent_id=agent_id).inc()

            logger.info(
                f"PRT session for {agent_id}: "
                f"status={result.get('status', 'created')}, trials={result.get('trials_created', 0)}"
            )

            return result

        except Exception as e:
            logger.error(f"PRT scheduling failed for {agent_id}: {e}")
            return None

    async def schedule_counterfactual(self, agent_id: str, priority: str):
        """Schedule a counterfactual challenge for an agent"""
        logger.info(f"Scheduling counterfactual for {agent_id} (priority: {priority})")

        try:
            from epistemic_scheduler import schedule_immediate_challenge

            result = schedule_immediate_challenge(
                agent_id=agent_id,
                challenge_type="counterfactual"
            )

            logger.info(f"Counterfactual scheduled for {agent_id}: {result.get('challenge_id')}")
            return result

        except Exception as e:
            logger.error(f"Counterfactual scheduling failed for {agent_id}: {e}")
            return None

    def get_status(self) -> dict:
        """Get daemon status"""
        health = get_system_epistemic_health()

        return {
            "running": self.running,
            "last_audit": self.last_audit.isoformat() if self.last_audit else None,
            "last_challenge_check": self.last_challenge_check.isoformat() if self.last_challenge_check else None,
            "metrics_enabled": METRICS_ENABLED,
            "system_health": health
        }


# Global daemon instance
daemon = None


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global daemon
    if daemon:
        daemon.stop()


async def main():
    """Main entry point"""
    global daemon

    # Create log directory
    log_dir = Path.home() / ".claude" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Setup signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Create and start daemon
    daemon = EpistemicFlexibilityDaemon()

    try:
        await daemon.start()
    except KeyboardInterrupt:
        daemon.stop()


if __name__ == "__main__":
    asyncio.run(main())
