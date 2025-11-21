"""
Intuition Runtime

Phase 5.2: Intuition
Target: Intuition 20% → 70% (+50 points)
Expected AGI Impact: +4.0 points (50% × 0.08 weight)

Extends EmotionalIntelligenceRuntime with:
- Pattern recognition without explicit rules
- Heuristic development
- Gut feeling simulation
- Fast vs Slow thinking (Kahneman's System 1/2)
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
import random

# Import parent runtime
from emotional_intelligence_runtime import (
    EmotionalIntelligenceRuntime,
    EmotionalContext,
    EmotionalSolution
)


# ============================================================================
# INTUITION DATA STRUCTURES
# ============================================================================

class PatternType(Enum):
    """Types of patterns that can be recognized"""
    STRUCTURAL = "structural"  # Arrangement/organization patterns
    TEMPORAL = "temporal"  # Time-based sequences
    ANALOGICAL = "analogical"  # Similarity to known situations
    CAUSAL = "causal"  # Cause-and-effect relationships
    STATISTICAL = "statistical"  # Frequency/probability patterns


class GutDirection(Enum):
    """Direction of gut feeling"""
    POSITIVE = "positive"  # Go ahead, good idea
    NEGATIVE = "negative"  # Avoid, bad idea
    NEUTRAL = "neutral"  # No strong feeling
    WARNING = "warning"  # Caution, potential danger


class ThinkingMode(Enum):
    """Kahneman's dual-process theory"""
    SYSTEM_1 = "fast_intuitive"  # Fast, automatic, emotional
    SYSTEM_2 = "slow_deliberate"  # Slow, effortful, logical


@dataclass
class IntuitivePattern:
    """Learned pattern from experience"""
    pattern_id: str
    pattern_type: PatternType
    description: str
    confidence: float  # 0.0-1.0
    instances_seen: int
    first_encountered: datetime
    last_applied: datetime
    success_rate: float  # Historical accuracy
    keywords: List[str]


@dataclass
class Heuristic:
    """Rule of thumb developed from experience"""
    heuristic_id: str
    rule: str  # "If X, then probably Y"
    domain: str
    reliability: float  # 0.0-1.0
    applications: int
    successes: int
    failures: int
    created: datetime


@dataclass
class GutFeeling:
    """Intuitive assessment"""
    direction: GutDirection
    strength: float  # 0.0-1.0 confidence in the feeling
    basis: str  # Why we feel this way
    reliability: float  # Historical accuracy of similar feelings
    explanation: Optional[str]  # Post-hoc rationalization
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class IntuitiveSolution:
    """Solution generated intuitively"""
    solution: str
    pattern_used: Optional[IntuitivePattern]
    heuristics_applied: List[Heuristic]
    gut_feeling: GutFeeling
    thinking_mode: ThinkingMode
    confidence: float
    reasoning_time: float  # Milliseconds
    timestamp: datetime = field(default_factory=datetime.now)


# ============================================================================
# INTUITION RUNTIME
# ============================================================================

