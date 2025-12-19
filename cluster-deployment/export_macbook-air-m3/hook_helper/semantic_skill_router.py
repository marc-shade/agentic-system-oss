#!/usr/bin/env python3
"""
Semantic Skill Router
2 Acre Studios Agentic System Optimization - Phase 0

Implements vector-based semantic search to route user queries to most relevant Skills.
Uses sentence-transformers for embedding generation and SQLite for vector storage.

Author: Phoenix (Claude Code)
Date: October 18, 2025
"""

import sqlite3
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import json

# Lazy import sentence-transformers (only load when needed)
_model = None

def get_model():
    """Lazy load sentence transformer model."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer('all-MiniLM-L6-v2')
            print("[Skills Router] Loaded embedding model: all-MiniLM-L6-v2")
        except ImportError:
            print("[Skills Router] WARNING: sentence-transformers not installed")
            print("[Skills Router] Install with: pip install sentence-transformers")
            _model = None
    return _model


class SemanticSkillRouter:
    """
    Semantic Skill Router using vector similarity search.

    Routes user queries/task contexts to most relevant Skills using:
    1. Embedding generation (sentence-transformers)
    2. Vector similarity search (cosine similarity)
    3. Confidence scoring (similarity + keyword overlap)
    4. Threshold-based selection (high/medium/low confidence)
    """

    def __init__(self, skills_db_path: str = None):
        """
        Initialize the semantic skill router.

        Args:
            skills_db_path: Path to skills database. Defaults to ~/.claude/skills/skills.db
        """
        if skills_db_path is None:
            skills_db_path = str(Path.home() / ".claude" / "skills" / "skills.db")

        self.db_path = Path(skills_db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.cache = {}  # LRU cache for recently used skills
        self.cache_max_size = 10

        # Initialize database
        self._init_database()

        print(f"[Skills Router] Initialized with database: {self.db_path}")

    def _init_database(self):
        """Initialize SQLite database with vector storage."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                embedding BLOB NOT NULL,
                full_content TEXT NOT NULL,
                token_cost INTEGER NOT NULL,
                complexity TEXT DEFAULT 'medium',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP,
                use_count INTEGER DEFAULT 0
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_skills_category ON skills(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_skills_use_count ON skills(use_count DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_skills_complexity ON skills(complexity)")

        conn.commit()
        conn.close()

        print("[Skills Router] Database initialized")

    def index_skill(self, skill_id: str, name: str, category: str,
                   description: str, full_content: str, token_cost: int,
                   complexity: str = "medium"):
        """
        Index a skill in the vector database.

        Args:
            skill_id: Unique identifier for the skill
            name: Skill name
            category: Skill category (business, development, research, etc.)
            description: Short description (~50 tokens)
            full_content: Complete skill content (lazy-loaded)
            token_cost: Estimated token cost when fully loaded
            complexity: simple, medium, or complex
        """
        model = get_model()
        if model is None:
            print(f"[Skills Router] WARNING: Cannot index {name} - model not loaded")
            return

        # Generate embedding from description + key examples
        embedding_text = f"{description}\n\nCategory: {category}\nName: {name}"
        embedding = model.encode(embedding_text)
        embedding_blob = embedding.astype(np.float32).tobytes()

        # Store in database
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO skills
            (id, name, category, description, embedding, full_content, token_cost, complexity, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (skill_id, name, category, description, embedding_blob, full_content, token_cost, complexity))

        conn.commit()
        conn.close()

        print(f"[Skills Router] Indexed skill: {name} ({category}) - {token_cost} tokens")

    def route(self, query: str, top_k: int = 5,
             category_filter: Optional[str] = None) -> List[Dict]:
        """
        Route query to most relevant skills using semantic search.

        Args:
            query: User query or task context
            top_k: Number of top matches to consider
            category_filter: Optional category filter (business, development, etc.)

        Returns:
            List of skill dicts with {name, content, token_cost, confidence}
        """
        model = get_model()
        if model is None:
            print("[Skills Router] WARNING: Model not loaded, using fallback")
            return self._get_fallback_skills(top_k)

        # Check cache first
        cache_key = f"{query}:{top_k}:{category_filter}"
        if cache_key in self.cache:
            print(f"[Skills Router] Cache hit for query")
            return self.cache[cache_key]

        # Generate query embedding
        query_embedding = model.encode(query)

        # Search vector database
        matches = self._vector_search(query_embedding, top_k * 2, category_filter)

        if not matches:
            print("[Skills Router] No matches found, using fallback")
            return self._get_fallback_skills(top_k)

        # Score confidence
        scored_matches = self._score_confidence(matches, query)

        # Apply confidence thresholds
        selected_skills = self._select_by_confidence(scored_matches, top_k)

        # Update usage stats
        self._update_usage(selected_skills)

        # Update cache
        self._update_cache(cache_key, selected_skills)

        # Log selection
        print(f"[Skills Router] Loaded {len(selected_skills)} skills for query")
        for skill in selected_skills[:3]:  # Show top 3
            print(f"  - {skill['name']} (confidence: {skill['confidence']:.2f})")

        return selected_skills

    def _vector_search(self, query_embedding: np.ndarray, k: int,
                      category_filter: Optional[str] = None) -> List[Tuple]:
        """
        Perform cosine similarity search in vector database.

        Args:
            query_embedding: Query vector
            k: Number of results to return
            category_filter: Optional category filter

        Returns:
            List of (similarity, skill_id, name, content, tokens, category) tuples
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Build query with optional filter
        sql = "SELECT id, name, embedding, full_content, token_cost, category FROM skills"
        params = []

        if category_filter:
            sql += " WHERE category = ?"
            params.append(category_filter)

        cursor.execute(sql, params)
        skills = cursor.fetchall()

        if not skills:
            conn.close()
            return []

        # Calculate cosine similarity for all skills
        similarities = []
        for skill_id, name, embedding_blob, content, tokens, category in skills:
            skill_embedding = np.frombuffer(embedding_blob, dtype=np.float32)
            similarity = np.dot(query_embedding, skill_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(skill_embedding)
            )
            similarities.append((similarity, skill_id, name, content, tokens, category))

        # Sort by similarity and return top k
        similarities.sort(reverse=True, key=lambda x: x[0])
        conn.close()

        return similarities[:k]

    def _score_confidence(self, matches: List[Tuple], query: str) -> List[Dict]:
        """
        Score confidence based on similarity and keyword overlap.

        Args:
            matches: List of similarity search results
            query: Original query text

        Returns:
            List of scored skill dicts
        """
        scored = []
        query_keywords = set(query.lower().split())

        for similarity, skill_id, name, content, tokens, category in matches:
            # Check keyword overlap in description (first 200 chars)
            description = content[:200].lower()
            content_keywords = set(description.split())
            keyword_overlap = len(query_keywords & content_keywords) / max(len(query_keywords), 1)

            # Combined confidence score
            # 70% semantic similarity + 30% keyword overlap
            confidence = (similarity * 0.7) + (keyword_overlap * 0.3)

            scored.append({
                'id': skill_id,
                'name': name,
                'category': category,
                'content': content,
                'token_cost': tokens,
                'confidence': confidence,
                'similarity': similarity,
                'keyword_overlap': keyword_overlap
            })

        return sorted(scored, key=lambda x: x['confidence'], reverse=True)

    def _select_by_confidence(self, scored_matches: List[Dict], top_k: int) -> List[Dict]:
        """
        Select skills based on confidence thresholds.

        Thresholds:
        - HIGH (>0.7): Use top matches only (3-5 skills)
        - MEDIUM (0.4-0.7): Top matches + some fallbacks
        - LOW (<0.4): Load fallback skills

        Args:
            scored_matches: List of scored skill dicts
            top_k: Desired number of skills

        Returns:
            Selected skills list
        """
        if not scored_matches:
            return self._get_fallback_skills(top_k)

        top_confidence = scored_matches[0]['confidence']

        if top_confidence > 0.7:
            # HIGH confidence: Use top matches
            selected = scored_matches[:min(top_k, 5)]
            print(f"[Skills Router] HIGH confidence ({top_confidence:.2f})")
            return selected

        elif top_confidence > 0.4:
            # MEDIUM confidence: Top matches + fallbacks
            num_top = min(3, len(scored_matches))
            num_fallback = min(2, top_k - num_top)
            selected = scored_matches[:num_top] + self._get_fallback_skills(num_fallback)
            print(f"[Skills Router] MEDIUM confidence ({top_confidence:.2f})")
            return selected

        else:
            # LOW confidence: Use fallbacks
            print(f"[Skills Router] LOW confidence ({top_confidence:.2f}), using fallbacks")
            return self._get_fallback_skills(top_k)

    def _get_fallback_skills(self, limit: int = 5) -> List[Dict]:
        """
        Get most frequently used skills as fallback.

        Args:
            limit: Maximum number of fallback skills

        Returns:
            List of fallback skill dicts
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, category, full_content, token_cost
            FROM skills
            ORDER BY use_count DESC, last_used DESC
            LIMIT ?
        """, (limit,))

        fallbacks = []
        for skill_id, name, category, content, tokens in cursor.fetchall():
            fallbacks.append({
                'id': skill_id,
                'name': name,
                'category': category,
                'content': content,
                'token_cost': tokens,
                'confidence': 0.5,
                'is_fallback': True
            })

        conn.close()
        return fallbacks

    def _update_usage(self, skills: List[Dict]):
        """
        Update usage statistics for loaded skills.

        Args:
            skills: List of skill dicts to update
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        for skill in skills:
            cursor.execute("""
                UPDATE skills
                SET use_count = use_count + 1,
                    last_used = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (skill['id'],))

        conn.commit()
        conn.close()

    def _update_cache(self, key: str, value: List[Dict]):
        """
        Update LRU cache with new entry.

        Args:
            key: Cache key
            value: Skill list to cache
        """
        # Remove oldest entry if cache is full
        if len(self.cache) >= self.cache_max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]

        self.cache[key] = value

    def get_stats(self) -> Dict:
        """
        Get router statistics.

        Returns:
            Dict with total skills, usage stats, etc.
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM skills")
        total_skills = cursor.fetchone()[0]

        cursor.execute("SELECT category, COUNT(*) FROM skills GROUP BY category")
        by_category = dict(cursor.fetchall())

        cursor.execute("SELECT AVG(use_count), MAX(use_count) FROM skills")
        avg_use, max_use = cursor.fetchone()

        cursor.execute("SELECT name, use_count FROM skills ORDER BY use_count DESC LIMIT 5")
        top_used = cursor.fetchall()

        conn.close()

        return {
            'total_skills': total_skills,
            'by_category': by_category,
            'avg_use_count': avg_use or 0,
            'max_use_count': max_use or 0,
            'top_used': top_used,
            'cache_size': len(self.cache)
        }


# Example usage and testing
if __name__ == "__main__":
    router = SemanticSkillRouter()

    # Example: Index the arc-competition skill
    router.index_skill(
        skill_id="arc-competition",
        name="ARC Competition Workflow",
        category="research",
        description="Comprehensive workflow automation for ARC-AGI-2 Kaggle competition development and submission",
        full_content="[Full skill content would go here...]",
        token_cost=180,
        complexity="complex"
    )

    # Example: Route a query
    results = router.route("Help me test my Kaggle submission")

    print("\n=== Router Stats ===")
    stats = router.get_stats()
    print(json.dumps(stats, indent=2))
