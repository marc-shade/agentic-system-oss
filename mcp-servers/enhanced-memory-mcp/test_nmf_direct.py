#!/usr/bin/env python3
"""Test NMF recall directly"""
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

async def test_nmf_recall():
    from neural_memory_fabric import get_nmf
    
    nmf = await get_nmf()
    
    print("\n" + "="*70)
    print("Testing NMF recall with named vectors...")
    print("="*70)
    
    results = await nmf.recall(query="voice communication system", mode="semantic", limit=20)
    
    print(f"\nResults: {len(results) if results else 0}")
    if results:
        for i, r in enumerate(results[:5], 1):
            print(f"{i}. Score: {r.get('similarity_score', 'N/A')}")
            print(f"   Content: {r.get('content', 'N/A')[:100]}")
    else:
        print("⚠️  No results returned")

asyncio.run(test_nmf_recall())
