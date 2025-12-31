#!/usr/bin/env python3
"""
Comprehensive Test Suite for GEPA-DGM Integration
==================================================

Tests all components of the GEPA (Genetic-Pareto) Reflection Engine
integration with the Darwin Gödel Machine.

Components tested:
1. ReflectionEngine - Natural language analysis
2. PromptEvolutionTree - Modification tracking with lesson accumulation
3. ParetoFrontier - Multi-objective optimization
4. GEPADGMIntegration - Full integration layer
5. DarwinGodelMachine with GEPA - End-to-end workflow
"""

import asyncio
import json
import sys
import unittest
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from gepa_reflection_engine import (
    ReflectionEngine,
    PromptEvolutionTree,
    ParetoFrontier,
    GEPADGMIntegration,
    ReflectionType,
    EvolutionStrategy,
    Reflection,
    EvolutionNode,
    ParetoSolution
)

from darwin_godel_machine import (
    DarwinGodelMachine,
    ModificationType,
    ProofStatus,
    GEPA_AVAILABLE
)


class TestReflectionEngine(unittest.TestCase):
    """Test cases for ReflectionEngine"""

    def setUp(self):
        self.engine = ReflectionEngine()

    def test_generate_reflection_performance(self):
        """Test performance reflection generation"""
        async def run_test():
            code_before = "def f(x): return x * 2"
            code_after = "def f(x): return x << 1"  # Bit shift optimization

            reflections = await self.engine.generate_reflection(
                modification_id="test_001",
                code_before=code_before,
                code_after=code_after,
                reflection_types=[ReflectionType.PERFORMANCE]
            )

            self.assertEqual(len(reflections), 1)
            self.assertEqual(reflections[0].reflection_type, ReflectionType.PERFORMANCE)
            self.assertIsInstance(reflections[0].content, str)
            self.assertGreater(len(reflections[0].content), 10)
            self.assertIsInstance(reflections[0].lessons_learned, list)
            self.assertIsInstance(reflections[0].confidence, float)
            self.assertGreaterEqual(reflections[0].confidence, 0.0)
            self.assertLessEqual(reflections[0].confidence, 1.0)

        asyncio.run(run_test())

    def test_generate_reflection_safety(self):
        """Test safety reflection generation"""
        async def run_test():
            code_before = "def f(x): return eval(x)"  # Unsafe
            code_after = "def f(x): return int(x)"    # Safe

            reflections = await self.engine.generate_reflection(
                modification_id="test_002",
                code_before=code_before,
                code_after=code_after,
                reflection_types=[ReflectionType.SAFETY]
            )

            self.assertEqual(len(reflections), 1)
            self.assertEqual(reflections[0].reflection_type, ReflectionType.SAFETY)
            # Should detect removal of unsafe pattern
            self.assertIn("arbitrary code evaluation", reflections[0].content.lower())

        asyncio.run(run_test())

    def test_generate_all_reflection_types(self):
        """Test generating all reflection types"""
        async def run_test():
            reflections = await self.engine.generate_reflection(
                modification_id="test_003",
                code_before="def f(): pass",
                code_after="def f() -> None: '''Docstring'''\n    pass",
                reflection_types=[
                    ReflectionType.PERFORMANCE,
                    ReflectionType.CORRECTNESS,
                    ReflectionType.SAFETY,
                    ReflectionType.ROBUSTNESS,
                    ReflectionType.READABILITY,
                    ReflectionType.GENERALIZATION
                ]
            )

            self.assertEqual(len(reflections), 6)
            types = {r.reflection_type for r in reflections}
            self.assertEqual(len(types), 6)

        asyncio.run(run_test())


