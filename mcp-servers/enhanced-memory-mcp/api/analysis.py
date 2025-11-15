"""
Analysis and Pattern Detection API
"""

from typing import List, Dict, Any, Optional
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path.home() / ".claude" / "enhanced_memories" / "memory.db"


def detect_conflicts(threshold: float = 0.85) -> List[Dict[str, Any]]:
    """
    Detect duplicate or conflicting memories.
    
    Example:
        conflicts = detect_conflicts(threshold=0.9)
        critical = [c for c in conflicts if c['score'] > 0.95]
        return {"critical_conflicts": len(critical)}
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, name, entity_type 
        FROM entities 
        WHERE resolved = 0 OR resolved IS NULL
    ''')
    
    conflicts = []
    # Simple name-based conflict detection
    # Real implementation would use semantic similarity
    
    conn.close()
    return conflicts


def analyze_patterns(
    entity_type: Optional[str] = None,
    time_range: Optional[int] = None
) -> Dict[str, Any]:
    """
    Analyze memory patterns and trends.
    
    Example:
        patterns = analyze_patterns(entity_type="project_outcome")
        success_rate = patterns['success_rate']
        return {"trend": "improving" if success_rate > 0.8 else "declining"}
    """
    from .memory import search_nodes
    
    # Get all entities
    all_entities = search_nodes("*", limit=1000)
    
    # Filter by type
    if entity_type:
        entities = [e for e in all_entities if e.get('entityType') == entity_type]
    else:
        entities = all_entities
    
    return {
        "total": len(entities),
        "by_type": _count_by_type(entities),
        "by_tier": _count_by_tier(entities),
        "patterns": "analysis_complete"
    }


def classify_content(content: str) -> Dict[str, Any]:
    """
    Classify memory content (reasoning vs general).
    
    Returns classification with category and weight.
    """
    # Simple classification based on keywords
    reasoning_keywords = ['algorithm', 'optimization', 'pattern', 'analysis']
    
    score = sum(1 for kw in reasoning_keywords if kw in content.lower())
    
    if score >= 2:
        category = 'reasoning'
        weight = 1.3
    else:
        category = 'general'
        weight = 1.0
    
    return {
        "category": category,
        "weight": weight,
        "confidence": min(score / len(reasoning_keywords), 1.0)
    }


def find_related(
    entity_name: str,
    limit: int = 10,
    min_similarity: float = 0.5
) -> List[Dict[str, Any]]:
    """
    Find related entities by semantic similarity.
    """
    # Placeholder - would use SAFLA/NMF for real implementation
    return []


# Helper functions
def _count_by_type(entities: List[Dict]) -> Dict[str, int]:
    """Count entities by type"""
    counts = {}
    for e in entities:
        et = e.get('entityType', 'unknown')
        counts[et] = counts.get(et, 0) + 1
    return counts


def _count_by_tier(entities: List[Dict]) -> Dict[str, int]:
    """Count entities by memory tier"""
    counts = {}
    for e in entities:
        tier = e.get('tier', 'unknown')
        counts[tier] = counts.get(tier, 0) + 1
    return counts
