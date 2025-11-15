#!/usr/bin/env python3
"""
Embedding Provider Benchmark Suite
Comprehensive testing of all embedding providers with quality and performance metrics
"""

import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import yaml
from dataclasses import dataclass, asdict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from embedding_providers import EmbeddingManager, EmbeddingResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Results for a single provider benchmark"""
    provider: str
    test_count: int
    successful: int
    failed: int
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    median_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    total_cost: float
    avg_cost_per_embedding: float
    dimensions: int
    local: bool
    errors: List[str]


@dataclass
class QualityMetric:
    """Quality metrics for semantic search"""
    query: str
    provider: str
    top_result: str
    similarity_score: float
    latency_ms: float
    rank_position: int


class ProviderBenchmark:
    """Benchmark suite for embedding providers"""

    def __init__(self, config_path: Optional[str] = None):
        # Load config
        if not config_path:
            config_path = Path(__file__).parent / "nmf_config.yaml"

        with open(config_path) as f:
            config = yaml.safe_load(f)

        self.manager = EmbeddingManager(config['embeddings'])
        self.test_queries = config.get('benchmarking', {}).get('test_queries', [])

        # Add more diverse test queries
        self.test_queries.extend([
            "artificial intelligence and machine learning",
            "vector database similarity search",
            "neural network embeddings",
            "natural language processing",
            "semantic search optimization",
            "distributed systems architecture",
            "real-time data processing",
            "machine learning model training",
            "cloud infrastructure deployment",
            "API design best practices"
        ])

    async def benchmark_provider_latency(
        self,
        provider: str,
        test_texts: List[str]
    ) -> BenchmarkResult:
        """Benchmark a single provider's latency and reliability"""
        logger.info(f"Benchmarking {provider} latency...")

        latencies = []
        costs = []
        dimensions = 0
        successful = 0
        failed = 0
        errors = []

        provider_info = self.manager.get_provider_info(provider)
        is_local = provider_info.get('local', False) if provider_info else False

        for i, text in enumerate(test_texts):
            try:
                result = await self.manager.generate_embedding(text, provider=provider)

                if result:
                    successful += 1
                    latencies.append(result.latency_ms)
                    dimensions = result.dimensions

                    if result.cost_estimate:
                        costs.append(result.cost_estimate)

                    if (i + 1) % 10 == 0:
                        logger.info(f"{provider}: {i + 1}/{len(test_texts)} completed")
                else:
                    failed += 1
                    errors.append(f"Test {i + 1}: No result returned")

            except Exception as e:
                failed += 1
                errors.append(f"Test {i + 1}: {str(e)}")
                logger.error(f"{provider} failed on test {i + 1}: {e}")

        # Calculate statistics
        if latencies:
            latencies.sort()
            avg_latency = sum(latencies) / len(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            median_latency = latencies[len(latencies) // 2]
            p95_latency = latencies[int(len(latencies) * 0.95)] if len(latencies) > 1 else max_latency
            p99_latency = latencies[int(len(latencies) * 0.99)] if len(latencies) > 1 else max_latency
        else:
            avg_latency = min_latency = max_latency = median_latency = p95_latency = p99_latency = 0

        total_cost = sum(costs) if costs else 0
        avg_cost = total_cost / len(costs) if costs else 0

        return BenchmarkResult(
            provider=provider,
            test_count=len(test_texts),
            successful=successful,
            failed=failed,
            avg_latency_ms=avg_latency,
            min_latency_ms=min_latency,
            max_latency_ms=max_latency,
            median_latency_ms=median_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            total_cost=total_cost,
            avg_cost_per_embedding=avg_cost,
            dimensions=dimensions,
            local=is_local,
            errors=errors[:10]  # Keep first 10 errors
        )

    async def benchmark_search_quality(
        self,
        providers: List[str],
        test_corpus: List[str],
        test_queries: List[str]
    ) -> Dict[str, List[QualityMetric]]:
        """Benchmark semantic search quality across providers"""
        logger.info("Benchmarking search quality...")

        # Generate embeddings for test corpus with each provider
        corpus_embeddings = {}

        for provider in providers:
            logger.info(f"Generating corpus embeddings with {provider}...")
            embeddings = []

            for text in test_corpus:
                result = await self.manager.generate_embedding(text, provider=provider)
                if result:
                    embeddings.append(result.embedding)
                else:
                    logger.warning(f"{provider} failed to embed: {text[:50]}...")

            corpus_embeddings[provider] = embeddings

        # Test queries against each provider's embeddings
        quality_metrics = {provider: [] for provider in providers}

        for query in test_queries:
            logger.info(f"Testing query: '{query}'")

            for provider in providers:
                if provider not in corpus_embeddings or not corpus_embeddings[provider]:
                    continue

                try:
                    start_time = time.time()

                    # Generate query embedding
                    query_result = await self.manager.generate_embedding(query, provider=provider)
                    if not query_result:
                        continue

                    latency_ms = (time.time() - start_time) * 1000

                    # Calculate similarities with corpus
                    similarities = []
                    for i, corpus_embedding in enumerate(corpus_embeddings[provider]):
                        similarity = self._cosine_similarity(query_result.embedding, corpus_embedding)
                        similarities.append((i, similarity))

                    # Sort by similarity
                    similarities.sort(key=lambda x: x[1], reverse=True)

                    # Record top result
                    if similarities:
                        top_idx, top_score = similarities[0]
                        quality_metrics[provider].append(QualityMetric(
                            query=query,
                            provider=provider,
                            top_result=test_corpus[top_idx][:100],
                            similarity_score=top_score,
                            latency_ms=latency_ms,
                            rank_position=1
                        ))

                except Exception as e:
                    logger.error(f"{provider} failed on query '{query}': {e}")

        return quality_metrics

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if len(vec1) != len(vec2):
            # If dimensions don't match (e.g., MLX is 384, others are 768)
            # Can't compare directly
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def print_latency_report(self, results: Dict[str, BenchmarkResult]):
        """Print latency benchmark results"""
        print()
        print("=" * 90)
        print("LATENCY BENCHMARK RESULTS")
        print("=" * 90)
        print()

        # Sort by average latency
        sorted_results = sorted(results.items(), key=lambda x: x[1].avg_latency_ms)

        print(f"{'Provider':<15} {'Success':<10} {'Avg (ms)':<12} {'Min':<10} {'Max':<10} {'P95':<10} {'P99':<10}")
        print("-" * 90)

        for provider, result in sorted_results:
            success_rate = f"{result.successful}/{result.test_count}"
            print(
                f"{provider:<15} "
                f"{success_rate:<10} "
                f"{result.avg_latency_ms:<12.2f} "
                f"{result.min_latency_ms:<10.2f} "
                f"{result.max_latency_ms:<10.2f} "
                f"{result.p95_latency_ms:<10.2f} "
                f"{result.p99_latency_ms:<10.2f}"
            )

        print()
        print("Cost Analysis:")
        print("-" * 90)
        print(f"{'Provider':<15} {'Local':<10} {'Total Cost':<15} {'Per Embedding':<15} {'Dimensions':<12}")
        print("-" * 90)

        for provider, result in sorted_results:
            local_str = "✅ Yes" if result.local else "❌ No"
            cost_str = f"${result.total_cost:.6f}" if result.total_cost > 0 else "Free"
            per_embedding_str = f"${result.avg_cost_per_embedding:.8f}" if result.avg_cost_per_embedding > 0 else "Free"

            print(
                f"{provider:<15} "
                f"{local_str:<10} "
                f"{cost_str:<15} "
                f"{per_embedding_str:<15} "
                f"{result.dimensions:<12}"
            )

        print("=" * 90)

    def print_quality_report(self, quality_metrics: Dict[str, List[QualityMetric]]):
        """Print search quality results"""
        print()
        print("=" * 90)
        print("SEARCH QUALITY RESULTS")
        print("=" * 90)
        print()

        for provider, metrics in quality_metrics.items():
            if not metrics:
                continue

            print(f"\n{provider.upper()} Results:")
            print("-" * 90)

            avg_score = sum(m.similarity_score for m in metrics) / len(metrics)
            avg_latency = sum(m.latency_ms for m in metrics) / len(metrics)

            print(f"Average Similarity Score: {avg_score:.4f} ({avg_score * 100:.2f}%)")
            print(f"Average Query Latency: {avg_latency:.2f}ms")
            print()

            # Show top 5 queries
            top_queries = sorted(metrics, key=lambda x: x.similarity_score, reverse=True)[:5]
            print("Top 5 Results:")
            for i, metric in enumerate(top_queries, 1):
                print(f"{i}. Query: '{metric.query}'")
                print(f"   Match: {metric.top_result}")
                print(f"   Similarity: {metric.similarity_score:.4f} ({metric.similarity_score * 100:.2f}%)")
                print()

        print("=" * 90)

    def generate_recommendations(
        self,
        latency_results: Dict[str, BenchmarkResult],
        quality_metrics: Dict[str, List[QualityMetric]]
    ) -> str:
        """Generate provider recommendations based on results"""
        recommendations = [
            "",
            "=" * 90,
            "PROVIDER RECOMMENDATIONS",
            "=" * 90,
            ""
        ]

        # Find best performers
        fastest = min(latency_results.items(), key=lambda x: x[1].avg_latency_ms)
        most_reliable = max(latency_results.items(), key=lambda x: x[1].successful / x[1].test_count)

        # Calculate average quality scores
        quality_scores = {}
        for provider, metrics in quality_metrics.items():
            if metrics:
                quality_scores[provider] = sum(m.similarity_score for m in metrics) / len(metrics)

        best_quality = max(quality_scores.items(), key=lambda x: x[1]) if quality_scores else None

        # Local vs Cloud
        local_providers = [p for p, r in latency_results.items() if r.local]
        cloud_providers = [p for p, r in latency_results.items() if not r.local]

        recommendations.extend([
            "🏆 BEST OVERALL PERFORMANCE:",
            f"   Fastest: {fastest[0]} ({fastest[1].avg_latency_ms:.2f}ms average)",
            f"   Most Reliable: {most_reliable[0]} ({most_reliable[1].successful}/{most_reliable[1].test_count} success)",
        ])

        if best_quality:
            recommendations.append(f"   Best Quality: {best_quality[0]} ({best_quality[1] * 100:.2f}% avg similarity)")

        recommendations.extend([
            "",
            "💡 USE CASE RECOMMENDATIONS:",
            ""
        ])

        if local_providers:
            fastest_local = min(
                [(p, r) for p, r in latency_results.items() if r.local],
                key=lambda x: x[1].avg_latency_ms
            )
            recommendations.extend([
                f"🔒 High-Volume/Privacy (Local): {fastest_local[0]}",
                f"   - Average latency: {fastest_local[1].avg_latency_ms:.2f}ms",
                f"   - No API costs",
                f"   - Complete privacy",
                ""
            ])

        if cloud_providers:
            best_cloud = min(
                [(p, r) for p, r in latency_results.items() if not r.local],
                key=lambda x: x[1].avg_latency_ms
            )
            recommendations.extend([
                f"☁️  Best Quality (Cloud): {best_cloud[0]}",
                f"   - Average latency: {best_cloud[1].avg_latency_ms:.2f}ms",
                f"   - Dimensions: {best_cloud[1].dimensions}",
                ""
            ])

        # Cost analysis
        free_providers = [p for p, r in latency_results.items() if r.total_cost == 0]
        if free_providers:
            recommendations.extend([
                f"💰 Cost-Effective Options: {', '.join(free_providers)}",
                "   - No API costs",
                ""
            ])

        recommendations.extend([
            "🎯 RECOMMENDED STRATEGY:",
            f"   1. Primary: {fastest[0]} (fastest response)",
            f"   2. Fallback: {most_reliable[0]} (most reliable)",
        ])

        if local_providers:
            recommendations.append(f"   3. High-volume: {local_providers[0]} (free local processing)")

        recommendations.append("")
        recommendations.append("=" * 90)

        return "\n".join(recommendations)


async def main():
    """Run comprehensive benchmark suite"""
    import argparse

    parser = argparse.ArgumentParser(description='Benchmark embedding providers')
    parser.add_argument('--providers', nargs='+', help='Specific providers to test')
    parser.add_argument('--skip-latency', action='store_true', help='Skip latency benchmarks')
    parser.add_argument('--skip-quality', action='store_true', help='Skip quality benchmarks')
    parser.add_argument('--quick', action='store_true', help='Quick test with fewer samples')
    args = parser.parse_args()

    print("=" * 90)
    print("EMBEDDING PROVIDER BENCHMARK SUITE")
    print("=" * 90)

    try:
        # Initialize benchmark
        benchmark = ProviderBenchmark()

        # Get available providers
        available_providers = benchmark.manager.get_available_providers()
        test_providers = args.providers if args.providers else available_providers

        # Filter to only available
        test_providers = [p for p in test_providers if p in available_providers]

        if not test_providers:
            print("❌ No providers available for testing")
            return

        print(f"Testing providers: {', '.join(test_providers)}")
        print()

        # Prepare test data
        if args.quick:
            test_texts = benchmark.test_queries[:10]
            test_corpus = benchmark.test_queries[:20]
            test_queries = benchmark.test_queries[:5]
        else:
            test_texts = benchmark.test_queries
            test_corpus = benchmark.test_queries + [
                "Python programming language features",
                "JavaScript async await patterns",
                "Database indexing strategies",
                "Microservices communication patterns",
                "Container orchestration with Kubernetes"
            ]
            test_queries = benchmark.test_queries[:10]

        # Latency benchmarks
        latency_results = {}
        if not args.skip_latency:
            print("🔬 Running latency benchmarks...")
            print()

            for provider in test_providers:
                result = await benchmark.benchmark_provider_latency(provider, test_texts)
                latency_results[provider] = result

            benchmark.print_latency_report(latency_results)

        # Quality benchmarks
        quality_metrics = {}
        if not args.skip_quality:
            print("🎯 Running search quality benchmarks...")
            print()

            # Filter providers with matching dimensions for fair comparison
            quality_metrics = await benchmark.benchmark_search_quality(
                test_providers,
                test_corpus,
                test_queries
            )

            benchmark.print_quality_report(quality_metrics)

        # Generate recommendations
        if latency_results:
            recommendations = benchmark.generate_recommendations(latency_results, quality_metrics)
            print(recommendations)

        # Save results
        results_path = Path.home() / '.claude' / 'embedding_benchmark_results.json'
        results = {
            'timestamp': time.time(),
            'providers_tested': test_providers,
            'latency_results': {
                provider: asdict(result)
                for provider, result in latency_results.items()
            },
            'quality_metrics': {
                provider: [asdict(m) for m in metrics]
                for provider, metrics in quality_metrics.items()
            }
        }

        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\n📄 Detailed results saved to: {results_path}")

    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
        logger.exception("Benchmark error")


if __name__ == "__main__":
    asyncio.run(main())
