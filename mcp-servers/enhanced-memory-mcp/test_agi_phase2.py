#!/usr/bin/env python3
"""
AGI Memory Phase 2 Test Suite

Tests temporal reasoning and consolidation capabilities:
- Causal link creation and traversal
- Temporal chain management
- Outcome prediction
- Pattern extraction consolidation
- Causal discovery consolidation
- Memory compression
- Full consolidation workflow

Run: python3 test_agi_phase2.py
"""

import sys
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from agi.temporal_reasoning import TemporalReasoning
from agi.consolidation import ConsolidationEngine

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

def setup_test_data():
    """Create test entities for temporal reasoning tests"""
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()

    # Create test entities
    test_entities = [
        ("test_action_deploy", "action", "working"),
        ("test_outcome_success", "outcome", "episodic"),
        ("test_context_production", "context", "semantic"),
        ("test_action_backup", "action", "working"),
        ("test_outcome_partial", "outcome", "episodic"),
        ("test_action_optimize", "action", "working"),
        ("test_outcome_failure", "outcome", "episodic"),
    ]

    entity_ids = {}
    for name, entity_type, tier in test_entities:
        cursor.execute(
            'INSERT INTO entities (name, entity_type, tier) VALUES (?, ?, ?)',
            (name, entity_type, tier)
        )
        entity_ids[name] = cursor.lastrowid

    conn.commit()
    conn.close()

    return entity_ids

def cleanup_test_data(entity_ids):
    """Remove test entities and related data"""
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()

    # Delete causal links
    cursor.execute('DELETE FROM causal_links WHERE cause_entity_id IN ({})'.format(
        ','.join('?' * len(entity_ids))
    ), list(entity_ids.values()))

    # Delete temporal chains
    cursor.execute('DELETE FROM temporal_chains WHERE chain_id LIKE "test_%"')

    # Delete consolidation jobs
    cursor.execute('DELETE FROM consolidation_jobs WHERE job_id >= 1000')

    # Delete test entities
    cursor.execute('DELETE FROM entities WHERE id IN ({})'.format(
        ','.join('?' * len(entity_ids))
    ), list(entity_ids.values()))

    conn.commit()
    conn.close()

def test_causal_link_creation(entity_ids):
    """Test 1: Causal Link Creation and Retrieval"""
    print_test_header("Causal Link Creation and Retrieval")

    temporal = TemporalReasoning()

    try:
        # Create a causal link: deploy action → success outcome
        link_id = temporal.create_causal_link(
            cause_entity_id=entity_ids["test_action_deploy"],
            effect_entity_id=entity_ids["test_outcome_success"],
            relationship_type="direct",
            strength=0.85,
            typical_delay_seconds=300,
            context_conditions={"environment": "production"}
        )

        print_success(f"Created causal link: {link_id}")
        print_info(f"  Link: {entity_ids['test_action_deploy']} → {entity_ids['test_outcome_success']}")
        print_info(f"  Strength: 0.85, Type: direct, Delay: 300s")

        # Verify link exists
        conn = sqlite3.connect(TEST_DB)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM causal_links WHERE link_id = ?', (link_id,))
        link = cursor.fetchone()
        conn.close()

        if link:
            print_success(f"Link verified in database")
            return True
        else:
            print_error("Link not found in database")
            return False

    except Exception as e:
        print_error(f"Failed: {e}")
        return False

def test_causal_chain_traversal(entity_ids):
    """Test 2: Causal Chain Traversal"""
    print_test_header("Causal Chain Traversal")

    temporal = TemporalReasoning()

    try:
        # Create a chain: context → action → outcome
        link1 = temporal.create_causal_link(
            cause_entity_id=entity_ids["test_context_production"],
            effect_entity_id=entity_ids["test_action_deploy"],
            relationship_type="contributory",
            strength=0.7
        )

        link2 = temporal.create_causal_link(
            cause_entity_id=entity_ids["test_action_deploy"],
            effect_entity_id=entity_ids["test_outcome_success"],
            relationship_type="direct",
            strength=0.85
        )

        print_success(f"Created causal chain: context → action → outcome")

        # Traverse forward from context
        forward_chain = temporal.get_causal_chain(
            entity_id=entity_ids["test_context_production"],
            direction="forward",
            depth=3,
            min_strength=0.5
        )

        print_info(f"Forward chain from context: {len(forward_chain)} links found")
        for item in forward_chain:
            print_info(f"  Level {item['level']}: Entity {item['entity_id']} "
                      f"(strength: {item['link']['strength']:.2f})")

        # Traverse backward from outcome
        backward_chain = temporal.get_causal_chain(
            entity_id=entity_ids["test_outcome_success"],
            direction="backward",
            depth=3,
            min_strength=0.5
        )

        print_info(f"Backward chain from outcome: {len(backward_chain)} links found")
        for item in backward_chain:
            print_info(f"  Level {item['level']}: Entity {item['entity_id']} "
                      f"(strength: {item['link']['strength']:.2f})")

        if len(forward_chain) > 0 and len(backward_chain) > 0:
            print_success("Causal chain traversal working correctly")
            return True
        else:
            print_error("Causal chain traversal incomplete")
            return False

    except Exception as e:
        print_error(f"Failed: {e}")
        return False

