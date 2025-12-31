"""
Feedback Loop Handlers
Closes the loop on autonomous learning by measuring what actually works
Enables adaptive scheduling and goal-directed research
"""
import os
import platform
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path


def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    system = platform.system()
    if system == "Darwin":
        if Path("/Volumes/SSDRAID0/agentic-system").exists():
            return Path("/Volumes/SSDRAID0/agentic-system")
        return Path("/Volumes/FILES/agentic-system")
    return Path("/home/marc/agentic-system")


_STORAGE_BASE = _get_storage_base()
_STATE_FILE = _STORAGE_BASE / "databases" / "feedback_loop_state.json"


def evaluate_recent_learnings(event):
    """
    Evaluate which recent learnings were actually useful
    Closes the feedback loop on autonomous improvement
    """
    print("=" * 60)
    print(f"Learning Feedback Evaluation - {datetime.now()}")
    print("=" * 60)

    results = {
        "timestamp": datetime.now().isoformat(),
        "entities_evaluated": 0,
        "high_value": 0,
        "low_value": 0,
        "pruned": 0
    }

    try:
        # Get entities created in last 24 hours
        recent_entities = get_recent_entities(hours=24)
        results["entities_evaluated"] = len(recent_entities)
        print(f"Evaluating {len(recent_entities)} recent entities")

        for entity in recent_entities:
            # Check if entity has been accessed/used
            access_count = entity.get("access_count", 0)

            # Check if entity contributed to successful outcomes
            contributed_to_success = check_success_contribution(entity)

            # Check retrieval relevance (was it retrieved when needed?)
            retrieval_score = entity.get("retrieval_score", 0.5)

            # Calculate value score
            value_score = calculate_value_score(
                access_count=access_count,
                contributed=contributed_to_success,
                retrieval_score=retrieval_score
            )

            if value_score > 0.7:
                results["high_value"] += 1
                # Boost importance
                boost_entity_salience(entity["id"], 0.1)
            elif value_score < 0.3:
                results["low_value"] += 1
                # Mark for potential pruning
                if should_prune(entity, value_score):
                    prune_entity(entity["id"])
                    results["pruned"] += 1

        # Store feedback for next cycle
        store_feedback_state(results)

        print(f"\n✓ Evaluation complete")
        print(f"  High value: {results['high_value']}")
        print(f"  Low value: {results['low_value']}")
        print(f"  Pruned: {results['pruned']}")

        return results

    except Exception as e:
        print(f"ERROR: Feedback evaluation failed: {e}")
        return {"status": "error", "error": str(e)}


def identify_knowledge_gaps(event):
    """
    Identify knowledge gaps to drive goal-directed research
    Instead of rotating topics, find what we actually need to learn
    """
    print("=" * 60)
    print(f"Knowledge Gap Analysis - {datetime.now()}")
    print("=" * 60)

    gaps = []

    try:
        # Get recent failed tasks/queries
        failures = get_recent_failures()
        for failure in failures:
            gap = extract_knowledge_gap(failure)
            if gap:
                gaps.append(gap)

        # Get low-confidence reasoning instances
        low_confidence = get_low_confidence_instances()
        for instance in low_confidence:
            gap = {
                "domain": instance.get("domain", "general"),
                "description": f"Low confidence in: {instance.get('topic', 'unknown')}",
                "severity": 1.0 - instance.get("confidence", 0.5),
                "source": "reasoning_confidence"
            }
            gaps.append(gap)

        # Get areas with sparse causal links
        sparse_areas = get_sparse_causal_areas()
        for area in sparse_areas:
            gaps.append({
                "domain": area["domain"],
                "description": f"Sparse causal understanding: {area['topic']}",
                "severity": 0.6,
                "source": "causal_graph"
            })

        # Deduplicate and prioritize
        prioritized_gaps = prioritize_gaps(gaps)

        # Store for research pipeline to use
        store_research_priorities(prioritized_gaps)

        print(f"\n✓ Identified {len(prioritized_gaps)} knowledge gaps")
        for i, gap in enumerate(prioritized_gaps[:5]):
            print(f"  {i+1}. {gap['domain']}: {gap['description'][:50]}...")

        return {
            "gaps_found": len(prioritized_gaps),
            "top_gaps": prioritized_gaps[:5]
        }

    except Exception as e:
        print(f"ERROR: Gap analysis failed: {e}")
        return {"status": "error", "error": str(e)}


