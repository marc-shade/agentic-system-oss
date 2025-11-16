#!/usr/bin/env python3
"""
AGI Memory Phase 4 Test Suite

Tests meta-cognitive awareness and self-improvement capabilities:
- Meta-cognitive state tracking
- Knowledge gap detection
- Reasoning strategy tracking
- Performance metrics
- Self-improvement cycles
- Multi-agent coordination

Run: python3 test_agi_phase4.py
"""

import sys
import sqlite3
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from agi.metacognition import MetaCognition, PerformanceTracker
from agi.self_improvement import SelfImprovement, CoordinationManager

# Test database path
TEST_DB = Path.home() / ".claude" / "enhanced_memories" / "memory.db"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_test_header(test_name):
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}TEST: {test_name}{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_success(message):
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")

def print_error(message):
    print(f"{Colors.RED}❌ {message}{Colors.END}")

def print_info(message):
    print(f"{Colors.YELLOW}ℹ️  {message}{Colors.END}")

def cleanup_test_data(agent_id: str):
    """Remove test data"""
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()

    # Delete Phase 4 test data
    cursor.execute('DELETE FROM metacognitive_states WHERE agent_id = ?', (agent_id,))
    cursor.execute('DELETE FROM knowledge_gaps WHERE agent_id = ?', (agent_id,))
    cursor.execute('DELETE FROM self_improvement_cycles WHERE agent_id = ?', (agent_id,))
    cursor.execute('DELETE FROM reasoning_strategies WHERE agent_id = ?', (agent_id,))
    cursor.execute('DELETE FROM performance_metrics WHERE agent_id = ?', (agent_id,))
    cursor.execute('DELETE FROM coordination_messages WHERE sender_agent_id = ? OR recipient_agent_id = ?',
                   (agent_id, agent_id))

    conn.commit()
    conn.close()

def test_metacognitive_tracking():
    """Test 1: Meta-Cognitive State Tracking"""
    print_test_header("Meta-Cognitive State Tracking")

    metacog = MetaCognition()
    agent_id = "test_agent_metacog"

    try:
        # Record meta-cognitive state
        state_id = metacog.record_metacognitive_state(
            agent_id=agent_id,
            self_awareness=0.7,
            knowledge_awareness=0.6,
            process_awareness=0.8,
            limitation_awareness=0.5,
            cognitive_load=0.4,
            confidence_level=0.75,
            task_context={"task": "reasoning"},
            reasoning_trace=["step1", "step2", "step3"]
        )

        print_success(f"Recorded meta-cognitive state: state_id={state_id}")
        print_info(f"  - Self-awareness: 0.7")
        print_info(f"  - Confidence: 0.75")
        print_info(f"  - Cognitive load: 0.4")

        # Retrieve current state
        state = metacog.get_current_state(agent_id)
        if state and state['confidence_level'] == 0.75:
            print_success("Retrieved current meta-cognitive state")
            cleanup_test_data(agent_id)
            return True
        else:
            print_error("Failed to retrieve state")
            cleanup_test_data(agent_id)
            return False

    except Exception as e:
        print_error(f"Failed: {e}")
        cleanup_test_data(agent_id)
        return False

def test_knowledge_gap_detection():
    """Test 2: Knowledge Gap Detection"""
    print_test_header("Knowledge Gap Detection")

    metacog = MetaCognition()
    agent_id = "test_agent_gaps"

    try:
        # Identify a knowledge gap
        gap_id = metacog.identify_knowledge_gap(
            agent_id=agent_id,
            domain="quantum_physics",
            gap_description="Limited understanding of quantum entanglement",
            gap_type="conceptual",
            severity=0.8,
            discovered_by="self-reflection"
        )

        print_success(f"Identified knowledge gap: gap_id={gap_id}")
        print_info(f"  - Domain: quantum_physics")
        print_info(f"  - Type: conceptual")
        print_info(f"  - Severity: 0.8")

        # Get knowledge gaps
        gaps = metacog.get_knowledge_gaps(agent_id, status="open", min_severity=0.5)

        if len(gaps) > 0 and gaps[0]['severity'] == 0.8:
            print_success(f"Retrieved {len(gaps)} open knowledge gap(s)")

            # Update learning progress
            metacog.update_gap_progress(gap_id, learning_progress=0.6)
            print_success("Updated learning progress to 0.6")

            cleanup_test_data(agent_id)
            return True
        else:
            print_error("Failed to retrieve knowledge gaps")
            cleanup_test_data(agent_id)
            return False

    except Exception as e:
        print_error(f"Failed: {e}")
        cleanup_test_data(agent_id)
        return False

def test_reasoning_strategy_tracking():
    """Test 3: Reasoning Strategy Tracking"""
    print_test_header("Reasoning Strategy Tracking")

    metacog = MetaCognition()
    agent_id = "test_agent_reasoning"

    try:
        # Track successful strategy
        metacog.track_reasoning_strategy(
            agent_id=agent_id,
            strategy_name="test_deductive",
            strategy_type="deductive",
            success=True,
            confidence=0.9
        )

        print_success("Tracked deductive reasoning: success=True, confidence=0.9")

        # Track another success
        metacog.track_reasoning_strategy(
            agent_id=agent_id,
            strategy_name="test_deductive",
            strategy_type="deductive",
            success=True,
            confidence=0.85
        )

        # Track a failure
        metacog.track_reasoning_strategy(
            agent_id=agent_id,
            strategy_name="test_deductive",
            strategy_type="deductive",
            success=False,
            confidence=0.5
        )

        print_info("Tracked 3 uses: 2 successes, 1 failure")

        # Get effective strategies (need at least 3 uses, 60% success rate)
        strategies = metacog.get_effective_strategies(
            agent_id=agent_id,
            min_success_rate=0.6,
            min_usage=3
        )

        if len(strategies) > 0:
            print_success(f"Found {len(strategies)} effective strategy(ies)")
            print_info(f"  - Strategy: {strategies[0]['strategy_name']}")
            print_info(f"  - Success rate: {strategies[0]['success_rate']:.2f}")
            cleanup_test_data(agent_id)
            return True
        else:
            print_error("No effective strategies found")
            cleanup_test_data(agent_id)
            return False

    except Exception as e:
        print_error(f"Failed: {e}")
        cleanup_test_data(agent_id)
        return False

def test_performance_tracking():
    """Test 4: Performance Metric Tracking"""
    print_test_header("Performance Metric Tracking")

    performance = PerformanceTracker()
    agent_id = "test_agent_performance"

    try:
        # Update metrics
        performance.update_metric(
            agent_id=agent_id,
            metric_name="reasoning_speed",
            metric_category="cognitive",
            current_value=0.6,
            target_value=0.9
        )

        print_success("Updated reasoning_speed: 0.6 (target: 0.9)")

        # Update again to show improvement
        performance.update_metric(
            agent_id=agent_id,
            metric_name="reasoning_speed",
            metric_category="cognitive",
            current_value=0.7,
            target_value=0.9
        )

        print_info("Updated reasoning_speed: 0.7 (improving)")

        # Get performance trends
        trends = performance.get_performance_trends(agent_id, category="cognitive")

        if len(trends) > 0:
            print_success(f"Retrieved {len(trends)} performance trend(s)")
            print_info(f"  - Metric: {trends[0]['metric_name']}")
            print_info(f"  - Trend: {trends[0].get('trend', 'N/A')}")
            cleanup_test_data(agent_id)
            return True
        else:
            print_error("No performance trends found")
            cleanup_test_data(agent_id)
            return False

    except Exception as e:
        print_error(f"Failed: {e}")
        cleanup_test_data(agent_id)
        return False

def test_improvement_cycle():
    """Test 5: Self-Improvement Cycle"""
    print_test_header("Self-Improvement Cycle")

    improvement = SelfImprovement()
    agent_id = "test_agent_improvement"

    try:
        # Start improvement cycle
        cycle_id = improvement.start_improvement_cycle(
            agent_id=agent_id,
            cycle_type="performance",
            improvement_goals={"speed": 0.9, "accuracy": 0.95}
        )

        print_success(f"Started improvement cycle: cycle_id={cycle_id}")

        # Assess baseline
        improvement.assess_baseline_performance(
            cycle_id=cycle_id,
            baseline_metrics={"speed": 0.6, "accuracy": 0.8},
            identified_weaknesses=["slow reasoning", "occasional errors"]
        )

        print_info("Assessed baseline: speed=0.6, accuracy=0.8")

        # Apply strategies
        improvement.apply_improvement_strategies(
            cycle_id=cycle_id,
            strategies=[{"name": "optimize_algorithm"}, {"name": "add_validation"}],
            changes=["refactored core", "added checks"]
        )

        print_info("Applied 2 improvement strategies")

        # Validate improvements
        success = improvement.validate_improvements(
            cycle_id=cycle_id,
            new_metrics={"speed": 0.75, "accuracy": 0.9},
            success_criteria={"min_improvement": 0.05}
        )

        print_info(f"Validation: success={success}")

        # Complete cycle
        improvement.complete_cycle(
            cycle_id=cycle_id,
            lessons_learned=["optimization works", "validation helps"],
            next_recommendations=["further optimization", "more testing"]
        )

        print_success("Completed improvement cycle")

        # Get history
        history = improvement.get_improvement_history(agent_id)

        if len(history) > 0:
            print_success(f"Retrieved improvement history: {len(history)} cycle(s)")
            cleanup_test_data(agent_id)
            return True
        else:
            print_error("No improvement history found")
            cleanup_test_data(agent_id)
            return False

    except Exception as e:
        print_error(f"Failed: {e}")
        cleanup_test_data(agent_id)
        return False

def test_multi_agent_coordination():
    """Test 6: Multi-Agent Coordination"""
    print_test_header("Multi-Agent Coordination")

    coordination = CoordinationManager()
    agent1 = "test_agent_sender"
    agent2 = "test_agent_receiver"

    try:
        # Send message
        message_id = coordination.send_message(
            sender_agent_id=agent1,
            recipient_agent_id=agent2,
            message_type="request",
            subject="Need help with task",
            message_content={"task": "data_analysis", "urgency": "high"},
            priority=0.8,
            requires_response=True
        )

        print_success(f"Sent coordination message: message_id={message_id}")
        print_info(f"  - From: {agent1}")
        print_info(f"  - To: {agent2}")
        print_info(f"  - Priority: 0.8")

        # Receive messages
        messages = coordination.receive_messages(agent2, status="pending")

        if len(messages) > 0:
            print_success(f"Received {len(messages)} message(s)")

            # Acknowledge message
            coordination.acknowledge_message(
                message_id=message_id,
                response_content={"status": "acknowledged", "eta": "2 hours"}
            )

            print_success("Acknowledged message with response")

            # Get pending coordination
            pending = coordination.get_pending_coordination(agent2)
            print_info(f"Pending coordination tasks: {len(pending)}")

            cleanup_test_data(agent1)
            cleanup_test_data(agent2)
            return True
        else:
            print_error("No messages received")
            cleanup_test_data(agent1)
            cleanup_test_data(agent2)
            return False

    except Exception as e:
        print_error(f"Failed: {e}")
        cleanup_test_data(agent1)
        cleanup_test_data(agent2)
        return False

def main():
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}AGI MEMORY PHASE 4 TEST SUITE{Colors.END}")
    print(f"{Colors.BLUE}Testing: Meta-Cognitive Awareness & Self-Improvement{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")

    # Setup
    print_info(f"Database: {TEST_DB}")

    # Run tests
    results = {
        "Meta-Cognitive State Tracking": test_metacognitive_tracking(),
        "Knowledge Gap Detection": test_knowledge_gap_detection(),
        "Reasoning Strategy Tracking": test_reasoning_strategy_tracking(),
        "Performance Metric Tracking": test_performance_tracking(),
        "Self-Improvement Cycle": test_improvement_cycle(),
        "Multi-Agent Coordination": test_multi_agent_coordination(),
    }

    # Summary
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}TEST SUMMARY{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for test_name, result in results.items():
        status = f"{Colors.GREEN}✅ PASSED{Colors.END}" if result else f"{Colors.RED}❌ FAILED{Colors.END}"
        print(f"{status}: {test_name}")

    print(f"\n{Colors.BLUE}Final Score: {passed}/{total} tests passed{Colors.END}")

    if passed == total:
        print(f"\n{Colors.GREEN}{'='*60}{Colors.END}")
        print(f"{Colors.GREEN}🎉 ALL TESTS PASSED! Phase 4 is ready for production.{Colors.END}")
        print(f"{Colors.GREEN}{'='*60}{Colors.END}\n")
        return 0
    else:
        print(f"\n{Colors.RED}{'='*60}{Colors.END}")
        print(f"{Colors.RED}⚠️  Some tests failed. Review output above.{Colors.END}")
        print(f"{Colors.RED}{'='*60}{Colors.END}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