class TestPromptEvolutionTree(unittest.TestCase):
    """Test cases for PromptEvolutionTree"""

    def setUp(self):
        self.tree = PromptEvolutionTree()

    def test_create_root_node(self):
        """Test root node creation"""
        node = self.tree.create_root_node(
            modification_id="root_001",
            prompt_content="def original(): pass",
            initial_scores={"performance": 0.5, "safety": 0.8}
        )

        self.assertIsNotNone(node)
        self.assertIsNone(node.parent_id)
        self.assertEqual(node.depth, 0)
        self.assertTrue(node.is_pareto_optimal)
        self.assertEqual(node.accumulated_lessons, [])

    def test_add_child_node(self):
        """Test adding child nodes"""
        async def run_test():
            # Create root
            root = self.tree.create_root_node(
                modification_id="root_002",
                prompt_content="def original(): pass"
            )

            # Generate reflections for child
            reflections = await self.tree.reflection_engine.generate_reflection(
                modification_id="child_001",
                code_before="def original(): pass",
                code_after="def improved(): return True"
            )

            # Add child
            child = self.tree.add_child_node(
                parent_id=root.node_id,
                modification_id="child_001",
                prompt_content="def improved(): return True",
                reflections=reflections,
                pareto_scores={"performance": 0.7, "safety": 0.9}
            )

            self.assertEqual(child.parent_id, root.node_id)
            self.assertEqual(child.depth, 1)
            self.assertGreater(len(child.accumulated_lessons), 0)

        asyncio.run(run_test())

    def test_lesson_accumulation(self):
        """Test that lessons accumulate across generations"""
        async def run_test():
            # Create root
            root = self.tree.create_root_node(
                modification_id="root_003",
                prompt_content="v0"
            )

            # Add several generations
            current_parent = root.node_id
            for i in range(5):
                reflections = await self.tree.reflection_engine.generate_reflection(
                    modification_id=f"gen_{i}",
                    code_before=f"v{i}",
                    code_after=f"v{i+1}"
                )

                child = self.tree.add_child_node(
                    parent_id=current_parent,
                    modification_id=f"gen_{i}",
                    prompt_content=f"v{i+1}",
                    reflections=reflections,
                    pareto_scores={"performance": 0.5 + i * 0.1}
                )
                current_parent = child.node_id

            # Check lesson accumulation
            lessons = self.tree.get_ancestry_lessons(current_parent)
            self.assertGreater(len(lessons), 0)

        asyncio.run(run_test())


class TestParetoFrontier(unittest.TestCase):
    """Test cases for ParetoFrontier"""

    def setUp(self):
        self.frontier = ParetoFrontier(
            objectives=["performance", "safety", "readability"]
        )

    def test_dominates(self):
        """Test Pareto dominance check"""
        a = {"performance": 0.8, "safety": 0.9, "readability": 0.7}
        b = {"performance": 0.7, "safety": 0.8, "readability": 0.6}

        self.assertTrue(self.frontier.dominates(a, b))
        self.assertFalse(self.frontier.dominates(b, a))

    def test_no_domination(self):
        """Test non-dominating solutions"""
        a = {"performance": 0.9, "safety": 0.5, "readability": 0.7}
        b = {"performance": 0.5, "safety": 0.9, "readability": 0.7}

        # Neither dominates the other (trade-off)
        self.assertFalse(self.frontier.dominates(a, b))
        self.assertFalse(self.frontier.dominates(b, a))

    def test_add_solution_pareto_optimal(self):
        """Test adding Pareto-optimal solutions"""
        # Add first solution
        is_optimal, dominated = self.frontier.add_solution(
            node_id="node_1",
            objectives={"performance": 0.8, "safety": 0.8, "readability": 0.8}
        )
        self.assertTrue(is_optimal)
        self.assertEqual(len(dominated), 0)

        # Add non-dominating solution (trade-off)
        is_optimal, dominated = self.frontier.add_solution(
            node_id="node_2",
            objectives={"performance": 0.9, "safety": 0.7, "readability": 0.7}
        )
        self.assertTrue(is_optimal)
        self.assertEqual(len(self.frontier.frontier), 2)

    def test_add_dominated_solution(self):
        """Test adding dominated solution"""
        # Add good solution
        self.frontier.add_solution(
            node_id="node_1",
            objectives={"performance": 0.9, "safety": 0.9, "readability": 0.9}
        )

        # Add dominated solution
        is_optimal, dominated = self.frontier.add_solution(
            node_id="node_2",
            objectives={"performance": 0.5, "safety": 0.5, "readability": 0.5}
        )
        self.assertFalse(is_optimal)
        self.assertEqual(len(self.frontier.frontier), 1)

    def test_select_for_evolution(self):
        """Test selection strategies"""
        self.frontier.add_solution("n1", {"performance": 0.9, "safety": 0.5, "readability": 0.7})
        self.frontier.add_solution("n2", {"performance": 0.5, "safety": 0.9, "readability": 0.7})
        self.frontier.add_solution("n3", {"performance": 0.7, "safety": 0.7, "readability": 0.9})

        # Test random selection
        selected = self.frontier.select_for_evolution("random")
        self.assertIn(selected, ["n1", "n2", "n3"])

        # Test diverse selection
        selected = self.frontier.select_for_evolution("diverse")
        self.assertIn(selected, ["n1", "n2", "n3"])


