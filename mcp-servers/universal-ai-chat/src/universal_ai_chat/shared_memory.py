#!/usr/bin/env python3
"""
Shared Memory Integration for Universal AI Chat
Provides cross-AI context sharing via Qdrant vector store.

All AI assistants (Claude, Codex, Gemini) can read/write to shared memory.
"""

import json
import hashlib
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Qdrant client
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance, VectorParams, PointStruct,
        Filter, FieldCondition, MatchValue, MatchAny
    )
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    logger.warning("qdrant-client not installed")

# Embedding model
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False

try:
    from fastembed import TextEmbedding
    FASTEMBED_AVAILABLE = True
except ImportError:
    FASTEMBED_AVAILABLE = False


# Configuration
QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))
SHARED_MEMORY_COLLECTION = "ai_shared_memory"
CONVERSATION_COLLECTION = "ai_conversations"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


class SharedMemoryStore:
    """
    Shared vector memory for cross-AI communication.

    Features:
    - Store/retrieve shared context by key
    - Semantic search across all AI-contributed knowledge
    - Track which AI contributed each piece of knowledge
    - Support for conversations, facts, and working memory
    """

    def __init__(self):
        self.client = None
        self.embedding_model = None

        if QDRANT_AVAILABLE:
            self.client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
            self._ensure_collections()

        # Initialize embedding model
        if EMBEDDINGS_AVAILABLE:
            self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        elif FASTEMBED_AVAILABLE:
            self.embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

    def _ensure_collections(self):
        """Create collections if they don't exist"""
        collections = [c.name for c in self.client.get_collections().collections]

        # Shared memory collection
        if SHARED_MEMORY_COLLECTION not in collections:
            self.client.create_collection(
                collection_name=SHARED_MEMORY_COLLECTION,
                vectors_config=VectorParams(
                    size=EMBEDDING_DIM,
                    distance=Distance.COSINE
                )
            )
            logger.info(f"Created collection: {SHARED_MEMORY_COLLECTION}")

        # Conversations collection
        if CONVERSATION_COLLECTION not in collections:
            self.client.create_collection(
                collection_name=CONVERSATION_COLLECTION,
                vectors_config=VectorParams(
                    size=EMBEDDING_DIM,
                    distance=Distance.COSINE
                )
            )
            logger.info(f"Created collection: {CONVERSATION_COLLECTION}")

    def _embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings"""
        if self.embedding_model is None:
            raise RuntimeError("No embedding model available")

        if isinstance(self.embedding_model, SentenceTransformer):
            return self.embedding_model.encode(texts).tolist()
        else:
            embeddings = list(self.embedding_model.embed(texts))
            return [e.tolist() for e in embeddings]

    def _generate_id(self, *args) -> str:
        """Generate deterministic ID from args"""
        combined = ":".join(str(a) for a in args)
        return hashlib.md5(combined.encode()).hexdigest()

    # ========== Shared Context Operations ==========

    def store_context(
        self,
        key: str,
        content: str,
        contributed_by: str,
        platform: str,
        context_type: str = "general",
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Store shared context accessible to all AIs.

        Args:
            key: Unique key for this context (e.g., "project_goals", "current_task")
            content: The context content
            contributed_by: Session ID of the contributing AI
            platform: AI platform (claude-code, codex-cli, gemini-cli)
            context_type: Type of context (general, decision, discovery, fact)
            metadata: Additional metadata

        Returns:
            Point ID
        """
        if not self.client:
            raise RuntimeError("Qdrant not available")

        point_id = self._generate_id(key, content[:100])
        embedding = self._embed([content])[0]

        payload = {
            "key": key,
            "content": content,
            "contributed_by": contributed_by,
            "platform": platform,
            "context_type": context_type,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "access_count": 0,
            **(metadata or {})
        }

        self.client.upsert(
            collection_name=SHARED_MEMORY_COLLECTION,
            points=[PointStruct(id=point_id, vector=embedding, payload=payload)]
        )

        logger.info(f"Stored shared context: {key} by {platform}")
        return point_id

    def get_context(self, key: str) -> Optional[Dict]:
        """Retrieve shared context by key"""
        if not self.client:
            return None

        # Search by exact key match
        results = self.client.scroll(
            collection_name=SHARED_MEMORY_COLLECTION,
            scroll_filter=Filter(
                must=[FieldCondition(key="key", match=MatchValue(value=key))]
            ),
            limit=1
        )[0]

        if results:
            point = results[0]
            # Update access count
            point.payload["access_count"] = point.payload.get("access_count", 0) + 1
            self.client.set_payload(
                collection_name=SHARED_MEMORY_COLLECTION,
                payload={"access_count": point.payload["access_count"]},
                points=[point.id]
            )
            return point.payload

        return None

    def search_context(
        self,
        query: str,
        platform_filter: Optional[str] = None,
        context_type_filter: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Semantic search across all shared context.

        Args:
            query: Search query
            platform_filter: Filter by contributing platform
            context_type_filter: Filter by context type
            limit: Max results

        Returns:
            List of matching contexts with scores
        """
        if not self.client:
            return []

        query_embedding = self._embed([query])[0]

        # Build filter
        conditions = []
        if platform_filter:
            conditions.append(
                FieldCondition(key="platform", match=MatchValue(value=platform_filter))
            )
        if context_type_filter:
            conditions.append(
                FieldCondition(key="context_type", match=MatchValue(value=context_type_filter))
            )

        query_filter = Filter(must=conditions) if conditions else None

        results = self.client.search(
            collection_name=SHARED_MEMORY_COLLECTION,
            query_vector=query_embedding,
            query_filter=query_filter,
            limit=limit
        )

        return [
            {
                "score": r.score,
                "key": r.payload.get("key"),
                "content": r.payload.get("content"),
                "platform": r.payload.get("platform"),
                "context_type": r.payload.get("context_type"),
                "contributed_by": r.payload.get("contributed_by"),
                "created_at": r.payload.get("created_at")
            }
            for r in results
        ]

    def list_all_context_keys(self) -> List[Dict]:
        """List all shared context keys with metadata"""
        if not self.client:
            return []

        results = self.client.scroll(
            collection_name=SHARED_MEMORY_COLLECTION,
            limit=1000,
            with_payload=True,
            with_vectors=False
        )[0]

        seen_keys = {}
        for point in results:
            key = point.payload.get("key")
            if key and key not in seen_keys:
                seen_keys[key] = {
                    "key": key,
                    "platform": point.payload.get("platform"),
                    "context_type": point.payload.get("context_type"),
                    "updated_at": point.payload.get("updated_at"),
                    "access_count": point.payload.get("access_count", 0)
                }

        return list(seen_keys.values())

    # ========== Conversation Operations ==========

    def store_message(
        self,
        message_id: str,
        from_session: str,
        from_platform: str,
        to_session: Optional[str],
        content: str,
        message_type: str = "chat",
        is_broadcast: bool = False,
        metadata: Optional[Dict] = None
    ) -> str:
        """Store a cross-AI message in vector memory"""
        if not self.client:
            raise RuntimeError("Qdrant not available")

        embedding = self._embed([content])[0]

        payload = {
            "message_id": message_id,
            "from_session": from_session,
            "from_platform": from_platform,
            "to_session": to_session,
            "content": content,
            "message_type": message_type,
            "is_broadcast": is_broadcast,
            "timestamp": datetime.now().isoformat(),
            **(metadata or {})
        }

        self.client.upsert(
            collection_name=CONVERSATION_COLLECTION,
            points=[PointStruct(id=message_id, vector=embedding, payload=payload)]
        )

        return message_id

    def search_messages(
        self,
        query: str,
        platform_filter: Optional[str] = None,
        session_filter: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Semantic search across all cross-AI messages"""
        if not self.client:
            return []

        query_embedding = self._embed([query])[0]

        conditions = []
        if platform_filter:
            conditions.append(
                FieldCondition(key="from_platform", match=MatchValue(value=platform_filter))
            )
        if session_filter:
            # Match either from or to
            conditions.append(
                FieldCondition(
                    key="from_session",
                    match=MatchAny(any=[session_filter])
                )
            )

        query_filter = Filter(must=conditions) if conditions else None

        results = self.client.search(
            collection_name=CONVERSATION_COLLECTION,
            query_vector=query_embedding,
            query_filter=query_filter,
            limit=limit
        )

        return [
            {
                "score": r.score,
                "message_id": r.payload.get("message_id"),
                "from_session": r.payload.get("from_session"),
                "from_platform": r.payload.get("from_platform"),
                "to_session": r.payload.get("to_session"),
                "content": r.payload.get("content"),
                "message_type": r.payload.get("message_type"),
                "timestamp": r.payload.get("timestamp")
            }
            for r in results
        ]

    def get_conversation_summary(self, session_a: str, session_b: str) -> Dict:
        """Get summary of conversation between two sessions"""
        if not self.client:
            return {}

        # Get all messages between these sessions
        results = self.client.scroll(
            collection_name=CONVERSATION_COLLECTION,
            scroll_filter=Filter(
                should=[
                    Filter(must=[
                        FieldCondition(key="from_session", match=MatchValue(value=session_a)),
                        FieldCondition(key="to_session", match=MatchValue(value=session_b))
                    ]),
                    Filter(must=[
                        FieldCondition(key="from_session", match=MatchValue(value=session_b)),
                        FieldCondition(key="to_session", match=MatchValue(value=session_a))
                    ])
                ]
            ),
            limit=1000
        )[0]

        if not results:
            return {
                "message_count": 0,
                "participants": [session_a, session_b]
            }

        messages = [r.payload for r in results]
        messages.sort(key=lambda x: x.get("timestamp", ""))

        return {
            "message_count": len(messages),
            "participants": [session_a, session_b],
            "first_message": messages[0].get("timestamp") if messages else None,
            "last_message": messages[-1].get("timestamp") if messages else None,
            "message_types": list(set(m.get("message_type") for m in messages))
        }

    # ========== Documentation Search ==========

    def search_docs(
        self,
        query: str,
        platform: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict]:
        """
        Search indexed AI CLI documentation.

        Args:
            query: Search query
            platform: Filter by platform (claude-code, codex-cli, gemini-cli)
            limit: Max results
        """
        from .indexer import AIDocIndexer, COLLECTION_NAME

        indexer = AIDocIndexer()
        return indexer.search(query, platform, limit)

    # ========== Stats ==========

    def get_stats(self) -> Dict:
        """Get shared memory statistics"""
        if not self.client:
            return {"available": False}

        stats = {
            "available": True,
            "collections": {}
        }

        try:
            # Shared memory stats
            sm_info = self.client.get_collection(SHARED_MEMORY_COLLECTION)
            stats["collections"]["shared_memory"] = {
                "points_count": sm_info.points_count,
                "vectors_count": sm_info.vectors_count
            }
        except:
            stats["collections"]["shared_memory"] = {"error": "not found"}

        try:
            # Conversations stats
            conv_info = self.client.get_collection(CONVERSATION_COLLECTION)
            stats["collections"]["conversations"] = {
                "points_count": conv_info.points_count,
                "vectors_count": conv_info.vectors_count
            }
        except:
            stats["collections"]["conversations"] = {"error": "not found"}

        return stats


# Singleton instance
_shared_memory: Optional[SharedMemoryStore] = None

def get_shared_memory() -> SharedMemoryStore:
    """Get or create shared memory singleton"""
    global _shared_memory
    if _shared_memory is None:
        _shared_memory = SharedMemoryStore()
    return _shared_memory
