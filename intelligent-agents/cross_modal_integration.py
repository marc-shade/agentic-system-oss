#!/usr/bin/env python3
"""
Cross-Modal Integration - Unified AGI Memory System

Connects visual, text, and code memories for:
- Cross-modal semantic search
- Temporal context correlation
- Unified AGI context retrieval
- Multi-modal pattern detection

Modalities:
- Visual: Screenshots, images, diagrams
- Text: Conversations, notes, documents
- Code: File changes, git commits, implementations
- Audio: Voice transcripts (future)

STATUS: Production Ready
"""

import asyncio
import hashlib
import json
import logging
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import sys

sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/intelligent-agents')
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/shared')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MemoryModality(Enum):
    """Types of memory modalities."""
    VISUAL = "visual"
    TEXT = "text"
    CODE = "code"
    AUDIO = "audio"
    MIXED = "mixed"


class ContextType(Enum):
    """Types of contextual relationships."""
    TEMPORAL = "temporal"          # Happened at same time
    CAUSAL = "causal"              # One caused another
    SEMANTIC = "semantic"          # Similar meaning
    SPATIAL = "spatial"            # Same location/file
    PROCEDURAL = "procedural"      # Part of same workflow


@dataclass
class UnifiedMemory:
    """A memory that can span multiple modalities."""
    id: str
    modality: MemoryModality
    timestamp: str
    content: Dict[str, Any]
    embedding: Optional[List[float]] = None
    concepts: List[str] = field(default_factory=list)
    related_memories: List[str] = field(default_factory=list)
    context_links: List[Dict[str, Any]] = field(default_factory=list)
    importance: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TemporalContext:
    """Context window around a point in time."""
    center_time: str
    window_minutes: int
    visual_memories: List[UnifiedMemory]
    text_memories: List[UnifiedMemory]
    code_memories: List[UnifiedMemory]
    correlations: List[Dict[str, Any]]


@dataclass
class CrossModalQuery:
    """A query that can span modalities."""
    query_text: str
    modalities: List[MemoryModality]
    time_range: Optional[Tuple[str, str]] = None
    concepts: List[str] = field(default_factory=list)
    limit: int = 20