def adaptive_schedule_check(event):
    """
    Check if improvement cycles should accelerate or slow down
    Based on recent progress and diminishing returns detection
    """
    print("=" * 60)
    print(f"Adaptive Schedule Check - {datetime.now()}")
    print("=" * 60)

    try:
        # Load recent cycle results
        state = load_feedback_state()
        recent_cycles = state.get("recent_cycles", [])

        if len(recent_cycles) < 3:
            print("Not enough data for adaptive scheduling")
            return {"recommendation": "maintain", "reason": "insufficient_data"}

        # Calculate improvement velocity
        velocities = []
        for i in range(1, len(recent_cycles)):
            prev = recent_cycles[i-1]
            curr = recent_cycles[i]

            # Compare entity creation rates
            prev_entities = prev.get("entities_created", 0)
            curr_entities = curr.get("entities_created", 0)

            if prev_entities > 0:
                velocity = (curr_entities - prev_entities) / prev_entities
                velocities.append(velocity)

        avg_velocity = sum(velocities) / len(velocities) if velocities else 0

        # Check for diminishing returns
        recent_high_value = sum(c.get("high_value", 0) for c in recent_cycles[-3:])
        recent_low_value = sum(c.get("low_value", 0) for c in recent_cycles[-3:])

        if recent_low_value > recent_high_value * 2:
            recommendation = "slow_down"
            reason = "diminishing_returns"
        elif avg_velocity > 0.2:
            recommendation = "accelerate"
            reason = "high_progress"
        else:
            recommendation = "maintain"
            reason = "steady_progress"

        result = {
            "recommendation": recommendation,
            "reason": reason,
            "avg_velocity": avg_velocity,
            "high_value_ratio": recent_high_value / max(recent_high_value + recent_low_value, 1)
        }

        print(f"\n✓ Recommendation: {recommendation}")
        print(f"  Reason: {reason}")
        print(f"  Velocity: {avg_velocity:.2f}")

        return result

    except Exception as e:
        print(f"ERROR: Adaptive check failed: {e}")
        return {"recommendation": "maintain", "error": str(e)}


def cross_cycle_context_sync(event):
    """
    Sync context between improvement cycles
    Ensures learnings from one cycle inform the next
    """
    print("=" * 60)
    print(f"Cross-Cycle Context Sync - {datetime.now()}")
    print("=" * 60)

    try:
        # Get last cycle's key learnings
        state = load_feedback_state()
        last_cycle = state.get("last_cycle", {})

        context = {
            "previous_focus": last_cycle.get("focus_area"),
            "successful_patterns": last_cycle.get("successful_patterns", []),
            "failed_approaches": last_cycle.get("failed_approaches", []),
            "knowledge_gaps_addressed": last_cycle.get("gaps_addressed", []),
            "remaining_gaps": last_cycle.get("remaining_gaps", []),
            "momentum_areas": identify_momentum_areas(state)
        }

        # Store context for next cycle
        store_cycle_context(context)

        print(f"\n✓ Context synced")
        print(f"  Previous focus: {context['previous_focus']}")
        print(f"  Successful patterns: {len(context['successful_patterns'])}")
        print(f"  Momentum areas: {len(context['momentum_areas'])}")

        return context

    except Exception as e:
        print(f"ERROR: Context sync failed: {e}")
        return {"status": "error", "error": str(e)}


# Helper functions

