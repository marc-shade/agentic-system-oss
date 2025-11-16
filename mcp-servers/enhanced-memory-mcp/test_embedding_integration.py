#!/usr/bin/env python3
"""
Comprehensive Embedding Integration Test
Tests all embedding providers, Qdrant integration, and benchmarking
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Any

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from embedding_providers import EmbeddingManager
from neural_memory_fabric import get_nmf
import yaml


class EmbeddingIntegrationTest:
    """Comprehensive test suite for embedding integration"""

    def __init__(self):
        self.config_path = Path(__file__).parent / "nmf_config.yaml"
        self.results = {
            "provider_tests": {},
            "nmf_tests": {},
            "benchmark": {},
            "population": {},
            "search_tests": {}
        }

    def load_config(self) -> Dict:
        """Load NMF configuration"""
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    async def test_provider_availability(self):
        """Test which embedding providers are available"""
        print("\n" + "="*60)
        print("TESTING EMBEDDING PROVIDER AVAILABILITY")
        print("="*60)

        config = self.load_config()
        manager = EmbeddingManager(config['embeddings'])

        available = manager.get_available_providers()
        print(f"\n✅ Available providers: {', '.join(available)}")

        self.results["provider_tests"]["available"] = available

        for provider in available:
            info = manager.get_provider_info(provider)
            print(f"\n📊 {provider}:")
            print(f"   Model: {info['model']}")
            print(f"   Dimensions: {info['dimensions']}")
            print(f"   Local: {info['local']}")

            self.results["provider_tests"][provider] = info

    async def test_embedding_generation(self):
        """Test embedding generation with each provider"""
        print("\n" + "="*60)
        print("TESTING EMBEDDING GENERATION")
        print("="*60)

        config = self.load_config()
        manager = EmbeddingManager(config['embeddings'])

        test_text = "Neural memory fabric with multi-provider embedding support"

        for provider in manager.get_available_providers():
            print(f"\n🧪 Testing {provider}...")
            start = time.time()

            try:
                result = await manager.generate_embedding(test_text, provider=provider)

                if result:
                    print(f"   ✅ Success!")
                    print(f"   Dimensions: {result.dimensions}")
                    print(f"   Latency: {result.latency_ms:.2f}ms")
                    if result.cost_estimate:
                        print(f"   Cost: ${result.cost_estimate:.6f}")

                    self.results["provider_tests"][f"{provider}_generation"] = {
                        "success": True,
                        "dimensions": result.dimensions,
                        "latency_ms": result.latency_ms,
                        "cost": result.cost_estimate
                    }
                else:
                    print(f"   ❌ Failed to generate embedding")
                    self.results["provider_tests"][f"{provider}_generation"] = {
                        "success": False
                    }

            except Exception as e:
                print(f"   ❌ Error: {e}")
                self.results["provider_tests"][f"{provider}_generation"] = {
                    "success": False,
                    "error": str(e)
                }

    async def test_nmf_initialization(self):
        """Test NMF initialization with Qdrant"""
        print("\n" + "="*60)
        print("TESTING NMF INITIALIZATION")
        print("="*60)

        try:
            nmf = await get_nmf()
            print("\n✅ NMF initialized successfully")

            # Check if vector backend is connected
            if nmf.vector_db:
                print("✅ Qdrant vector backend connected")
                print(f"   Collection: {nmf.vector_collection_name}")

                # Get collection info
                from qdrant_client import QdrantClient
                client = QdrantClient(host="localhost", port=6333)
                collection_info = client.get_collection(nmf.vector_collection_name)
                print(f"   Vectors: {collection_info.points_count}")
                print(f"   Vector size: {collection_info.config.params.vectors.size}")

                self.results["nmf_tests"]["qdrant"] = {
                    "connected": True,
                    "collection": nmf.vector_collection_name,
                    "points_count": collection_info.points_count,
                    "vector_size": collection_info.config.params.vectors.size
                }
            else:
                print("⚠️  Qdrant vector backend not connected")
                self.results["nmf_tests"]["qdrant"] = {"connected": False}

            # Check embedding manager
            if nmf.embedding_manager:
                print("✅ Embedding manager initialized")
                available = nmf.embedding_manager.get_available_providers()
                print(f"   Providers: {', '.join(available)}")

                self.results["nmf_tests"]["embedding_manager"] = {
                    "initialized": True,
                    "providers": available
                }
            else:
                print("⚠️  Embedding manager not initialized")
                self.results["nmf_tests"]["embedding_manager"] = {"initialized": False}

        except Exception as e:
            print(f"❌ NMF initialization failed: {e}")
            self.results["nmf_tests"]["error"] = str(e)

    async def test_memory_storage(self):
        """Test storing memories with embeddings"""
        print("\n" + "="*60)
        print("TESTING MEMORY STORAGE WITH EMBEDDINGS")
        print("="*60)

        try:
            nmf = await get_nmf()

            test_memories = [
                {
                    "content": "Embedding integration test - multi-provider support with Qdrant",
                    "tags": ["test", "embedding", "qdrant"]
                },
                {
                    "content": "Apple MLX provides local embedding generation on Apple Silicon",
                    "tags": ["test", "mlx", "local"]
                },
                {
                    "content": "Semantic search enables finding similar memories using vector similarity",
                    "tags": ["test", "search", "semantic"]
                }
            ]

            stored = []
            for i, memory in enumerate(test_memories):
                print(f"\n📝 Storing memory {i+1}...")
                result = await nmf.remember(
                    content=memory["content"],
                    metadata={"tags": memory["tags"]},
                    agent_id="test_agent"
                )

                if result.get("success"):
                    print(f"   ✅ Stored: {result['memory_id']}")
                    stored.append(result['memory_id'])
                else:
                    print(f"   ❌ Failed to store")

            self.results["nmf_tests"]["storage"] = {
                "attempted": len(test_memories),
                "stored": len(stored),
                "memory_ids": stored
            }

            print(f"\n✅ Successfully stored {len(stored)}/{len(test_memories)} memories")

        except Exception as e:
            print(f"❌ Memory storage failed: {e}")
            self.results["nmf_tests"]["storage"] = {"error": str(e)}

    async def test_semantic_search(self):
        """Test semantic search with embeddings"""
        print("\n" + "="*60)
        print("TESTING SEMANTIC SEARCH")
        print("="*60)

        try:
            nmf = await get_nmf()

            test_queries = [
                "embedding technology",
                "local AI models",
                "vector similarity search"
            ]

            for query in test_queries:
                print(f"\n🔍 Query: '{query}'")
                results = await nmf.recall(
                    query=query,
                    mode="semantic",
                    agent_id="test_agent",
                    limit=3
                )

                print(f"   Found {len(results)} results:")
                for i, result in enumerate(results[:3]):
                    print(f"   {i+1}. {result.get('content', '')[:60]}...")
                    print(f"      Similarity: {result.get('similarity_score', 0):.3f}")

                self.results["search_tests"][query] = {
                    "count": len(results),
                    "top_scores": [r.get('similarity_score', 0) for r in results[:3]]
                }

        except Exception as e:
            print(f"❌ Semantic search failed: {e}")
            self.results["search_tests"]["error"] = str(e)

    async def test_hybrid_retrieval(self):
        """Test hybrid retrieval (semantic + graph + temporal)"""
        print("\n" + "="*60)
        print("TESTING HYBRID RETRIEVAL")
        print("="*60)

        try:
            nmf = await get_nmf()

            query = "embedding and search"
            print(f"\n🔍 Hybrid search: '{query}'")

            results = await nmf.recall(
                query=query,
                mode="hybrid",
                agent_id="test_agent",
                limit=5
            )

            print(f"   Found {len(results)} results via hybrid search:")
            for i, result in enumerate(results[:5]):
                print(f"   {i+1}. {result.get('content', '')[:60]}...")
                print(f"      Score: {result.get('similarity_score', 0):.3f}")
                print(f"      Source: {result.get('source', 'unknown')}")

            self.results["search_tests"]["hybrid"] = {
                "count": len(results),
                "sources": [r.get('source', 'unknown') for r in results]
            }

        except Exception as e:
            print(f"❌ Hybrid retrieval failed: {e}")
            self.results["search_tests"]["hybrid_error"] = str(e)

    async def benchmark_providers(self):
        """Benchmark all available embedding providers"""
        print("\n" + "="*60)
        print("BENCHMARKING EMBEDDING PROVIDERS")
        print("="*60)

        config = self.load_config()
        manager = EmbeddingManager(config['embeddings'])

        # Use test queries from config
        test_queries = config.get('benchmarking', {}).get('test_queries', [
            "memory system architecture",
            "agent collaboration",
            "vector embeddings"
        ])

        print(f"\n📊 Running benchmark with {len(test_queries)} test queries...")
        results = await manager.benchmark_providers(test_queries)

        print("\n" + "-"*60)
        print("BENCHMARK RESULTS")
        print("-"*60)

        for provider, stats in results["providers"].items():
            print(f"\n🏆 {provider.upper()}")
            print(f"   Success rate: {stats['successful']}/{results['test_count']}")

            if stats['successful'] > 0:
                print(f"   Avg latency: {stats['avg_latency_ms']:.2f}ms")
                print(f"   Min latency: {stats['min_latency_ms']:.2f}ms")
                print(f"   Max latency: {stats['max_latency_ms']:.2f}ms")
                print(f"   Dimensions: {stats['dimensions']}")

                if stats['total_cost'] > 0:
                    print(f"   Total cost: ${stats['total_cost']:.6f}")

        self.results["benchmark"] = results

    async def populate_from_memory_db(self):
        """Populate Qdrant with existing memory-db entities"""
        print("\n" + "="*60)
        print("POPULATING QDRANT FROM MEMORY-DB")
        print("="*60)

        try:
            from memory_client import MemoryClient

            # Get entities from memory-db
            client = MemoryClient()
            status = await client.get_memory_status()

            total_entities = status['entities']['total']
            print(f"\n📊 Found {total_entities} entities in memory-db")

            # Search for sample entities
            sample = await client.search_nodes("", limit=10)
            print(f"   Retrieved {sample['count']} sample entities")

            # Store in NMF with embeddings
            nmf = await get_nmf()
            stored = 0

            for entity in sample['results']:
                content = " ".join(entity.get('observations', []))
                if content:
                    result = await nmf.remember(
                        content=content,
                        metadata={
                            "source": "memory-db",
                            "entity_name": entity['name'],
                            "entity_type": entity['entityType']
                        },
                        agent_id="memory_migration"
                    )

                    if result.get("success"):
                        stored += 1
                        print(f"   ✅ Migrated: {entity['name']}")

            print(f"\n✅ Successfully migrated {stored}/{sample['count']} entities to Qdrant")

            self.results["population"] = {
                "total_memory_db": total_entities,
                "sampled": sample['count'],
                "migrated": stored
            }

        except Exception as e:
            print(f"❌ Population failed: {e}")
            self.results["population"] = {"error": str(e)}

    def save_results(self):
        """Save test results to file"""
        results_file = Path.home() / ".claude" / "enhanced_memories" / "embedding_test_results.json"
        results_file.parent.mkdir(parents=True, exist_ok=True)

        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        print(f"\n💾 Results saved to: {results_file}")

    async def run_all_tests(self):
        """Run all integration tests"""
        print("\n" + "="*60)
        print("EMBEDDING INTEGRATION TEST SUITE")
        print("="*60)

        start_time = time.time()

        try:
            # Phase 1: Provider tests
            await self.test_provider_availability()
            await self.test_embedding_generation()

            # Phase 2: NMF tests
            await self.test_nmf_initialization()
            await self.test_memory_storage()

            # Phase 3: Search tests
            await self.test_semantic_search()
            await self.test_hybrid_retrieval()

            # Phase 4: Benchmark
            await self.benchmark_providers()

            # Phase 5: Population
            await self.populate_from_memory_db()

        except Exception as e:
            print(f"\n❌ Test suite error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            elapsed = time.time() - start_time
            print("\n" + "="*60)
            print(f"TEST SUITE COMPLETED IN {elapsed:.2f}s")
            print("="*60)

            self.save_results()


async def main():
    """Main entry point"""
    test = EmbeddingIntegrationTest()
    await test.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