class IntuitionRuntime(EmotionalIntelligenceRuntime):
    """
    Phase 5.2: Intuition Runtime

    Extends EmotionalIntelligenceRuntime with fast pattern recognition and gut feelings.

    Target: Intuition 20% → 70%
    Expected AGI Impact: 92.0% → 94.4% (+2.4 points)
    """

    def __init__(self, verbose=True, enable_learning=True, reasoning_depth=5,
                 constraints: Optional[Any] = None, health_check_interval: int = 60):
        super().__init__(verbose=verbose, enable_learning=enable_learning,
                        reasoning_depth=reasoning_depth, constraints=constraints,
                        health_check_interval=health_check_interval)

        # Intuition components
        self.learned_patterns: List[IntuitivePattern] = []
        self.heuristics: List[Heuristic] = []
        self.gut_feelings_history: List[GutFeeling] = []
        self.intuitive_solutions: List[IntuitiveSolution] = []

        # Initialize with some common patterns and heuristics
        self._initialize_base_patterns()
        self._initialize_base_heuristics()

        # Thinking mode thresholds
        self.system1_complexity_threshold = 0.4  # Use intuition if complexity < 0.4
        self.system1_time_pressure_threshold = 0.7  # Use intuition if time pressure > 0.7

        if self.verbose:
            print("\n⚡ Intuition Runtime initialized")
            print(f"   Learned patterns: {len(self.learned_patterns)}")
            print(f"   Heuristics: {len(self.heuristics)}")

    def _initialize_base_patterns(self):
        """Initialize with common patterns everyone recognizes"""
        base_patterns = [
            IntuitivePattern(
                pattern_id="error_retry_loop",
                pattern_type=PatternType.TEMPORAL,
                description="Same error appearing after multiple retry attempts",
                confidence=0.85,
                instances_seen=100,
                first_encountered=datetime.now(),
                last_applied=datetime.now(),
                success_rate=0.88,
                keywords=["error", "retry", "again", "still", "repeated"]
            ),
            IntuitivePattern(
                pattern_id="deadline_pressure",
                pattern_type=PatternType.TEMPORAL,
                description="Approaching deadline with incomplete work",
                confidence=0.90,
                instances_seen=150,
                first_encountered=datetime.now(),
                last_applied=datetime.now(),
                success_rate=0.85,
                keywords=["deadline", "time", "urgent", "soon", "hurry"]
            ),
            IntuitivePattern(
                pattern_id="friday_deployment",
                pattern_type=PatternType.TEMPORAL,
                description="Deploying to production on Friday evening",
                confidence=0.95,
                instances_seen=50,
                first_encountered=datetime.now(),
                last_applied=datetime.now(),
                success_rate=0.92,
                keywords=["friday", "deploy", "production", "evening", "weekend"]
            ),
            IntuitivePattern(
                pattern_id="complexity_escalation",
                pattern_type=PatternType.STRUCTURAL,
                description="Problem complexity increasing faster than expected",
                confidence=0.80,
                instances_seen=75,
                first_encountered=datetime.now(),
                last_applied=datetime.now(),
                success_rate=0.82,
                keywords=["complex", "complicated", "harder", "difficult", "unexpected"]
            ),
            IntuitivePattern(
                pattern_id="team_conflict",
                pattern_type=PatternType.CAUSAL,
                description="Team performance degrading due to interpersonal conflict",
                confidence=0.85,
                instances_seen=60,
                first_encountered=datetime.now(),
                last_applied=datetime.now(),
                success_rate=0.80,
                keywords=["conflict", "disagreement", "tension", "team", "morale"]
            )
        ]

        self.learned_patterns.extend(base_patterns)

    def _initialize_base_heuristics(self):
        """Initialize with common heuristics"""
        base_heuristics = [
            Heuristic(
                heuristic_id="simple_first",
                rule="If problem seems complex, try simplest solution first",
                domain="problem_solving",
                reliability=0.85,
                applications=200,
                successes=170,
                failures=30,
                created=datetime.now()
            ),
            Heuristic(
                heuristic_id="test_before_commit",
                rule="If making code changes, always test before committing",
                domain="software_development",
                reliability=0.95,
                applications=500,
                successes=475,
                failures=25,
                created=datetime.now()
            ),
            Heuristic(
                heuristic_id="backup_before_experiment",
                rule="If trying something risky, backup current state first",
                domain="risk_management",
                reliability=0.92,
                applications=150,
                successes=138,
                failures=12,
                created=datetime.now()
            ),
            Heuristic(
                heuristic_id="ask_experts",
                rule="If stuck for > 2 hours, ask someone with more experience",
                domain="problem_solving",
                reliability=0.88,
                applications=100,
                successes=88,
                failures=12,
                created=datetime.now()
            ),
            Heuristic(
                heuristic_id="iterate_quickly",
                rule="If uncertain about approach, prototype quickly and test",
                domain="product_development",
                reliability=0.82,
                applications=120,
                successes=98,
                failures=22,
                created=datetime.now()
            )
        ]

        self.heuristics.extend(base_heuristics)

    async def recognize_pattern(self, situation: str) -> List[IntuitivePattern]:
        """
        Fast pattern recognition without explicit reasoning

        Matches situation against learned patterns using keyword similarity
        """
        situation_lower = situation.lower()

        # Fast keyword matching
        matching_patterns = []
        for pattern in self.learned_patterns:
            # Count keyword matches
            matches = sum(1 for keyword in pattern.keywords if keyword in situation_lower)

            if matches > 0:
                # Pattern matches! Adjust confidence based on match quality
                match_quality = matches / len(pattern.keywords)
                adjusted_confidence = pattern.confidence * pattern.success_rate * match_quality

                # Create a copy with adjusted confidence
                recognized_pattern = IntuitivePattern(
                    pattern_id=pattern.pattern_id,
                    pattern_type=pattern.pattern_type,
                    description=pattern.description,
                    confidence=adjusted_confidence,
                    instances_seen=pattern.instances_seen + 1,
                    first_encountered=pattern.first_encountered,
                    last_applied=datetime.now(),
                    success_rate=pattern.success_rate,
                    keywords=pattern.keywords
                )

                matching_patterns.append(recognized_pattern)

        # Sort by confidence
        matching_patterns.sort(key=lambda p: p.confidence, reverse=True)

        if self.verbose and matching_patterns:
            print(f"\n⚡ Pattern recognition (fast):")
            for i, pattern in enumerate(matching_patterns[:3], 1):
                print(f"   {i}. {pattern.description} (confidence={pattern.confidence:.2f}, type={pattern.pattern_type.value})")

        return matching_patterns

    async def generate_gut_feeling(self, situation: str) -> GutFeeling:
        """
        Generate intuitive gut feeling about situation

        Synthesizes pattern recognition and heuristics into a feeling
        """
        situation_lower = situation.lower()

        # Recognize patterns
        patterns = await self.recognize_pattern(situation)

        # Check for warning signs (common bad ideas)
        warning_keywords = {
            "friday deploy": 0.9,
            "skip test": 0.85,
            "no backup": 0.8,
            "rush": 0.75,
            "ignore warning": 0.85,
            "force push": 0.9,
            "production hotfix": 0.7
        }

        warning_score = 0.0
        warning_basis = []
        for keyword, weight in warning_keywords.items():
            if keyword in situation_lower:
                warning_score = max(warning_score, weight)
                warning_basis.append(keyword)

        # Check for positive signs
        positive_keywords = {
            "tested": 0.8,
            "reviewed": 0.75,
            "approved": 0.8,
            "documented": 0.7,
            "validated": 0.85
        }

        positive_score = 0.0
        positive_basis = []
        for keyword, weight in positive_keywords.items():
            if keyword in situation_lower:
                positive_score = max(positive_score, weight)
                positive_basis.append(keyword)

        # Determine gut feeling direction
        if warning_score > 0.7:
            direction = GutDirection.WARNING
            strength = warning_score
            basis = f"Warning signs detected: {', '.join(warning_basis)}"
        elif warning_score > positive_score:
            direction = GutDirection.NEGATIVE
            strength = warning_score
            basis = f"Negative indicators: {', '.join(warning_basis)}"
        elif positive_score > 0.6:
            direction = GutDirection.POSITIVE
            strength = positive_score
            basis = f"Positive indicators: {', '.join(positive_basis)}"
        elif patterns and patterns[0].confidence > 0.6:
            # Pattern-based feeling
            if patterns[0].success_rate > 0.7:
                direction = GutDirection.POSITIVE
            else:
                direction = GutDirection.NEGATIVE
            strength = patterns[0].confidence
            basis = f"Pattern match: {patterns[0].description}"
        else:
            direction = GutDirection.NEUTRAL
            strength = 0.5
            basis = "No strong indicators detected"

        # Reliability based on history
        # For now, use a baseline + pattern success rates
        reliability = 0.7  # Baseline gut feeling reliability
        if patterns:
            reliability = sum(p.success_rate for p in patterns[:3]) / min(3, len(patterns))

        # Post-hoc explanation
        explanation = f"Based on {len(patterns)} pattern matches and keyword analysis"

        gut_feeling = GutFeeling(
            direction=direction,
            strength=strength,
            basis=basis,
            reliability=reliability,
            explanation=explanation
        )

        self.gut_feelings_history.append(gut_feeling)

        if self.verbose:
            print(f"\n🎯 Gut feeling generated:")
            print(f"   Direction: {direction.value}")
            print(f"   Strength: {strength:.2f}")
            print(f"   Basis: {basis}")
            print(f"   Reliability: {reliability:.2f}")

        return gut_feeling

    async def apply_heuristics(self, situation: str, domain: str = "general") -> List[Heuristic]:
        """
        Apply relevant heuristics to situation

        Fast selection of applicable rules-of-thumb
        """
        applicable = []

        for heuristic in self.heuristics:
            # Check if heuristic domain matches or is general
            if heuristic.domain == domain or heuristic.domain == "general":
                # Fast check if heuristic might apply
                # For now, use simple keyword matching
                rule_keywords = heuristic.rule.lower().split()
                situation_words = situation.lower().split()

                # If any rule keywords appear in situation
                if any(keyword in situation_words for keyword in rule_keywords[:3]):
                    applicable.append(heuristic)

        if self.verbose and applicable:
            print(f"\n📏 Heuristics applied: {len(applicable)}")
            for h in applicable[:3]:
                print(f"   - {h.rule[:60]}... (reliability={h.reliability:.2f})")

        return applicable

    def assess_complexity(self, problem: str) -> float:
        """
        Assess problem complexity quickly (for System 1/2 decision)

        Returns: 0.0-1.0 complexity score
        """
        complexity_indicators = {
            "keywords": ["complex", "complicated", "difficult", "intricate", "sophisticated"],
            "length": len(problem.split()),  # Longer problems often more complex
            "questions": problem.count("?"),  # Multiple questions = more complex
            "conditions": sum(1 for word in ["if", "when", "unless", "provided"] if word in problem.lower())
        }

        # Keyword score
        keyword_score = sum(1 for keyword in complexity_indicators["keywords"] if keyword in problem.lower()) / len(complexity_indicators["keywords"])

        # Length score (normalized by 100 words)
        length_score = min(1.0, complexity_indicators["length"] / 100.0)

        # Questions score
        question_score = min(1.0, complexity_indicators["questions"] / 3.0)

        # Conditions score
        condition_score = min(1.0, complexity_indicators["conditions"] / 3.0)

        # Weighted average
        complexity = (
            keyword_score * 0.3 +
            length_score * 0.3 +
            question_score * 0.2 +
            condition_score * 0.2
        )

        return complexity

    def assess_time_pressure(self, context: Optional[Dict] = None) -> float:
        """
        Assess time pressure quickly

        Returns: 0.0-1.0 pressure score
        """
        if not context:
            return 0.3  # Default moderate pressure

        # Check for time-related context
        if "deadline" in context:
            # TODO: Calculate based on actual deadline
            return 0.8
        elif "urgent" in context:
            return 0.9
        elif "immediate" in context:
            return 1.0
        else:
            return 0.3

    async def intuitive_solve(self, problem: str, context: Optional[Dict] = None) -> IntuitiveSolution:
        """
        Solve problem intuitively (System 1 thinking)

        Fast, automatic, pattern-based solution
        """
        start_time = datetime.now()

        if self.verbose:
            print(f"\n⚡ Intuitive solving (System 1)...")

        # 1. Fast pattern recognition
        patterns = await self.recognize_pattern(problem)

        # 2. Generate gut feeling
        gut = await self.generate_gut_feeling(problem)

        # 3. Apply heuristics
        heuristics = await self.apply_heuristics(problem)

        # 4. Check gut feeling - if warning, defer to System 2
        if gut.direction == GutDirection.WARNING and gut.strength > 0.7:
            if self.verbose:
                print(f"   ⚠️ Strong warning detected - deferring to System 2 reasoning")

            # Fall back to slow reasoning
            reasoning = await self.reason_sequentially(problem, depth=7)
            solution_text = reasoning.conclusion
            confidence = reasoning.confidence
            thinking_mode = ThinkingMode.SYSTEM_2

            end_time = datetime.now()
            reasoning_time = (end_time - start_time).total_seconds() * 1000  # ms

            return IntuitiveSolution(
                solution=solution_text,
                pattern_used=None,
                heuristics_applied=heuristics,
                gut_feeling=gut,
                thinking_mode=thinking_mode,
                confidence=confidence,
                reasoning_time=reasoning_time
            )

        # 5. Use best pattern if available
        if patterns and patterns[0].confidence > 0.6:
            best_pattern = patterns[0]

            # Generate solution based on pattern
            solution_text = f"Pattern recognized: {best_pattern.description}. " \
                          f"Applying proven approach (success rate: {best_pattern.success_rate*100:.0f}%). "

            # Add heuristic guidance
            if heuristics:
                solution_text += f"Applying heuristic: {heuristics[0].rule}"

            confidence = best_pattern.confidence * best_pattern.success_rate

            if self.verbose:
                print(f"   ✅ Pattern-based solution (confidence={confidence:.2f})")

        else:
            # No strong pattern - use heuristics or default approach
            if heuristics:
                solution_text = f"No clear pattern, but applying heuristic: {heuristics[0].rule}"
                confidence = heuristics[0].reliability * 0.7
            else:
                solution_text = "No clear pattern or heuristic match. Recommend systematic analysis."
                confidence = 0.5

            best_pattern = None

            if self.verbose:
                print(f"   💡 Heuristic-based solution (confidence={confidence:.2f})")

        end_time = datetime.now()
        reasoning_time = (end_time - start_time).total_seconds() * 1000  # ms

        solution = IntuitiveSolution(
            solution=solution_text,
            pattern_used=best_pattern,
            heuristics_applied=heuristics,
            gut_feeling=gut,
            thinking_mode=ThinkingMode.SYSTEM_1,
            confidence=confidence,
            reasoning_time=reasoning_time
        )

        self.intuitive_solutions.append(solution)

        return solution

    async def solve_with_adaptive_thinking(self, problem: str,
                                           context: Optional[Dict] = None) -> IntuitiveSolution:
        """
        Solve problem with adaptive thinking mode selection

        Chooses between System 1 (intuition) and System 2 (deliberation)
        """
        # Assess problem characteristics
        complexity = self.assess_complexity(problem)
        time_pressure = self.assess_time_pressure(context)

        if self.verbose:
            print(f"\n🧠 Adaptive thinking mode selection:")
            print(f"   Complexity: {complexity:.2f}")
            print(f"   Time pressure: {time_pressure:.2f}")

        # Decision logic: Use System 1 if low complexity OR high time pressure
        use_system1 = (complexity < self.system1_complexity_threshold or
                      time_pressure > self.system1_time_pressure_threshold)

        if use_system1:
            if self.verbose:
                print(f"   → Using System 1 (intuitive)")
            return await self.intuitive_solve(problem, context)
        else:
            if self.verbose:
                print(f"   → Using System 2 (deliberate)")

            # Use slow, deliberate reasoning
            start_time = datetime.now()
            reasoning = await self.reason_sequentially(problem, depth=7)

            # Still generate gut feeling for comparison
            gut = await self.generate_gut_feeling(problem)
            patterns = await self.recognize_pattern(problem)
            heuristics = await self.apply_heuristics(problem)

            end_time = datetime.now()
            reasoning_time = (end_time - start_time).total_seconds() * 1000

            solution = IntuitiveSolution(
                solution=reasoning.conclusion,
                pattern_used=patterns[0] if patterns else None,
                heuristics_applied=heuristics,
                gut_feeling=gut,
                thinking_mode=ThinkingMode.SYSTEM_2,
                confidence=reasoning.confidence,
                reasoning_time=reasoning_time
            )

            self.intuitive_solutions.append(solution)

            return solution

    async def develop_heuristic(self, pattern: IntuitivePattern,
                               outcome: bool) -> Optional[Heuristic]:
        """
        Develop new heuristic from successful pattern application

        If pattern works reliably, extract a rule-of-thumb
        """
        # Only create heuristic if pattern has enough data
        if pattern.instances_seen < 10:
            return None

        # Only create if success rate is high enough
        if pattern.success_rate < 0.75:
            return None

        # Create heuristic from pattern
        heuristic = Heuristic(
            heuristic_id=f"heuristic_from_{pattern.pattern_id}",
            rule=f"If situation matches '{pattern.description}', apply known solution pattern",
            domain="pattern_derived",
            reliability=pattern.success_rate,
            applications=1,
            successes=1 if outcome else 0,
            failures=0 if outcome else 1,
            created=datetime.now()
        )

        self.heuristics.append(heuristic)

        if self.verbose:
            print(f"\n📏 New heuristic developed:")
            print(f"   Rule: {heuristic.rule}")
            print(f"   Reliability: {heuristic.reliability:.2f}")

        return heuristic

    def get_intuition_metrics(self) -> Dict[str, Any]:
        """Get intuition performance metrics"""
        if not self.intuitive_solutions:
            return {
                "intuition_score": 20.0,  # Baseline
                "patterns_recognized": 0,
                "heuristics_applied": 0,
                "gut_feelings": 0
            }

        # Calculate intuition score components
        pattern_usage = len([s for s in self.intuitive_solutions if s.pattern_used]) / len(self.intuitive_solutions)
        avg_confidence = sum(s.confidence for s in self.intuitive_solutions) / len(self.intuitive_solutions)
        system1_usage = len([s for s in self.intuitive_solutions if s.thinking_mode == ThinkingMode.SYSTEM_1]) / len(self.intuitive_solutions)
        avg_speed = sum(s.reasoning_time for s in self.intuitive_solutions) / len(self.intuitive_solutions)

        # Speed score: faster is better (target < 100ms for System 1)
        speed_score = max(0.0, min(1.0, 1.0 - (avg_speed / 1000.0)))

        # Intuition score (0-100)
        intuition_score = (
            pattern_usage * 25 +  # 25% weight on pattern recognition
            avg_confidence * 25 +  # 25% weight on confidence
            system1_usage * 25 +  # 25% weight on intuitive mode usage
            speed_score * 25  # 25% weight on speed
        ) * 100

        # Add baseline (started at 20%)
        intuition_score = min(100, 20 + intuition_score * 0.8)

        return {
            "intuition_score": intuition_score,
            "patterns_recognized": len(self.learned_patterns),
            "heuristics_available": len(self.heuristics),
            "gut_feelings_generated": len(self.gut_feelings_history),
            "intuitive_solutions": len(self.intuitive_solutions),
            "pattern_usage_rate": pattern_usage,
            "average_confidence": avg_confidence,
            "system1_usage_rate": system1_usage,
            "average_reasoning_time_ms": avg_speed,
            "speed_score": speed_score
        }


