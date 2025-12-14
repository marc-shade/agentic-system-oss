#!/usr/bin/env python3
"""
Build Initial Knowledge Graph from Enhanced Memory

Strategies:
1. Co-occurrence: Entities mentioned together in observations
2. Type-based: Entities of similar types relate
3. Temporal: Entities created near same time
4. Semantic: Shared keywords/topics
"""

import sqlite3
from pathlib import Path
from collections import defaultdict
import re
from typing import List, Dict, Set, Tuple
import json


def get_connection():
    db_path = Path.home() / ".claude" / "enhanced_memories" / "memory.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def extract_keywords(text: str) -> Set[str]:
    """Extract significant keywords from text"""
    # Remove common words
    stopwords = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that',
        'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
    }

    # Extract words
    words = re.findall(r'\b[a-z]{3,}\b', text.lower())

    # Filter stopwords and return significant terms
    keywords = {w for w in words if w not in stopwords}

    return keywords


def build_co_occurrence_relationships(min_shared_keywords: int = 3) -> int:
    """
    Build relationships based on shared keywords in observations

    If two entities share many keywords, they're likely related
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Get all entities with their observation content
    cursor.execute('''
        SELECT
            e.id,
            e.name,
            e.entity_type,
            GROUP_CONCAT(o.content, ' ') as all_content
        FROM entities e
        JOIN observations o ON e.id = o.entity_id
        GROUP BY e.id
    ''')

    entities = cursor.fetchall()
    print(f"Processing {len(entities)} entities for co-occurrence...")

    # Build keyword index
    entity_keywords = {}
    for entity in entities:
        keywords = extract_keywords(entity['all_content'])
        entity_keywords[entity['id']] = {
            'keywords': keywords,
            'name': entity['name'],
            'type': entity['entity_type']
        }

    # Find pairs with significant overlap
    relationships = []
    processed = set()

    for id1, data1 in entity_keywords.items():
        for id2, data2 in entity_keywords.items():
            if id1 >= id2:  # Skip self and duplicates
                continue

            pair_key = tuple(sorted([id1, id2]))
            if pair_key in processed:
                continue

            processed.add(pair_key)

            # Calculate keyword overlap
            shared = data1['keywords'] & data2['keywords']

            if len(shared) >= min_shared_keywords:
                # Determine relationship type based on entity types
                if data1['type'] == data2['type']:
                    rel_type = 'relates_to'
                elif 'skill' in data1['type'] or 'skill' in data2['type']:
                    rel_type = 'uses'
                elif 'system' in data1['type'] or 'system' in data2['type']:
                    rel_type = 'part_of'
                else:
                    rel_type = 'relates_to'

                # Weight by overlap strength
                weight = min(1.0, len(shared) / 10.0)

                relationships.append({
                    'from_id': id1,
                    'to_id': id2,
                    'rel_type': rel_type,
                    'weight': weight,
                    'shared_keywords': list(shared)[:10]  # Store sample
                })

    # Insert relationships
    for rel in relationships:
        cursor.execute('''
            INSERT OR IGNORE INTO relations
            (from_entity_id, to_entity_id, relation_type, weight, context)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            rel['from_id'],
            rel['to_id'],
            rel['rel_type'],
            rel['weight'],
            json.dumps({'shared_keywords': rel['shared_keywords']})
        ))

    conn.commit()
    count = cursor.rowcount
    conn.close()

    print(f"Created {len(relationships)} relationships")
    return len(relationships)


def build_type_based_relationships() -> int:
    """
    Create relationships between entities of related types

    E.g., all 'skill' entities relate to each other, milestones depend on configurations
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Define type-based relationship rules
    type_rules = [
        # Skills use other skills
        ('skill', 'skill', 'uses', 0.3),

        # Milestones depend on configurations
        ('milestone', 'system_configuration', 'depends_on', 0.7),

        # Configurations are part of systems
        ('service_configuration', 'system_configuration', 'part_of', 0.6),

        # Services implement skills
        ('service_configuration', 'skill', 'implements', 0.5),
    ]

    count = 0
    for type1, type2, rel_type, weight in type_rules:
        # Get entities of each type
        cursor.execute('SELECT id FROM entities WHERE entity_type = ?', (type1,))
        entities1 = [row['id'] for row in cursor.fetchall()]

        cursor.execute('SELECT id FROM entities WHERE entity_type = ?', (type2,))
        entities2 = [row['id'] for row in cursor.fetchall()]

        # Create relationships
        for e1 in entities1[:20]:  # Limit to avoid explosion
            for e2 in entities2[:20]:
                if e1 != e2:
                    cursor.execute('''
                        INSERT OR IGNORE INTO relations
                        (from_entity_id, to_entity_id, relation_type, weight)
                        VALUES (?, ?, ?, ?)
                    ''', (e1, e2, rel_type, weight))
                    count += 1

    conn.commit()
    conn.close()

    print(f"Created {count} type-based relationships")
    return count