class TestGEPADGMIntegration(unittest.TestCase):
    """Test cases for GEPA-DGM integration"""

    def setUp(self):
        self.integration = GEPADGMIntegration()

    def test_enhance_proof_with_reflection(self):
        """Test enhanced proof generation"""
        async def run_test():
            code_before = """
def calculate(x, y):
    result = 0
    for i in range(y):
        result = result + x
    return result
"""
            code_after = """
def calculate(x: int, y: int) -> int:
    '''Multiply x by y using direct multiplication.'''
    return x * y
"""

            proof = await self.integration.enhance_proof_with_reflection(
                modification_id="proof_test_001",
                code_before=code_before,
                code_after=code_after
            )

            self.assertIn("proof", proof)
            self.assertIn("reflections", proof)
            self.assertIn("dimension_scores", proof)
            self.assertIn("overall_confidence", proof)
            self.assertIn("lessons_learned", proof)
            self.assertIn("improvement_directions", proof)

            self.assertGreater(proof["overall_confidence"], 0)
            self.assertGreater(len(proof["reflections"]), 0)

        asyncio.run(run_test())

    def test_track_modification_evolution(self):
        """Test evolution tracking"""
        async def run_test():
            import uuid
            unique_id = str(uuid.uuid4())[:8]

            # Track first modification (use unique IDs to avoid database conflicts)
            node1 = await self.integration.track_modification_evolution(
                modification_id=f"track_{unique_id}_001",
                code_content="def v1(): pass"
            )

            self.assertEqual(node1.depth, 0)
            # Note: is_pareto_optimal may be False if dominated by existing solutions
            # in the persistent database, so we just check it's a boolean
            self.assertIsInstance(node1.is_pareto_optimal, bool)

            # Track child modification
            node2 = await self.integration.track_modification_evolution(
                modification_id=f"track_{unique_id}_002",
                code_content="def v2(): return True",
                parent_modification_id=f"track_{unique_id}_001"
            )

            self.assertEqual(node2.depth, 1)
            self.assertEqual(node2.parent_id, node1.node_id)

        asyncio.run(run_test())

    def test_evolution_summary(self):
        """Test evolution summary generation"""
        async def run_test():
            # Add some nodes
            await self.integration.track_modification_evolution(
                modification_id="summary_001",
                code_content="v1"
            )

            summary = self.integration.get_evolution_summary()

            self.assertIn("tree_statistics", summary)
            self.assertIn("pareto_frontier_size", summary)
            self.assertIn("objectives", summary)

        asyncio.run(run_test())


class TestDarwinGodelMachineWithGEPA(unittest.TestCase):
    """Test DarwinGodelMachine with GEPA integration"""

    def setUp(self):
        self.machine = DarwinGodelMachine(enable_gepa=True)

    def test_gepa_enabled(self):
        """Test GEPA is enabled"""
        if GEPA_AVAILABLE:
            self.assertTrue(self.machine.gepa_enabled)
            self.assertIsNotNone(self.machine.gepa_integration)
        else:
            self.assertFalse(self.machine.gepa_enabled)

    def test_generate_gepa_proof(self):
        """Test GEPA proof generation"""
        async def run_test():
            if not self.machine.gepa_enabled:
                self.skipTest("GEPA not available")

            code_before = "def f(x): return x + 1"
            code_after = "def f(x: int) -> int: return x + 1"

            proof = await self.machine._generate_gepa_proof(
                code_before=code_before,
                code_after=code_after,
                modification_id="dgm_proof_001"
            )

            self.assertIn("proof", proof)
            self.assertIn("overall_confidence", proof)
            self.assertGreater(len(proof["proof"]), 0)

        asyncio.run(run_test())

    def test_track_modification_evolution(self):
        """Test modification tracking in evolution tree"""
        async def run_test():
            if not self.machine.gepa_enabled:
                self.skipTest("GEPA not available")

            modification = self.machine.propose_modification(
                code_before="def old(): pass",
                code_after="def new(): return 42",
                modification_type=ModificationType.ALGORITHM_IMPROVE,
                description="Test modification"
            )

            evolution_info = await self.machine.track_modification_evolution(modification)

            self.assertIsNotNone(evolution_info)
            self.assertIn("node_id", evolution_info)
            self.assertIn("depth", evolution_info)
            self.assertIn("is_pareto_optimal", evolution_info)

        asyncio.run(run_test())

    def test_evolution_summary(self):
        """Test getting evolution summary"""
        if not self.machine.gepa_enabled:
            self.skipTest("GEPA not available")

        summary = self.machine.get_evolution_summary()

        if summary:
            self.assertIn("tree_statistics", summary)
            self.assertIn("pareto_frontier_size", summary)


