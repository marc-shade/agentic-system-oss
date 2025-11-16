#!/usr/bin/env python3
"""
Atomic Qdrant Collection Schema Upgrade with Zero-Downtime
Uses collection aliases for instant switchover to sparse vector support
"""
import asyncio
import logging
from datetime import datetime
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams, Distance, SparseVectorParams, SparseIndexParams,
    PointStruct
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

QDRANT_URL = "http://localhost:6333"
COLLECTION_ALIAS = "enhanced_memory"
NEW_COLLECTION = "enhanced_memory_v2"

async def upgrade_collection_atomic():
    """Atomic collection upgrade with alias switchover"""
    print("="*80)
    print("ATOMIC QDRANT COLLECTION UPGRADE - ZERO DOWNTIME")
    print("="*80)

    client = QdrantClient(url=QDRANT_URL)

    # Step 1: Get current collection
    print("\n📊 Step 1: Analyzing current state...")
    
    try:
        current_info = client.get_collection(collection_name=COLLECTION_ALIAS)
        point_count = current_info.points_count
        vectors_config = current_info.config.params.vectors
        
        print(f"   Points: {point_count:,}")
        
        # Check if already upgraded
        if isinstance(vectors_config, dict) and "text-sparse" in str(vectors_config):
            print("\n✅ Collection already supports sparse vectors!")
            return
            
    except Exception as e:
        logger.error(f"Failed to get collection info: {e}")
        return

    # Step 2: Create new collection
    print(f"\n🔧 Step 2: Creating '{NEW_COLLECTION}' with sparse vectors...")
    
    try:
        try:
            client.delete_collection(collection_name=NEW_COLLECTION)
        except:
            pass
            
        client.create_collection(
            collection_name=NEW_COLLECTION,
            vectors_config={
                "text-dense": VectorParams(size=768, distance=Distance.COSINE),
            },
            sparse_vectors_config={
                "text-sparse": SparseVectorParams(
                    index=SparseIndexParams(on_disk=False)
                )
            }
        )
        print(f"✅ Created with dense (768d) + sparse (BM25) support")
        
    except Exception as e:
        logger.error(f"Failed to create collection: {e}")
        return

    # Step 3: Migrate points
    print(f"\n📦 Step 3: Migrating {point_count:,} points...")
    
    migrated = 0
    batch_size = 100
    
    try:
        offset = None
        
        while True:
            result = client.scroll(
                collection_name=COLLECTION_ALIAS,
                limit=batch_size,
                offset=offset,
                with_payload=True,
                with_vectors=True
            )
            
            batch_points, next_offset = result
            
            if not batch_points:
                break
                
            new_points = []
            for point in batch_points:
                try:
                    dense_vector = point.vector if not isinstance(point.vector, dict) else point.vector.get("text-dense", list(point.vector.values())[0])
                    
                    new_points.append(PointStruct(
                        id=point.id,
                        payload=point.payload,
                        vector={"text-dense": dense_vector}
                    ))
                except Exception as e:
                    logger.error(f"Failed point {point.id}: {e}")
                    
            if new_points:
                client.upsert(collection_name=NEW_COLLECTION, points=new_points)
                migrated += len(new_points)
                
                if migrated % 500 == 0 or migrated == point_count:
                    print(f"   Progress: {migrated:,}/{point_count:,} ({migrated/point_count*100:.1f}%)")
                    
            if next_offset is None:
                break
            offset = next_offset
            
        print(f"✅ Migrated {migrated:,} points")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return

    # Step 4: Verify
    print(f"\n🔍 Step 4: Verifying...")
    
    new_info = client.get_collection(collection_name=NEW_COLLECTION)
    new_count = new_info.points_count
    
    if new_count != point_count:
        print(f"⚠️  Count mismatch! {point_count:,} → {new_count:,}")
        return
    else:
        print(f"✅ Verification passed: {new_count:,} points")

    # Step 5: Atomic switchover
    print(f"\n🔄 Step 5: Atomic alias switchover...")
    
    try:
        client.update_collection_aliases(
            change_aliases_operations=[
                {"create_alias": {
                    "collection_name": NEW_COLLECTION,
                    "alias_name": COLLECTION_ALIAS
                }}
            ]
        )
        print(f"✅ Alias '{COLLECTION_ALIAS}' → '{NEW_COLLECTION}'")
        print(f"   Zero-downtime switchover complete!")
        
    except Exception as e:
        logger.error(f"Switchover failed: {e}")
        return

    print("\n" + "="*80)
    print("✅ ATOMIC UPGRADE COMPLETE")
    print("="*80)
    print(f"Active: {COLLECTION_ALIAS} (alias)")
    print(f"Physical: {NEW_COLLECTION}")
    print(f"Migrated: {migrated:,} points")
    print(f"\nNext: Run reindex_sparse_vectors.py")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(upgrade_collection_atomic())