def test_outcome_prediction(entity_ids):
    """Test 3: Outcome Prediction Based on Causal History"""
    print_test_header("Outcome Prediction")

    temporal = TemporalReasoning()

    try:
        # Create multiple causal links for prediction
        # Deploy action → success (high strength)
        temporal.create_causal_link(
            entity_ids["test_action_deploy"],
            entity_ids["test_outcome_success"],
            "direct", 0.85
        )

        # Deploy action → partial (medium strength)
        temporal.create_causal_link(
            entity_ids["test_action_deploy"],
            entity_ids["test_outcome_partial"],
            "direct", 0.4
        )

        # Update evidence count by recreating links
        for _ in range(5):
            temporal.create_causal_link(
                entity_ids["test_action_deploy"],
                entity_ids["test_outcome_success"],
                "direct", 0.85
            )

        print_success("Created causal history for prediction")

        # Predict outcomes of deploy action
        prediction = temporal.predict_outcome(
            action_entity_id=entity_ids["test_action_deploy"],
            context={"environment": "production"}
        )

        print_info(f"Prediction confidence: {prediction['confidence']:.2f}")
        print_info(f"Similar cases: {prediction['similar_cases']}")
        print_info(f"Reasoning: {prediction['reasoning']}")

        if prediction['likely_outcomes']:
            print_success(f"Found {len(prediction['likely_outcomes'])} likely outcomes:")
            for outcome in prediction['likely_outcomes']:
                print_info(f"  - Entity {outcome['entity_id']}: "
                          f"{outcome['probability']:.2%} probability "
                          f"({outcome['relationship_type']})")
            return True
        else:
            print_error("No outcomes predicted")
            return False

    except Exception as e:
        print_error(f"Failed: {e}")
        return False

def test_temporal_chain_management(entity_ids):
    """Test 4: Temporal Chain Management"""
    print_test_header("Temporal Chain Management")

    temporal = TemporalReasoning()

    try:
        # Create temporal chain
        entity_sequence = [
            entity_ids["test_context_production"],
            entity_ids["test_action_deploy"],
            entity_ids["test_outcome_success"]
        ]

        chain_id = temporal.create_temporal_chain(
            entity_ids=entity_sequence,
            chain_type="causal",
            chain_name="test_deployment_workflow",
            description="Test deployment workflow chain",
            confidence=0.8
        )

        print_success(f"Created temporal chain: {chain_id}")
        print_info(f"  Type: causal, Entities: {len(entity_sequence)}")

        # Retrieve chain
        chain = temporal.get_temporal_chain(chain_id)

        if chain:
            print_success("Retrieved temporal chain successfully")
            print_info(f"  Chain type: {chain['chain_type']}")
            print_info(f"  Confidence: {chain['confidence']}")
            print_info(f"  Entities: {chain['entities']}")
            return True
        else:
            print_error("Failed to retrieve temporal chain")
            return False

    except Exception as e:
        print_error(f"Failed: {e}")
        return False

def test_pattern_extraction(entity_ids):
    """Test 5: Pattern Extraction Consolidation"""
    print_test_header("Pattern Extraction Consolidation")

    consolidation = ConsolidationEngine()

    try:
        # Create multiple episodic memories of same type for pattern detection
        conn = sqlite3.connect(TEST_DB)
        cursor = conn.cursor()

        pattern_entities = []
        for i in range(5):
            cursor.execute(
                'INSERT INTO entities (name, entity_type, tier) VALUES (?, ?, ?)',
                (f"test_pattern_deploy_{i}", "deployment_pattern", "episodic")
            )
            pattern_entities.append(cursor.lastrowid)

        conn.commit()
        conn.close()

        print_success(f"Created {len(pattern_entities)} episodic memories for pattern detection")

        # Run pattern extraction
        results = consolidation.run_pattern_extraction(
            time_window_hours=24,
            min_pattern_frequency=3
        )

        print_info(f"Job ID: {results['job_id']}")
        print_info(f"Patterns found: {results['patterns_found']}")
        print_info(f"Patterns promoted: {results['patterns_promoted']}")
        print_info(f"Semantic memories created: {results['semantic_memories_created']}")

        # Cleanup pattern test entities
        conn = sqlite3.connect(TEST_DB)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM entities WHERE id IN ({})'.format(
            ','.join('?' * len(pattern_entities))
        ), pattern_entities)
        conn.commit()
        conn.close()

        if results['patterns_found'] > 0:
            print_success("Pattern extraction working correctly")
            return True
        else:
            print_error("No patterns found (expected at least 1)")
            return False

    except Exception as e:
        print_error(f"Failed: {e}")
        return False

