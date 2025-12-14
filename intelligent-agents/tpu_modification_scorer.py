#!/usr/bin/env python3
"""
TPU Modification Scorer - Edge TPU Accelerated Code Change Prioritization

Scores proposed code modifications by semantic similarity to successful past
modifications. Uses text embeddings for fast, continuous evaluation without
API costs.

Integration with Darwin-Gödel Machine for self-improvement prioritization.

Usage:
    from tpu_modification_scorer import TPUModificationScorer

    scorer = TPUModificationScorer()
    score = await scorer.score_modification(
        description="Optimize embedding cache lookup",
        code_diff=diff_content
    )
    print(f"Priority score: {score.priority}")  # 0.0-1.0
"""
import platform

import os
import sys
import json
import logging
import sqlite3
import numpy as np
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Add hooks path for tpu_importance
AGENTIC_SYSTEM_PATH = os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE))
HOOKS_PATH = os.path.join(AGENTIC_SYSTEM_PATH, "scripts/hooks")
if HOOKS_PATH not in sys.path:
    sys.path.insert(0, HOOKS_PATH)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("tpu_modification_scorer")

# Try to import TPU capabilities
TPU_AVAILABLE = False
_embed_text = None

try:
    from tpu_importance import embed_text, is_tpu_available
    if is_tpu_available():
        _embed_text = embed_text
        TPU_AVAILABLE = True
        logger.info("TPU modification scoring enabled")
except ImportError:
    logger.info("TPU not available, using fallback scoring")

# Try to import tpu_monitor for usage tracking
try:
    from tpu_monitor import record_tpu_usage
    HAS_TPU_MONITOR = True
except ImportError:
    HAS_TPU_MONITOR = False


# Database for modification history
DB_PATH = Path(AGENTIC_SYSTEM_PATH) / "databases" / "modification_scorer.db"


@dataclass
class ModificationScore:
    """Score for a proposed modification"""
    priority: float  # 0.0-1.0, higher = higher priority
    similarity_to_successful: float  # Similarity to past successful mods
    similarity_to_failed: float  # Similarity to past failed mods
    novelty: float  # 1 - max_similarity (higher = more novel)
    confidence: float  # Confidence in the score
    similar_mods: List[Dict]  # Most similar past modifications
    reasoning: str  # Explanation of the score
    latency_ms: float  # TPU inference latency


