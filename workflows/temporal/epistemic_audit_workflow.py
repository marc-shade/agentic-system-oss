"""
Epistemic Audit Temporal Workflow
Scheduled epistemic flexibility audits with cluster-wide coordination

Based on Stanford CICL research and Reflection-Bench methodology.
"""

import asyncio
import logging
import sys
from datetime import timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

from temporalio import workflow, activity
from temporalio.common import RetryPolicy

# Add MCP paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers" / "enhanced-memory-mcp"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers" / "enhanced-memory-mcp" / "agi"))

logger = logging.getLogger(__name__)


# ============================================================================
# Activities
# ============================================================================

@activity.defn
async def run_flexibility_audit_activity(agent_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """Run epistemic flexibility audit on agents"""
    from counterfactual_testing import run_flexibility_audit

    try:
        result = run_flexibility_audit(agent_ids)
        logger.info(f"Audit complete: {result.get('agents_audited', 0)} agents")
        return result
    except Exception as e:
        logger.error(f"Audit failed: {e}")
        raise


@activity.defn
async def run_prt_session_activity(
    agent_id: str,
    num_trials: int = 10
) -> Dict[str, Any]:
    """Run Probability Reversal Task session"""
    from probability_reversal_task import run_quick_calibration

    try:
        result = run_quick_calibration(agent_id, num_trials)
        logger.info(
            f"PRT session for {agent_id}: "
            f"flexibility={result.get('summary', {}).get('overall_flexibility', 0):.2f}"
        )
        return result
    except Exception as e:
        logger.error(f"PRT session failed for {agent_id}: {e}")
        raise


@activity.defn
async def schedule_counterfactual_activity(
    agent_id: str,
    challenge_type: str = "counterfactual"
) -> Dict[str, Any]:
    """Schedule counterfactual challenge for agent"""
    from epistemic_scheduler import schedule_immediate_challenge

    try:
        result = schedule_immediate_challenge(agent_id, challenge_type)
        logger.info(f"Scheduled challenge for {agent_id}: {result.get('challenge_id')}")
        return result
    except Exception as e:
        logger.error(f"Challenge scheduling failed for {agent_id}: {e}")
        raise


@activity.defn
async def get_system_health_activity() -> Dict[str, Any]:
    """Get system epistemic health status"""
    from epistemic_scheduler import get_system_epistemic_health

    try:
        return get_system_epistemic_health()
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise


@activity.defn
async def record_audit_metrics_activity(audit_result: Dict[str, Any]) -> None:
    """Record audit metrics to monitoring system"""
    try:
        # Store in enhanced memory for tracking
        from cluster_brain import get_cluster_brain
        brain = get_cluster_brain()

        # Add as learning for cluster
        brain.add_learning(
            learning=f"Epistemic audit: cluster avg {audit_result.get('cluster_average_flexibility', 0):.2f}",
            category="epistemic_flexibility",
            source_task="epistemic_audit_workflow"
        )

        logger.info("Audit metrics recorded")
    except Exception as e:
        logger.warning(f"Could not record metrics: {e}")


# ============================================================================
# Workflows
# ============================================================================

@workflow.defn
class EpistemicAuditWorkflow:
    """
    Scheduled workflow for epistemic flexibility audits

    Can be triggered:
    - On schedule (hourly, daily)
    - On demand via CLI
    - When low scores detected by daemon
    """

    @workflow.run
    async def run(
        self,
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Run epistemic audit workflow

        Args:
            params: Optional parameters
                - agent_ids: Specific agents to audit (None = all)
                - include_prt: Run PRT sessions for low-scoring agents
                - challenge_critical: Schedule challenges for critical agents
        """
        params = params or {}
        agent_ids = params.get("agent_ids")
        include_prt = params.get("include_prt", True)
        challenge_critical = params.get("challenge_critical", True)

        workflow.logger.info("Starting epistemic audit workflow")

        # Step 1: Run flexibility audit
        audit_result = await workflow.execute_activity(
            run_flexibility_audit_activity,
            args=[agent_ids],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=3)
        )

        # Step 2: Process low-scoring agents
        attention_agents = audit_result.get("agents_needing_attention", [])
        per_agent = audit_result.get("per_agent_results", {})

        prt_results = {}
        challenge_results = {}

        for agent_id in attention_agents:
            score = per_agent.get(agent_id, {}).get("composite_flexibility_score", 0)

            # Critical agents (< 0.2) get PRT if enabled
            if score < 0.2 and include_prt:
                workflow.logger.info(f"Running PRT for critical agent {agent_id}")
                prt_result = await workflow.execute_activity(
                    run_prt_session_activity,
                    args=[agent_id, 10],
                    start_to_close_timeout=timedelta(minutes=10),
                    retry_policy=RetryPolicy(maximum_attempts=2)
                )
                prt_results[agent_id] = prt_result

            # Warning agents (0.2 - 0.4) get counterfactual challenges
            elif score < 0.4 and challenge_critical:
                workflow.logger.info(f"Scheduling challenge for agent {agent_id}")
                challenge_result = await workflow.execute_activity(
                    schedule_counterfactual_activity,
                    args=[agent_id, "counterfactual"],
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=RetryPolicy(maximum_attempts=2)
                )
                challenge_results[agent_id] = challenge_result

        # Step 3: Record metrics
        await workflow.execute_activity(
            record_audit_metrics_activity,
            args=[audit_result],
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=RetryPolicy(maximum_attempts=2)
        )

        # Build result
        result = {
            "workflow_id": workflow.info().workflow_id,
            "audit_result": audit_result,
            "prt_sessions": prt_results,
            "challenges_scheduled": challenge_results,
            "summary": {
                "agents_audited": audit_result.get("agents_audited", 0),
                "cluster_average": audit_result.get("cluster_average_flexibility", 0),
                "attention_needed": len(attention_agents),
                "prt_run": len(prt_results),
                "challenges_scheduled": len(challenge_results)
            }
        }

        workflow.logger.info(
            f"Audit complete: {result['summary']['agents_audited']} agents, "
            f"cluster avg: {result['summary']['cluster_average']:.2f}"
        )

        return result


@workflow.defn
class ContinuousEpistemicMonitoringWorkflow:
    """
    Long-running workflow for continuous epistemic monitoring

    Uses Temporal's continue-as-new for infinite duration.
    """

    @workflow.run
    async def run(
        self,
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Run continuous monitoring cycle

        Runs audit, waits for interval, then continues as new workflow.
        """
        params = params or {}
        interval_hours = params.get("interval_hours", 1)
        max_iterations = params.get("max_iterations", 24)  # Restart daily

        iteration = params.get("_iteration", 0)

        workflow.logger.info(f"Continuous monitoring iteration {iteration}")

        # Run audit
        audit_result = await workflow.execute_activity(
            run_flexibility_audit_activity,
            args=[None],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=3)
        )

        # Check health and respond
        health = await workflow.execute_activity(
            get_system_health_activity,
            start_to_close_timeout=timedelta(minutes=1)
        )

        # If system unhealthy, run interventions
        if health.get("status") != "healthy":
            attention_agents = audit_result.get("agents_needing_attention", [])
            for agent_id in attention_agents[:3]:  # Limit to 3 per cycle
                await workflow.execute_activity(
                    schedule_counterfactual_activity,
                    args=[agent_id],
                    start_to_close_timeout=timedelta(minutes=2)
                )

        # Wait for next iteration
        await asyncio.sleep(interval_hours * 3600)

        # Continue as new or finish
        if iteration < max_iterations:
            # Continue as new workflow
            workflow.continue_as_new(
                args=[{
                    **params,
                    "_iteration": iteration + 1
                }]
            )
        else:
            # Daily restart - let scheduler restart us
            return {
                "iterations_completed": iteration + 1,
                "final_health": health
            }


# ============================================================================
# CLI Interface
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Epistemic Audit Workflow CLI")
    parser.add_argument(
        "--run-audit",
        action="store_true",
        help="Run single audit (without Temporal)"
    )
    parser.add_argument(
        "--agent",
        type=str,
        help="Specific agent to audit"
    )
    parser.add_argument(
        "--health",
        action="store_true",
        help="Show system health"
    )

    args = parser.parse_args()

    if args.health:
        from epistemic_scheduler import get_system_epistemic_health
        import json
        print(json.dumps(get_system_epistemic_health(), indent=2))

    elif args.run_audit:
        from counterfactual_testing import run_flexibility_audit
        agent_ids = [args.agent] if args.agent else None
        result = run_flexibility_audit(agent_ids)
        import json
        print(json.dumps(result, indent=2, default=str))

    else:
        parser.print_help()
