#!/usr/bin/env python3
"""
MCTS Improvement Scheduler - Automated Self-Improvement Cycles

Based on research:
- Agent Q: MCTS exploration of candidate approaches + DPO selection
- ExACT: Reflective-MCTS with backtracking
- OS-Copilot: Skill accumulation from experience
- SOL: Self-Initiated Open World Learning

This scheduler:
1. Identifies skills with low success rates
2. Generates candidate improvement strategies
3. Simulates expected outcomes using historical data
4. Selects and applies improvements via MCTS-style selection
5. Tracks improvement cycles and validates results

Designed to run weekly via systemd timer or cron.
"""

import os
import sys
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import random

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "intelligent-agents"))

# Configuration
SCHEDULER_STATE_FILE = Path("/mnt/agentic-system/databases/mcts_scheduler_state.json")
IMPROVEMENT_HISTORY_FILE = Path("/mnt/agentic-system/databases/improvement_history.jsonl")
LOG_FILE = Path("/mnt/agentic-system/logs/mcts-scheduler.log")

SUCCESS_RATE_THRESHOLD = 0.90  # Target success rate
MINIMUM_EXECUTIONS = 50  # Minimum executions to consider for improvement
MAX_CONCURRENT_IMPROVEMENTS = 2  # Max skills to improve simultaneously