def _ensure_db():
    """Ensure database exists with proper schema."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS modifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            description TEXT NOT NULL,
            code_diff TEXT,
            embedding BLOB,
            success INTEGER DEFAULT 0,
            improvement_percent REAL DEFAULT 0.0,
            source TEXT,
            metadata TEXT
        )
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_mod_success ON modifications(success)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_mod_timestamp ON modifications(timestamp)
    ''')

    conn.commit()
    conn.close()


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class TPUModificationScorer:
    """
    Score code modifications using TPU embeddings.

    Prioritizes modifications based on:
    - Similarity to past successful modifications
    - Dissimilarity from past failed modifications
    - Novelty (exploring new areas vs. tried approaches)
    """

    def __init__(self):
        """Initialize the modification scorer."""
        _ensure_db()
        self.use_tpu = TPU_AVAILABLE
        self._embedding_cache: Dict[str, np.ndarray] = {}

        # Precompute embeddings for known good patterns
        self._pattern_embeddings = self._load_pattern_embeddings()

        if self.use_tpu:
            logger.info("TPU modification scorer ready")
        else:
            logger.info("Using fallback keyword-based scoring")

    def _load_pattern_embeddings(self) -> Dict[str, np.ndarray]:
        """Load embeddings for known improvement patterns."""
        patterns = {}

        # High-value improvement patterns
        improvement_patterns = {
            "performance": "Optimize performance by reducing latency and improving throughput",
            "memory": "Reduce memory usage and optimize data structures",
            "caching": "Add caching layer to reduce redundant computation",
            "error_handling": "Improve error handling and recovery mechanisms",
            "parallelization": "Add parallel processing for concurrent execution",
            "algorithm": "Replace algorithm with more efficient implementation",
            "cleanup": "Clean up code, remove dead code, simplify logic",
            "security": "Fix security vulnerability and improve safety",
            "testing": "Add tests to improve coverage and reliability",
            "documentation": "Improve documentation and code clarity"
        }

        if self.use_tpu and _embed_text:
            import time
            for name, description in improvement_patterns.items():
                try:
                    start = time.perf_counter()
                    embedding = _embed_text(description)
                    latency = (time.perf_counter() - start) * 1000

                    if embedding is not None:
                        patterns[name] = np.array(embedding, dtype=np.float32)

                        if HAS_TPU_MONITOR:
                            record_tpu_usage(
                                "pattern_embedding",
                                latency_ms=latency,
                                source="modification_scorer",
                                metadata={"pattern": name}
                            )
                except Exception as e:
                    logger.warning(f"Failed to embed pattern {name}: {e}")

        return patterns

    def _get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get text embedding, with caching."""
        if text in self._embedding_cache:
            return self._embedding_cache[text]

        if not self.use_tpu or not _embed_text:
            return None

        try:
            import time
            start = time.perf_counter()
            embedding = _embed_text(text)
            latency = (time.perf_counter() - start) * 1000

            if embedding is not None:
                emb_array = np.array(embedding, dtype=np.float32)
                self._embedding_cache[text] = emb_array

                if HAS_TPU_MONITOR:
                    record_tpu_usage(
                        "modification_embedding",
                        latency_ms=latency,
                        source="modification_scorer"
                    )

                return emb_array
        except Exception as e:
            logger.warning(f"Failed to embed text: {e}")

        return None

    def _get_past_modifications(self, success_filter: Optional[bool] = None, limit: int = 100) -> List[Dict]:
        """Get past modifications with embeddings."""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        if success_filter is None:
            cursor.execute('''
                SELECT id, description, embedding, success, improvement_percent
                FROM modifications
                WHERE embedding IS NOT NULL
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
        else:
            cursor.execute('''
                SELECT id, description, embedding, success, improvement_percent
                FROM modifications
                WHERE embedding IS NOT NULL AND success = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (1 if success_filter else 0, limit))

        results = []
        for row in cursor.fetchall():
            try:
                embedding = np.frombuffer(row[2], dtype=np.float32)
                results.append({
                    "id": row[0],
                    "description": row[1],
                    "embedding": embedding,
                    "success": bool(row[3]),
                    "improvement_percent": row[4]
                })
            except Exception:
                continue

        conn.close()
        return results

    async def score_modification(
        self,
        description: str,
        code_diff: Optional[str] = None,
        context: Optional[str] = None
    ) -> ModificationScore:
        """
        Score a proposed modification for priority.

        Args:
            description: What the modification does
            code_diff: Optional code diff content
            context: Optional additional context

        Returns:
            ModificationScore with priority and analysis
        """
        import time
        start_time = time.perf_counter()

        # Build full text for embedding
        full_text = description
        if code_diff:
            # Include first 500 chars of diff for context
            full_text += f" | Changes: {code_diff[:500]}"
        if context:
            full_text += f" | Context: {context}"

        # Get embedding
        embedding = self._get_embedding(full_text)

        if embedding is None:
            # Fallback to keyword-based scoring
            return self._fallback_score(description)

        # Compare to successful modifications
        successful_mods = self._get_past_modifications(success_filter=True)
        failed_mods = self._get_past_modifications(success_filter=False)

        # Calculate similarities
        successful_sims = []
        for mod in successful_mods:
            sim = cosine_similarity(embedding, mod["embedding"])
            successful_sims.append({
                "id": mod["id"],
                "description": mod["description"],
                "similarity": sim,
                "improvement": mod["improvement_percent"]
            })

        failed_sims = []
        for mod in failed_mods:
            sim = cosine_similarity(embedding, mod["embedding"])
            failed_sims.append({
                "id": mod["id"],
                "description": mod["description"],
                "similarity": sim
            })

        # Sort by similarity
        successful_sims.sort(key=lambda x: x["similarity"], reverse=True)
        failed_sims.sort(key=lambda x: x["similarity"], reverse=True)

        # Calculate scores
        max_success_sim = successful_sims[0]["similarity"] if successful_sims else 0.0
        max_failed_sim = failed_sims[0]["similarity"] if failed_sims else 0.0

        # Pattern matching score
        pattern_scores = {}
        for name, pattern_emb in self._pattern_embeddings.items():
            pattern_scores[name] = cosine_similarity(embedding, pattern_emb)

        best_pattern = max(pattern_scores, key=pattern_scores.get) if pattern_scores else "unknown"
        best_pattern_score = pattern_scores.get(best_pattern, 0.0)

        # Calculate priority
        # Higher score = more like successful mods, less like failed mods, good patterns
        priority = (
            0.4 * max_success_sim +  # Similarity to successful
            0.3 * (1.0 - max_failed_sim) +  # Dissimilarity from failed
            0.3 * best_pattern_score  # Match to known good patterns
        )

        # Novelty = how different from past attempts
        all_sims = [s["similarity"] for s in successful_sims + failed_sims]
        novelty = 1.0 - (max(all_sims) if all_sims else 0.0)

        # Confidence based on sample size
        sample_size = len(successful_mods) + len(failed_mods)
        confidence = min(1.0, sample_size / 50)  # Max confidence at 50 samples

        # Build reasoning
        reasoning_parts = []
        if max_success_sim > 0.7:
            reasoning_parts.append(f"Similar to successful: {successful_sims[0]['description'][:50]}...")
        if max_failed_sim > 0.7:
            reasoning_parts.append(f"Warning: Similar to failed: {failed_sims[0]['description'][:50]}...")
        if best_pattern_score > 0.6:
            reasoning_parts.append(f"Matches pattern: {best_pattern} ({best_pattern_score:.2f})")
        if novelty > 0.7:
            reasoning_parts.append("Novel approach - exploring new territory")

        reasoning = " | ".join(reasoning_parts) if reasoning_parts else "Standard modification"

        latency_ms = (time.perf_counter() - start_time) * 1000

        if HAS_TPU_MONITOR:
            record_tpu_usage(
                "modification_scoring",
                latency_ms=latency_ms,
                source="modification_scorer",
                metadata={
                    "priority": priority,
                    "pattern": best_pattern
                }
            )

        return ModificationScore(
            priority=priority,
            similarity_to_successful=max_success_sim,
            similarity_to_failed=max_failed_sim,
            novelty=novelty,
            confidence=confidence,
            similar_mods=successful_sims[:3],  # Top 3 similar
            reasoning=reasoning,
            latency_ms=latency_ms
        )

    def _fallback_score(self, description: str) -> ModificationScore:
        """Fallback keyword-based scoring when TPU unavailable."""
        # High-value keywords
        high_value = ["optimize", "performance", "cache", "fix", "security", "memory"]
        medium_value = ["refactor", "clean", "improve", "update", "enhance"]
        low_value = ["comment", "rename", "format", "style"]

        desc_lower = description.lower()

        score = 0.5  # Base score
        for kw in high_value:
            if kw in desc_lower:
                score += 0.1
        for kw in medium_value:
            if kw in desc_lower:
                score += 0.05
        for kw in low_value:
            if kw in desc_lower:
                score -= 0.05

        score = max(0.0, min(1.0, score))

        return ModificationScore(
            priority=score,
            similarity_to_successful=0.0,
            similarity_to_failed=0.0,
            novelty=0.5,
            confidence=0.3,  # Low confidence for fallback
            similar_mods=[],
            reasoning="Keyword-based scoring (TPU unavailable)",
            latency_ms=0.0
        )

    def record_modification_outcome(
        self,
        description: str,
        code_diff: Optional[str],
        success: bool,
        improvement_percent: float = 0.0,
        source: str = "unknown"
    ) -> bool:
        """
        Record a modification outcome for future learning.

        Args:
            description: What the modification did
            code_diff: The code changes
            success: Whether it improved the system
            improvement_percent: Measured improvement (if any)
            source: Where this modification came from

        Returns:
            True if recorded successfully
        """
        try:
            # Get embedding
            full_text = description
            if code_diff:
                full_text += f" | Changes: {code_diff[:500]}"

            embedding = self._get_embedding(full_text)
            embedding_bytes = embedding.tobytes() if embedding is not None else None

            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO modifications
                (timestamp, description, code_diff, embedding, success, improvement_percent, source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                description,
                code_diff,
                embedding_bytes,
                1 if success else 0,
                improvement_percent,
                source
            ))

            conn.commit()
            conn.close()

            logger.info(f"Recorded modification: {description[:50]}... success={success}")
            return True

        except Exception as e:
            logger.error(f"Failed to record modification: {e}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get modification scoring statistics."""
        try:
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) FROM modifications')
            total = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM modifications WHERE success = 1')
            successful = cursor.fetchone()[0]

            cursor.execute('SELECT AVG(improvement_percent) FROM modifications WHERE success = 1')
            avg_improvement = cursor.fetchone()[0] or 0.0

            conn.close()

            return {
                "total_modifications": total,
                "successful": successful,
                "failed": total - successful,
                "success_rate": successful / max(total, 1),
                "avg_improvement_percent": avg_improvement,
                "tpu_available": self.use_tpu,
                "patterns_loaded": len(self._pattern_embeddings),
                "cache_size": len(self._embedding_cache)
            }

        except Exception as e:
            return {"error": str(e)}


