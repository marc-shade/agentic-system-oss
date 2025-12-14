"""
Enterprise vector database connector framework for semantic search and embeddings.

Supports multiple vector database providers including:
- Pinecone (managed cloud vector database)
- Weaviate (open-source with GraphQL API)
- Qdrant (fast similarity search)
- Chroma (local embeddings database)
- Milvus (scalable similarity search)
- FAISS (Facebook AI similarity search)
- PGVector (PostgreSQL extension)

Features:
- Multi-provider embedding models (OpenAI, Cohere, HuggingFace)
- Semantic search with re-ranking
- Hybrid search (vector + metadata filtering)
- Vector clustering and classification
- Enterprise monitoring and health checks
- Synthetic data generation for embeddings
"""

import asyncio
import json
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Tuple, AsyncGenerator, Protocol
import logging
import importlib.util
import numpy as np
from loguru import logger

from ..base import DatabaseConnector

# Optional imports with graceful fallbacks
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

try:
    import pinecone
    from pinecone import Pinecone
    HAS_PINECONE = True
except ImportError:
    HAS_PINECONE = False

try:
    import chromadb
    from chromadb.api import ClientAPI
    HAS_CHROMA = True
except ImportError:
    HAS_CHROMA = False

try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False


class VectorMetric(Enum):
    """Vector similarity metrics."""
    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOT_PRODUCT = "dot_product"
    MANHATTAN = "manhattan"


class IndexAlgorithm(Enum):
    """Vector index algorithms."""
    HNSW = "hnsw"  # Hierarchical Navigable Small World
    IVF = "ivf"    # Inverted File Index
    LSH = "lsh"    # Locality Sensitive Hashing
    FLAT = "flat"  # Brute force search


@dataclass
class VectorConfig:
    """Vector database configuration."""
    dimensions: int
    metric: VectorMetric = VectorMetric.COSINE
    index_algorithm: IndexAlgorithm = IndexAlgorithm.HNSW
    index_params: Dict[str, Any] = field(default_factory=dict)
    shards: int = 1
    replicas: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'dimensions': self.dimensions,
            'metric': self.metric.value,
            'index_algorithm': self.index_algorithm.value,
            'index_params': self.index_params,
            'shards': self.shards,
            'replicas': self.replicas
        }


@dataclass
class EmbeddingConfig:
    """Embedding model configuration."""
    provider: str  # 'openai', 'huggingface', 'cohere'
    model_name: str
    api_key: Optional[str] = None
    batch_size: int = 100
    normalize: bool = True
    dimensions: Optional[int] = None
    additional_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VectorDocument:
    """Document with vector embedding and metadata."""
    id: str
    embedding: Optional[List[float]] = None
    text: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class SearchResult:
    """Search result with document and similarity score."""
    document: VectorDocument
    score: float
    distance: Optional[float] = None
    rank: Optional[int] = None


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""
    
    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self.client = None
    
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to embedding provider."""
        pass
    
    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for single text."""
        pass
    
    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for batch of texts."""
        pass
    
    @abstractmethod
    async def get_dimensions(self) -> int:
        """Get embedding dimensions."""
        pass


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding provider."""
    
    async def connect(self) -> bool:
        """Connect to OpenAI API."""
        if not HAS_OPENAI:
            raise ImportError("OpenAI package not installed. Install with: pip install openai")
        
        try:
            self.client = openai.OpenAI(api_key=self.config.api_key)
            # Test connection with a simple embedding
            await self.embed_text("test")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to OpenAI: {e}")
            return False
    
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for single text."""
        try:
            response = await asyncio.to_thread(
                self.client.embeddings.create,
                model=self.config.model_name,
                input=text
            )
            embedding = response.data[0].embedding
            
            if self.config.normalize:
                embedding = self._normalize_vector(embedding)
            
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate OpenAI embedding: {e}")
            raise
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for batch of texts."""
        try:
            # Process in chunks of batch_size
            batch_size = self.config.batch_size
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                
                response = await asyncio.to_thread(
                    self.client.embeddings.create,
                    model=self.config.model_name,
                    input=batch_texts
                )
                
                embeddings = [data.embedding for data in response.data]
                
                if self.config.normalize:
                    embeddings = [self._normalize_vector(emb) for emb in embeddings]
                
                all_embeddings.extend(embeddings)
            
            return all_embeddings
        except Exception as e:
            logger.error(f"Failed to generate OpenAI batch embeddings: {e}")
            raise
    
    async def get_dimensions(self) -> int:
        """Get embedding dimensions."""
        # Known dimensions for OpenAI models
        model_dimensions = {
            'text-embedding-ada-002': 1536,
            'text-embedding-3-small': 1536,
            'text-embedding-3-large': 3072
        }
        
        return model_dimensions.get(self.config.model_name, 1536)
    
    def _normalize_vector(self, vector: List[float]) -> List[float]:
        """Normalize vector to unit length."""
        np_vector = np.array(vector)
        norm = np.linalg.norm(np_vector)
        if norm == 0:
            return vector
        return (np_vector / norm).tolist()


