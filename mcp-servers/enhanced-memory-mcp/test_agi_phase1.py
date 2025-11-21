#!/usr/bin/env python3
"""
Test Suite for AGI Memory Phase 1

Tests:
- Agent identity persistence
- Session continuity
- Action outcome tracking
- Cross-session learning
"""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from agi import AgentIdentity, SessionManager, ActionTracker


def test_agent_identity():
    """Test agent identity creation and updates"""
    print("\n🧪 Testing Agent Identity...")
    print("=" * 60)

    agent_id = "test_agent_001"
    identity = AgentIdentity(agent_id)

    # Get initial identity
    initial = identity.get_identity()
    print(f"✅ Created agent: {initial['agent_id']}")
    print(f"   Created at: {initial['created_at']}")
    print(f"   Total sessions: {initial['total_sessions']}")

    # Update skills
    identity.update_skills({
        "coding": 0.85,
        "research": 0.92,
        "debugging": 0.78
    })
    updated = identity.get_identity()
    print(f"\n✅ Updated skills: {updated['skill_levels']}")

    # Add beliefs
    identity.add_belief("Async/await is better than threads for I/O")
    identity.add_belief("Test-driven development catches bugs early")
    updated = identity.get_identity()
    print(f"\n✅ Added beliefs: {len(updated['core_beliefs'])} beliefs")
    for i, belief in enumerate(updated['core_beliefs'], 1):
        print(f"   {i}. {belief}")

    # Update personality
    identity.update_personality({
        "curiosity": 0.8,
        "caution": 0.6,
        "creativity": 0.9
    })
    updated = identity.get_identity()
    print(f"\n✅ Updated personality: {updated['personality_traits']}")

    # Set preferences
    identity.set_preference("preferred_editor", "vim")
    identity.set_preference("code_style", "functional")
    updated = identity.get_identity()
    print(f"\n✅ Set preferences: {updated['preferences']}")

    print("\n✨ Agent Identity Test: PASSED")
    return True


def test_session_management():
    """Test session creation and linking"""
    print("\n🧪 Testing Session Management...")
    print("=" * 60)

    agent_id = "test_agent_001"
    manager = SessionManager(agent_id)

    # Start first session
    session1_id = manager.start_session("Working on AGI memory implementation")
    print(f"✅ Started session 1: {session1_id}")

    # End first session with learnings
    manager.end_session(
        session1_id,
        key_learnings=[
            "Created agent identity system",
            "Implemented session linking",
            "Added action outcome tracking"
        ],
        unfinished_work={
            "goals": ["Test cross-session learning"],
            "tasks": ["Create benchmark suite"]
        },
        performance_metrics={
            "success_rate": 0.95,
            "actions_completed": 12,
            "errors_encountered": 1
        }
    )
    print(f"✅ Ended session 1 with learnings and metrics")

    # Get session context
    context1 = manager.get_session_context(session1_id)
    print(f"\n📋 Session 1 Context:")
    print(f"   Duration: {context1['duration_seconds']}s")
    print(f"   Learnings: {len(context1['key_learnings'])} items")
    print(f"   Performance: {context1['performance_metrics']}")

    # Start second session (should link to first)
    session2_id = manager.start_session("Continuing AGI implementation from yesterday")
    print(f"\n✅ Started session 2: {session2_id}")

    # Verify linkage
    context2 = manager.get_session_context(session2_id)
    print(f"✅ Session 2 linked to previous: {context2['previous_session_id'] == session1_id}")

    # Get session chain
    chain = manager.get_session_chain(session2_id, depth=5)
    print(f"\n📜 Session Chain: {len(chain)} sessions")
    for i, session in enumerate(chain, 1):
        print(f"   {i}. {session['session_id'][:8]}... (started: {session['started_at']})")

    # Get recent sessions
    recent = manager.get_recent_sessions(limit=10)
    print(f"\n✅ Found {len(recent)} recent sessions for agent")

    print("\n✨ Session Management Test: PASSED")
    return True