# Improvement strategy templates based on research
IMPROVEMENT_STRATEGIES = {
    "retry_with_backoff": {
        "name": "Retry with Exponential Backoff",
        "expected_improvement": 0.08,
        "risk": 0.1,
        "complexity": 0.2,
        "applicable_causes": ["network_timeout", "connection_issue", "mcp_communication", "database_error"]
    },
    "incremental_checkpoints": {
        "name": "Incremental Checkpoints",
        "expected_improvement": 0.06,
        "risk": 0.15,
        "complexity": 0.3,
        "applicable_causes": ["unknown_cause", "memory_exhaustion"]
    },
    "input_validation": {
        "name": "Enhanced Input Validation",
        "expected_improvement": 0.05,
        "risk": 0.05,
        "complexity": 0.2,
        "applicable_causes": ["serialization_error", "resource_not_found"]
    },
    "connection_pooling": {
        "name": "Connection Pooling",
        "expected_improvement": 0.07,
        "risk": 0.1,
        "complexity": 0.4,
        "applicable_causes": ["database_error", "connection_issue"]
    },
    "batch_processing": {
        "name": "Batch Processing",
        "expected_improvement": 0.04,
        "risk": 0.2,
        "complexity": 0.5,
        "applicable_causes": ["memory_exhaustion", "network_timeout"]
    },
    "health_checks": {
        "name": "Pre-operation Health Checks",
        "expected_improvement": 0.05,
        "risk": 0.05,
        "complexity": 0.15,
        "applicable_causes": ["mcp_communication", "resource_not_found"]
    }
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - MCTSScheduler - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE) if LOG_FILE.parent.exists() else logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MCTSImprovementScheduler:
    """
    MCTS-inspired scheduler for systematic skill improvement.
    """

    def __init__(self):
        self.state = self._load_state()

    def _load_state(self) -> dict:
        """Load scheduler state."""
        if SCHEDULER_STATE_FILE.exists():
            try:
                with open(SCHEDULER_STATE_FILE, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "last_run": None,
            "total_cycles": 0,
            "active_improvements": [],
            "completed_improvements": [],
            "strategy_success_rates": {}
        }

    def _save_state(self):
        """Save scheduler state."""
        try:
            SCHEDULER_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(SCHEDULER_STATE_FILE, 'w') as f:
                json.dump(self.state, f, indent=2, default=str)
        except IOError as e:
            logger.error(f"Failed to save state: {e}")

    def _call_mcp(self, endpoint: str, payload: dict) -> Optional[dict]:
        """Call enhanced-memory MCP endpoint."""
        try:
            req = urllib.request.Request(
                f"http://localhost:8765/{endpoint}",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except Exception as e:
            logger.warning(f"MCP call failed ({endpoint}): {e}")
            return None

    def _get_skills_needing_improvement(self) -> List[dict]:
        """
        Get skills with success rates below threshold.
        Uses MCP to get current skill statistics.
        """
        result = self._call_mcp("get_skills", {"min_success_rate": 0, "limit": 50})
        if not result:
            return []

        skills = json.loads(result.get("result", "[]")) if isinstance(result.get("result"), str) else result.get("result", [])

        needing_improvement = []
        for skill in skills:
            success_rate = skill.get("success_rate", 1.0)
            execution_count = skill.get("execution_count", 0)

            if success_rate < SUCCESS_RATE_THRESHOLD and execution_count >= MINIMUM_EXECUTIONS:
                needing_improvement.append({
                    "skill_name": skill.get("skill_name"),
                    "skill_category": skill.get("skill_category"),
                    "success_rate": success_rate,
                    "execution_count": execution_count,
                    "failure_rate": 1 - success_rate,
                    "improvement_potential": SUCCESS_RATE_THRESHOLD - success_rate
                })

        # Sort by improvement potential (highest first)
        needing_improvement.sort(key=lambda x: x["improvement_potential"], reverse=True)
        return needing_improvement

    def _load_contrastive_analysis(self) -> dict:
        """Load the latest contrastive analysis."""
        analysis_file = Path("/mnt/agentic-system/databases/contrastive_analysis.json")
        if analysis_file.exists():
            try:
                with open(analysis_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _select_strategies_for_skill(self, skill_name: str, skill_analysis: dict) -> List[dict]:
        """
        MCTS EXPLORE: Generate candidate strategies for a skill.
        Based on failure causes from contrastive analysis.
        """
        candidates = []
        causes = skill_analysis.get("potential_cause_distribution", {})

        for strategy_id, strategy in IMPROVEMENT_STRATEGIES.items():
            # Check if strategy applies to any of the skill's failure causes
            applicable = any(cause in strategy["applicable_causes"]
                           for cause in causes.keys())

            if applicable or not causes:  # Apply if no specific causes known
                # Calculate expected value using MCTS-style scoring
                expected_value = self._calculate_expected_value(strategy, skill_analysis)

                candidates.append({
                    "strategy_id": strategy_id,
                    "strategy": strategy,
                    "expected_value": expected_value,
                    "applicable_causes": [c for c in causes.keys()
                                         if c in strategy["applicable_causes"]]
                })

        # Sort by expected value (MCTS selection)
        candidates.sort(key=lambda x: x["expected_value"], reverse=True)
        return candidates[:3]  # Top 3 candidates

    def _calculate_expected_value(self, strategy: dict, skill_analysis: dict) -> float:
        """
        Calculate expected value of a strategy using MCTS-style evaluation.
        EV = expected_improvement × (1 - risk) / complexity
        Modified by historical success rate of this strategy.
        """
        expected_improvement = strategy["expected_improvement"]
        risk = strategy["risk"]
        complexity = strategy["complexity"]

        # Get historical success rate for this strategy
        historical_rate = self.state.get("strategy_success_rates", {}).get(
            strategy.get("name", ""), 0.5
        )

        # Base expected value
        base_ev = expected_improvement * (1 - risk) / max(complexity, 0.1)

        # Adjust by historical success
        adjusted_ev = base_ev * (0.5 + 0.5 * historical_rate)

        # Bonus for high failure rate (more room for improvement)
        failure_rate = 1 - skill_analysis.get("success_rate", 0.9)
        adjusted_ev *= (1 + failure_rate)

        return adjusted_ev

    def _simulate_outcome(self, skill: dict, strategy: dict, analysis: dict) -> dict:
        """
        MCTS SIMULATE: Predict outcome using historical data.
        """
        current_rate = skill.get("success_rate", 0)
        expected_improvement = strategy["strategy"]["expected_improvement"]
        risk = strategy["strategy"]["risk"]

        # Simulate with uncertainty
        noise = random.gauss(0, 0.02)  # Small random noise
        predicted_improvement = expected_improvement * (1 - risk) + noise
        predicted_rate = min(1.0, current_rate + predicted_improvement)

        return {
            "current_rate": current_rate,
            "predicted_rate": predicted_rate,
            "predicted_improvement": predicted_rate - current_rate,
            "confidence": 0.7 - risk  # Higher risk = lower confidence
        }

    def _record_improvement_cycle(self, skill: dict, strategy: dict,
                                   simulation: dict, applied: bool):
        """Record improvement cycle for learning."""
        record = {
            "timestamp": datetime.now().isoformat(),
            "skill_name": skill.get("skill_name"),
            "strategy_id": strategy.get("strategy_id"),
            "strategy_name": strategy["strategy"]["name"],
            "baseline_success_rate": skill.get("success_rate"),
            "expected_improvement": strategy["strategy"]["expected_improvement"],
            "simulation": simulation,
            "applied": applied,
            "cycle_number": self.state["total_cycles"]
        }

        try:
            IMPROVEMENT_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(IMPROVEMENT_HISTORY_FILE, 'a') as f:
                f.write(json.dumps(record, default=str) + '\n')
        except IOError as e:
            logger.error(f"Failed to record cycle: {e}")

    def _create_improvement_episode(self, skill: dict, strategy: dict, simulation: dict):
        """Create episode in enhanced-memory for AGI learning."""
        episode_data = {
            "cycle_type": "mcts_improvement",
            "skill_name": skill.get("skill_name"),
            "strategy_applied": strategy["strategy"]["name"],
            "baseline_rate": skill.get("success_rate"),
            "target_rate": simulation.get("predicted_rate"),
            "expected_improvement": simulation.get("predicted_improvement"),
            "research_basis": ["Agent Q", "ExACT", "OS-Copilot", "SOL"]
        }

        self._call_mcp("add_episode", {
            "event_type": "mcts_improvement_cycle",
            "episode_data": episode_data,
            "significance_score": 0.8,
            "tags": ["mcts", "self-improvement", "automated-scheduler"]
        })

    def run_improvement_cycle(self, dry_run: bool = False) -> dict:
        """
        Main MCTS improvement cycle.

        1. IDENTIFY: Find skills needing improvement
        2. EXPLORE: Generate candidate strategies
        3. SIMULATE: Predict outcomes
        4. SELECT: Choose best strategy
        5. APPLY: Implement improvement (or record for manual implementation)
        6. BACKPROPAGATE: Update strategy success rates
        """
        logger.info("=" * 60)
        logger.info("MCTS IMPROVEMENT CYCLE STARTING")
        logger.info("=" * 60)

        self.state["last_run"] = datetime.now().isoformat()
        self.state["total_cycles"] = self.state.get("total_cycles", 0) + 1

        # Load contrastive analysis
        analysis = self._load_contrastive_analysis()

        # Step 1: IDENTIFY skills needing improvement
        skills = self._get_skills_needing_improvement()
        logger.info(f"Found {len(skills)} skills below {SUCCESS_RATE_THRESHOLD:.0%} threshold")

        if not skills:
            logger.info("No skills need improvement - all above threshold!")
            self._save_state()
            return {"status": "no_improvement_needed", "skills_checked": 0}

        results = {
            "status": "completed",
            "cycle_number": self.state["total_cycles"],
            "skills_analyzed": len(skills),
            "improvements_proposed": [],
            "dry_run": dry_run
        }

        # Process top skills (limited by MAX_CONCURRENT_IMPROVEMENTS)
        for skill in skills[:MAX_CONCURRENT_IMPROVEMENTS]:
            logger.info(f"\nAnalyzing: {skill['skill_name']} "
                       f"(success: {skill['success_rate']:.1%}, "
                       f"executions: {skill['execution_count']})")

            # Get skill-specific analysis
            skill_analysis = analysis.get("analyses", {}).get(skill["skill_name"], {})

            # Step 2: EXPLORE - Generate candidate strategies
            candidates = self._select_strategies_for_skill(skill["skill_name"], skill_analysis)
            logger.info(f"  Generated {len(candidates)} candidate strategies")

            for i, candidate in enumerate(candidates):
                logger.info(f"    {i+1}. {candidate['strategy']['name']} "
                           f"(EV: {candidate['expected_value']:.3f})")

            if not candidates:
                logger.warning(f"  No applicable strategies for {skill['skill_name']}")
                continue

            # Step 3: SIMULATE - Predict outcome for best candidate
            best_strategy = candidates[0]
            simulation = self._simulate_outcome(skill, best_strategy, skill_analysis)
            logger.info(f"  Simulation: {simulation['current_rate']:.1%} → "
                       f"{simulation['predicted_rate']:.1%} "
                       f"(confidence: {simulation['confidence']:.1%})")

            # Step 4: SELECT - Use best strategy if meets criteria
            if simulation["predicted_improvement"] > 0.02:  # >2% improvement expected
                logger.info(f"  ✓ Strategy selected: {best_strategy['strategy']['name']}")

                improvement = {
                    "skill_name": skill["skill_name"],
                    "strategy": best_strategy["strategy"]["name"],
                    "strategy_id": best_strategy["strategy_id"],
                    "baseline_rate": skill["success_rate"],
                    "predicted_rate": simulation["predicted_rate"],
                    "expected_improvement": simulation["predicted_improvement"],
                    "recommendations": skill_analysis.get("recommendations", [])
                }
                results["improvements_proposed"].append(improvement)

                # Step 5: APPLY (or record for manual implementation)
                if not dry_run:
                    # Record improvement cycle
                    self._record_improvement_cycle(skill, best_strategy, simulation, applied=True)
                    # Create episode for AGI learning
                    self._create_improvement_episode(skill, best_strategy, simulation)
                    # Add to active improvements for tracking
                    self.state["active_improvements"].append({
                        "skill_name": skill["skill_name"],
                        "strategy": best_strategy["strategy"]["name"],
                        "started_at": datetime.now().isoformat(),
                        "baseline_rate": skill["success_rate"],
                        "target_rate": simulation["predicted_rate"]
                    })
                else:
                    self._record_improvement_cycle(skill, best_strategy, simulation, applied=False)
            else:
                logger.info(f"  ✗ No strategy meets improvement threshold")

        # Save state
        self._save_state()

        logger.info("\n" + "=" * 60)
        logger.info(f"CYCLE COMPLETE: {len(results['improvements_proposed'])} improvements proposed")
        logger.info("=" * 60)

        return results

    def validate_active_improvements(self) -> dict:
        """
        MCTS BACKPROPAGATE: Validate improvements and update strategy success rates.
        Called after some time has passed to measure actual results.
        """
        logger.info("Validating active improvements...")

        validated = []
        still_active = []

        for improvement in self.state.get("active_improvements", []):
            skill_name = improvement["skill_name"]
            started_at = datetime.fromisoformat(improvement["started_at"])

            # Only validate improvements older than 1 day
            if datetime.now() - started_at < timedelta(days=1):
                still_active.append(improvement)
                continue

            # Get current success rate
            result = self._call_mcp("get_skills", {"min_success_rate": 0, "limit": 100})
            if not result:
                still_active.append(improvement)
                continue

            skills = json.loads(result.get("result", "[]")) if isinstance(result.get("result"), str) else result.get("result", [])
            skill_data = next((s for s in skills if s.get("skill_name") == skill_name), None)

            if not skill_data:
                still_active.append(improvement)
                continue

            current_rate = skill_data.get("success_rate", 0)
            baseline_rate = improvement["baseline_rate"]
            target_rate = improvement["target_rate"]

            actual_improvement = current_rate - baseline_rate
            target_improvement = target_rate - baseline_rate
            success = actual_improvement >= target_improvement * 0.5  # 50% of target = success

            # Update strategy success rates (BACKPROPAGATE)
            strategy_name = improvement["strategy"]
            strategy_rates = self.state.setdefault("strategy_success_rates", {})
            current_strategy_rate = strategy_rates.get(strategy_name, 0.5)
            # Exponential moving average
            strategy_rates[strategy_name] = current_strategy_rate * 0.7 + (1.0 if success else 0.0) * 0.3

            validated.append({
                "skill_name": skill_name,
                "strategy": strategy_name,
                "baseline_rate": baseline_rate,
                "target_rate": target_rate,
                "actual_rate": current_rate,
                "actual_improvement": actual_improvement,
                "success": success
            })

            # Move to completed
            improvement["completed_at"] = datetime.now().isoformat()
            improvement["actual_rate"] = current_rate
            improvement["success"] = success
            self.state.setdefault("completed_improvements", []).append(improvement)

            logger.info(f"  Validated {skill_name}: {baseline_rate:.1%} → {current_rate:.1%} "
                       f"({'✓ Success' if success else '✗ Below target'})")

        self.state["active_improvements"] = still_active
        self._save_state()

        return {
            "validated_count": len(validated),
            "still_active": len(still_active),
            "validations": validated
        }

    def get_status(self) -> dict:
        """Get scheduler status."""
        return {
            "last_run": self.state.get("last_run"),
            "total_cycles": self.state.get("total_cycles", 0),
            "active_improvements": len(self.state.get("active_improvements", [])),
            "completed_improvements": len(self.state.get("completed_improvements", [])),
            "strategy_success_rates": self.state.get("strategy_success_rates", {})
        }


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="MCTS Improvement Scheduler")
    parser.add_argument("--dry-run", action="store_true", help="Analyze without applying")
    parser.add_argument("--validate", action="store_true", help="Validate active improvements")
    parser.add_argument("--status", action="store_true", help="Show scheduler status")
    parser.add_argument("--run-cycle", action="store_true", help="Run full improvement cycle (for systemd)")
    args = parser.parse_args()

    scheduler = MCTSImprovementScheduler()

    if args.status:
        status = scheduler.get_status()
        print(json.dumps(status, indent=2, default=str))
    elif args.validate:
        result = scheduler.validate_active_improvements()
        print(json.dumps(result, indent=2, default=str))
    elif args.run_cycle or not any([args.status, args.validate, args.dry_run]):
        # Full cycle: validate previous + run new improvements
        logger.info("Starting full MCTS improvement cycle...")
        validation = scheduler.validate_active_improvements()
        logger.info(f"Validated {validation['validated_count']} previous improvements")
        result = scheduler.run_improvement_cycle(dry_run=False)
        result["validation"] = validation
        print(json.dumps(result, indent=2, default=str))
    else:
        result = scheduler.run_improvement_cycle(dry_run=args.dry_run)
        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
