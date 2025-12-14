#!/usr/bin/env python3
"""
AI CLI Documentation Indexer
Indexes documentation for Claude Code, OpenAI Codex, and Gemini CLI into Qdrant.

This creates a local vector corpus for development reference across all AI platforms.
"""

import asyncio
import hashlib
import json
import os
import re
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Qdrant client
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance, VectorParams, PointStruct,
        Filter, FieldCondition, MatchValue
    )
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    logger.warning("qdrant-client not installed. Vector indexing disabled.")

# Embedding model
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    logger.warning("sentence-transformers not installed. Using fastembed fallback.")

try:
    from fastembed import TextEmbedding
    FASTEMBED_AVAILABLE = True
except ImportError:
    FASTEMBED_AVAILABLE = False


# Configuration
QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))
COLLECTION_NAME = "ai_cli_docs"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

# Documentation sources
DOCS_DIR = Path(__file__).parent.parent.parent / "docs"


class DocumentChunker:
    """Chunk markdown documents for vector indexing"""

    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_markdown(self, content: str, metadata: Dict[str, Any]) -> List[Dict]:
        """Split markdown into semantic chunks"""
        chunks = []

        # Split by headers first
        sections = re.split(r'\n(#{1,3}\s+[^\n]+)\n', content)

        current_header = metadata.get("title", "")
        current_text = ""

        i = 0
        while i < len(sections):
            section = sections[i]

            # Check if it's a header
            if re.match(r'^#{1,3}\s+', section):
                # Save previous section if exists
                if current_text.strip():
                    chunks.extend(self._split_text(current_text, {
                        **metadata,
                        "section": current_header
                    }))
                current_header = section.strip('#').strip()
                current_text = ""
            else:
                current_text += section

            i += 1

        # Don't forget the last section
        if current_text.strip():
            chunks.extend(self._split_text(current_text, {
                **metadata,
                "section": current_header
            }))

        return chunks

    def _split_text(self, text: str, metadata: Dict) -> List[Dict]:
        """Split text into overlapping chunks"""
        chunks = []
        words = text.split()

        if len(words) <= self.chunk_size:
            if text.strip():
                chunks.append({
                    "text": text.strip(),
                    "metadata": metadata,
                    "char_count": len(text)
                })
            return chunks

        i = 0
        while i < len(words):
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = " ".join(chunk_words)

            if chunk_text.strip():
                chunks.append({
                    "text": chunk_text.strip(),
                    "metadata": {
                        **metadata,
                        "chunk_index": len(chunks)
                    },
                    "char_count": len(chunk_text)
                })

            i += self.chunk_size - self.overlap

        return chunks


class AIDocIndexer:
    """Index AI CLI documentation into Qdrant"""

    def __init__(self):
        self.chunker = DocumentChunker()
        self.client = None
        self.embedding_model = None

        if QDRANT_AVAILABLE:
            self.client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

        # Initialize embedding model
        if EMBEDDINGS_AVAILABLE:
            logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
            self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        elif FASTEMBED_AVAILABLE:
            logger.info("Using fastembed for embeddings")
            self.embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        else:
            raise RuntimeError("No embedding library available. Install sentence-transformers or fastembed.")

    def create_collection(self):
        """Create or recreate the vector collection"""
        if not self.client:
            logger.error("Qdrant client not available")
            return False

        # Check if collection exists
        collections = self.client.get_collections().collections
        exists = any(c.name == COLLECTION_NAME for c in collections)

        if exists:
            logger.info(f"Collection {COLLECTION_NAME} already exists. Recreating...")
            self.client.delete_collection(COLLECTION_NAME)

        self.client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=EMBEDDING_DIM,
                distance=Distance.COSINE
            )
        )

        logger.info(f"Created collection: {COLLECTION_NAME}")
        return True

    def embed_text(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for text"""
        if isinstance(self.embedding_model, SentenceTransformer):
            return self.embedding_model.encode(texts).tolist()
        else:
            # fastembed
            embeddings = list(self.embedding_model.embed(texts))
            return [e.tolist() for e in embeddings]

    def index_document(self, filepath: Path) -> int:
        """Index a single document"""
        logger.info(f"Indexing: {filepath}")

        content = filepath.read_text()

        # Determine platform from filename
        platform = "unknown"
        if "codex" in filepath.name.lower():
            platform = "codex-cli"
        elif "gemini" in filepath.name.lower():
            platform = "gemini-cli"
        elif "claude" in filepath.name.lower():
            platform = "claude-code"

        metadata = {
            "source": str(filepath),
            "platform": platform,
            "filename": filepath.name,
            "indexed_at": datetime.now().isoformat()
        }

        # Extract title from first header
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            metadata["title"] = title_match.group(1)

        # Chunk the document
        chunks = self.chunker.chunk_markdown(content, metadata)

        if not chunks:
            logger.warning(f"No chunks generated for {filepath}")
            return 0

        # Generate embeddings
        texts = [c["text"] for c in chunks]
        embeddings = self.embed_text(texts)

        # Create points for Qdrant
        points = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            point_id = hashlib.md5(
                f"{filepath}:{i}:{chunk['text'][:100]}".encode()
            ).hexdigest()

            points.append(PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "text": chunk["text"],
                    **chunk["metadata"]
                }
            ))

        # Upsert to Qdrant
        self.client.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )

        logger.info(f"Indexed {len(points)} chunks from {filepath.name}")
        return len(points)

    def index_all_docs(self, docs_dir: Path = None) -> Dict[str, int]:
        """Index all documentation files"""
        if docs_dir is None:
            docs_dir = DOCS_DIR

        if not docs_dir.exists():
            logger.error(f"Documentation directory not found: {docs_dir}")
            return {}

        # Create collection
        self.create_collection()

        results = {}
        total = 0

        for md_file in docs_dir.glob("**/*.md"):
            count = self.index_document(md_file)
            results[md_file.name] = count
            total += count

        logger.info(f"Total indexed: {total} chunks from {len(results)} documents")
        return results

    def search(self, query: str, platform: str = None, limit: int = 5) -> List[Dict]:
        """Search the indexed documentation"""
        if not self.client:
            return []

        # Generate query embedding
        query_embedding = self.embed_text([query])[0]

        # Build filter if platform specified
        query_filter = None
        if platform:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="platform",
                        match=MatchValue(value=platform)
                    )
                ]
            )

        # Search
        results = self.client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_embedding,
            query_filter=query_filter,
            limit=limit
        )

        return [
            {
                "score": r.score,
                "text": r.payload.get("text"),
                "platform": r.payload.get("platform"),
                "section": r.payload.get("section"),
                "source": r.payload.get("source")
            }
            for r in results
        ]


def main():
    """CLI entry point for indexing"""
    import argparse

    parser = argparse.ArgumentParser(description="Index AI CLI documentation")
    parser.add_argument("--docs-dir", type=Path, default=DOCS_DIR,
                       help="Documentation directory")
    parser.add_argument("--search", type=str, help="Search query")
    parser.add_argument("--platform", type=str,
                       choices=["claude-code", "codex-cli", "gemini-cli"],
                       help="Filter by platform")

    args = parser.parse_args()

    indexer = AIDocIndexer()

    if args.search:
        results = indexer.search(args.search, args.platform)
        print(json.dumps(results, indent=2))
    else:
        results = indexer.index_all_docs(args.docs_dir)
        print("\nIndexing complete:")
        for doc, count in results.items():
            print(f"  {doc}: {count} chunks")


if __name__ == "__main__":
    main()
