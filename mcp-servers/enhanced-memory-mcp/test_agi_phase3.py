#!/usr/bin/env python3
"""
AGI Memory Phase 3 Test Suite

Tests emotional tagging and associative network capabilities:
- Emotional tagging and valence
- Salience scoring
- Associative link creation
- Activation spreading
- Attention mechanisms
- Forgetting curves

Run: python3 test_agi_phase3.py
"""

import sys
import sqlite3
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from agi.emotional_memory import EmotionalMemory
from agi.associative_network import AssociativeNetwork, AttentionMechanism, ForgettingCurve

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

def setup_test_entities():
    """Create test entities"""
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()

    test_entities = [
        ("test_happy_memory", "memory", "episodic"),
        ("test_sad_memory", "memory", "episodic"),
        ("test_important_fact", "fact", "semantic"),
        ("test_procedure", "procedure", "procedural"),
        ("test_related_memory", "memory", "episodic"),
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
    """Remove test data"""
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()

    # Delete all Phase 3 data for test entities
    for entity_id in entity_ids.values():
        cursor.execute('DELETE FROM emotional_tags WHERE entity_id = ?', (entity_id,))
        cursor.execute('DELETE FROM attention_weights WHERE entity_id = ?', (entity_id,))
        cursor.execute('DELETE FROM forgetting_curves WHERE entity_id = ?', (entity_id,))

    cursor.execute('DELETE FROM memory_associations WHERE entity_a_id IN ({})'.format(
        ','.join('?' * len(entity_ids))
    ), list(entity_ids.values()))

    cursor.execute('DELETE FROM entities WHERE id IN ({})'.format(
        ','.join('?' * len(entity_ids))
    ), list(entity_ids.values()))

    conn.commit()
    conn.close()

def test_emotional_tagging(entity_ids):
    """Test 1: Emotional Tagging"""
    print_test_header("Emotional Tagging")

    emotional = EmotionalMemory()

    try:
        # Tag happy memory
        tag_id = emotional.tag_entity(
            entity_id=entity_ids["test_happy_memory"],
            valence=0.8,  # Positive
            arousal=0.6,  # Moderately excited
            primary_emotion="joy",
            salience_score=0.9  # Very important
        )

        print_success(f"Tagged happy memory: valence=0.8, arousal=0.6, salience=0.9")

        # Tag sad memory
        emotional.tag_entity(
            entity_id=entity_ids["test_sad_memory"],
            valence=-0.7,  # Negative
            arousal=0.4,  # Low arousal
            primary_emotion="sadness",
            salience_score=0.5
        )

        print_success(f"Tagged sad memory: valence=-0.7, arousal=0.4, salience=0.5")

        # Retrieve and verify
        tag = emotional.get_emotional_tag(entity_ids["test_happy_memory"])
        if tag and tag['valence'] == 0.8:
            print_success("Retrieved emotional tag correctly")
            return True
        else:
            print_error("Failed to retrieve emotional tag")
            return False

    except Exception as e:
        print_error(f"Failed: {e}")
        return False

def test_emotion_search(entity_ids):
    """Test 2: Search by Emotion"""
    print_test_header("Search by Emotion")

    emotional = EmotionalMemory()

    try:
        # Search for positive memories
        results = emotional.search_by_emotion({
            "valence_min": 0.5,
            "min_salience": 0.7
        }, limit=10)

        print_info(f"Found {len(results)} positive high-salience memories")

        if len(results) > 0:
            print_success("Emotional search working")
            for result in results[:3]:
                print_info(f"  - {result.get('name')}: valence={result.get('valence'):.2f}, "
                          f"salience={result.get('salience_score'):.2f}")
            return True
        else:
            print_error("No results found")
            return False

    except Exception as e:
        print_error(f"Failed: {e}")
        return False

def test_associative_links(entity_ids):
    """Test 3: Associative Link Creation"""
    print_test_header("Associative Link Creation")

    network = AssociativeNetwork()

    try:
        # Create semantic association
        assoc_id = network.create_association(
            entity_a_id=entity_ids["test_happy_memory"],
            entity_b_id=entity_ids["test_related_memory"],
            association_type="semantic",
            association_strength=0.8
        )

        print_success(f"Created semantic association: {assoc_id}, strength=0.8")

        # Create emotional association
        network.create_association(
            entity_a_id=entity_ids["test_happy_memory"],
            entity_b_id=entity_ids["test_important_fact"],
            association_type="emotional",
            association_strength=0.6
        )

        print_success("Created emotional association: strength=0.6")

        # Get associations
        associations = network.get_associations(
            entity_id=entity_ids["test_happy_memory"],
            min_strength=0.5
        )

        print_info(f"Found {len(associations)} associations")

        if len(associations) >= 2:
            print_success("Association retrieval working")
            return True
        else:
            print_error("Expected at least 2 associations")
            return False

    except Exception as e:
        print_error(f"Failed: {e}")
        return False

def test_activation_spreading(entity_ids):
    """Test 4: Activation Spreading"""
    print_test_header("Activation Spreading")

    network = AssociativeNetwork()

    try:
        # Spread activation from happy memory
        activated = network.spread_activation(
            source_entity_id=entity_ids["test_happy_memory"],
            initial_activation=1.0,
            max_hops=2,
            activation_threshold=0.2
        )

        print_info(f"Activated {len(activated)} entities")

        if len(activated) > 0:
            print_success("Activation spreading working")
            for item in activated[:3]:
                print_info(f"  - Entity {item['entity_id']}: "
                          f"activation={item['activation_level']:.3f}")
            return True
        else:
            print_error("No entities activated")
            return False

    except Exception as e:
        print_error(f"Failed: {e}")
        return False

def test_attention_mechanism(entity_ids):
    """Test 5: Attention Mechanism"""
    print_test_header("Attention Mechanism")

    attention = AttentionMechanism()

    try:
        # Set attention on important fact
        attention.set_attention(
            entity_id=entity_ids["test_important_fact"],
            relevance_score=0.9,
            emotional_weight=0.5
        )

        print_success("Set attention: relevance=0.9")

        # Get attended memories
        attended = attention.get_attended_memories(threshold=0.2, limit=10)

        print_info(f"Found {len(attended)} attended memories")

        if len(attended) > 0:
            print_success("Attention mechanism working")
            return True
        else:
            print_error("No attended memories found")
            return False

    except Exception as e:
        print_error(f"Failed: {e}")
        return False

def test_forgetting_curve(entity_ids):
    """Test 6: Forgetting Curve"""
    print_test_header("Forgetting Curve")

    forgetting = ForgettingCurve()

    try:
        # Initialize curve
        forgetting.initialize_curve(
            entity_id=entity_ids["test_procedure"],
            initial_strength=1.0,
            decay_constant=0.5
        )

        print_success("Initialized forgetting curve: strength=1.0, decay=0.5")

        # Apply forgetting (24 hours)
        new_strength = forgetting.apply_forgetting(
            entity_id=entity_ids["test_procedure"],
            time_elapsed_hours=24
        )

        print_info(f"After 24 hours: strength={new_strength:.3f}")

        if 0.0 < new_strength < 1.0:
            print_success("Forgetting curve working (strength decayed)")
            return True
        else:
            print_error(f"Unexpected strength: {new_strength}")
            return False

    except Exception as e:
        print_error(f"Failed: {e}")
        return False

def main():
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}AGI MEMORY PHASE 3 TEST SUITE{Colors.END}")
    print(f"{Colors.BLUE}Testing: Emotional Tagging & Associative Networks{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")

    # Setup
    print_info(f"Database: {TEST_DB}")
    print_info("Setting up test data...")
    entity_ids = setup_test_entities()
    print_success(f"Created {len(entity_ids)} test entities\n")

    # Run tests
    results = {
        "Emotional Tagging": test_emotional_tagging(entity_ids),
        "Search by Emotion": test_emotion_search(entity_ids),
        "Associative Links": test_associative_links(entity_ids),
        "Activation Spreading": test_activation_spreading(entity_ids),
        "Attention Mechanism": test_attention_mechanism(entity_ids),
        "Forgetting Curve": test_forgetting_curve(entity_ids),
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
        print(f"{Colors.GREEN}🎉 ALL TESTS PASSED! Phase 3 is ready for production.{Colors.END}")
        print(f"{Colors.GREEN}{'='*60}{Colors.END}\n")
        return 0
    else:
        print(f"\n{Colors.RED}{'='*60}{Colors.END}")
        print(f"{Colors.RED}⚠️  Some tests failed. Review output above.{Colors.END}")
        print(f"{Colors.RED}{'='*60}{Colors.END}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
