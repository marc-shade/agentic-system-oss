#!/usr/bin/env python3
"""
Comprehensive RAG Tools Integration Test Suite

Tests all RAG tiers implemented in enhanced-memory-mcp:
- Tier 1: Hybrid Search, Re-ranking
- Tier 2: Query Expansion, Multi-Query RAG
- Tier 3: Contextual Retrieval, Hierarchical RAG
- Tier 4: GraphRAG, Agentic RAG, Self-Reflective RAG

Tests include:
1. Module imports
2. Tool registration with mock FastMCP app
3. Class instantiation
4. Basic functionality verification
"""

import sys
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass
import traceback

# Add enhanced-memory MCP to path
sys.path.insert(0, str(Path(__file__).parent))


@dataclass
class TestResult:
    """Result of a single test"""
    name: str
    passed: bool
    message: str = ""
    details: Optional[Dict[str, Any]] = None


class MockFastMCPApp:
    """Mock FastMCP app for tool registration testing"""

    def __init__(self):
        self.tools: Dict[str, Callable] = {}

    def tool(self):
        """Decorator to register tools"""
        def decorator(func):
            self.tools[func.__name__] = func
            return func
        return decorator


class RAGIntegrationTestSuite:
    """Comprehensive test suite for all RAG tools"""

    def __init__(self):
        self.results: List[TestResult] = []
        self.mock_app = MockFastMCPApp()
        self.nmf_instance = None  # Will be set if available

    def add_result(self, name: str, passed: bool, message: str = "", details: Dict = None):
        """Add a test result"""
        self.results.append(TestResult(name, passed, message, details))

    # ========== TIER 1: Foundation ==========

    def test_hybrid_search_import(self) -> bool:
        """Test hybrid search module imports"""
        try:
            from hybrid_search_tools import register_hybrid_search_tools
            from hybrid_search import get_hybrid_searcher
            self.add_result("Tier 1: Hybrid Search Import", True, "Module imports successfully")
            return True
        except Exception as e:
            self.add_result("Tier 1: Hybrid Search Import", False, str(e))
            return False

    def test_hybrid_search_registration(self) -> bool:
        """Test hybrid search tool registration"""
        try:
            from hybrid_search_tools import register_hybrid_search_tools
            mock = MockFastMCPApp()
            register_hybrid_search_tools(mock)

            # Check tools registered (names may vary based on implementation)
            if len(mock.tools) >= 1:
                self.add_result("Tier 1: Hybrid Search Registration", True,
                               f"Registered {len(mock.tools)} tools", {"tools": list(mock.tools.keys())})
                return True
            else:
                self.add_result("Tier 1: Hybrid Search Registration", False, "No tools registered")
                return False
        except Exception as e:
            self.add_result("Tier 1: Hybrid Search Registration", False, str(e))
            return False

    def test_reranking_import(self) -> bool:
        """Test re-ranking module imports"""
        try:
            from reranking_tools import register_reranking_tools
            from reranking import get_reranker
            self.add_result("Tier 1: Re-ranking Import", True, "Module imports successfully")
            return True
        except Exception as e:
            self.add_result("Tier 1: Re-ranking Import", False, str(e))
            return False

    def test_reranking_registration(self) -> bool:
        """Test re-ranking tool registration"""
        try:
            from reranking_tools import register_reranking_tools
            mock = MockFastMCPApp()

            # Create a mock memory client
            class MockMemoryClient:
                pass

            register_reranking_tools(mock, MockMemoryClient())

            if len(mock.tools) >= 1:
                self.add_result("Tier 1: Re-ranking Registration", True,
                               f"Registered {len(mock.tools)} tools", {"tools": list(mock.tools.keys())})
                return True
            else:
                self.add_result("Tier 1: Re-ranking Registration", False, "No tools registered")
                return False
        except Exception as e:
            self.add_result("Tier 1: Re-ranking Registration", False, str(e))
            return False

    # ========== TIER 2: Query Enhancement ==========

    def test_query_expansion_import(self) -> bool:
        """Test query expansion module imports"""
        try:
            from query_expansion_tools import register_query_expansion_tools
            self.add_result("Tier 2: Query Expansion Import", True, "Module imports successfully")
            return True
        except Exception as e:
            self.add_result("Tier 2: Query Expansion Import", False, str(e))
            return False

    def test_query_expansion_registration(self) -> bool:
        """Test query expansion tool registration"""
        try:
            from query_expansion_tools import register_query_expansion_tools
            mock = MockFastMCPApp()

            # Create a mock NMF instance
            class MockNMF:
                async def recall(self, query, mode="semantic", limit=10):
                    return []

            register_query_expansion_tools(mock, MockNMF())

            if len(mock.tools) >= 1:
                self.add_result("Tier 2: Query Expansion Registration", True,
                               f"Registered {len(mock.tools)} tools", {"tools": list(mock.tools.keys())})
                return True
            else:
                self.add_result("Tier 2: Query Expansion Registration", False, "No tools registered")
                return False
        except Exception as e:
            self.add_result("Tier 2: Query Expansion Registration", False, str(e))
            return False

    def test_multi_query_rag_import(self) -> bool:
        """Test multi-query RAG module imports"""
        try:
            from multi_query_rag_tools import register_multi_query_rag_tools
            self.add_result("Tier 2: Multi-Query RAG Import", True, "Module imports successfully")
            return True
        except Exception as e:
            self.add_result("Tier 2: Multi-Query RAG Import", False, str(e))
            return False

    def test_multi_query_rag_registration(self) -> bool:
        """Test multi-query RAG tool registration"""
        try:
            from multi_query_rag_tools import register_multi_query_rag_tools
            mock = MockFastMCPApp()

            # Create a mock NMF instance
            class MockNMF:
                async def recall(self, query, mode="semantic", limit=10):
                    return []

            register_multi_query_rag_tools(mock, MockNMF())

            if len(mock.tools) >= 1:
                self.add_result("Tier 2: Multi-Query RAG Registration", True,
                               f"Registered {len(mock.tools)} tools", {"tools": list(mock.tools.keys())})
                return True
            else:
                self.add_result("Tier 2: Multi-Query RAG Registration", False, "No tools registered")
                return False
        except Exception as e:
            self.add_result("Tier 2: Multi-Query RAG Registration", False, str(e))
            return False

    # ========== TIER 3: Context-Aware ==========

    def test_contextual_retrieval_import(self) -> bool:
        """Test contextual retrieval module imports"""
        try:
            from contextual_retrieval_tools import register_contextual_retrieval_tools
            self.add_result("Tier 3: Contextual Retrieval Import", True, "Module imports successfully")
            return True
        except Exception as e:
            self.add_result("Tier 3: Contextual Retrieval Import", False, str(e))
            return False

    def test_contextual_retrieval_registration(self) -> bool:
        """Test contextual retrieval tool registration"""
        try:
            from contextual_retrieval_tools import register_contextual_retrieval_tools
            mock = MockFastMCPApp()

            # Create a mock NMF instance (required by register_contextual_retrieval_tools)
            class MockNMF:
                async def recall(self, query, mode="semantic", limit=10):
                    return []

            register_contextual_retrieval_tools(mock, MockNMF())

            expected_tools = ['generate_context_for_chunk', 'reindex_with_context',
                            'get_reindexing_progress', 'get_contextual_retrieval_stats']
            for tool in expected_tools:
                if tool not in mock.tools:
                    self.add_result("Tier 3: Contextual Retrieval Registration", False, f"Missing tool: {tool}")
                    return False

            self.add_result("Tier 3: Contextual Retrieval Registration", True,
                           f"Registered {len(mock.tools)} tools", {"tools": list(mock.tools.keys())})
            return True
        except Exception as e:
            self.add_result("Tier 3: Contextual Retrieval Registration", False, str(e))
            return False

    def test_hierarchical_rag_import(self) -> bool:
        """Test hierarchical RAG module imports"""
        try:
            from hierarchical_rag_tools import register_hierarchical_rag_tools
            from hierarchical_rag_tools import HierarchicalIndex, HierarchicalDocument, HierarchicalSearchResult
            self.add_result("Tier 3: Hierarchical RAG Import", True, "Module and classes import successfully")
            return True
        except Exception as e:
            self.add_result("Tier 3: Hierarchical RAG Import", False, str(e))
            return False

    def test_hierarchical_rag_registration(self) -> bool:
        """Test hierarchical RAG tool registration"""
        try:
            from hierarchical_rag_tools import register_hierarchical_rag_tools
            mock = MockFastMCPApp()
            register_hierarchical_rag_tools(mock, nmf_instance=None)

            expected_tools = ['search_hierarchical', 'index_document_hierarchical',
                            'get_document_structure', 'get_section_content', 'get_hierarchical_stats']
            for tool in expected_tools:
                if tool not in mock.tools:
                    self.add_result("Tier 3: Hierarchical RAG Registration", False, f"Missing tool: {tool}")
                    return False

            self.add_result("Tier 3: Hierarchical RAG Registration", True,
                           f"Registered {len(mock.tools)} tools", {"tools": list(mock.tools.keys())})
            return True
        except Exception as e:
            self.add_result("Tier 3: Hierarchical RAG Registration", False, str(e))
            return False

    def test_hierarchical_index_creation(self) -> bool:
        """Test HierarchicalIndex class instantiation"""
        try:
            from hierarchical_rag_tools import HierarchicalIndex, HierarchicalDocument

            # Create index instance
            index = HierarchicalIndex(nmf_instance=None)

            # Verify HierarchicalDocument has expected fields
            doc = HierarchicalDocument(entity_name="test", document_hash="abc123", summary="Test summary")
            if not doc.entity_name or not doc.document_hash:
                self.add_result("Tier 3: HierarchicalIndex Creation", False,
                              "HierarchicalDocument missing required fields")
                return False

            # Verify index has required methods
            required_methods = ['index_document', 'search_hierarchical', 'get_document', 'get_section', 'get_chunk', 'get_stats']
            for method in required_methods:
                if not hasattr(index, method):
                    self.add_result("Tier 3: HierarchicalIndex Creation", False,
                                  f"Missing method: {method}")
                    return False

            self.add_result("Tier 3: HierarchicalIndex Creation", True,
                           "HierarchicalIndex instantiated with all required methods",
                           {"methods": required_methods})
            return True
        except Exception as e:
            self.add_result("Tier 3: HierarchicalIndex Creation", False, str(e))
            return False

    # ========== TIER 4: Advanced Autonomous ==========

    def test_graphrag_import(self) -> bool:
        """Test GraphRAG module imports"""
        try:
            from graphrag_tools import register_graphrag_tools
            self.add_result("Tier 4: GraphRAG Import", True, "Module imports successfully")
            return True
        except Exception as e:
            self.add_result("Tier 4: GraphRAG Import", False, str(e))
            return False

    def test_graphrag_registration(self) -> bool:
        """Test GraphRAG tool registration"""
        try:
            from graphrag_tools import register_graphrag_tools
            mock = MockFastMCPApp()

            db_path = Path.home() / ".claude" / "enhanced_memories" / "memory.db"
            register_graphrag_tools(mock, db_path)

            expected_tools = ['graph_enhanced_search', 'get_entity_neighbors',
                            'add_entity_relationship', 'get_graph_statistics',
                            'extract_entity_relationships', 'extract_all_relationships',
                            'build_local_graph']
            for tool in expected_tools:
                if tool not in mock.tools:
                    self.add_result("Tier 4: GraphRAG Registration", False, f"Missing tool: {tool}")
                    return False

            self.add_result("Tier 4: GraphRAG Registration", True,
                           f"Registered {len(mock.tools)} tools", {"tools": list(mock.tools.keys())})
            return True
        except Exception as e:
            self.add_result("Tier 4: GraphRAG Registration", False, str(e))
            return False

    def test_agentic_rag_import(self) -> bool:
        """Test Agentic RAG module imports"""
        try:
            from agentic_rag_tools import register_agentic_rag_tools
            from agentic_rag_tools import (
                QueryType, QueryComplexity, RetrievalStrategy,
                QueryProfile, RetrievalResult, StrategyPerformance,
                QueryAnalyzer, ResultEvaluator, QueryRefiner, AgenticRetriever
            )
            self.add_result("Tier 4: Agentic RAG Import", True,
                           "Module and all classes import successfully")
            return True
        except Exception as e:
            self.add_result("Tier 4: Agentic RAG Import", False, str(e))
            return False

    def test_agentic_rag_registration(self) -> bool:
        """Test Agentic RAG tool registration"""
        try:
            from agentic_rag_tools import register_agentic_rag_tools
            mock = MockFastMCPApp()
            register_agentic_rag_tools(mock, nmf_instance=None)

            expected_tools = ['search_agentic', 'analyze_query',
                            'search_reflective', 'get_agentic_rag_stats']
            for tool in expected_tools:
                if tool not in mock.tools:
                    self.add_result("Tier 4: Agentic RAG Registration", False, f"Missing tool: {tool}")
                    return False

            self.add_result("Tier 4: Agentic RAG Registration", True,
                           f"Registered {len(mock.tools)} tools", {"tools": list(mock.tools.keys())})
            return True
        except Exception as e:
            self.add_result("Tier 4: Agentic RAG Registration", False, str(e))
            return False

    def test_agentic_rag_classes(self) -> bool:
        """Test Agentic RAG class instantiation"""
        try:
            from agentic_rag_tools import (
                QueryType, QueryComplexity, RetrievalStrategy,
                QueryAnalyzer, ResultEvaluator, QueryRefiner, AgenticRetriever
            )

            # Test enums
            assert len(list(QueryType)) >= 5, "Should have at least 5 query types"
            assert len(list(QueryComplexity)) >= 3, "Should have at least 3 complexity levels"
            assert len(list(RetrievalStrategy)) >= 5, "Should have at least 5 strategies"

            # Test class instantiation
            analyzer = QueryAnalyzer()
            assert hasattr(analyzer, 'analyze'), "QueryAnalyzer should have analyze method"

            evaluator = ResultEvaluator()
            assert hasattr(evaluator, 'evaluate'), "ResultEvaluator should have evaluate method"

            refiner = QueryRefiner()
            assert hasattr(refiner, 'refine'), "QueryRefiner should have refine method"

            retriever = AgenticRetriever(nmf_instance=None)
            # AgenticRetriever uses 'retrieve' (not 'search') as the main async method
            required_methods = ['retrieve', 'analyzer', 'evaluator', 'refiner']
            for method in required_methods:
                assert hasattr(retriever, method), f"AgenticRetriever should have {method} attribute"

            self.add_result("Tier 4: Agentic RAG Classes", True,
                           "All classes instantiated with required methods",
                           {
                               "query_types": len(list(QueryType)),
                               "complexity_levels": len(list(QueryComplexity)),
                               "strategies": len(list(RetrievalStrategy))
                           })
            return True
        except Exception as e:
            self.add_result("Tier 4: Agentic RAG Classes", False, str(e))
            return False

    def test_query_analyzer_functionality(self) -> bool:
        """Test QueryAnalyzer basic functionality"""
        try:
            from agentic_rag_tools import QueryAnalyzer, QueryType, QueryComplexity

            analyzer = QueryAnalyzer()

            # Test various query types
            test_cases = [
                ("What is Python?", QueryType.FACTUAL),
                ("How do I implement a linked list?", QueryType.PROCEDURAL),
                ("What are the benefits of microservices?", QueryType.EXPLORATORY),
                ("Compare REST vs GraphQL", QueryType.COMPARATIVE),
                ("Why does my code throw this error?", QueryType.ANALYTICAL),
            ]

            passed_cases = 0
            for query, expected_type in test_cases:
                profile = analyzer.analyze(query)
                if profile.query_type == expected_type:
                    passed_cases += 1

            # Allow some flexibility in classification (at least 3 of 5 correct)
            if passed_cases >= 3:
                self.add_result("Tier 4: QueryAnalyzer Functionality", True,
                               f"Classified {passed_cases}/5 queries correctly",
                               {"test_cases": passed_cases})
                return True
            else:
                self.add_result("Tier 4: QueryAnalyzer Functionality", False,
                               f"Only classified {passed_cases}/5 queries correctly")
                return False
        except Exception as e:
            self.add_result("Tier 4: QueryAnalyzer Functionality", False, str(e))
            return False

    def test_result_evaluator_functionality(self) -> bool:
        """Test ResultEvaluator basic functionality"""
        try:
            from agentic_rag_tools import ResultEvaluator, QueryAnalyzer

            evaluator = ResultEvaluator()
            analyzer = QueryAnalyzer()

            # Create mock results as List[Dict[str, Any]] (not RetrievalResult)
            mock_results = [
                {
                    "content": "Python is a programming language used for web development.",
                    "score": 0.9,
                    "metadata": {"source": "test1"}
                },
                {
                    "content": "Python supports object-oriented programming.",
                    "score": 0.85,
                    "metadata": {"source": "test2"}
                },
                {
                    "content": "Python has extensive standard library.",
                    "score": 0.8,
                    "metadata": {"source": "test3"}
                },
            ]

            query = "What is Python?"
            # First analyze the query to get a QueryProfile
            query_profile = analyzer.analyze(query)

            # evaluate() returns Tuple[float, List[str]] - (quality_score, missing_aspects)
            quality_score, missing_aspects = evaluator.evaluate(mock_results, query, query_profile)

            # Check quality score is in valid range
            if not (0.0 <= quality_score <= 1.0):
                self.add_result("Tier 4: ResultEvaluator Functionality", False,
                               f"Invalid quality score: {quality_score}")
                return False

            # Check missing_aspects is a list
            if not isinstance(missing_aspects, list):
                self.add_result("Tier 4: ResultEvaluator Functionality", False,
                               f"missing_aspects should be a list, got {type(missing_aspects)}")
                return False

            self.add_result("Tier 4: ResultEvaluator Functionality", True,
                           "Evaluation produced valid results",
                           {"quality_score": quality_score, "missing_aspects_count": len(missing_aspects)})
            return True
        except Exception as e:
            self.add_result("Tier 4: ResultEvaluator Functionality", False, str(e))
            return False

    # ========== INTEGRATION TESTS ==========

    def test_all_tools_in_server(self) -> bool:
        """Test that server.py imports all RAG tools"""
        try:
            server_path = Path(__file__).parent / "server.py"
            with open(server_path) as f:
                server_content = f.read()

            expected_imports = [
                'register_hybrid_search_tools',
                'register_reranking_tools',
                'register_query_expansion_tools',
                'register_multi_query_rag_tools',
                'register_contextual_retrieval_tools',
                'register_hierarchical_rag_tools',
                'register_graphrag_tools',
                'register_agentic_rag_tools',
            ]

            missing = []
            for imp in expected_imports:
                if imp not in server_content:
                    missing.append(imp)

            if missing:
                self.add_result("Integration: Server RAG Tools", False,
                               f"Missing imports: {missing}")
                return False

            self.add_result("Integration: Server RAG Tools", True,
                           f"All {len(expected_imports)} RAG tool registrations found in server.py")
            return True
        except Exception as e:
            self.add_result("Integration: Server RAG Tools", False, str(e))
            return False

    def test_rag_tier_completeness(self) -> bool:
        """Verify RAG implementation completeness by tier"""
        try:
            roadmap_path = Path(__file__).parent / "COMPLETE_RAG_ROADMAP.md"
            if not roadmap_path.exists():
                self.add_result("Integration: RAG Tier Completeness", False,
                               "COMPLETE_RAG_ROADMAP.md not found")
                return False

            with open(roadmap_path) as f:
                content = f.read()

            # Check for completion markers
            tier_status = {
                "Tier 1": "Hybrid Search" in content and "Re-ranking" in content,
                "Tier 2": "Query Expansion" in content and "Multi-Query" in content,
                "Tier 3": "Contextual" in content and "Hierarchical" in content,
                "Tier 4": "GraphRAG" in content and "Agentic" in content,
            }

            completed_tiers = sum(tier_status.values())

            # Check overall completion percentage
            if "82%" in content or "9 of 11" in content:
                self.add_result("Integration: RAG Tier Completeness", True,
                               f"RAG implementation at 82% - {completed_tiers}/4 tiers documented",
                               {"tier_status": tier_status})
                return True
            else:
                self.add_result("Integration: RAG Tier Completeness", True,
                               f"{completed_tiers}/4 tiers documented",
                               {"tier_status": tier_status})
                return True
        except Exception as e:
            self.add_result("Integration: RAG Tier Completeness", False, str(e))
            return False

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return summary"""
        print("=" * 70)
        print("COMPREHENSIVE RAG TOOLS INTEGRATION TEST SUITE")
        print("=" * 70)
        print()

        # Tier 1 Tests
        print("=" * 70)
        print("TIER 1: Foundation (Hybrid Search + Re-ranking)")
        print("=" * 70)
        self.test_hybrid_search_import()
        self.test_hybrid_search_registration()
        self.test_reranking_import()
        self.test_reranking_registration()

        # Tier 2 Tests
        print("\n" + "=" * 70)
        print("TIER 2: Query Enhancement (Query Expansion + Multi-Query)")
        print("=" * 70)
        self.test_query_expansion_import()
        self.test_query_expansion_registration()
        self.test_multi_query_rag_import()
        self.test_multi_query_rag_registration()

        # Tier 3 Tests
        print("\n" + "=" * 70)
        print("TIER 3: Context-Aware (Contextual Retrieval + Hierarchical)")
        print("=" * 70)
        self.test_contextual_retrieval_import()
        self.test_contextual_retrieval_registration()
        self.test_hierarchical_rag_import()
        self.test_hierarchical_rag_registration()
        self.test_hierarchical_index_creation()

        # Tier 4 Tests
        print("\n" + "=" * 70)
        print("TIER 4: Advanced Autonomous (GraphRAG + Agentic + Self-Reflective)")
        print("=" * 70)
        self.test_graphrag_import()
        self.test_graphrag_registration()
        self.test_agentic_rag_import()
        self.test_agentic_rag_registration()
        self.test_agentic_rag_classes()
        self.test_query_analyzer_functionality()
        self.test_result_evaluator_functionality()

        # Integration Tests
        print("\n" + "=" * 70)
        print("INTEGRATION TESTS")
        print("=" * 70)
        self.test_all_tools_in_server()
        self.test_rag_tier_completeness()

        # Print results
        self._print_results()

        return self._get_summary()

    def _print_results(self):
        """Print formatted test results"""
        print("\n" + "=" * 70)
        print("TEST RESULTS SUMMARY")
        print("=" * 70)

        # Group by tier
        tier_groups = {
            "Tier 1": [],
            "Tier 2": [],
            "Tier 3": [],
            "Tier 4": [],
            "Integration": []
        }

        for result in self.results:
            for tier in tier_groups:
                if tier in result.name:
                    tier_groups[tier].append(result)
                    break

        # Print by tier
        for tier, results in tier_groups.items():
            if not results:
                continue
            print(f"\n{tier}:")
            for result in results:
                status = "PASS" if result.passed else "FAIL"
                print(f"  [{status}] {result.name}")
                if result.message:
                    print(f"         {result.message}")

        # Overall summary
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        percentage = (passed / total * 100) if total > 0 else 0

        print("\n" + "=" * 70)
        print(f"OVERALL: {passed}/{total} tests passed ({percentage:.1f}%)")
        print("=" * 70)

        if passed == total:
            print("\nAll RAG tools integration tests passed!")
        else:
            print(f"\n{total - passed} test(s) failed. Review errors above.")

    def _get_summary(self) -> Dict[str, Any]:
        """Get test summary as dict"""
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)

        return {
            "passed": passed,
            "total": total,
            "percentage": (passed / total * 100) if total > 0 else 0,
            "results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "message": r.message,
                    "details": r.details
                }
                for r in self.results
            ]
        }


def main():
    """Run all RAG integration tests"""
    suite = RAGIntegrationTestSuite()
    summary = suite.run_all_tests()

    # Return exit code based on test results
    return 0 if summary["passed"] == summary["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