# ============================================================================
# DEMONSTRATION
# ============================================================================

async def main():
    """Demonstrate Intuition Runtime"""

    print("=" * 70)
    print("⚡ INTUITION RUNTIME DEMONSTRATION")
    print("Phase 5.2: Intuition")
    print("=" * 70)

    runtime = IntuitionRuntime(verbose=True)

    # Test problems with varying complexity and time pressure
    test_cases = [
        {
            "problem": "Should we deploy to production on Friday evening?",
            "context": {"deadline": "tonight"},
            "description": "Classic bad idea (should trigger warning)"
        },
        {
            "problem": "Error 500 keeps appearing after retry, retry, retry...",
            "context": None,
            "description": "Retry loop pattern"
        },
        {
            "problem": "What is 2+2?",
            "context": None,
            "description": "Simple problem (System 1)"
        },
        {
            "problem": "Design a distributed consensus algorithm that handles Byzantine failures while maintaining linearizability and partition tolerance",
            "context": None,
            "description": "Complex problem (System 2)"
        },
        {
            "problem": "Team productivity dropping, people avoiding meetings, tension in code reviews",
            "context": None,
            "description": "Team conflict pattern"
        }
    ]

    print(f"\n📋 Testing {len(test_cases)} problems with adaptive thinking...\n")

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'=' * 70}")
        print(f"Test {i}/{len(test_cases)}: {test_case['description']}")
        print(f"{'=' * 70}")
        print(f"Problem: {test_case['problem']}")

        solution = await runtime.solve_with_adaptive_thinking(
            test_case["problem"],
            test_case["context"]
        )

        print(f"\n📊 Results:")
        print(f"   Thinking mode: {solution.thinking_mode.value}")
        print(f"   Confidence: {solution.confidence:.2f}")
        print(f"   Reasoning time: {solution.reasoning_time:.1f}ms")
        print(f"   Gut feeling: {solution.gut_feeling.direction.value} (strength={solution.gut_feeling.strength:.2f})")
        if solution.pattern_used:
            print(f"   Pattern: {solution.pattern_used.description}")
        print(f"   Heuristics: {len(solution.heuristics_applied)}")

    # Get overall metrics
    print(f"\n{'=' * 70}")
    print("📈 INTUITION METRICS")
    print(f"{'=' * 70}")

    metrics = runtime.get_intuition_metrics()
    print(f"Intuition Score: {metrics['intuition_score']:.1f}%")
    print(f"Patterns recognized: {metrics['patterns_recognized']}")
    print(f"Heuristics available: {metrics['heuristics_available']}")
    print(f"Gut feelings generated: {metrics['gut_feelings_generated']}")
    print(f"Pattern usage rate: {metrics['pattern_usage_rate']*100:.1f}%")
    print(f"Average confidence: {metrics['average_confidence']:.2f}")
    print(f"System 1 usage rate: {metrics['system1_usage_rate']*100:.1f}%")
    print(f"Average reasoning time: {metrics['average_reasoning_time_ms']:.1f}ms")
    print(f"Speed score: {metrics['speed_score']:.2f}")

    # Calculate dimension impact
    print(f"\n{'=' * 70}")
    print("📈 ESTIMATED AGI IMPACT")
    print(f"{'=' * 70}")

    intuition_score = metrics['intuition_score'] / 100.0
    agi_impact = (intuition_score - 0.20) * 0.08 * 100  # Started at 20%, 8% weight

    print(f"Intuition dimension: 20% → {intuition_score*100:.1f}% (+{(intuition_score-0.20)*100:.1f} points)")
    print(f"Overall AGI: 92.0% → {92.0 + agi_impact:.1f}% (+{agi_impact:.1f} points)")
    print(f"Status: {'✅ Phase 5.2 COMPLETE' if intuition_score >= 0.70 else '⚠️ Below target (70%)'}")

    print(f"\n✅ Intuition Runtime demonstration complete!")


if __name__ == "__main__":
    asyncio.run(main())