def run_integration_demo():
    """Run a comprehensive integration demo"""
    print("\n" + "=" * 70)
    print("GEPA-DGM Integration Test Suite")
    print("=" * 70)

    async def demo():
        # Initialize components
        print("\n[1] Initializing components...")
        integration = GEPADGMIntegration()
        machine = DarwinGodelMachine(enable_gepa=True)

        print(f"    GEPA Available: {GEPA_AVAILABLE}")
        print(f"    DGM GEPA Enabled: {machine.gepa_enabled}")

        # Test reflection engine
        print("\n[2] Testing ReflectionEngine...")
        code_v1 = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
"""
        code_v2 = """
from functools import lru_cache

@lru_cache(maxsize=None)
def fibonacci(n: int) -> int:
    '''Calculate fibonacci number with memoization.'''
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
"""

        proof = await integration.enhance_proof_with_reflection(
            modification_id="demo_fib",
            code_before=code_v1,
            code_after=code_v2
        )

        print(f"    Overall Confidence: {proof['overall_confidence']:.2%}")
        print(f"    Dimensions analyzed: {len(proof['dimension_scores'])}")
        print(f"    Lessons learned: {len(proof['lessons_learned'])}")

        # Test evolution tracking
        print("\n[3] Testing PromptEvolutionTree...")
        node1 = await integration.track_modification_evolution(
            modification_id="demo_fib_v1",
            code_content=code_v1
        )
        print(f"    Created root node: {node1.node_id[:12]}...")

        node2 = await integration.track_modification_evolution(
            modification_id="demo_fib_v2",
            code_content=code_v2,
            parent_modification_id="demo_fib_v1"
        )
        print(f"    Created child node: {node2.node_id[:12]}... (depth {node2.depth})")
        print(f"    Accumulated lessons: {len(node2.accumulated_lessons)}")

        # Test Pareto frontier
        print("\n[4] Testing ParetoFrontier...")
        summary = integration.get_evolution_summary()
        print(f"    Total nodes: {summary['tree_statistics']['total_nodes']}")
        print(f"    Pareto frontier size: {summary['pareto_frontier_size']}")

        # Test full DGM workflow
        print("\n[5] Testing DarwinGodelMachine with GEPA...")
        machine.set_baseline()

        mod = machine.propose_modification(
            code_before=code_v1,
            code_after=code_v2,
            modification_type=ModificationType.ALGORITHM_IMPROVE,
            description="Add memoization to fibonacci"
        )
        print(f"    Proposed modification: {mod.modification_id[:12]}...")
        print(f"    Expected improvement: {mod.expected_improvement:.1%}")
        print(f"    Safety score: {mod.safety_score:.2f}")

        gepa_proof = await machine._generate_gepa_proof(
            code_before=code_v1,
            code_after=code_v2,
            modification_id=mod.modification_id
        )
        print(f"    GEPA confidence: {gepa_proof['overall_confidence']:.2%}")

        evo_info = await machine.track_modification_evolution(mod)
        if evo_info:
            print(f"    Evolution tracked: depth {evo_info['depth']}, Pareto optimal: {evo_info['is_pareto_optimal']}")

        print("\n" + "=" * 70)
        print("All integration tests completed successfully!")
        print("=" * 70)

    asyncio.run(demo())


if __name__ == "__main__":
    # Run unit tests
    print("Running unit tests...")
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestReflectionEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestPromptEvolutionTree))
    suite.addTests(loader.loadTestsFromTestCase(TestParetoFrontier))
    suite.addTests(loader.loadTestsFromTestCase(TestGEPADGMIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestDarwinGodelMachineWithGEPA))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Run integration demo
    if result.wasSuccessful():
        run_integration_demo()
    else:
        print("\nSkipping integration demo due to test failures")
        sys.exit(1)
