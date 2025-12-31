#!/usr/bin/env python3
"""
Enhanced Memory Integration for Node Chat
Stores node conversations in Qdrant vector database for long-term recall and learning.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Check if enhanced memory integration is enabled
ENHANCED_MEMORY_ENABLED = os.environ.get('ENHANCED_MEMORY_INTEGRATION', 'false').lower() == 'true'

class NodeChatMemoryIntegration:
    """Integrates node chat with enhanced memory system"""

    def __init__(self, storage_base: str, node_id: str):
        self.storage_base = storage_base
        self.node_id = node_id
        self.qdrant_client = None
        self.collection_name = "node_conversations"
        self._initialized = False

        if ENHANCED_MEMORY_ENABLED:
            self._initialize_qdrant()

    def _initialize_qdrant(self):
        """Initialize Qdrant client connection"""
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams, PointStruct

            # Connect to local Qdrant
            self.qdrant_client = QdrantClient(host="localhost", port=6333)

            # Check if collection exists, create if not
            collections = self.qdrant_client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.collection_name not in collection_names:
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=384,  # Match embedding model dimension
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")

            self._initialized = True
            logger.info("Enhanced memory integration initialized successfully")

        except ImportError:
            logger.warning("qdrant-client not installed, enhanced memory disabled")
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant: {e}")

    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text using local embedding model"""
        try:
            # Try using sentence-transformers
            from sentence_transformers import SentenceTransformer

            if not hasattr(self, '_embed_model'):
                self._embed_model = SentenceTransformer('all-MiniLM-L6-v2')

            embedding = self._embed_model.encode(text).tolist()
            return embedding

        except ImportError:
            # Fallback to Ollama embeddings
            try:
                import requests
                # Cloud-first Ollama for embeddings (can also run locally if needed)
                ollama_url = os.environ.get('OLLAMA_HOST', 'http://Marcs-Mac-Studio.local:11434')
                response = requests.post(
                    f"{ollama_url}/api/embeddings",
                    json={"model": "nomic-embed-text", "prompt": text},
                    timeout=10
                )
                if response.status_code == 200:
                    return response.json().get('embedding')
            except Exception as e:
                logger.debug(f"Ollama embedding failed: {e}")

        return None

    def store_conversation_message(
        self,
        message_id: str,
        from_node: str,
        to_node: str,
        content: str,
        conversation_id: str,
        timestamp: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Store a conversation message in enhanced memory"""

        if not self._initialized or not ENHANCED_MEMORY_ENABLED:
            return False

        try:
            from qdrant_client.models import PointStruct

            # Generate embedding
            embedding = self._get_embedding(content)
            if not embedding:
                logger.warning("Could not generate embedding for message")
                return False

            # Build payload
            payload = {
                "message_id": message_id,
                "from_node": from_node,
                "to_node": to_node,
                "content": content,
                "conversation_id": conversation_id,
                "timestamp": timestamp,
                "stored_by": self.node_id,
                "stored_at": datetime.utcnow().isoformat(),
                "type": "node_conversation",
                **(metadata or {})
            }

            # Generate point ID from message_id
            import hashlib
            point_id = int(hashlib.sha256(message_id.encode()).hexdigest()[:16], 16)

            # Store in Qdrant
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload=payload
                    )
                ]
            )

            logger.debug(f"Stored message {message_id} in enhanced memory")
            return True

        except Exception as e:
            logger.error(f"Failed to store message in enhanced memory: {e}")
            return False

    def search_conversations(
        self,
        query: str,
        limit: int = 10,
        from_node: Optional[str] = None,
        to_node: Optional[str] = None
    ) -> List[Dict]:
        """Search past conversations by semantic similarity"""

        if not self._initialized or not ENHANCED_MEMORY_ENABLED:
            return []

        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            # Generate query embedding
            query_embedding = self._get_embedding(query)
            if not query_embedding:
                return []

            # Build filter conditions
            conditions = []
            if from_node:
                conditions.append(
                    FieldCondition(key="from_node", match=MatchValue(value=from_node))
                )
            if to_node:
                conditions.append(
                    FieldCondition(key="to_node", match=MatchValue(value=to_node))
                )

            search_filter = Filter(must=conditions) if conditions else None

            # Search Qdrant
            results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=limit
            )

            return [
                {
                    "score": hit.score,
                    **hit.payload
                }
                for hit in results
            ]

        except Exception as e:
            logger.error(f"Failed to search conversations: {e}")
            return []

    def get_conversation_context(
        self,
        conversation_id: str,
        limit: int = 20
    ) -> List[Dict]:
        """Retrieve context from a specific conversation"""

        if not self._initialized or not ENHANCED_MEMORY_ENABLED:
            return []

        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            # Filter by conversation ID
            results = self.qdrant_client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="conversation_id",
                            match=MatchValue(value=conversation_id)
                        )
                    ]
                ),
                limit=limit,
                with_payload=True,
                with_vectors=False
            )

            messages = [point.payload for point in results[0]]
            # Sort by timestamp
            messages.sort(key=lambda x: x.get('timestamp', ''))
            return messages

        except Exception as e:
            logger.error(f"Failed to get conversation context: {e}")
            return []

    def store_learning_insight(
        self,
        insight: str,
        source_conversation_id: str,
        insight_type: str = "coordination_pattern",
        confidence: float = 0.8
    ) -> bool:
        """Store learned insights from conversations"""

        if not self._initialized or not ENHANCED_MEMORY_ENABLED:
            return False

        try:
            from qdrant_client.models import PointStruct
            import hashlib
            import uuid

            embedding = self._get_embedding(insight)
            if not embedding:
                return False

            payload = {
                "insight_id": str(uuid.uuid4()),
                "content": insight,
                "type": "learned_insight",
                "insight_type": insight_type,
                "source_conversation_id": source_conversation_id,
                "learned_by": self.node_id,
                "confidence": confidence,
                "timestamp": datetime.utcnow().isoformat()
            }

            point_id = int(hashlib.sha256(payload['insight_id'].encode()).hexdigest()[:16], 16)

            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload=payload
                    )
                ]
            )

            logger.info(f"Stored learning insight: {insight[:50]}...")
            return True

        except Exception as e:
            logger.error(f"Failed to store insight: {e}")
            return False

    def get_relevant_insights(
        self,
        context: str,
        limit: int = 5
    ) -> List[Dict]:
        """Retrieve relevant insights for a given context"""

        if not self._initialized or not ENHANCED_MEMORY_ENABLED:
            return []

        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            embedding = self._get_embedding(context)
            if not embedding:
                return []

            results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=embedding,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="type",
                            match=MatchValue(value="learned_insight")
                        )
                    ]
                ),
                limit=limit
            )

            return [
                {
                    "score": hit.score,
                    **hit.payload
                }
                for hit in results
            ]

        except Exception as e:
            logger.error(f"Failed to get insights: {e}")
            return []

    def get_stats(self) -> Dict:
        """Get statistics about stored memories"""

        if not self._initialized or not ENHANCED_MEMORY_ENABLED:
            return {"enabled": False, "reason": "Enhanced memory not initialized"}

        try:
            info = self.qdrant_client.get_collection(self.collection_name)

            return {
                "enabled": True,
                "collection": self.collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status.name
            }

        except Exception as e:
            return {"enabled": True, "error": str(e)}


# Singleton instance
_memory_integration: Optional[NodeChatMemoryIntegration] = None

def get_memory_integration(storage_base: str, node_id: str) -> NodeChatMemoryIntegration:
    """Get or create the memory integration singleton"""
    global _memory_integration
    if _memory_integration is None:
        _memory_integration = NodeChatMemoryIntegration(storage_base, node_id)
    return _memory_integration