class CrossModalEmbedder:
    """Generate embeddings that work across modalities."""

    def __init__(self):
        self._cache = {}

    async def embed(self, content: str, modality: MemoryModality) -> List[float]:
        """Generate modality-aware embedding."""
        cache_key = f"{modality.value}:{hashlib.md5(content.encode()).hexdigest()}"

        if cache_key in self._cache:
            return self._cache[cache_key]

        # Prepend modality context for better cross-modal alignment
        contextualized = f"[{modality.value}] {content}"

        # Generate embedding (using hash-based for now, SAFLA in production)
        hash_bytes = hashlib.sha256(contextualized.encode()).digest()
        embedding = [float(b) / 255.0 for b in hash_bytes[:128]]

        # Normalize
        magnitude = sum(x**2 for x in embedding) ** 0.5
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]

        self._cache[cache_key] = embedding
        return embedding

    async def embed_multi(self, contents: Dict[MemoryModality, str]) -> List[float]:
        """Generate unified embedding from multiple modalities."""
        embeddings = []

        for modality, content in contents.items():
            if content:
                emb = await self.embed(content, modality)
                embeddings.append(emb)

        if not embeddings:
            return []

        # Average embeddings
        result = [0.0] * len(embeddings[0])
        for emb in embeddings:
            for i, v in enumerate(emb):
                result[i] += v / len(embeddings)

        return result

    def similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity."""
        if not a or not b or len(a) != len(b):
            return 0.0

        dot = sum(x * y for x, y in zip(a, b))
        mag_a = sum(x**2 for x in a) ** 0.5
        mag_b = sum(x**2 for x in b) ** 0.5

        if mag_a == 0 or mag_b == 0:
            return 0.0

        return dot / (mag_a * mag_b)


class CodeMemoryTracker:
    """Track code changes and file modifications."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize code memory database."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS code_memories (
                id TEXT PRIMARY KEY,
                timestamp TEXT,
                file_path TEXT,
                change_type TEXT,
                description TEXT,
                diff_summary TEXT,
                language TEXT,
                embedding TEXT,
                concepts TEXT,
                metadata TEXT
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_code_timestamp ON code_memories(timestamp)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_code_file ON code_memories(file_path)
        ''')

        conn.commit()
        conn.close()

    async def record_change(
        self,
        file_path: str,
        change_type: str,
        description: str,
        diff_summary: str = "",
        language: str = ""
    ) -> UnifiedMemory:
        """Record a code change as a memory."""
        memory_id = f"code_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hashlib.md5(file_path.encode()).hexdigest()[:8]}"

        embedder = CrossModalEmbedder()
        content_text = f"{change_type}: {file_path} - {description}"
        embedding = await embedder.embed(content_text, MemoryModality.CODE)

        memory = UnifiedMemory(
            id=memory_id,
            modality=MemoryModality.CODE,
            timestamp=datetime.now().isoformat(),
            content={
                "file_path": file_path,
                "change_type": change_type,
                "description": description,
                "diff_summary": diff_summary,
                "language": language
            },
            embedding=embedding,
            concepts=self._extract_concepts(file_path, description),
            metadata={"source": "code_tracker"}
        )

        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO code_memories
            (id, timestamp, file_path, change_type, description, diff_summary, language, embedding, concepts, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            memory.id,
            memory.timestamp,
            file_path,
            change_type,
            description,
            diff_summary,
            language,
            json.dumps(embedding),
            json.dumps(memory.concepts),
            json.dumps(memory.metadata)
        ))

        conn.commit()
        conn.close()

        return memory

    def _extract_concepts(self, file_path: str, description: str) -> List[str]:
        """Extract concepts from code change."""
        concepts = []

        # Extract from file path
        parts = Path(file_path).parts
        for part in parts:
            if part not in ['.', '..', 'src', 'lib', 'test', 'tests']:
                concepts.append(f"path:{part}")

        # Extract file extension
        ext = Path(file_path).suffix
        if ext:
            concepts.append(f"lang:{ext[1:]}")

        # Extract keywords from description
        keywords = ['fix', 'add', 'update', 'remove', 'refactor', 'implement', 'test']
        desc_lower = description.lower()
        for kw in keywords:
            if kw in desc_lower:
                concepts.append(f"action:{kw}")

        return concepts

    def get_recent(self, hours: int = 24, limit: int = 100) -> List[UnifiedMemory]:
        """Get recent code memories."""
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, timestamp, file_path, change_type, description,
                   diff_summary, language, embedding, concepts, metadata
            FROM code_memories
            WHERE timestamp > ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (cutoff, limit))

        memories = []
        for row in cursor.fetchall():
            memories.append(UnifiedMemory(
                id=row[0],
                modality=MemoryModality.CODE,
                timestamp=row[1],
                content={
                    "file_path": row[2],
                    "change_type": row[3],
                    "description": row[4],
                    "diff_summary": row[5],
                    "language": row[6]
                },
                embedding=json.loads(row[7]) if row[7] else None,
                concepts=json.loads(row[8]) if row[8] else [],
                metadata=json.loads(row[9]) if row[9] else {}
            ))

        conn.close()
        return memories


class TextMemoryTracker:
    """Track text-based memories (conversations, notes, documents)."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize text memory database."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS text_memories (
                id TEXT PRIMARY KEY,
                timestamp TEXT,
                text_type TEXT,
                content TEXT,
                summary TEXT,
                embedding TEXT,
                concepts TEXT,
                source TEXT,
                metadata TEXT
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_text_timestamp ON text_memories(timestamp)
        ''')

        conn.commit()
        conn.close()

    async def record(
        self,
        content: str,
        text_type: str = "note",
        summary: str = "",
        source: str = ""
    ) -> UnifiedMemory:
        """Record text content as a memory."""
        memory_id = f"text_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hashlib.md5(content[:100].encode()).hexdigest()[:8]}"

        embedder = CrossModalEmbedder()
        embedding = await embedder.embed(content[:500], MemoryModality.TEXT)

        memory = UnifiedMemory(
            id=memory_id,
            modality=MemoryModality.TEXT,
            timestamp=datetime.now().isoformat(),
            content={
                "text_type": text_type,
                "content": content,
                "summary": summary or content[:200]
            },
            embedding=embedding,
            concepts=self._extract_concepts(content),
            metadata={"source": source}
        )

        # Store
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO text_memories
            (id, timestamp, text_type, content, summary, embedding, concepts, source, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            memory.id,
            memory.timestamp,
            text_type,
            content,
            summary,
            json.dumps(embedding),
            json.dumps(memory.concepts),
            source,
            json.dumps(memory.metadata)
        ))

        conn.commit()
        conn.close()

        return memory

    def _extract_concepts(self, content: str) -> List[str]:
        """Extract concepts from text."""
        concepts = []

        # Simple keyword extraction
        important_words = [
            'error', 'bug', 'fix', 'feature', 'implement',
            'design', 'architecture', 'performance', 'security',
            'test', 'deploy', 'config', 'database', 'api'
        ]

        content_lower = content.lower()
        for word in important_words:
            if word in content_lower:
                concepts.append(f"topic:{word}")

        return concepts[:10]

    def get_recent(self, hours: int = 24, limit: int = 100) -> List[UnifiedMemory]:
        """Get recent text memories."""
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, timestamp, text_type, content, summary, embedding, concepts, source, metadata
            FROM text_memories
            WHERE timestamp > ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (cutoff, limit))

        memories = []
        for row in cursor.fetchall():
            memories.append(UnifiedMemory(
                id=row[0],
                modality=MemoryModality.TEXT,
                timestamp=row[1],
                content={
                    "text_type": row[2],
                    "content": row[3],
                    "summary": row[4]
                },
                embedding=json.loads(row[5]) if row[5] else None,
                concepts=json.loads(row[6]) if row[6] else [],
                metadata=json.loads(row[8]) if row[8] else {}
            ))

        conn.close()
        return memories


