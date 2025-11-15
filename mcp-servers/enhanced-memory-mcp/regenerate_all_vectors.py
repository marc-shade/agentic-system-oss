#!/usr/bin/env python3
"""
Regenerate ALL vectors (dense + sparse) for all entities
CRITICAL: Previous reindex accidentally deleted dense vectors
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
from neural_memory_fabric import get_nmf

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "enhanced_memory"

class VectorRegenerator:
    """Regenerate both dense and sparse vectors"""

    def __init__(self):
        self.client = QdrantClient(url=QDRANT_URL)
        self.sparse_model = None
        self.nmf = None

    async def initialize(self):
        """Initialize embedding models"""
        logger.info("Initializing embedding models...")

        # Initialize sparse model (BM25)
        self.sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")
        logger.info("✅ Sparse model (BM25) initialized")

        # Initialize NMF for dense embeddings
        self.nmf = await get_nmf()
        logger.info("✅ NMF initialized for dense embeddings")

    def generate_sparse_vector(self, text: str) -> SparseVector:
        """Generate BM25 sparse vector"""
        embeddings = list(self.sparse_model.embed([text]))
        sparse_embedding = embeddings[0]
        indices = sparse_embedding.indices.tolist()
        values = sparse_embedding.values.tolist()
        return SparseVector(indices=indices, values=values)

    async def generate_dense_vector(self, text: str) -> List[float]:
        """Generate dense embedding vector"""
        embedding_result = await self.nmf.embedding_manager.generate_embedding(text)
        return embedding_result.embedding if hasattr(embedding_result, 'embedding') else embedding_result

    async def fetch_all_points(self) -> List[Dict[str, Any]]:
        """Fetch all points from collection"""
        logger.info(f"Fetching all points from {COLLECTION_NAME}...")

        points = []
        offset = None

        while True:
            result = self.client.scroll(
                collection_name=COLLECTION_NAME,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False  # Don't need existing vectors
            )

            batch_points, next_offset = result
            points.extend(batch_points)

            if next_offset is None:
                break
            offset = next_offset

        logger.info(f"✅ Fetched {len(points)} points")
        return points

    async def regenerate_batch(self, points: List[Any], batch_num: int, total_batches: int):
        """Regenerate vectors for a batch of points"""
        logger.info(f"Processing batch {batch_num}/{total_batches} ({len(points)} points)...")

        updated_points = []

        for point in points:
            try:
                # Extract content
                content = point.payload.get('content', '')

                if not content:
                    logger.warning(f"Point {point.id} has no content, skipping")
                    continue

                # Generate BOTH dense and sparse vectors
                dense_vector = await self.generate_dense_vector(content)
                sparse_vector = self.generate_sparse_vector(content)

                # Create updated point with BOTH vectors
                updated_point = PointStruct(
                    id=point.id,
                    payload=point.payload,
                    vector={
                        "text-dense": dense_vector,    # Dense embedding (768d)
                        "text-sparse": sparse_vector   # Sparse BM25
                    }
                )
                updated_points.append(updated_point)

            except Exception as e:
                logger.error(f"Failed to regenerate vectors for point {point.id}: {e}")

        # Batch upsert
        if updated_points:
            self.client.upsert(
                collection_name=COLLECTION_NAME,
                points=updated_points
            )
            logger.info(f"✅ Batch {batch_num} complete: {len(updated_points)} points updated")

        return len(updated_points)

    async def regenerate_all(self, batch_size: int = 25):
        """Regenerate all vectors"""
        print("="*70)
        print("VECTOR REGENERATION - DENSE + SPARSE")
        print("="*70)

        # Initialize models
        await self.initialize()

        # Fetch all points
        points = await self.fetch_all_points()

        if not points:
            logger.warning("No points to regenerate")
            return

        # Process in batches
        total_updated = 0
        total_batches = (len(points) + batch_size - 1) // batch_size

        print(f"\nRegenerating vectors for {len(points)} points in {total_batches} batches...")
        print(f"Batch size: {batch_size}")
        print()

        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            batch_num = i // batch_size + 1

            updated = await self.regenerate_batch(batch, batch_num, total_batches)
            total_updated += updated

            # Progress update
            if batch_num % 5 == 0 or batch_num == total_batches:
                print(f"Progress: {batch_num}/{total_batches} batches ({total_updated}/{len(points)} points)")

        # Final report
        print("\n" + "="*70)
        print("VECTOR REGENERATION COMPLETE")
        print("="*70)
        print(f"Total points: {len(points)}")
        print(f"✅ Updated: {total_updated}")
        print(f"❌ Failed: {len(points) - total_updated}")
        print(f"Success rate: {total_updated/len(points)*100:.1f}%")
        print("="*70)
        print("\n✅ All vectors regenerated! Dense (768d) + Sparse (BM25)")

async def main():
    regenerator = VectorRegenerator()
    await regenerator.regenerate_all(batch_size=25)

if __name__ == "__main__":
    asyncio.run(main())