# CLI interface
if __name__ == "__main__":
    import asyncio
    import argparse

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    elif system == "Linux":
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()


    parser = argparse.ArgumentParser(description="TPU Modification Scorer")
    parser.add_argument("command", choices=["score", "record", "stats"],
                       help="Command to run")
    parser.add_argument("--description", "-d", type=str, help="Modification description")
    parser.add_argument("--success", action="store_true", help="Mark as successful")
    parser.add_argument("--improvement", type=float, default=0.0, help="Improvement percent")

    args = parser.parse_args()

    scorer = TPUModificationScorer()

    if args.command == "score":
        if not args.description:
            print("Error: --description required for scoring")
            sys.exit(1)

        score = asyncio.run(scorer.score_modification(args.description))
        print(json.dumps({
            "priority": score.priority,
            "similarity_successful": score.similarity_to_successful,
            "similarity_failed": score.similarity_to_failed,
            "novelty": score.novelty,
            "confidence": score.confidence,
            "reasoning": score.reasoning,
            "latency_ms": score.latency_ms
        }, indent=2))

    elif args.command == "record":
        if not args.description:
            print("Error: --description required for recording")
            sys.exit(1)

        success = scorer.record_modification_outcome(
            description=args.description,
            code_diff=None,
            success=args.success,
            improvement_percent=args.improvement,
            source="cli"
        )
        print(f"Recorded: {success}")

    elif args.command == "stats":
        stats = scorer.get_statistics()
        print(json.dumps(stats, indent=2))