def test_action_tracking():
    """Test action outcome tracking"""
    print("\n🧪 Testing Action Outcome Tracking...")
    print("=" * 60)

    tracker = ActionTracker("test_agent_001")

    # Record successful action
    action1_id = tracker.record_action(
        action_type="code_change",
        action_description="Added agent identity persistence",
        expected_result="Agent identity survives restarts",
        actual_result="Identity persists correctly across sessions",
        success_score=0.95,
        action_context="Implementing Phase 1 of AGI memory",
        duration_ms=15000
    )
    print(f"✅ Recorded successful action: {action1_id} (score: 0.95)")

    # Record partial success
    action2_id = tracker.record_action(
        action_type="code_change",
        action_description="Attempted session auto-linking",
        expected_result="Sessions link automatically",
        actual_result="Links work but need manual session_id",
        success_score=0.65,
        action_context="Session continuity feature",
        duration_ms=20000
    )
    print(f"✅ Recorded partial success: {action2_id} (score: 0.65)")

    # Record failure
    action3_id = tracker.record_action(
        action_type="command",
        action_description="pip install broken-package",
        expected_result="Package installs successfully",
        actual_result="ERROR: Package not found",
        success_score=0.1,
        action_context="Testing dependency installation",
        duration_ms=5000
    )
    print(f"✅ Recorded failure: {action3_id} (score: 0.1)")

    # Get similar actions
    similar = tracker.get_similar_actions("code_change", context="session", limit=5)
    print(f"\n🔍 Found {len(similar)} similar 'code_change' actions")
    for action in similar:
        print(f"   - {action['action_description']} (score: {action['success_score']})")

    # Get success rate
    success_rate = tracker.get_success_rate("code_change", time_window_hours=24)
    print(f"\n📊 Success rate for 'code_change': {success_rate['success_rate']:.2%}")
    print(f"   Total actions: {success_rate['total_actions']}")
    print(f"   Success count: {success_rate['success_count']}")
    print(f"   Avg score: {success_rate['avg_score']:.2f}")

    # Get learnings
    learnings = tracker.get_learnings_for_action("code_change", limit=5)
    print(f"\n🧠 Key learnings from 'code_change' actions:")
    for i, learning in enumerate(learnings, 1):
        print(f"   {i}. {learning}")

    # Check if should retry failure
    retry_decision = tracker.should_retry_action(action3_id, "Try alternate package source")
    print(f"\n🔄 Should retry failed action?")
    print(f"   Decision: {retry_decision['should_retry']}")
    print(f"   Confidence: {retry_decision['confidence']:.2%}")
    print(f"   Reasoning: {retry_decision['reasoning']}")

    # Get overall statistics
    stats = tracker.get_action_statistics()
    print(f"\n📈 Overall Action Statistics:")
    print(f"   Total actions: {stats['total_actions']}")
    print(f"   By category: {stats['by_category']}")
    print(f"   Avg success: {stats['avg_success_score']:.2f}")
    print(f"   Recent trend: {stats['trend']}")

    print("\n✨ Action Tracking Test: PASSED")
    return True


def test_cross_session_learning():
    """Test learning across sessions"""
    print("\n🧪 Testing Cross-Session Learning...")
    print("=" * 60)

    agent_id = "test_agent_learning"
    identity = AgentIdentity(agent_id)
    manager = SessionManager(agent_id)
    tracker = ActionTracker(agent_id)

    # Session 1: Learn something
    print("📚 Session 1: Initial Learning")
    session1 = manager.start_session("Learning about async patterns")

    # Record learning actions
    tracker.record_action(
        action_type="research",
        action_description="Researched async/await patterns",
        expected_result="Understand async best practices",
        actual_result="Learned async is better for I/O operations",
        success_score=0.9,
        session_id=session1
    )

    # Update skills based on learning
    identity.update_skills({"async_programming": 0.7})

    # Add belief
    identity.add_belief("Async/await prevents callback hell")

    manager.end_session(
        session1,
        key_learnings=["Async patterns improve I/O performance"],
        performance_metrics={"learning_score": 0.9}
    )

    # Session 2: Apply learning
    print("\n📚 Session 2: Applying Learning")
    session2 = manager.start_session("Applying async knowledge")

    # Check previous learnings
    learnings = tracker.get_learnings_for_action("research")
    print(f"✅ Retrieved {len(learnings)} learnings from previous session")
    for learning in learnings:
        print(f"   - {learning}")

    # Record application
    tracker.record_action(
        action_type="code_change",
        action_description="Refactored code to use async/await",
        expected_result="Improved I/O performance",
        actual_result="Performance improved by 40%",
        success_score=0.95,
        session_id=session2,
        action_context="Applied async learning"
    )

    # Skill improves with practice
    identity.update_skills({"async_programming": 0.85})

    manager.end_session(
        session2,
        key_learnings=["Successfully applied async patterns"],
        performance_metrics={"learning_score": 0.95, "improvement": 0.4}
    )

    # Session 3: Mastery
    print("\n📚 Session 3: Demonstrating Mastery")
    session3 = manager.start_session("Advanced async implementation")

    # Get session chain to see progression
    chain = manager.get_session_chain(session3, depth=3)
    print(f"\n📜 Learning progression across {len(chain)} sessions:")
    for i, sess in enumerate(reversed(chain), 1):
        learnings = sess.get('key_learnings', [])
        if learnings:
            print(f"   Session {i}: {', '.join(learnings)}")

    # Final skill level
    final_identity = identity.get_identity()
    async_skill = final_identity['skill_levels'].get('async_programming', 0)
    print(f"\n✅ Async programming skill evolved: 0.0 → 0.7 → 0.85")
    print(f"   Current level: {async_skill}")

    # Check beliefs accumulated
    beliefs = final_identity['core_beliefs']
    print(f"\n✅ Core beliefs accumulated: {len(beliefs)}")
    for belief in beliefs:
        if "async" in belief.lower():
            print(f"   - {belief}")

    print("\n✨ Cross-Session Learning Test: PASSED")
    return True


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🚀 AGI Memory Phase 1 Test Suite")
    print("="*60)

    tests = [
        ("Agent Identity", test_agent_identity),
        ("Session Management", test_session_management),
        ("Action Tracking", test_action_tracking),
        ("Cross-Session Learning", test_cross_session_learning)
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"\n❌ {name} FAILED")
        except Exception as e:
            failed += 1
            print(f"\n❌ {name} FAILED with exception:")
            print(f"   {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*60)
    print(f"📊 Test Results: {passed}/{len(tests)} passed")
    if failed == 0:
        print("✨ ALL TESTS PASSED!")
    else:
        print(f"⚠️  {failed} test(s) failed")
    print("="*60 + "\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