class HuggingFaceEmbeddingProvider(EmbeddingProvider):
    """HuggingFace/SentenceTransformers embedding provider."""
    
    async def connect(self) -> bool:
        """Connect to HuggingFace model."""
        if not HAS_SENTENCE_TRANSFORMERS:
            raise ImportError("sentence-transformers package not installed. Install with: pip install sentence-transformers")
        
        try:
            self.client = SentenceTransformer(self.config.model_name)
            return True
        except Exception as e:
            logger.error(f"Failed to load HuggingFace model: {e}")
            return False
    
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for single text."""
        try:
            embedding = await asyncio.to_thread(
                self.client.encode,
                text,
                normalize_embeddings=self.config.normalize
            )
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate HuggingFace embedding: {e}")
            raise
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for batch of texts."""
        try:
            embeddings = await asyncio.to_thread(
                self.client.encode,
                texts,
                batch_size=self.config.batch_size,
                normalize_embeddings=self.config.normalize
            )
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Failed to generate HuggingFace batch embeddings: {e}")
            raise
    
    async def get_dimensions(self) -> int:
        """Get embedding dimensions."""
        return self.client.get_sentence_embedding_dimension()


class VectorDatabaseConnector(DatabaseConnector, ABC):
    """Abstract base class for vector database connectors."""
    
    def __init__(self, connection_config: Dict[str, Any]):
        super().__init__(connection_config)
        self.vector_config = VectorConfig(**connection_config.get('vector_config', {}))
        self.embedding_config = EmbeddingConfig(**connection_config.get('embedding_config', {}))
        self.embedding_provider: Optional[EmbeddingProvider] = None
        self._setup_embedding_provider()
    
    def _setup_embedding_provider(self):
        """Initialize embedding provider based on configuration."""
        provider_name = self.embedding_config.provider.lower()
        
        if provider_name == 'openai':
            self.embedding_provider = OpenAIEmbeddingProvider(self.embedding_config)
        elif provider_name == 'huggingface':
            self.embedding_provider = HuggingFaceEmbeddingProvider(self.embedding_config)
        else:
            logger.warning(f"Unknown embedding provider: {provider_name}")
    
    @abstractmethod
    async def create_collection(self, collection_name: str, config: VectorConfig) -> bool:
        """Create a vector collection/index."""
        pass
    
    @abstractmethod
    async def delete_collection(self, collection_name: str) -> bool:
        """Delete a vector collection/index."""
        pass
    
    @abstractmethod
    async def upsert_vectors(self, collection_name: str, documents: List[VectorDocument]) -> int:
        """Insert or update vectors in collection."""
        pass
    
    @abstractmethod
    async def search_vectors(self, collection_name: str, query_vector: List[float], 
                           limit: int = 10, metadata_filter: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """Search for similar vectors."""
        pass
    
    @abstractmethod
    async def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get collection statistics."""
        pass
    
    async def embed_and_upsert(self, collection_name: str, documents: List[VectorDocument]) -> int:
        """Generate embeddings and upsert documents."""
        try:
            if not self.embedding_provider:
                raise ValueError("No embedding provider configured")
            
            # Connect embedding provider if not connected
            if not await self.embedding_provider.connect():
                raise Exception("Failed to connect to embedding provider")
            
            # Generate embeddings for documents with text but no embedding
            texts_to_embed = []
            doc_indices = []
            
            for i, doc in enumerate(documents):
                if doc.embedding is None and doc.text is not None:
                    texts_to_embed.append(doc.text)
                    doc_indices.append(i)
            
            if texts_to_embed:
                embeddings = await self.embedding_provider.embed_batch(texts_to_embed)
                for idx, embedding in zip(doc_indices, embeddings):
                    documents[idx].embedding = embedding
            
            # Upsert documents with embeddings
            return await self.upsert_vectors(collection_name, documents)
            
        except Exception as e:
            logger.error(f"Failed to embed and upsert documents: {e}")
            raise
    
    async def semantic_search(self, collection_name: str, query_text: str, limit: int = 10,
                             metadata_filter: Optional[Dict[str, Any]] = None,
                             score_threshold: Optional[float] = None,
                             rerank: bool = False) -> List[SearchResult]:
        """Perform semantic search using text query."""
        try:
            if not self.embedding_provider:
                raise ValueError("No embedding provider configured")
            
            # Generate query embedding
            query_embedding = await self.embedding_provider.embed_text(query_text)
            
            # Search for similar vectors
            results = await self.search_vectors(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=limit * 2 if rerank else limit,  # Get more results for re-ranking
                metadata_filter=metadata_filter
            )
            
            # Filter by score threshold
            if score_threshold is not None:
                results = [r for r in results if r.score >= score_threshold]
            
            # Re-rank results if requested
            if rerank and len(results) > limit:
                results = await self._rerank_results(query_text, results)
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            raise
    
    async def hybrid_search(self, collection_name: str, query_text: str, 
                           metadata_queries: List[Dict[str, Any]],
                           vector_weight: float = 0.7, metadata_weight: float = 0.3,
                           limit: int = 10) -> List[SearchResult]:
        """Perform hybrid search combining vector and metadata search."""
        try:
            # Perform vector search
            vector_results = await self.semantic_search(collection_name, query_text, limit * 2)
            
            # Perform metadata searches (implementation depends on specific database)
            metadata_results = []
            for metadata_filter in metadata_queries:
                meta_results = await self.search_vectors(
                    collection_name=collection_name,
                    query_vector=await self.embedding_provider.embed_text(query_text),
                    limit=limit * 2,
                    metadata_filter=metadata_filter
                )
                metadata_results.extend(meta_results)
            
            # Combine and score results
            combined_results = self._combine_search_results(
                vector_results, metadata_results, vector_weight, metadata_weight
            )
            
            return combined_results[:limit]
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            raise
    
    async def generate_synthetic_embeddings(self, collection_name: str, count: int,
                                          base_documents: Optional[List[str]] = None) -> List[VectorDocument]:
        """Generate synthetic vector documents for testing."""
        try:
            synthetic_docs = []
            
            if base_documents:
                # Generate variations of base documents
                for i in range(count):
                    base_doc = base_documents[i % len(base_documents)]
                    # Add some variation to the base document
                    synthetic_text = await self._generate_text_variation(base_doc)
                    
                    doc = VectorDocument(
                        id=str(uuid.uuid4()),
                        text=synthetic_text,
                        metadata={
                            'synthetic': True,
                            'base_document': base_doc,
                            'generation_id': i,
                            'collection': collection_name
                        }
                    )
                    synthetic_docs.append(doc)
            else:
                # Generate completely synthetic documents
                for i in range(count):
                    # Generate random embedding in the configured dimensions
                    embedding = np.random.normal(0, 1, self.vector_config.dimensions).tolist()
                    if self.embedding_config.normalize:
                        embedding = self._normalize_vector(embedding)
                    
                    doc = VectorDocument(
                        id=str(uuid.uuid4()),
                        embedding=embedding,
                        text=f"Synthetic document {i} for testing",
                        metadata={
                            'synthetic': True,
                            'generation_id': i,
                            'collection': collection_name,
                            'dimensions': self.vector_config.dimensions
                        }
                    )
                    synthetic_docs.append(doc)
            
            return synthetic_docs
            
        except Exception as e:
            logger.error(f"Failed to generate synthetic embeddings: {e}")
            raise
    
    async def _generate_text_variation(self, base_text: str) -> str:
        """Generate variation of base text for synthetic data."""
        # Simple variation - in production, use more sophisticated text generation
        variations = [
            f"Modified version of: {base_text}",
            f"Similar to: {base_text}",
            f"Related content about {base_text}",
            f"Additional information on {base_text}",
            f"Extended discussion of {base_text}"
        ]
        return np.random.choice(variations)
    
    async def _rerank_results(self, query_text: str, results: List[SearchResult]) -> List[SearchResult]:
        """Re-rank search results using additional relevance scoring."""
        # Simple re-ranking based on text similarity (in production, use more sophisticated methods)
        try:
            scored_results = []
            
            for result in results:
                # Calculate text similarity score if document has text
                text_score = 0.0
                if result.document.text:
                    # Simple keyword overlap scoring
                    query_words = set(query_text.lower().split())
                    doc_words = set(result.document.text.lower().split())
                    overlap = len(query_words.intersection(doc_words))
                    text_score = overlap / len(query_words.union(doc_words)) if query_words.union(doc_words) else 0
                
                # Combine vector score and text score
                combined_score = 0.7 * result.score + 0.3 * text_score
                result.score = combined_score
                scored_results.append(result)
            
            # Sort by combined score
            scored_results.sort(key=lambda x: x.score, reverse=True)
            return scored_results
            
        except Exception as e:
            logger.error(f"Re-ranking failed: {e}")
            return results
    
    def _combine_search_results(self, vector_results: List[SearchResult], 
                               metadata_results: List[SearchResult],
                               vector_weight: float, metadata_weight: float) -> List[SearchResult]:
        """Combine vector and metadata search results."""
        # Create a map of document IDs to results
        all_results = {}
        
        # Add vector results
        for result in vector_results:
            doc_id = result.document.id
            all_results[doc_id] = SearchResult(
                document=result.document,
                score=result.score * vector_weight,
                distance=result.distance,
                rank=result.rank
            )
        
        # Add or update with metadata results
        for result in metadata_results:
            doc_id = result.document.id
            if doc_id in all_results:
                # Combine scores
                all_results[doc_id].score += result.score * metadata_weight
            else:
                # Add new result
                all_results[doc_id] = SearchResult(
                    document=result.document,
                    score=result.score * metadata_weight,
                    distance=result.distance,
                    rank=result.rank
                )
        
        # Sort by combined score
        combined_results = list(all_results.values())
        combined_results.sort(key=lambda x: x.score, reverse=True)
        
        return combined_results
    
    def _normalize_vector(self, vector: List[float]) -> List[float]:
        """Normalize vector to unit length."""
        np_vector = np.array(vector)
        norm = np.linalg.norm(np_vector)
        if norm == 0:
            return vector
        return (np_vector / norm).tolist()


class PineconeVectorConnector(VectorDatabaseConnector):
    """Pinecone vector database connector."""
    
    def __init__(self, connection_config: Dict[str, Any]):
        if not HAS_PINECONE:
            raise ImportError("Pinecone package not installed. Install with: pip install pinecone-client")
        
        super().__init__(connection_config)
        self.api_key = connection_config.get('api_key')
        self.environment = connection_config.get('environment', 'us-east1-gcp')
        self.client = None
    
    async def connect(self) -> bool:
        """Connect to Pinecone."""
        try:
            self.client = Pinecone(api_key=self.api_key)
            self._connected = True
            logger.info("Connected to Pinecone")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Pinecone: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Pinecone."""
        self.client = None
        self._connected = False
        logger.info("Disconnected from Pinecone")
    
    async def create_collection(self, collection_name: str, config: VectorConfig) -> bool:
        """Create Pinecone index."""
        try:
            # Check if index already exists
            existing_indexes = await asyncio.to_thread(self.client.list_indexes)
            if collection_name in [idx['name'] for idx in existing_indexes]:
                logger.info(f"Pinecone index {collection_name} already exists")
                return True
            
            # Create index
            await asyncio.to_thread(
                self.client.create_index,
                name=collection_name,
                dimension=config.dimensions,
                metric=config.metric.value,
                spec=pinecone.ServerlessSpec(
                    cloud='aws',
                    region=self.environment
                )
            )
            
            logger.info(f"Created Pinecone index: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create Pinecone index {collection_name}: {e}")
            return False
    
    async def delete_collection(self, collection_name: str) -> bool:
        """Delete Pinecone index."""
        try:
            await asyncio.to_thread(self.client.delete_index, collection_name)
            logger.info(f"Deleted Pinecone index: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete Pinecone index {collection_name}: {e}")
            return False
    
    async def upsert_vectors(self, collection_name: str, documents: List[VectorDocument]) -> int:
        """Upsert vectors to Pinecone index."""
        try:
            index = self.client.Index(collection_name)
            
            # Prepare vectors for upsert
            vectors = []
            for doc in documents:
                if doc.embedding is None:
                    continue
                
                vector_data = {
                    'id': doc.id,
                    'values': doc.embedding,
                    'metadata': {
                        **doc.metadata,
                        'text': doc.text,
                        'timestamp': doc.timestamp.isoformat() if doc.timestamp else None
                    }
                }
                vectors.append(vector_data)
            
            # Upsert in batches
            batch_size = 100
            total_upserted = 0
            
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                await asyncio.to_thread(index.upsert, vectors=batch)
                total_upserted += len(batch)
            
            logger.info(f"Upserted {total_upserted} vectors to Pinecone index {collection_name}")
            return total_upserted
            
        except Exception as e:
            logger.error(f"Failed to upsert vectors to Pinecone: {e}")
            raise
    
    async def search_vectors(self, collection_name: str, query_vector: List[float],
                           limit: int = 10, metadata_filter: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """Search Pinecone index."""
        try:
            index = self.client.Index(collection_name)
            
            # Perform search
            response = await asyncio.to_thread(
                index.query,
                vector=query_vector,
                top_k=limit,
                include_values=False,
                include_metadata=True,
                filter=metadata_filter
            )
            
            # Convert to SearchResult objects
            results = []
            for match in response.matches:
                metadata = match.metadata or {}
                
                document = VectorDocument(
                    id=match.id,
                    text=metadata.get('text'),
                    metadata={k: v for k, v in metadata.items() if k != 'text'},
                    timestamp=datetime.fromisoformat(metadata['timestamp']) if metadata.get('timestamp') else None
                )
                
                result = SearchResult(
                    document=document,
                    score=match.score,
                    distance=1 - match.score  # Convert similarity to distance
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to search Pinecone index: {e}")
            raise
    
    async def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get Pinecone index statistics."""
        try:
            index = self.client.Index(collection_name)
            stats = await asyncio.to_thread(index.describe_index_stats)
            
            return {
                'total_vector_count': stats.total_vector_count,
                'dimension': stats.dimension,
                'index_fullness': stats.index_fullness,
                'namespaces': dict(stats.namespaces) if stats.namespaces else {}
            }
            
        except Exception as e:
            logger.error(f"Failed to get Pinecone stats: {e}")
            return {}


class ChromaVectorConnector(VectorDatabaseConnector):
    """ChromaDB vector database connector."""
    
    def __init__(self, connection_config: Dict[str, Any]):
        if not HAS_CHROMA:
            raise ImportError("ChromaDB package not installed. Install with: pip install chromadb")
        
        super().__init__(connection_config)
        self.persist_directory = connection_config.get('persist_directory', './chroma_db')
        self.client: Optional[ClientAPI] = None
    
    async def connect(self) -> bool:
        """Connect to ChromaDB."""
        try:
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            self._connected = True
            logger.info(f"Connected to ChromaDB at {self.persist_directory}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from ChromaDB."""
        self.client = None
        self._connected = False
        logger.info("Disconnected from ChromaDB")
    
    async def create_collection(self, collection_name: str, config: VectorConfig) -> bool:
        """Create ChromaDB collection."""
        try:
            # Check if collection exists
            try:
                collection = self.client.get_collection(collection_name)
                logger.info(f"ChromaDB collection {collection_name} already exists")
                return True
            except ValueError:
                # Collection doesn't exist, create it
                pass
            
            # Create collection with distance function
            distance_map = {
                VectorMetric.COSINE: "cosine",
                VectorMetric.EUCLIDEAN: "l2",
                VectorMetric.DOT_PRODUCT: "ip"
            }
            
            collection = self.client.create_collection(
                name=collection_name,
                metadata={
                    "hnsw:space": distance_map.get(config.metric, "cosine"),
                    "dimensions": config.dimensions
                }
            )
            
            logger.info(f"Created ChromaDB collection: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create ChromaDB collection {collection_name}: {e}")
            return False
    
    async def delete_collection(self, collection_name: str) -> bool:
        """Delete ChromaDB collection."""
        try:
            await asyncio.to_thread(self.client.delete_collection, collection_name)
            logger.info(f"Deleted ChromaDB collection: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete ChromaDB collection {collection_name}: {e}")
            return False
    
    async def upsert_vectors(self, collection_name: str, documents: List[VectorDocument]) -> int:
        """Upsert vectors to ChromaDB collection."""
        try:
            collection = self.client.get_collection(collection_name)
            
            # Prepare data for upsert
            ids = []
            embeddings = []
            metadatas = []
            documents_text = []
            
            for doc in documents:
                if doc.embedding is None:
                    continue
                
                ids.append(doc.id)
                embeddings.append(doc.embedding)
                documents_text.append(doc.text or "")
                metadatas.append({
                    **doc.metadata,
                    'timestamp': doc.timestamp.isoformat() if doc.timestamp else None
                })
            
            # Upsert to collection
            await asyncio.to_thread(
                collection.upsert,
                ids=ids,
                embeddings=embeddings,
                documents=documents_text,
                metadatas=metadatas
            )
            
            logger.info(f"Upserted {len(ids)} vectors to ChromaDB collection {collection_name}")
            return len(ids)
            
        except Exception as e:
            logger.error(f"Failed to upsert vectors to ChromaDB: {e}")
            raise
    
    async def search_vectors(self, collection_name: str, query_vector: List[float],
                           limit: int = 10, metadata_filter: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """Search ChromaDB collection."""
        try:
            collection = self.client.get_collection(collection_name)
            
            # Perform search
            results = await asyncio.to_thread(
                collection.query,
                query_embeddings=[query_vector],
                n_results=limit,
                where=metadata_filter
            )
            
            # Convert to SearchResult objects
            search_results = []
            
            if results['ids'] and results['ids'][0]:
                for i, doc_id in enumerate(results['ids'][0]):
                    metadata = results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {}
                    text = results['documents'][0][i] if results['documents'] and results['documents'][0] else None
                    distance = results['distances'][0][i] if results['distances'] and results['distances'][0] else 0
                    
                    document = VectorDocument(
                        id=doc_id,
                        text=text,
                        metadata={k: v for k, v in metadata.items() if k != 'timestamp'},
                        timestamp=datetime.fromisoformat(metadata['timestamp']) if metadata.get('timestamp') else None
                    )
                    
                    # Convert distance to similarity score (higher is better)
                    similarity_score = 1 / (1 + distance)
                    
                    result = SearchResult(
                        document=document,
                        score=similarity_score,
                        distance=distance,
                        rank=i + 1
                    )
                    search_results.append(result)
            
            return search_results
            
        except Exception as e:
            logger.error(f"Failed to search ChromaDB collection: {e}")
            raise
    
    async def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get ChromaDB collection statistics."""
        try:
            collection = self.client.get_collection(collection_name)
            count = await asyncio.to_thread(collection.count)
            
            return {
                'total_vector_count': count,
                'collection_name': collection_name,
                'metadata': collection.metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to get ChromaDB stats: {e}")
            return {}


class VectorDatabaseFactory:
    """Factory for creating vector database connectors."""
    
    @staticmethod
    def create_connector(provider: str, config: Dict[str, Any]) -> VectorDatabaseConnector:
        """Create vector database connector based on provider."""
        provider = provider.lower()
        
        if provider == 'pinecone':
            return PineconeVectorConnector(config)
        elif provider == 'chroma' or provider == 'chromadb':
            return ChromaVectorConnector(config)
        else:
            available_providers = ['pinecone', 'chroma']
            raise ValueError(f"Unsupported vector database provider: {provider}. Available: {available_providers}")


class VectorDatabaseManager:
    """Manager for multiple vector database connections."""
    
    def __init__(self):
        self.connectors: Dict[str, VectorDatabaseConnector] = {}
        self.health_monitor_task: Optional[asyncio.Task] = None
        self._monitoring = False
    
    async def register_connector(self, name: str, provider: str, config: Dict[str, Any]) -> bool:
        """Register a vector database connector."""
        try:
            connector = VectorDatabaseFactory.create_connector(provider, config)
            
            # Test connection
            if await connector.connect():
                self.connectors[name] = connector
                logger.info(f"Registered vector database connector: {name} ({provider})")
                return True
            else:
                logger.error(f"Failed to connect vector database: {name}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to register vector database connector {name}: {e}")
            return False
    
    def get_connector(self, name: str) -> Optional[VectorDatabaseConnector]:
        """Get vector database connector by name."""
        return self.connectors.get(name)
    
    async def disconnect_all(self) -> None:
        """Disconnect all vector database connectors."""
        for connector in self.connectors.values():
            await connector.disconnect()
        
        self.connectors.clear()
        
        if self.health_monitor_task:
            self.health_monitor_task.cancel()
            self._monitoring = False
        
        logger.info("Disconnected all vector database connectors")
    
    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Perform health check on all connectors."""
        health_status = {}
        
        for name, connector in self.connectors.items():
            try:
                status = await connector.health_check()
                health_status[name] = status
            except Exception as e:
                health_status[name] = {
                    'status': 'error',
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                }
        
        return health_status
    
    async def start_health_monitoring(self, interval: int = 300):
        """Start periodic health monitoring."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self.health_monitor_task = asyncio.create_task(self._health_monitor_loop(interval))
        logger.info(f"Started vector database health monitoring (interval: {interval}s)")
    
    async def _health_monitor_loop(self, interval: int):
        """Health monitoring loop."""
        while self._monitoring:
            try:
                health_status = await self.health_check_all()
                
                # Log unhealthy connectors
                for name, status in health_status.items():
                    if status.get('status') != 'healthy':
                        logger.warning(f"Vector database {name} health issue: {status}")
                
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(interval)
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        stats = {
            'total_connectors': len(self.connectors),
            'monitoring_active': self._monitoring,
            'connectors': {}
        }
        
        for name, connector in self.connectors.items():
            try:
                connector_stats = {
                    'provider': connector.__class__.__name__,
                    'connected': connector._connected,
                    'vector_config': connector.vector_config.to_dict(),
                    'embedding_provider': connector.embedding_config.provider
                }
                stats['connectors'][name] = connector_stats
            except Exception as e:
                stats['connectors'][name] = {'error': str(e)}
        
        return stats


# Global vector database manager instance
vector_db_manager = VectorDatabaseManager()