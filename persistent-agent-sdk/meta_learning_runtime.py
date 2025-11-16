"""
Meta-Learning Runtime

Phase 5.3: Meta-Learning
Target: Meta-Learning 40% → 85% (+45 points)
Expected AGI Impact: +3.6 points (45% × 0.08 weight)

Extends IntuitionRuntime with:
- Learning strategy selection
- Cross-domain knowledge transfer
- Learning rate adaptation
- Meta-knowledge base
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
import json

# Import parent runtime
from intuition_runtime import (
    IntuitionRuntime,
    IntuitivePattern,
    IntuitiveSolution,
    ThinkingMode
)


# ============================================================================
# META-LEARNING DATA STRUCTURES
# ============================================================================

class LearningStrategy(Enum):
    """Types of learning strategies"""
    SUPERVISED = "supervised_learning"
    UNSUPERVISED = "unsupervised_learning"
    REINFORCEMENT = "reinforcement_learning"
    TRANSFER = "transfer_learning"
    FEW_SHOT = "few_shot_learning"
    ZERO_SHOT = "zero_shot_learning"
    META = "meta_learning"
    CURRICULUM = "curriculum_learning"
    ACTIVE = "active_learning"


@dataclass
class LearningContext:
    """Context for learning a new task"""
    domain: str
    task_type: str
    data_availability: str  # "abundant", "limited", "none"
    time_constraints: float  # 0.0-1.0
    performance_target: float  # 0.0-1.0
    prior_knowledge: Dict[str, float]  # domain -> expertise level
    complexity: float  # 0.0-1.0


@dataclass
class KnowledgeTransfer:
    """Cross-domain knowledge transfer"""
    source_domain: str
    target_domain: str
    transferable_concepts: List[str]
    transfer_effectiveness: float  # 0.0-1.0
    adaptation_required: List[str]
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class MetaKnowledge:
    """Knowledge about learning itself"""
    concept: str
    learning_difficulty: float  # 0.0-1.0 (how hard to learn)
    prerequisite_concepts: List[str]
    learning_time_estimate: float  # Hours to proficiency
    best_learning_strategy: LearningStrategy
    common_misconceptions: List[str]
    effective_analogies: List[str]
    mastery_indicators: List[str]


@dataclass
class LearningCurve:
    """Track learning progress over time"""
    task: str
    strategy: LearningStrategy
    performance_history: List[Tuple[datetime, float]]  # (time, performance)
    learning_rate: float  # Current rate of improvement
    plateau_detected: bool
    plateau_count: int
    total_learning_time: float  # Hours


@dataclass
class MetaLearningSolution:
    """Solution with meta-learning insights"""
    solution: str
    strategy_used: LearningStrategy
    knowledge_transfers: List[KnowledgeTransfer]
    learning_time_estimate: float
    meta_learning_score: float
    learning_insights: List[str]
    timestamp: datetime = field(default_factory=datetime.now)


# ============================================================================
# META-LEARNING RUNTIME
# ============================================================================

class MetaLearningRuntime(IntuitionRuntime):
    """
    Phase 5.3: Meta-Learning Runtime

    Extends IntuitionRuntime with learning about learning.

    Target: Meta-Learning 40% → 85%
    Expected AGI Impact: 94.4% → 96.5% (+2.1 points)
    """

    def __init__(self, verbose=True, enable_learning=True, reasoning_depth=5,
                 constraints: Optional[Any] = None, health_check_interval: int = 60):
        super().__init__(verbose=verbose, enable_learning=enable_learning,
                        reasoning_depth=reasoning_depth, constraints=constraints,
                        health_check_interval=health_check_interval)

        # Meta-learning components
        self.meta_knowledge_base: List[MetaKnowledge] = []
        self.knowledge_transfers: List[KnowledgeTransfer] = []
        self.learning_curves: Dict[str, LearningCurve] = {}
        self.meta_learning_solutions: List[MetaLearningSolution] = []

        # Initialize meta-knowledge about common concepts
        self._initialize_meta_knowledge()

        # Learning rate adaptation parameters
        self.base_learning_rate = 0.1
        self.plateau_threshold = 3  # Number of iterations without improvement

        if self.verbose:
            print("\n🎓 Meta-Learning Runtime initialized")
            print(f"   Meta-knowledge entries: {len(self.meta_knowledge_base)}")
            print(f"   Learning strategies: {len(LearningStrategy)}")

    def _initialize_meta_knowledge(self):
        """Initialize meta-knowledge base with common concepts"""
        base_knowledge = [
            MetaKnowledge(
                concept="recursion",
                learning_difficulty=0.7,
                prerequisite_concepts=["functions", "base_cases", "call_stack"],
                learning_time_estimate=4.0,
                best_learning_strategy=LearningStrategy.CURRICULUM,
                common_misconceptions=[
                    "recursion_is_always_slow",
                    "recursion_only_for_trees"
                ],
                effective_analogies=["matryoshka_dolls", "mirrors_reflecting_mirrors"],
                mastery_indicators=["can_convert_iteration_to_recursion", "understands_tail_recursion"]
            ),
            MetaKnowledge(
                concept="object_oriented_programming",
                learning_difficulty=0.5,
                prerequisite_concepts=["data_structures", "functions", "abstraction"],
                learning_time_estimate=8.0,
                best_learning_strategy=LearningStrategy.SUPERVISED,
                common_misconceptions=[
                    "oop_is_always_better",
                    "inheritance_over_composition"
                ],
                effective_analogies=["real_world_objects", "blueprints_and_instances"],
                mastery_indicators=["uses_composition_appropriately", "understands_polymorphism"]
            ),
            MetaKnowledge(
                concept="machine_learning_basics",
                learning_difficulty=0.6,
                prerequisite_concepts=["statistics", "linear_algebra", "programming"],
                learning_time_estimate=20.0,
                best_learning_strategy=LearningStrategy.CURRICULUM,
                common_misconceptions=[
                    "more_data_always_better",
                    "complex_models_always_better"
                ],
                effective_analogies=["learning_from_examples", "pattern_matching"],
                mastery_indicators=["understands_bias_variance_tradeoff", "can_select_appropriate_model"]
            ),
            MetaKnowledge(
                concept="asynchronous_programming",
                learning_difficulty=0.8,
                prerequisite_concepts=["synchronous_programming", "callbacks", "event_loops"],
                learning_time_estimate=10.0,
                best_learning_strategy=LearningStrategy.SUPERVISED,
                common_misconceptions=[
                    "async_always_faster",
                    "async_is_multithreading"
                ],
                effective_analogies=["restaurant_service", "cooking_multiple_dishes"],
                mastery_indicators=["understands_event_loop", "handles_errors_correctly"]
            ),
            MetaKnowledge(
                concept="database_normalization",
                learning_difficulty=0.6,
                prerequisite_concepts=["relational_databases", "data_modeling"],
                learning_time_estimate=6.0,
                best_learning_strategy=LearningStrategy.SUPERVISED,
                common_misconceptions=[
                    "always_normalize_to_3nf",
                    "denormalization_is_bad"
                ],
                effective_analogies=["organizing_closet", "reducing_redundancy"],
                mastery_indicators=["knows_normal_forms", "understands_tradeoffs"]
            )
        ]

        self.meta_knowledge_base.extend(base_knowledge)

    async def select_learning_strategy(self, context: LearningContext) -> LearningStrategy:
        """
        Select optimal learning strategy based on context

        Chooses strategy based on data availability, time, and prior knowledge
        """
        if self.verbose:
            print(f"\n🎓 Selecting learning strategy...")
            print(f"   Domain: {context.domain}")
            print(f"   Data: {context.data_availability}")
            print(f"   Prior knowledge: {len(context.prior_knowledge)} domains")

        # Strategy selection logic
        if context.data_availability == "none":
            # No data available - use zero-shot
            strategy = LearningStrategy.ZERO_SHOT
            reason = "No training data available"

        elif context.data_availability == "limited":
            # Limited data - use few-shot or transfer learning
            if context.prior_knowledge:
                strategy = LearningStrategy.TRANSFER
                reason = "Limited data but relevant prior knowledge available"
            else:
                strategy = LearningStrategy.FEW_SHOT
                reason = "Limited data, no prior knowledge"

        elif context.prior_knowledge:
            # Abundant data + prior knowledge - transfer learning
            strategy = LearningStrategy.TRANSFER
            reason = "Can leverage knowledge from related domains"

        elif context.time_constraints > 0.7:
            # Time pressure - active learning (query most informative examples)
            strategy = LearningStrategy.ACTIVE
            reason = "High time pressure, need efficient learning"

        elif context.complexity > 0.7:
            # Complex task - curriculum learning (start simple, increase difficulty)
            strategy = LearningStrategy.CURRICULUM
            reason = "High complexity, need structured learning path"

        else:
            # Default - supervised learning
            strategy = LearningStrategy.SUPERVISED
            reason = "Standard supervised learning approach"

        if self.verbose:
            print(f"   Selected: {strategy.value}")
            print(f"   Reason: {reason}")

        return strategy

    async def identify_transfer_opportunities(self, target_domain: str) -> List[KnowledgeTransfer]:
        """
        Identify opportunities to transfer knowledge from other domains

        Looks at domain experts to find transferable concepts
        """
        transfers = []

        # Check all available domain experts
        for source_domain, expert in self.domain_experts.items():
            if source_domain == target_domain:
                continue  # Can't transfer from self

            # Find common concepts
            source_concepts = set(expert.knowledge_base.concepts)

            # Check if target domain expert exists
            if target_domain in self.domain_experts:
                target_expert = self.domain_experts[target_domain]
                target_concepts = set(target_expert.knowledge_base.concepts)

                # Transferable concepts are those in common
                transferable = list(source_concepts & target_concepts)

                if transferable:
                    # Calculate transfer effectiveness
                    # More concepts in common = more effective transfer
                    effectiveness = len(transferable) / max(len(source_concepts), len(target_concepts))

                    # What adaptation is needed?
                    # Concepts not in target but in source might need explanation
                    adaptation_needed = list(source_concepts - target_concepts)[:5]

                    transfer = KnowledgeTransfer(
                        source_domain=source_domain,
                        target_domain=target_domain,
                        transferable_concepts=transferable,
                        transfer_effectiveness=effectiveness,
                        adaptation_required=adaptation_needed,
                        confidence=effectiveness
                    )

                    transfers.append(transfer)

        # Sort by effectiveness
        transfers.sort(key=lambda t: t.transfer_effectiveness, reverse=True)

        if self.verbose and transfers:
            print(f"\n🔄 Transfer opportunities identified: {len(transfers)}")
            for i, t in enumerate(transfers[:3], 1):
                print(f"   {i}. {t.source_domain} → {t.target_domain} "
                      f"(effectiveness={t.transfer_effectiveness:.2f}, "
                      f"concepts={len(t.transferable_concepts)})")

        return transfers

    async def apply_transferred_knowledge(self, task: str,
                                         transfer: KnowledgeTransfer) -> str:
        """
        Apply knowledge from source domain to target domain task
        """
        if self.verbose:
            print(f"\n🔄 Applying transfer learning...")
            print(f"   Source: {transfer.source_domain}")
            print(f"   Target: {transfer.target_domain}")
            print(f"   Transferable concepts: {len(transfer.transferable_concepts)}")

        # Get source domain expert
        source_expert = self.domain_experts[transfer.source_domain]

        # Generate solution using source domain expertise
        source_solution = await source_expert.solve_with_expertise(task, {})

        # Adapt solution for target domain
        adapted_solution = (
            f"Applying knowledge from {transfer.source_domain}:\n\n"
            f"{source_solution}\n\n"
            f"Transferable concepts: {', '.join(transfer.transferable_concepts[:5])}\n"
            f"Transfer effectiveness: {transfer.transfer_effectiveness:.1%}"
        )

        if transfer.adaptation_required:
            adapted_solution += f"\n\nNote: May need adaptation for: {', '.join(transfer.adaptation_required[:3])}"

        return adapted_solution

    def adapt_learning_rate(self, task: str, performance: float) -> float:
        """
        Adapt learning rate based on progress

        Increases rate if improving, decreases if plateaued
        """
        if task not in self.learning_curves:
            # First observation - use base rate
            self.learning_curves[task] = LearningCurve(
                task=task,
                strategy=LearningStrategy.SUPERVISED,  # Default
                performance_history=[(datetime.now(), performance)],
                learning_rate=self.base_learning_rate,
                plateau_detected=False,
                plateau_count=0,
                total_learning_time=0.0
            )
            return self.base_learning_rate

        curve = self.learning_curves[task]

        # Add new performance point
        curve.performance_history.append((datetime.now(), performance))

        # Check for plateau (no improvement in last N iterations)
        if len(curve.performance_history) >= 3:
            recent_performance = [p for _, p in curve.performance_history[-3:]]

            # If performance isn't improving
            if max(recent_performance) - min(recent_performance) < 0.05:
                curve.plateau_count += 1

                if curve.plateau_count >= self.plateau_threshold:
                    curve.plateau_detected = True
                    # Decrease learning rate to escape plateau
                    curve.learning_rate *= 0.5
                    curve.plateau_count = 0  # Reset counter

                    if self.verbose:
                        print(f"\n📉 Plateau detected for {task}")
                        print(f"   Reducing learning rate to {curve.learning_rate:.4f}")
            else:
                # Improving - increase learning rate slightly
                curve.learning_rate = min(1.0, curve.learning_rate * 1.1)
                curve.plateau_count = 0
                curve.plateau_detected = False

        return curve.learning_rate

    async def meta_learn(self, task: str, context: LearningContext) -> str:
        """
        Apply meta-learning: learning to learn

        Uses knowledge about learning strategies to optimize learning process
        """
        if self.verbose:
            print(f"\n🎓 Meta-learning approach...")

        # 1. Check meta-knowledge base for relevant concepts
        relevant_meta = []
        for meta in self.meta_knowledge_base:
            if any(keyword in task.lower() for keyword in [meta.concept.lower(), *[p.lower() for p in meta.prerequisite_concepts]]):
                relevant_meta.append(meta)

        # 2. If we have meta-knowledge, use it
        if relevant_meta:
            best_meta = max(relevant_meta, key=lambda m: 1.0 - m.learning_difficulty)

            solution = (
                f"Meta-learning approach for '{task}':\n\n"
                f"Concept: {best_meta.concept}\n"
                f"Learning difficulty: {best_meta.learning_difficulty:.1%}\n"
                f"Estimated learning time: {best_meta.learning_time_estimate:.1f} hours\n"
                f"Best strategy: {best_meta.best_learning_strategy.value}\n\n"
                f"Prerequisites:\n"
            )

            for prereq in best_meta.prerequisite_concepts:
                solution += f"  - {prereq}\n"

            solution += f"\nEffective analogies:\n"
            for analogy in best_meta.effective_analogies:
                solution += f"  - {analogy}\n"

            solution += f"\nCommon misconceptions to avoid:\n"
            for misconception in best_meta.common_misconceptions:
                solution += f"  - {misconception}\n"

            solution += f"\nMastery indicators:\n"
            for indicator in best_meta.mastery_indicators:
                solution += f"  - {indicator}\n"

        else:
            # No specific meta-knowledge - use general learning principles
            solution = (
                f"Meta-learning principles for '{task}':\n\n"
                "1. Start with fundamentals before advanced topics\n"
                "2. Practice deliberately with feedback\n"
                "3. Space repetition over time\n"
                "4. Test yourself frequently\n"
                "5. Connect new knowledge to existing knowledge\n"
                "6. Teach others to solidify understanding\n"
                "7. Reflect on learning process regularly\n"
            )

        return solution

    async def learn_with_strategy(self, task: str, strategy: LearningStrategy) -> str:
        """
        Learn task using specified strategy
        """
        if self.verbose:
            print(f"\n📚 Learning with strategy: {strategy.value}")

        # Simulate learning with different strategies
        strategy_approaches = {
            LearningStrategy.SUPERVISED: "Learn from labeled examples with clear inputs and outputs",
            LearningStrategy.UNSUPERVISED: "Discover patterns and structure in data without labels",
            LearningStrategy.REINFORCEMENT: "Learn through trial and error with rewards and penalties",
            LearningStrategy.FEW_SHOT: "Learn from only a few examples by leveraging prior knowledge",
            LearningStrategy.ZERO_SHOT: "Apply without examples using only task description",
            LearningStrategy.CURRICULUM: "Start simple, gradually increase difficulty",
            LearningStrategy.ACTIVE: "Query most informative examples to learn efficiently",
            LearningStrategy.META: "Learn how to learn this type of task more effectively"
        }

        approach = strategy_approaches.get(strategy, "Apply general learning principles")

        solution = (
            f"Learning strategy: {strategy.value}\n"
            f"Approach: {approach}\n\n"
            f"Applying to task: {task}\n"
        )

        return solution

    async def learn_optimally(self, task: str, context: LearningContext) -> MetaLearningSolution:
        """
        Learn using optimal strategy based on context

        Integrates strategy selection, transfer learning, and meta-learning
        """
        if self.verbose:
            print(f"\n🎓 Optimal learning for: {task[:60]}...")

        start_time = datetime.now()

        # 1. Select optimal strategy
        strategy = await self.select_learning_strategy(context)

        # 2. Identify transfer opportunities
        transfers = []
        if strategy == LearningStrategy.TRANSFER:
            transfers = await self.identify_transfer_opportunities(context.domain)

        learning_insights = []

        # 3. Apply appropriate learning approach
        if strategy == LearningStrategy.TRANSFER and transfers:
            # Use transfer learning
            best_transfer = transfers[0]
            self.knowledge_transfers.append(best_transfer)
            solution = await self.apply_transferred_knowledge(task, best_transfer)
            learning_insights.append(
                f"Successfully transferred knowledge from {best_transfer.source_domain}"
            )

        elif strategy == LearningStrategy.META:
            # Use meta-learning
            solution = await self.meta_learn(task, context)
            learning_insights.append("Applied meta-learning principles")

        else:
            # Use selected strategy
            solution = await self.learn_with_strategy(task, strategy)
            learning_insights.append(f"Used {strategy.value} approach")

        # 4. Estimate learning time
        # Check meta-knowledge for time estimate
        relevant_meta = [m for m in self.meta_knowledge_base
                        if m.concept.lower() in task.lower()]

        if relevant_meta:
            learning_time = relevant_meta[0].learning_time_estimate
        else:
            # Default estimates based on complexity
            learning_time = context.complexity * 10.0  # Hours

        learning_insights.append(f"Estimated learning time: {learning_time:.1f} hours")

        # 5. Calculate meta-learning score
        meta_score = self._calculate_meta_learning_score(
            strategy, transfers, context
        )

        end_time = datetime.now()

        meta_solution = MetaLearningSolution(
            solution=solution,
            strategy_used=strategy,
            knowledge_transfers=transfers,
            learning_time_estimate=learning_time,
            meta_learning_score=meta_score,
            learning_insights=learning_insights
        )

        self.meta_learning_solutions.append(meta_solution)

        if self.verbose:
            print(f"\n✅ Optimal learning complete!")
            print(f"   Strategy: {strategy.value}")
            print(f"   Transfers: {len(transfers)}")
            print(f"   Meta-score: {meta_score:.2f}")
            print(f"   Estimated time: {learning_time:.1f}h")

        return meta_solution

    def _calculate_meta_learning_score(self, strategy: LearningStrategy,
                                       transfers: List[KnowledgeTransfer],
                                       context: LearningContext) -> float:
        """Calculate meta-learning effectiveness score"""
        # Components:
        # 1. Strategy appropriateness (did we pick the right strategy?)
        # 2. Transfer effectiveness (if using transfer learning)
        # 3. Meta-knowledge utilization
        # 4. Learning efficiency

        # Strategy appropriateness (baseline 0.7, higher for optimal choices)
        strategy_score = 0.7
        if strategy == LearningStrategy.TRANSFER and context.prior_knowledge:
            strategy_score = 0.9
        elif strategy == LearningStrategy.ZERO_SHOT and context.data_availability == "none":
            strategy_score = 0.9
        elif strategy == LearningStrategy.CURRICULUM and context.complexity > 0.7:
            strategy_score = 0.9

        # Transfer effectiveness
        if transfers:
            transfer_score = sum(t.transfer_effectiveness for t in transfers) / len(transfers)
        else:
            transfer_score = 0.6  # Neutral if no transfers

        # Meta-knowledge utilization
        meta_knowledge_score = min(1.0, len(self.meta_knowledge_base) / 10.0)

        # Learning efficiency (how many strategies we've mastered)
        efficiency_score = min(1.0, len(self.meta_learning_solutions) / 20.0) + 0.4

        # Weighted average
        meta_score = (
            strategy_score * 0.3 +
            transfer_score * 0.3 +
            meta_knowledge_score * 0.2 +
            efficiency_score * 0.2
        )

        return meta_score

    def get_meta_learning_metrics(self) -> Dict[str, Any]:
        """Get meta-learning performance metrics"""
        if not self.meta_learning_solutions:
            return {
                "meta_learning_score": 40.0,  # Baseline
                "strategies_used": 0,
                "knowledge_transfers": 0,
                "meta_knowledge_entries": len(self.meta_knowledge_base)
            }

        # Strategy diversity
        strategies_used = set(s.strategy_used for s in self.meta_learning_solutions)

        # Average meta-score
        avg_meta_score = sum(s.meta_learning_score for s in self.meta_learning_solutions) / len(self.meta_learning_solutions)

        # Transfer effectiveness
        avg_transfer_effectiveness = 0.0
        if self.knowledge_transfers:
            avg_transfer_effectiveness = sum(t.transfer_effectiveness for t in self.knowledge_transfers) / len(self.knowledge_transfers)

        # Meta-learning score (0-100)
        # Started at 40%, so calculate improvement
        strategy_diversity = len(strategies_used) / len(LearningStrategy)
        meta_knowledge_coverage = min(1.0, len(self.meta_knowledge_base) / 15.0)

        meta_learning_score = (
            avg_meta_score * 30 +  # 30% weight on solution quality
            strategy_diversity * 20 +  # 20% weight on strategy diversity
            avg_transfer_effectiveness * 25 +  # 25% weight on transfer learning
            meta_knowledge_coverage * 25  # 25% weight on meta-knowledge
        ) * 100

        # Add baseline (started at 40%)
        meta_learning_score = min(100, 40 + meta_learning_score * 0.6)

        return {
            "meta_learning_score": meta_learning_score,
            "strategies_used": len(strategies_used),
            "total_strategies": len(LearningStrategy),
            "knowledge_transfers": len(self.knowledge_transfers),
            "avg_transfer_effectiveness": avg_transfer_effectiveness,
            "meta_knowledge_entries": len(self.meta_knowledge_base),
            "learning_solutions": len(self.meta_learning_solutions),
            "average_meta_score": avg_meta_score,
            "strategy_diversity": strategy_diversity,
            "meta_knowledge_coverage": meta_knowledge_coverage
        }


# ============================================================================
# DEMONSTRATION
# ============================================================================

async def main():
    """Demonstrate Meta-Learning Runtime"""

    print("=" * 70)
    print("🎓 META-LEARNING RUNTIME DEMONSTRATION")
    print("Phase 5.3: Meta-Learning")
    print("=" * 70)

    runtime = MetaLearningRuntime(verbose=True)

    # Test meta-learning with various contexts
    test_contexts = [
        {
            "task": "Learn recursion for solving tree traversal problems",
            "context": LearningContext(
                domain="computer_science",
                task_type="algorithm",
                data_availability="limited",
                time_constraints=0.5,
                performance_target=0.8,
                prior_knowledge={"mathematics": 0.75},
                complexity=0.7
            )
        },
        {
            "task": "Understand quantum mechanics principles",
            "context": LearningContext(
                domain="physics",
                task_type="theory",
                data_availability="abundant",
                time_constraints=0.3,
                performance_target=0.7,
                prior_knowledge={"mathematics": 0.80, "physics": 0.60},
                complexity=0.9
            )
        },
        {
            "task": "Master asynchronous programming patterns",
            "context": LearningContext(
                domain="computer_science",
                task_type="programming",
                data_availability="abundant",
                time_constraints=0.6,
                performance_target=0.85,
                prior_knowledge={"computer_science": 0.82},
                complexity=0.8
            )
        }
    ]

    print(f"\n📋 Testing {len(test_contexts)} learning contexts...\n")

    for i, test in enumerate(test_contexts, 1):
        print(f"\n{'=' * 70}")
        print(f"Test {i}/{len(test_contexts)}")
        print(f"{'=' * 70}")

        solution = await runtime.learn_optimally(test["task"], test["context"])

        print(f"\n📊 Results:")
        print(f"   Strategy: {solution.strategy_used.value}")
        print(f"   Transfers: {len(solution.knowledge_transfers)}")
        if solution.knowledge_transfers:
            print(f"   Best transfer: {solution.knowledge_transfers[0].source_domain} "
                  f"(effectiveness={solution.knowledge_transfers[0].transfer_effectiveness:.2f})")
        print(f"   Meta-score: {solution.meta_learning_score:.2f}")
        print(f"   Learning time: {solution.learning_time_estimate:.1f}h")
        print(f"\n   Learning insights:")
        for insight in solution.learning_insights:
            print(f"   - {insight}")

    # Get overall metrics
    print(f"\n{'=' * 70}")
    print("📈 META-LEARNING METRICS")
    print(f"{'=' * 70}")

    metrics = runtime.get_meta_learning_metrics()
    print(f"Meta-Learning Score: {metrics['meta_learning_score']:.1f}%")
    print(f"Strategies used: {metrics['strategies_used']}/{metrics['total_strategies']}")
    print(f"Knowledge transfers: {metrics['knowledge_transfers']}")
    print(f"Average transfer effectiveness: {metrics['avg_transfer_effectiveness']:.2f}")
    print(f"Meta-knowledge entries: {metrics['meta_knowledge_entries']}")
    print(f"Learning solutions: {metrics['learning_solutions']}")
    print(f"Average meta-score: {metrics['average_meta_score']:.2f}")
    print(f"Strategy diversity: {metrics['strategy_diversity']:.2f}")

    # Calculate dimension impact
    print(f"\n{'=' * 70}")
    print("📈 ESTIMATED AGI IMPACT")
    print(f"{'=' * 70}")

    meta_score = metrics['meta_learning_score'] / 100.0
    agi_impact = (meta_score - 0.40) * 0.08 * 100  # Started at 40%, 8% weight

    print(f"Meta-Learning dimension: 40% → {meta_score*100:.1f}% (+{(meta_score-0.40)*100:.1f} points)")
    print(f"Overall AGI: 94.4% → {94.4 + agi_impact:.1f}% (+{agi_impact:.1f} points)")
    print(f"Status: {'✅ Phase 5.3 COMPLETE' if meta_score >= 0.85 else '⚠️ Below target (85%)'}")

    print(f"\n✅ Meta-Learning Runtime demonstration complete!")


if __name__ == "__main__":
    asyncio.run(main())