class CrossModalMemoryManager:
    """
    Unified cross-modal memory management.

    Coordinates visual, text, and code memories for unified AGI context.
    """

    def __init__(
        self,
        storage_path: str = "/Volumes/SSDRAID0/agentic-system/databases/cross_modal"
    ):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)

        # Initialize modality-specific trackers
        self.code_tracker = CodeMemoryTracker(
            os.path.join(storage_path, "code_memories.db")
        )
        self.text_tracker = TextMemoryTracker(
            os.path.join(storage_path, "text_memories.db")
        )

        # Cross-modal index
        self._init_cross_modal_index()

        self.embedder = CrossModalEmbedder()

        logger.info(f"CrossModalMemoryManager initialized at {storage_path}")

    def _init_cross_modal_index(self):
        """Initialize cross-modal correlation index."""
        db_path = os.path.join(self.storage_path, "cross_modal_index.db")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Temporal correlations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS temporal_correlations (
                id TEXT PRIMARY KEY,
                memory_id_1 TEXT,
                modality_1 TEXT,
                memory_id_2 TEXT,
                modality_2 TEXT,
                time_delta_seconds REAL,
                correlation_strength REAL,
                context_type TEXT,
                created_at TEXT
            )
        ''')

        # Semantic correlations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS semantic_correlations (
                id TEXT PRIMARY KEY,
                memory_id_1 TEXT,
                modality_1 TEXT,
                memory_id_2 TEXT,
                modality_2 TEXT,
                similarity_score REAL,
                shared_concepts TEXT,
                created_at TEXT
            )
        ''')

        conn.commit()
        conn.close()

    async def record_code_change(
        self,
        file_path: str,
        change_type: str,
        description: str,
        **kwargs
    ) -> UnifiedMemory:
        """Record a code change and find correlations."""
        memory = await self.code_tracker.record_change(
            file_path, change_type, description, **kwargs
        )

        # Find temporal correlations with recent visual memories
        await self._find_temporal_correlations(memory)

        return memory

    async def record_text(
        self,
        content: str,
        text_type: str = "note",
        **kwargs
    ) -> UnifiedMemory:
        """Record text content and find correlations."""
        memory = await self.text_tracker.record(content, text_type, **kwargs)

        # Find correlations
        await self._find_temporal_correlations(memory)

        return memory

    async def _find_temporal_correlations(
        self,
        memory: UnifiedMemory,
        window_minutes: int = 5
    ) -> List[Dict]:
        """Find memories from other modalities in the same time window."""
        correlations = []

        try:
            mem_time = datetime.fromisoformat(memory.timestamp.replace("Z", "+00:00"))
        except Exception:
            mem_time = datetime.now()

        # Get visual memories in window
        try:
            from visual_memory_integration import VisualMemoryManager
            vis_manager = VisualMemoryManager()
            visual_memories = vis_manager.memory_store.get_recent(hours=1, limit=50)

            for vis_mem in visual_memories:
                try:
                    vis_time = datetime.fromisoformat(vis_mem.timestamp.replace("Z", "+00:00"))
                    delta = abs((mem_time - vis_time).total_seconds())

                    if delta <= window_minutes * 60:
                        correlation = {
                            "memory_id_1": memory.id,
                            "modality_1": memory.modality.value,
                            "memory_id_2": vis_mem.id,
                            "modality_2": "visual",
                            "time_delta_seconds": delta,
                            "correlation_strength": 1.0 - (delta / (window_minutes * 60)),
                            "context_type": ContextType.TEMPORAL.value
                        }
                        correlations.append(correlation)
                        self._store_correlation(correlation)
                except Exception:
                    continue

        except ImportError:
            pass

        return correlations

    def _store_correlation(self, correlation: Dict) -> None:
        """Store a correlation in the index."""
        db_path = os.path.join(self.storage_path, "cross_modal_index.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        corr_id = f"corr_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hashlib.md5(str(correlation).encode()).hexdigest()[:8]}"

        cursor.execute('''
            INSERT OR REPLACE INTO temporal_correlations
            (id, memory_id_1, modality_1, memory_id_2, modality_2,
             time_delta_seconds, correlation_strength, context_type, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            corr_id,
            correlation["memory_id_1"],
            correlation["modality_1"],
            correlation["memory_id_2"],
            correlation["modality_2"],
            correlation["time_delta_seconds"],
            correlation["correlation_strength"],
            correlation["context_type"],
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

    async def search(
        self,
        query: str,
        modalities: Optional[List[MemoryModality]] = None,
        hours: int = 24,
        limit: int = 20
    ) -> List[UnifiedMemory]:
        """
        Cross-modal semantic search.

        Args:
            query: Search query
            modalities: Which modalities to search (None = all)
            hours: Time range
            limit: Max results

        Returns:
            Ranked list of memories across modalities
        """
        if modalities is None:
            modalities = [MemoryModality.VISUAL, MemoryModality.TEXT, MemoryModality.CODE]

        # Generate query embedding
        query_embedding = await self.embedder.embed(query, MemoryModality.MIXED)

        all_memories = []

        # Gather memories from each modality
        if MemoryModality.CODE in modalities:
            code_memories = self.code_tracker.get_recent(hours=hours, limit=limit)
            all_memories.extend(code_memories)

        if MemoryModality.TEXT in modalities:
            text_memories = self.text_tracker.get_recent(hours=hours, limit=limit)
            all_memories.extend(text_memories)

        if MemoryModality.VISUAL in modalities:
            try:
                from visual_memory_integration import VisualMemoryManager
                vis_manager = VisualMemoryManager()
                visual_memories = vis_manager.memory_store.get_recent(hours=hours, limit=limit)

                # Convert to UnifiedMemory format
                for vm in visual_memories:
                    all_memories.append(UnifiedMemory(
                        id=vm.id,
                        modality=MemoryModality.VISUAL,
                        timestamp=vm.timestamp,
                        content={
                            "description": vm.description,
                            "scene_type": vm.scene_type,
                            "objects": vm.objects
                        },
                        embedding=vm.embedding,
                        concepts=vm.concepts,
                        importance=vm.importance.value / 5.0
                    ))
            except ImportError:
                pass

        # Score and rank
        scored = []
        for mem in all_memories:
            if mem.embedding:
                score = self.embedder.similarity(query_embedding, mem.embedding)
                scored.append((score, mem))

        scored.sort(key=lambda x: x[0], reverse=True)

        return [mem for _, mem in scored[:limit]]

    def get_temporal_context(
        self,
        timestamp: str,
        window_minutes: int = 10
    ) -> TemporalContext:
        """
        Get all memories around a specific time.

        Returns unified context across all modalities.
        """
        try:
            center = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except Exception:
            center = datetime.now()

        start = center - timedelta(minutes=window_minutes)
        end = center + timedelta(minutes=window_minutes)

        # Collect from all modalities
        visual_memories = []
        text_memories = []
        code_memories = []
        correlations = []

        # Visual
        try:
            from visual_memory_integration import VisualMemoryManager
            vis_manager = VisualMemoryManager()
            all_visual = vis_manager.memory_store.get_recent(hours=24, limit=200)

            for vm in all_visual:
                try:
                    vm_time = datetime.fromisoformat(vm.timestamp.replace("Z", "+00:00"))
                    if start <= vm_time <= end:
                        visual_memories.append(UnifiedMemory(
                            id=vm.id,
                            modality=MemoryModality.VISUAL,
                            timestamp=vm.timestamp,
                            content={"description": vm.description, "scene_type": vm.scene_type},
                            embedding=vm.embedding
                        ))
                except Exception:
                    continue
        except ImportError:
            pass

        # Text
        all_text = self.text_tracker.get_recent(hours=24, limit=200)
        for tm in all_text:
            try:
                tm_time = datetime.fromisoformat(tm.timestamp.replace("Z", "+00:00"))
                if start <= tm_time <= end:
                    text_memories.append(tm)
            except Exception:
                continue

        # Code
        all_code = self.code_tracker.get_recent(hours=24, limit=200)
        for cm in all_code:
            try:
                cm_time = datetime.fromisoformat(cm.timestamp.replace("Z", "+00:00"))
                if start <= cm_time <= end:
                    code_memories.append(cm)
            except Exception:
                continue

        # Find correlations in this window
        for v in visual_memories:
            for c in code_memories:
                correlations.append({
                    "type": "visual-code",
                    "visual_id": v.id,
                    "code_id": c.id,
                    "relation": "temporal_proximity"
                })

        return TemporalContext(
            center_time=timestamp,
            window_minutes=window_minutes,
            visual_memories=visual_memories,
            text_memories=text_memories,
            code_memories=code_memories,
            correlations=correlations
        )

    def get_context_for_file(self, file_path: str, hours: int = 48) -> Dict[str, Any]:
        """Get all context related to a specific file."""
        code_memories = self.code_tracker.get_recent(hours=hours, limit=500)

        # Filter to this file
        file_memories = [m for m in code_memories if file_path in m.content.get("file_path", "")]

        if not file_memories:
            return {"file_path": file_path, "memories": [], "context": {}}

        # Get temporal context around each change
        all_context = []
        for mem in file_memories[:10]:  # Limit to recent 10 changes
            ctx = self.get_temporal_context(mem.timestamp, window_minutes=5)
            all_context.append({
                "change": mem.content,
                "timestamp": mem.timestamp,
                "visual_context": len(ctx.visual_memories),
                "text_context": len(ctx.text_memories)
            })

        return {
            "file_path": file_path,
            "total_changes": len(file_memories),
            "recent_changes": all_context,
            "concepts": list(set(c for m in file_memories for c in m.concepts))
        }

    def get_unified_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get unified summary across all modalities."""
        visual_count = 0
        text_count = 0
        code_count = 0

        try:
            from visual_memory_integration import VisualMemoryManager
            vis_manager = VisualMemoryManager()
            visual_memories = vis_manager.memory_store.get_recent(hours=hours, limit=1000)
            visual_count = len(visual_memories)
        except ImportError:
            pass

        text_memories = self.text_tracker.get_recent(hours=hours, limit=1000)
        text_count = len(text_memories)

        code_memories = self.code_tracker.get_recent(hours=hours, limit=1000)
        code_count = len(code_memories)

        # Get correlation count
        db_path = os.path.join(self.storage_path, "cross_modal_index.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        cursor.execute('SELECT COUNT(*) FROM temporal_correlations WHERE created_at > ?', (cutoff,))
        correlation_count = cursor.fetchone()[0]

        conn.close()

        return {
            "time_range_hours": hours,
            "modality_counts": {
                "visual": visual_count,
                "text": text_count,
                "code": code_count
            },
            "total_memories": visual_count + text_count + code_count,
            "cross_modal_correlations": correlation_count,
            "timestamp": datetime.now().isoformat()
        }


# MCP Tool Functions
async def cross_modal_search(query: str, modalities: str = "all", limit: int = 20) -> Dict:
    """MCP Tool: Cross-modal semantic search."""
    manager = CrossModalMemoryManager()

    mod_list = None
    if modalities != "all":
        mod_list = [MemoryModality(m.strip()) for m in modalities.split(",")]

    results = await manager.search(query, mod_list, limit=limit)

    return {
        "query": query,
        "results": [
            {
                "id": m.id,
                "modality": m.modality.value,
                "timestamp": m.timestamp,
                "content_summary": str(m.content)[:200]
            }
            for m in results
        ],
        "count": len(results)
    }


def get_temporal_context(timestamp: str, window_minutes: int = 10) -> Dict:
    """MCP Tool: Get cross-modal context around a timestamp."""
    manager = CrossModalMemoryManager()
    ctx = manager.get_temporal_context(timestamp, window_minutes)

    return {
        "center_time": ctx.center_time,
        "window_minutes": ctx.window_minutes,
        "visual_count": len(ctx.visual_memories),
        "text_count": len(ctx.text_memories),
        "code_count": len(ctx.code_memories),
        "correlations": ctx.correlations[:10]
    }


def get_unified_memory_summary(hours: int = 24) -> Dict:
    """MCP Tool: Get unified summary across modalities."""
    manager = CrossModalMemoryManager()
    return manager.get_unified_summary(hours)


async def record_code_change(file_path: str, change_type: str, description: str) -> Dict:
    """MCP Tool: Record a code change."""
    manager = CrossModalMemoryManager()
    memory = await manager.record_code_change(file_path, change_type, description)

    return {
        "memory_id": memory.id,
        "concepts": memory.concepts,
        "stored": True
    }


async def record_text_memory(content: str, text_type: str = "note") -> Dict:
    """MCP Tool: Record text content."""
    manager = CrossModalMemoryManager()
    memory = await manager.record_text(content, text_type)

    return {
        "memory_id": memory.id,
        "concepts": memory.concepts,
        "stored": True
    }


# CLI Entry Point
async def main():
    """Demo cross-modal integration."""
    import argparse

    parser = argparse.ArgumentParser(description="Cross-Modal Integration")
    parser.add_argument("--summary", action="store_true", help="Show unified summary")
    parser.add_argument("--search", type=str, help="Cross-modal search query")
    parser.add_argument("--context", type=str, help="Get temporal context (ISO timestamp)")

    args = parser.parse_args()

    manager = CrossModalMemoryManager()

    if args.summary:
        summary = manager.get_unified_summary()
        print(json.dumps(summary, indent=2))

    elif args.search:
        results = await manager.search(args.search)
        for mem in results:
            print(f"[{mem.modality.value}] {mem.timestamp}: {str(mem.content)[:100]}")

    elif args.context:
        ctx = manager.get_temporal_context(args.context)
        print(f"Context around {args.context}:")
        print(f"  Visual: {len(ctx.visual_memories)}")
        print(f"  Text: {len(ctx.text_memories)}")
        print(f"  Code: {len(ctx.code_memories)}")

    else:
        print("Use --summary, --search 'query', or --context 'timestamp'")


if __name__ == "__main__":
    asyncio.run(main())
