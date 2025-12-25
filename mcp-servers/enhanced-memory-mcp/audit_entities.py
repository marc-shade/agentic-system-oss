#!/usr/bin/env python3
"""
Entity Audit Script for Stage 3 Hardening

Audits existing entities to identify:
1. Entities that may have gamed the 75/15 classifier (high keyword, low semantic)
2. Entities without proper provenance metadata
3. Entities with suspicious observation patterns

Part of AGI Stage 3 adversarial hardening.
"""

import sqlite3
import os
import sys
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reasoning_prioritizer import ReasoningPrioritizer, ContentCategory

DB_PATH = os.path.expanduser("~/.claude/enhanced_memories/memory.db")


@dataclass
class AuditResult:
    """Result of auditing a single entity."""
    entity_id: int
    entity_name: str
    entity_type: str
    observation_count: int
    avg_semantic_score: float
    avg_keyword_score: float
    classification: str
    suspicious: bool
    reason: str


def audit_entities():
    """Audit all entities for potential gaming or low quality."""

    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Initialize semantic classifier
    print("Loading semantic model...")
    prioritizer = ReasoningPrioritizer()
    print("Model loaded.\n")

    # Get all entities with their observations
    cursor.execute("""
        SELECT
            e.id, e.name, e.entity_type,
            o.id as obs_id, o.content
        FROM entities e
        LEFT JOIN observations o ON e.id = o.entity_id
        WHERE o.content IS NOT NULL AND o.content != ''
        ORDER BY e.id
    """)

    rows = cursor.fetchall()
    print(f"Found {len(rows)} entity-observation pairs to analyze.\n")

    # Group by entity
    entity_observations: Dict[int, Dict[str, Any]] = defaultdict(lambda: {
        "name": "",
        "type": "",
        "observations": []
    })

    for row in rows:
        entity_id, name, entity_type, obs_id, content = row
        entity_observations[entity_id]["name"] = name or f"entity_{entity_id}"
        entity_observations[entity_id]["type"] = entity_type or "unknown"
        entity_observations[entity_id]["observations"].append(content)

    print(f"Grouped into {len(entity_observations)} unique entities.\n")

    # Audit each entity
    results: List[AuditResult] = []
    suspicious_count = 0
    category_counts = defaultdict(int)

    print("Analyzing entities...")
    print("-" * 80)

    for entity_id, data in entity_observations.items():
        name = data["name"]
        entity_type = data["type"]
        observations = data["observations"]

        # Combine all observations for analysis
        combined_content = " ".join(observations[:5])  # Limit to first 5 for performance

        if len(combined_content) < 10:
            continue

        # Run through semantic classifier
        try:
            score = prioritizer.classify_content(combined_content)
        except Exception as e:
            print(f"  Error analyzing entity {entity_id}: {e}")
            continue

        category_counts[score.category.value] += 1

        # Detect suspicious patterns
        suspicious = False
        reason = ""

        # Pattern 1: High keyword score but low semantic score (keyword stuffing)
        if score.keyword_score > 0.6 and score.semantic_score < 0.4:
            suspicious = True
            reason = f"Keyword stuffing: keyword={score.keyword_score:.2f}, semantic={score.semantic_score:.2f}"

        # Pattern 2: Very high keyword score without proportional semantic backing
        if score.keyword_score > 0.8 and score.semantic_score < 0.5:
            suspicious = True
            reason = f"Extreme keyword gaming: keyword={score.keyword_score:.2f}, semantic={score.semantic_score:.2f}"

        # Pattern 3: Classified as REASONING but semantic score is borderline
        if score.category == ContentCategory.REASONING_CENTRIC and score.semantic_score < 0.5:
            suspicious = True
            reason = f"Low-confidence reasoning: semantic={score.semantic_score:.2f}"

        result = AuditResult(
            entity_id=entity_id,
            entity_name=name[:50],
            entity_type=entity_type,
            observation_count=len(observations),
            avg_semantic_score=score.semantic_score,
            avg_keyword_score=score.keyword_score,
            classification=score.category.value,
            suspicious=suspicious,
            reason=reason
        )
        results.append(result)

        if suspicious:
            suspicious_count += 1
            print(f"  ⚠️  SUSPICIOUS: {name[:40]} (ID: {entity_id})")
            print(f"      Type: {entity_type}, Reason: {reason}")

    conn.close()

    # Print summary
    print("\n" + "=" * 80)
    print("AUDIT SUMMARY")
    print("=" * 80)
    print(f"\nTotal entities analyzed: {len(results)}")
    print(f"Suspicious entities found: {suspicious_count}")
    print(f"\nCategory distribution:")
    for category, count in sorted(category_counts.items()):
        pct = (count / len(results) * 100) if results else 0
        print(f"  {category}: {count} ({pct:.1f}%)")

    # Calculate score distributions
    if results:
        semantic_scores = [r.avg_semantic_score for r in results]
        keyword_scores = [r.avg_keyword_score for r in results]

        print(f"\nSemantic score distribution:")
        print(f"  Min: {min(semantic_scores):.3f}")
        print(f"  Max: {max(semantic_scores):.3f}")
        print(f"  Avg: {sum(semantic_scores)/len(semantic_scores):.3f}")

        print(f"\nKeyword score distribution:")
        print(f"  Min: {min(keyword_scores):.3f}")
        print(f"  Max: {max(keyword_scores):.3f}")
        print(f"  Avg: {sum(keyword_scores)/len(keyword_scores):.3f}")

    # List all suspicious entities
    if suspicious_count > 0:
        print(f"\n" + "-" * 80)
        print("SUSPICIOUS ENTITIES (require review):")
        print("-" * 80)
        for r in results:
            if r.suspicious:
                print(f"\n  Entity ID: {r.entity_id}")
                print(f"  Name: {r.entity_name}")
                print(f"  Type: {r.entity_type}")
                print(f"  Observations: {r.observation_count}")
                print(f"  Keyword Score: {r.avg_keyword_score:.3f}")
                print(f"  Semantic Score: {r.avg_semantic_score:.3f}")
                print(f"  Classification: {r.classification}")
                print(f"  Reason: {r.reason}")
    else:
        print("\n✅ No suspicious entities detected. Memory integrity verified.")

    return results, suspicious_count


if __name__ == "__main__":
    audit_entities()
