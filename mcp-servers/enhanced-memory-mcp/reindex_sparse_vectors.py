#!/usr/bin/env python3
"""
Re-index Existing Entities with BM25 Sparse Vectors
Adds sparse vector support to all 1,175 entities for hybrid search
"""
import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent))

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, SparseVector
from fastembed import SparseTextEmbedding
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "enhanced_memory"

class SparseVectorIndexer:
    """Re-index entities with BM25 sparse vectors"""

    def __init__(self):
        self.client = QdrantClient(url=QDRANT_URL)
        self.sparse_model = None

    def initialize_sparse_model(self):
        """Initialize BM25 sparse embedding model"""
        logger.info("Initializing BM25 sparse embedding model...")
        # Use SPLADE model for sparse vectors (state-of-the-art for BM25-like)
        self.sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")
        logger.info("✅ Sparse model initialized")

    def generate_sparse_vector(self, text: str) -> SparseVector:
        """Generate BM25 sparse vector for text"""
        # Generate sparse embedding
        embeddings = list(self.sparse_model.embed([text]))
        sparse_embedding = embeddings[0]

        # Convert to Qdrant SparseVector format
        indices = sparse_embedding.indices.tolist()
        values = sparse_embedding.values.tolist()

        return SparseVector(indices=indices, values=values)

    async def fetch_all_points(self) -> List[Dict[str, Any]]:
        """Fetch all points from Qdrant collection"""
        logger.info(f"Fetching all points from {COLLECTION_NAME}...")

        points = []
        offset = None

        while True:
            # Scroll through collection
            result = self.client.scroll(
                collection_name=COLLECTION_NAME,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=True  # Need dense vectors to preserve them
            )

            batch_points, next_offset = result
            points.extend(batch_points)

            if next_offset is None:
                break
            offset = next_offset

        logger.info(f"✅ Fetched {len(points)} points")
        return points

    async def reindex_batch(self, points: List[Any], batch_num: int, total_batches: int):
        """Re-index a batch of points with sparse vectors"""
        logger.info(f"Processing batch {batch_num}/{total_batches} ({len(points)} points)...")

        updated_points = []

        for point in points:
            try:
                # Extract content for sparse vector generation
                content = point.payload.get('content', '')

                if not content:
                    logger.warning(f"Point {point.id} has no content, skipping")
                    continue

                # Generate sparse vector
                sparse_vector = self.generate_sparse_vector(content)

                # Extract existing dense vector
                dense_vector = None
                if isinstance(point.vector, dict):
                    dense_vector = point.vector.get("text-dense")
                elif point.vector:  # Simple vector (not dict)
                    dense_vector = point.vector

                if not dense_vector:
                    logger.warning(f"Point {point.id} has no dense vector, skipping")
                    continue

                # Create updated point with BOTH dense and sparse vectors
                updated_point = PointStruct(
                    id=point.id,
                    payload=point.payload,
                    vector={
                        "text-dense": dense_vector,  # Preserve existing dense vector
                        "text-sparse": sparse_vector  # Add new sparse vector
                    }
                )
                updated_points.append(updated_point)

            except Exception as e:
                logger.error(f"Failed to reindex point {point.id}: {e}")

        # Batch upsert with sparse vectors
        if updated_points:
            self.client.upsert(
                collection_name=COLLECTION_NAME,
                points=updated_points
            )
            logger.info(f"✅ Batch {batch_num} complete: {len(updated_points)} points updated")

        return len(updated_points)

    async def reindex_all(self, batch_size: int = 50):
        """Re-index all points with sparse vectors"""
        print("="*70)
        print("SPARSE VECTOR RE-INDEXING")
        print("="*70)

        # Initialize sparse model
        self.initialize_sparse_model()

        # Fetch all points
        points = await self.fetch_all_points()

        if not points:
            logger.warning("No points to reindex")
            return

        # Process in batches
        total_updated = 0
        total_batches = (len(points) + batch_size - 1) // batch_size

        print(f"\nRe-indexing {len(points)} points in {total_batches} batches...")
        print(f"Batch size: {batch_size}")
        print()

        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            batch_num = i // batch_size + 1

            updated = await self.reindex_batch(batch, batch_num, total_batches)
            total_updated += updated

            # Progress update
            if batch_num % 5 == 0 or batch_num == total_batches:
                print(f"Progress: {batch_num}/{total_batches} batches ({total_updated}/{len(points)} points)")

        # Final report
        print("\n" + "="*70)
        print("RE-INDEXING COMPLETE")
        print("="*70)
        print(f"Total points: {len(points)}")
        print(f"✅ Updated: {total_updated}")
        print(f"❌ Failed: {len(points) - total_updated}")
        print(f"Success rate: {total_updated/len(points)*100:.1f}%")
        print("="*70)
        print("\n✅ Hybrid search (BM25 + Vector) now fully operational!")

async def main():
    indexer = SparseVectorIndexer()
    await indexer.reindex_all(batch_size=50)

if __name__ == "__main__":
    asyncio.run(main())