def build_temporal_relationships(time_window_hours: int = 24) -> int:
    """
    Create relationships between entities created near same time

    Entities created together are often related
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Get entities grouped by creation time
    cursor.execute('''
        SELECT
            e1.id as id1,
            e2.id as id2,
            e1.entity_type as type1,
            e2.entity_type as type2
        FROM entities e1
        JOIN entities e2 ON
            e1.id < e2.id
            AND ABS(strftime('%s', e1.created_at) - strftime('%s', e2.created_at)) <= ?
        WHERE e1.entity_type = e2.entity_type
        LIMIT 500
    ''', (time_window_hours * 3600,))

    pairs = cursor.fetchall()

    count = 0
    for pair in pairs:
        cursor.execute('''
            INSERT OR IGNORE INTO relations
            (from_entity_id, to_entity_id, relation_type, weight)
            VALUES (?, ?, ?, ?)
        ''', (pair['id1'], pair['id2'], 'relates_to', 0.4))
        count += 1

    conn.commit()
    conn.close()

    print(f"Created {count} temporal relationships")
    return count


def build_hierarchical_relationships() -> int:
    """
    Build hierarchical relationships based on naming patterns

    E.g., "system_x" contains "system_x_component_y"
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT id, name FROM entities')
    entities = {row['id']: row['name'] for row in cursor.fetchall()}

    count = 0
    for id1, name1 in entities.items():
        for id2, name2 in entities.items():
            if id1 == id2:
                continue

            # Check if name2 starts with name1 (hierarchical)
            name1_parts = name1.split('_')
            name2_parts = name2.split('_')

            # If name2 has more parts and shares prefix with name1
            if len(name2_parts) > len(name1_parts):
                if name2_parts[:len(name1_parts)] == name1_parts:
                    # name2 is a child of name1
                    cursor.execute('''
                        INSERT OR IGNORE INTO relations
                        (from_entity_id, to_entity_id, relation_type, weight)
                        VALUES (?, ?, ?, ?)
                    ''', (id1, id2, 'part_of', 0.8))
                    count += 1

    conn.commit()
    conn.close()

    print(f"Created {count} hierarchical relationships")
    return count


def main():
    print("=== Building Initial Knowledge Graph ===\n")

    stats = {
        'co_occurrence': 0,
        'type_based': 0,
        'temporal': 0,
        'hierarchical': 0
    }

    print("1. Building co-occurrence relationships...")
    stats['co_occurrence'] = build_co_occurrence_relationships(min_shared_keywords=2)

    print("\n2. Building type-based relationships...")
    stats['type_based'] = build_type_based_relationships()

    print("\n3. Building temporal relationships...")
    stats['temporal'] = build_temporal_relationships(time_window_hours=24)

    print("\n4. Building hierarchical relationships...")
    stats['hierarchical'] = build_hierarchical_relationships()

    total = sum(stats.values())

    print(f"\n=== Graph Building Complete ===")
    print(f"Total relationships created: {total}")
    print(f"  - Co-occurrence: {stats['co_occurrence']}")
    print(f"  - Type-based: {stats['type_based']}")
    print(f"  - Temporal: {stats['temporal']}")
    print(f"  - Hierarchical: {stats['hierarchical']}")


if __name__ == "__main__":
    main()