def test_causal_discovery(entity_ids):
    """Test 6: Causal Discovery Consolidation"""
    print_test_header("Causal Discovery Consolidation")

    consolidation = ConsolidationEngine()

    try:
        # Create action outcomes for causal discovery
        conn = sqlite3.connect(TEST_DB)
        cursor = conn.cursor()

        now = datetime.now()

        # Create successful action outcome
        cursor.execute(
            '''
            INSERT INTO action_outcomes (
                action_type, action_description,
                entity_id, expected_result, actual_result,
                success_score, outcome_category,
                executed_at, action_context
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                "deploy", "Test deployment action",
                entity_ids["test_action_deploy"],
                "success", "success",
                0.9, "success",
                now.isoformat(),
                json.dumps({"context_id": entity_ids["test_context_production"]})
            )
        )

        conn.commit()
        conn.close()

        print_success("Created action outcomes for causal discovery")

        # Run causal discovery
        results = consolidation.run_causal_discovery(
            time_window_hours=24,
            min_confidence=0.6
        )

        print_info(f"Job ID: {results['job_id']}")
        print_info(f"Chains created: {results['chains_created']}")
        print_info(f"Links created: {results['links_created']}")

        if results['job_id']:
            print_success("Causal discovery completed successfully")
            return True
        else:
            print_error("Causal discovery failed")
            return False

    except Exception as e:
        print_error(f"Failed: {e}")
        return False

def test_full_consolidation():
    """Test 7: Full Consolidation Workflow"""
    print_test_header("Full Consolidation Workflow")

    consolidation = ConsolidationEngine()

    try:
        # Run full consolidation (pattern extraction + causal discovery + compression)
        results = consolidation.run_full_consolidation(
            time_window_hours=24
        )

        print_info("Full consolidation results:")

        if "pattern_extraction" in results:
            pe = results["pattern_extraction"]
            if "error" in pe:
                print_error(f"  Pattern extraction: {pe['error']}")
            else:
                print_success(f"  Pattern extraction: {pe.get('patterns_found', 0)} patterns")

        if "causal_discovery" in results:
            cd = results["causal_discovery"]
            if "error" in cd:
                print_error(f"  Causal discovery: {cd['error']}")
            else:
                print_success(f"  Causal discovery: {cd.get('links_created', 0)} links")

        if "memory_compression" in results:
            mc = results["memory_compression"]
            if "error" in mc:
                print_error(f"  Memory compression: {mc['error']}")
            else:
                print_success(f"  Memory compression: {mc.get('memories_compressed', 0)} memories")

        # Check consolidation stats
        stats = consolidation.get_consolidation_stats()
        print_info(f"\nConsolidation Statistics:")
        print_info(f"  Total jobs: {stats['total_jobs']}")
        print_info(f"  Status breakdown: {stats['by_status']}")
        print_info(f"  Totals: {stats['totals']}")

        if stats['total_jobs'] > 0:
            print_success("Full consolidation workflow working correctly")
            return True
        else:
            print_error("No consolidation jobs found")
            return False

    except Exception as e:
        print_error(f"Failed: {e}")
        return False

def main():
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}AGI MEMORY PHASE 2 TEST SUITE{Colors.END}")
    print(f"{Colors.BLUE}Testing: Temporal Reasoning & Consolidation{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")

    # Setup
    print_info(f"Database: {TEST_DB}")
    print_info("Setting up test data...")
    entity_ids = setup_test_data()
    print_success(f"Created {len(entity_ids)} test entities\n")

    # Run tests
    results = {
        "Causal Link Creation": test_causal_link_creation(entity_ids),
        "Causal Chain Traversal": test_causal_chain_traversal(entity_ids),
        "Outcome Prediction": test_outcome_prediction(entity_ids),
        "Temporal Chain Management": test_temporal_chain_management(entity_ids),
        "Pattern Extraction": test_pattern_extraction(entity_ids),
        "Causal Discovery": test_causal_discovery(entity_ids),
        "Full Consolidation": test_full_consolidation(),
    }

    # Cleanup
    print_info("\nCleaning up test data...")
    cleanup_test_data(entity_ids)
    print_success("Cleanup complete")

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
        print(f"{Colors.GREEN}🎉 ALL TESTS PASSED! Phase 2 is ready for production.{Colors.END}")
        print(f"{Colors.GREEN}{'='*60}{Colors.END}\n")
        return 0
    else:
        print(f"\n{Colors.RED}{'='*60}{Colors.END}")
        print(f"{Colors.RED}⚠️  Some tests failed. Review output above.{Colors.END}")
        print(f"{Colors.RED}{'='*60}{Colors.END}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