def get_recent_entities(hours=24):
    """Get entities created in last N hours"""
    try:
        response = requests.post(
            "http://localhost:8101/search_nodes",
            json={"query": "*", "limit": 100},
            timeout=30
        )
        if response.status_code == 200:
            entities = response.json().get("results", [])
            cutoff = datetime.now() - timedelta(hours=hours)
            # Filter by creation time (if available)
            return [e for e in entities if e.get("created_at", datetime.now().isoformat()) > cutoff.isoformat()]
    except:
        pass
    return []


def check_success_contribution(entity):
    """Check if entity contributed to successful task outcomes"""
    # Would query task outcomes and check entity references
    return False


def calculate_value_score(access_count, contributed, retrieval_score):
    """Calculate overall value score for an entity"""
    access_weight = min(access_count / 10, 1.0) * 0.3
    contribution_weight = 0.4 if contributed else 0.0
    retrieval_weight = retrieval_score * 0.3
    return access_weight + contribution_weight + retrieval_weight


def should_prune(entity, value_score):
    """Determine if entity should be pruned"""
    age_days = (datetime.now() - datetime.fromisoformat(
        entity.get("created_at", datetime.now().isoformat())
    )).days
    # Only prune if old AND low value
    return age_days > 7 and value_score < 0.2


def boost_entity_salience(entity_id, amount):
    """Boost entity importance"""
    try:
        requests.post(
            "http://localhost:8101/update_salience",
            json={"entity_id": entity_id, "salience_delta": amount, "reason": "feedback_loop"},
            timeout=10
        )
    except:
        pass


def prune_entity(entity_id):
    """Mark entity for archival/deletion"""
    try:
        requests.post(
            "http://localhost:8101/archive_entity",
            json={"entity_id": entity_id, "reason": "low_value_feedback"},
            timeout=10
        )
    except:
        pass


def get_recent_failures():
    """Get recent failed tasks/queries"""
    return []  # Would query task history


def extract_knowledge_gap(failure):
    """Extract knowledge gap from failure"""
    return None


def get_low_confidence_instances():
    """Get instances where confidence was low"""
    try:
        response = requests.get(
            "http://localhost:8101/get_knowledge_gaps",
            params={"agent_id": "agi_claude", "status": "open"},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("gaps", [])
    except:
        pass
    return []


def get_sparse_causal_areas():
    """Find areas with sparse causal understanding"""
    return []


def prioritize_gaps(gaps):
    """Prioritize knowledge gaps by severity and impact"""
    return sorted(gaps, key=lambda x: x.get("severity", 0), reverse=True)[:10]


def store_research_priorities(priorities):
    """Store priorities for research pipeline"""
    try:
        with open(_STORAGE_BASE / "databases" / "research_priorities.json", "w") as f:
            json.dump({"priorities": priorities, "updated": datetime.now().isoformat()}, f)
    except:
        pass


def load_feedback_state():
    """Load feedback loop state"""
    try:
        if _STATE_FILE.exists():
            with open(_STATE_FILE) as f:
                return json.load(f)
    except:
        pass
    return {"recent_cycles": []}


def store_feedback_state(results):
    """Store feedback state"""
    try:
        state = load_feedback_state()
        state["recent_cycles"].append(results)
        state["recent_cycles"] = state["recent_cycles"][-10:]  # Keep last 10
        state["last_update"] = datetime.now().isoformat()

        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except:
        pass


def identify_momentum_areas(state):
    """Identify areas where we're making good progress"""
    momentum = []
    cycles = state.get("recent_cycles", [])
    if len(cycles) >= 2:
        recent_focus = [c.get("focus_area") for c in cycles[-3:] if c.get("focus_area")]
        # Areas mentioned multiple times with good results
        from collections import Counter
        counts = Counter(recent_focus)
        momentum = [area for area, count in counts.items() if count >= 2]
    return momentum


def store_cycle_context(context):
    """Store context for next cycle"""
    try:
        with open(_STORAGE_BASE / "databases" / "cycle_context.json", "w") as f:
            json.dump(context, f, indent=2)
    except:
        pass
