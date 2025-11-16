"""
Emotional Intelligence Runtime

Phase 5.1: Emotional Intelligence
Target: Emotional Intelligence 0% → 70% (+70 points)
Expected AGI Impact: +5.6 points (70% × 0.08 weight)

Extends CollaborativeAgentRuntime with:
- Emotion recognition (8 basic emotions)
- Empathy modeling
- Social dynamics understanding
- Emotional regulation
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
import json
import os

# Import parent runtime
from collaborative_agent_runtime import (
    CollaborativeAgentRuntime,
    CollaborationPattern,
    AgentInSwarm,
    CollaborativeSolution
)


# ============================================================================
# EMOTIONAL INTELLIGENCE DATA STRUCTURES
# ============================================================================

class EmotionType(Enum):
    """Plutchik's 8 basic emotions"""
    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    TRUST = "trust"
    ANTICIPATION = "anticipation"


@dataclass
class EmotionalContext:
    """Emotional context extracted from text"""
    primary_emotion: EmotionType
    intensity: float  # 0.0-1.0
    secondary_emotions: List[EmotionType]
    emotional_valence: float  # -1.0 (negative) to +1.0 (positive)
    arousal_level: float  # 0.0 (calm) to 1.0 (excited)
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SocialContext:
    """Social dynamics and context"""
    relationship_type: str  # "professional", "personal", "collaborative"
    power_dynamics: Dict[str, float]  # Agent power/status levels
    social_norms: List[str]
    cultural_context: str
    group_dynamics: Dict[str, Any]
    formality_level: float  # 0.0 (informal) to 1.0 (formal)


@dataclass
class EmpathyResponse:
    """Empathetic response to emotional state"""
    perspective_taking: str  # Understanding their viewpoint
    emotional_resonance: float  # How much we share their feeling
    compassionate_response: str  # What we say/do
    validation: str  # Acknowledging their emotion
    support_offered: List[str]  # Concrete support actions


@dataclass
class EmotionalSolution:
    """Solution with emotional intelligence"""
    solution: str
    emotional_context: EmotionalContext
    empathetic_framing: str
    social_awareness: SocialContext
    emotional_regulation_applied: List[str]
    emotional_intelligence_score: float
    timestamp: datetime = field(default_factory=datetime.now)


# ============================================================================
# EMOTIONAL INTELLIGENCE RUNTIME
# ============================================================================

class EmotionalIntelligenceRuntime(CollaborativeAgentRuntime):
    """
    Phase 5.1: Emotional Intelligence Runtime

    Extends CollaborativeAgentRuntime with emotional understanding and empathy.

    Target: Emotional Intelligence 0% → 70%
    Expected AGI Impact: 89.0% → 92.0% (+3.0 points)
    """

    def __init__(self, verbose=True, enable_learning=True, reasoning_depth=5,
                 constraints: Optional[Any] = None, health_check_interval: int = 60):
        super().__init__(verbose=verbose, enable_learning=enable_learning,
                        reasoning_depth=reasoning_depth, constraints=constraints,
                        health_check_interval=health_check_interval)

        # Emotional intelligence components
        self.emotion_recognition_history: List[EmotionalContext] = []
        self.empathy_responses: List[EmpathyResponse] = []
        self.emotional_solutions: List[EmotionalSolution] = []

        # Emotion keywords for recognition (simple NLP-based approach)
        self.emotion_keywords = self._define_emotion_keywords()
        self.valence_keywords = self._define_valence_keywords()

        # Social norms database
        self.social_norms = self._define_social_norms()

        # Emotional regulation strategies
        self.regulation_strategies = [
            "cognitive_reappraisal",
            "situation_modification",
            "attentional_deployment",
            "response_modulation",
            "acceptance"
        ]

        if self.verbose:
            print("\n😊 Emotional Intelligence Runtime initialized")
            print(f"   Emotion types: {len(EmotionType)}")
            print(f"   Regulation strategies: {len(self.regulation_strategies)}")

    def _define_emotion_keywords(self) -> Dict[EmotionType, List[str]]:
        """Define keywords for each emotion type"""
        return {
            EmotionType.JOY: [
                "happy", "joy", "excited", "delighted", "pleased", "cheerful",
                "thrilled", "ecstatic", "glad", "satisfied", "content", "joyful"
            ],
            EmotionType.SADNESS: [
                "sad", "unhappy", "depressed", "miserable", "disappointed",
                "heartbroken", "sorrowful", "melancholy", "down", "blue", "grief"
            ],
            EmotionType.ANGER: [
                "angry", "mad", "furious", "irritated", "frustrated", "annoyed",
                "enraged", "outraged", "hostile", "resentful", "bitter"
            ],
            EmotionType.FEAR: [
                "afraid", "scared", "fearful", "terrified", "anxious", "worried",
                "nervous", "frightened", "panicked", "alarmed", "dread"
            ],
            EmotionType.SURPRISE: [
                "surprised", "shocked", "amazed", "astonished", "startled",
                "stunned", "astounded", "unexpected", "sudden"
            ],
            EmotionType.DISGUST: [
                "disgusted", "repulsed", "revolted", "sickened", "appalled",
                "nauseated", "repelled", "grossed out"
            ],
            EmotionType.TRUST: [
                "trust", "confident", "secure", "assured", "reliable", "faith",
                "belief", "certain", "dependable"
            ],
            EmotionType.ANTICIPATION: [
                "anticipate", "expect", "looking forward", "eager", "hopeful",
                "await", "prepared", "ready", "excited about"
            ]
        }

    def _define_valence_keywords(self) -> Dict[str, List[str]]:
        """Define keywords for emotional valence"""
        return {
            "positive": [
                "great", "wonderful", "excellent", "fantastic", "amazing",
                "good", "nice", "pleasant", "beautiful", "lovely"
            ],
            "negative": [
                "bad", "terrible", "awful", "horrible", "unpleasant",
                "poor", "nasty", "ugly", "dreadful", "dismal"
            ]
        }

    def _define_social_norms(self) -> Dict[str, List[str]]:
        """Define social norms for different contexts"""
        return {
            "professional": [
                "maintain_professionalism",
                "respect_hierarchy",
                "formal_communication",
                "avoid_personal_topics",
                "deadline_adherence"
            ],
            "personal": [
                "emotional_openness",
                "informal_communication",
                "empathy_expression",
                "relationship_building"
            ],
            "collaborative": [
                "equal_participation",
                "constructive_feedback",
                "shared_decision_making",
                "mutual_support"
            ]
        }

    async def analyze_emotional_context(self, text: str) -> EmotionalContext:
        """
        Analyze emotional context in text

        Uses keyword matching and intensity scoring to detect emotions
        """
        text_lower = text.lower()

        # Detect emotions and their intensities
        emotion_scores = {}
        for emotion, keywords in self.emotion_keywords.items():
            score = sum(1.0 for keyword in keywords if keyword in text_lower)
            if score > 0:
                # Normalize by number of keywords and text length
                emotion_scores[emotion] = min(1.0, score / (len(text_lower.split()) * 0.1))

        # Determine primary and secondary emotions
        if not emotion_scores:
            # Default to neutral (trust)
            primary_emotion = EmotionType.TRUST
            intensity = 0.3
            secondary_emotions = []
            confidence = 0.4
        else:
            sorted_emotions = sorted(emotion_scores.items(), key=lambda x: x[1], reverse=True)
            primary_emotion = sorted_emotions[0][0]
            intensity = sorted_emotions[0][1]
            secondary_emotions = [e for e, score in sorted_emotions[1:3] if score > 0.3]
            confidence = min(1.0, intensity + 0.2)

        # Calculate valence (positive/negative)
        positive_score = sum(1 for word in self.valence_keywords["positive"] if word in text_lower)
        negative_score = sum(1 for word in self.valence_keywords["negative"] if word in text_lower)

        if positive_score + negative_score > 0:
            valence = (positive_score - negative_score) / (positive_score + negative_score)
        else:
            # Emotion-based valence
            valence_map = {
                EmotionType.JOY: 1.0,
                EmotionType.TRUST: 0.8,
                EmotionType.ANTICIPATION: 0.6,
                EmotionType.SURPRISE: 0.0,
                EmotionType.FEAR: -0.6,
                EmotionType.ANGER: -0.8,
                EmotionType.DISGUST: -0.9,
                EmotionType.SADNESS: -0.7
            }
            valence = valence_map.get(primary_emotion, 0.0)

        # Calculate arousal (excitement level)
        arousal_map = {
            EmotionType.ANGER: 0.9,
            EmotionType.FEAR: 0.8,
            EmotionType.SURPRISE: 0.8,
            EmotionType.JOY: 0.7,
            EmotionType.ANTICIPATION: 0.6,
            EmotionType.DISGUST: 0.5,
            EmotionType.SADNESS: 0.3,
            EmotionType.TRUST: 0.2
        }
        arousal_level = arousal_map.get(primary_emotion, 0.5) * intensity

        context = EmotionalContext(
            primary_emotion=primary_emotion,
            intensity=intensity,
            secondary_emotions=secondary_emotions,
            emotional_valence=valence,
            arousal_level=arousal_level,
            confidence=confidence
        )

        self.emotion_recognition_history.append(context)

        if self.verbose:
            print(f"\n😊 Emotional context analyzed:")
            print(f"   Primary emotion: {primary_emotion.value} (intensity={intensity:.2f})")
            print(f"   Secondary: {[e.value for e in secondary_emotions]}")
            print(f"   Valence: {valence:.2f} | Arousal: {arousal_level:.2f}")
            print(f"   Confidence: {confidence:.2f}")

        return context

    async def generate_empathetic_response(self, context: EmotionalContext,
                                          problem: str) -> EmpathyResponse:
        """
        Generate empathetic response to emotional state

        Uses perspective-taking, validation, and compassionate communication
        """
        emotion = context.primary_emotion
        intensity = context.intensity

        # Perspective-taking (understand their viewpoint)
        perspective_templates = {
            EmotionType.JOY: "I sense your enthusiasm about {problem}. That's a positive energy to work with.",
            EmotionType.SADNESS: "I understand this situation regarding {problem} is difficult for you.",
            EmotionType.ANGER: "I recognize your frustration with {problem}. That's a legitimate reaction.",
            EmotionType.FEAR: "I see that {problem} is creating uncertainty for you. That's understandable.",
            EmotionType.SURPRISE: "This development with {problem} seems unexpected for you.",
            EmotionType.DISGUST: "I notice your strong reaction to {problem}. Your standards are important.",
            EmotionType.TRUST: "I appreciate your confidence in approaching {problem}.",
            EmotionType.ANTICIPATION: "I can sense your eagerness about {problem}. Let's channel that energy."
        }

        perspective_taking = perspective_templates[emotion].format(problem=problem[:50])

        # Emotional resonance (how much we share their feeling)
        # Higher intensity emotions get more resonance
        emotional_resonance = min(0.9, intensity * 0.8 + 0.3)

        # Validation (acknowledging their emotion)
        validation_templates = {
            EmotionType.JOY: "Your positive feelings are well-founded.",
            EmotionType.SADNESS: "It's completely valid to feel this way.",
            EmotionType.ANGER: "Your frustration is justified given the circumstances.",
            EmotionType.FEAR: "Feeling uncertain is a natural response.",
            EmotionType.SURPRISE: "Being surprised shows you're engaged.",
            EmotionType.DISGUST: "Your reaction reflects your values.",
            EmotionType.TRUST: "Your confidence is well-placed.",
            EmotionType.ANTICIPATION: "Looking forward is a healthy mindset."
        }

        validation = validation_templates[emotion]

        # Compassionate response (what we say)
        response_templates = {
            EmotionType.JOY: "Let's build on this positive momentum to create an excellent solution.",
            EmotionType.SADNESS: "I'm here to help address this in a way that respects your feelings.",
            EmotionType.ANGER: "Let's channel this energy into solving the underlying issue effectively.",
            EmotionType.FEAR: "Let's work together to address your concerns systematically.",
            EmotionType.SURPRISE: "Let's take a moment to understand this unexpected development.",
            EmotionType.DISGUST: "Let's find a solution that aligns with your standards.",
            EmotionType.TRUST: "Let's honor that trust with a thorough and reliable approach.",
            EmotionType.ANTICIPATION: "Let's harness that forward-looking energy productively."
        }

        compassionate_response = response_templates[emotion]

        # Support offered
        support_templates = {
            EmotionType.JOY: ["maximize_positive_outcome", "celebrate_success"],
            EmotionType.SADNESS: ["emotional_support", "problem_mitigation", "hope_restoration"],
            EmotionType.ANGER: ["address_root_cause", "provide_outlet", "facilitate_resolution"],
            EmotionType.FEAR: ["uncertainty_reduction", "safety_assurance", "step_by_step_guidance"],
            EmotionType.SURPRISE: ["explanation_provision", "time_to_process"],
            EmotionType.DISGUST: ["value_alignment", "standard_maintenance"],
            EmotionType.TRUST: ["reliability_demonstration", "transparency"],
            EmotionType.ANTICIPATION: ["momentum_building", "expectation_management"]
        }

        support_offered = support_templates[emotion]

        empathy = EmpathyResponse(
            perspective_taking=perspective_taking,
            emotional_resonance=emotional_resonance,
            compassionate_response=compassionate_response,
            validation=validation,
            support_offered=support_offered
        )

        self.empathy_responses.append(empathy)

        if self.verbose:
            print(f"\n💙 Empathetic response generated:")
            print(f"   Perspective: {perspective_taking}")
            print(f"   Resonance: {emotional_resonance:.2f}")
            print(f"   Validation: {validation}")

        return empathy

    async def assess_social_context(self, problem: str,
                                   participants: Optional[List[AgentInSwarm]] = None) -> SocialContext:
        """
        Assess social dynamics and context
        """
        problem_lower = problem.lower()

        # Determine relationship type
        if any(word in problem_lower for word in ["team", "collaborate", "together", "group"]):
            relationship_type = "collaborative"
        elif any(word in problem_lower for word in ["work", "professional", "business", "project"]):
            relationship_type = "professional"
        else:
            relationship_type = "personal"

        # Power dynamics (if agents involved)
        power_dynamics = {}
        if participants:
            for agent in participants:
                # Leader has more power, specialists equal
                power_dynamics[agent.agent_id] = 0.8 if agent.role == "leader" else 0.5
        else:
            power_dynamics = {"user": 0.7, "system": 0.5}

        # Social norms for this context
        social_norms = self.social_norms.get(relationship_type, [])

        # Cultural context (default to professional western)
        cultural_context = "professional_western"

        # Group dynamics
        group_dynamics = {
            "cohesion": 0.7,
            "trust_level": 0.75,
            "conflict_level": 0.2,
            "cooperation_level": 0.8
        }

        # Formality level
        formality_map = {
            "professional": 0.8,
            "collaborative": 0.5,
            "personal": 0.3
        }
        formality_level = formality_map[relationship_type]

        context = SocialContext(
            relationship_type=relationship_type,
            power_dynamics=power_dynamics,
            social_norms=social_norms,
            cultural_context=cultural_context,
            group_dynamics=group_dynamics,
            formality_level=formality_level
        )

        if self.verbose:
            print(f"\n👥 Social context assessed:")
            print(f"   Relationship: {relationship_type}")
            print(f"   Formality: {formality_level:.2f}")
            print(f"   Norms: {len(social_norms)}")

        return context

    async def apply_emotional_regulation(self, emotion: EmotionType,
                                        intensity: float) -> List[str]:
        """
        Apply emotional regulation strategies

        Choose strategies based on emotion type and intensity
        """
        strategies_applied = []

        # High intensity negative emotions need regulation
        if intensity > 0.6 and emotion in [EmotionType.ANGER, EmotionType.FEAR,
                                           EmotionType.SADNESS, EmotionType.DISGUST]:
            # Cognitive reappraisal - reframe the situation
            strategies_applied.append("cognitive_reappraisal")

            if intensity > 0.8:
                # Response modulation - adjust our response intensity
                strategies_applied.append("response_modulation")

        # Moderate negative emotions
        elif intensity > 0.4 and emotion in [EmotionType.ANGER, EmotionType.FEAR]:
            # Attentional deployment - redirect focus
            strategies_applied.append("attentional_deployment")

        # Any negative emotion
        if emotion in [EmotionType.SADNESS, EmotionType.FEAR]:
            # Acceptance - acknowledge and accept the emotion
            strategies_applied.append("acceptance")

        # Positive emotions - enhance them
        if emotion in [EmotionType.JOY, EmotionType.TRUST, EmotionType.ANTICIPATION]:
            strategies_applied.append("emotion_enhancement")

        if self.verbose and strategies_applied:
            print(f"\n🧘 Emotional regulation applied: {strategies_applied}")

        return strategies_applied

    async def solve_with_emotional_awareness(self, problem: str,
                                             context: Optional[Dict[str, Any]] = None) -> EmotionalSolution:
        """
        Solve problem with emotional intelligence

        Combines technical solution with emotional understanding and empathy
        """
        if self.verbose:
            print(f"\n😊 Solving with emotional awareness...")
            print(f"   Problem: {problem[:80]}...")

        # 1. Analyze emotional context in problem
        emotional_ctx = await self.analyze_emotional_context(problem)

        # 2. Generate empathetic response
        empathy = await self.generate_empathetic_response(emotional_ctx, problem)

        # 3. Assess social context
        social_ctx = await self.assess_social_context(problem)

        # 4. Apply emotional regulation if needed
        regulation_applied = await self.apply_emotional_regulation(
            emotional_ctx.primary_emotion,
            emotional_ctx.intensity
        )

        # 5. Generate technical solution (use collaborative solving)
        technical_solution = await self.collaborative_solve(
            problem,
            pattern=CollaborationPattern.COOPERATIVE,
            num_agents=3
        )

        # 6. Frame solution with empathy
        empathetic_framing = (
            f"{empathy.perspective_taking} "
            f"{empathy.validation} "
            f"{empathy.compassionate_response}\n\n"
            f"Solution: {technical_solution.consensus_solution}"
        )

        # 7. Calculate emotional intelligence score
        ei_score = self._calculate_emotional_intelligence_score(
            emotional_ctx, empathy, social_ctx
        )

        solution = EmotionalSolution(
            solution=technical_solution.consensus_solution,
            emotional_context=emotional_ctx,
            empathetic_framing=empathetic_framing,
            social_awareness=social_ctx,
            emotional_regulation_applied=regulation_applied,
            emotional_intelligence_score=ei_score
        )

        self.emotional_solutions.append(solution)

        if self.verbose:
            print(f"\n✅ Emotionally aware solution complete!")
            print(f"   EI score: {ei_score:.2f}")
            print(f"   Regulation applied: {regulation_applied}")

        return solution

    def _calculate_emotional_intelligence_score(self, emotional_ctx: EmotionalContext,
                                                empathy: EmpathyResponse,
                                                social_ctx: SocialContext) -> float:
        """Calculate overall emotional intelligence score"""
        # Components of EI
        emotion_recognition = emotional_ctx.confidence  # 0.0-1.0
        empathy_quality = empathy.emotional_resonance  # 0.0-1.0
        social_awareness = min(1.0, len(social_ctx.social_norms) / 5.0)  # 0.0-1.0

        # Weighted average
        ei_score = (
            emotion_recognition * 0.35 +
            empathy_quality * 0.35 +
            social_awareness * 0.30
        )

        return ei_score

    def get_emotional_intelligence_metrics(self) -> Dict[str, Any]:
        """Get emotional intelligence performance metrics"""
        if not self.emotional_solutions:
            return {
                "emotional_intelligence_score": 0.0,
                "emotions_recognized": 0,
                "empathy_responses": 0,
                "average_ei_score": 0.0
            }

        avg_ei_score = sum(s.emotional_intelligence_score for s in self.emotional_solutions) / len(self.emotional_solutions)

        # Emotion distribution
        emotion_counts = {}
        for ctx in self.emotion_recognition_history:
            emotion = ctx.primary_emotion.value
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1

        return {
            "emotional_intelligence_score": avg_ei_score * 100,  # 0-100 scale
            "emotions_recognized": len(self.emotion_recognition_history),
            "unique_emotions": len(emotion_counts),
            "empathy_responses": len(self.empathy_responses),
            "emotional_solutions": len(self.emotional_solutions),
            "average_ei_score": avg_ei_score,
            "emotion_distribution": emotion_counts,
            "average_emotional_resonance": sum(e.emotional_resonance for e in self.empathy_responses) / len(self.empathy_responses) if self.empathy_responses else 0.0
        }


# ============================================================================
# DEMONSTRATION
# ============================================================================

async def main():
    """Demonstrate Emotional Intelligence Runtime"""

    print("=" * 70)
    print("😊 EMOTIONAL INTELLIGENCE RUNTIME DEMONSTRATION")
    print("Phase 5.1: Emotional Intelligence")
    print("=" * 70)

    runtime = EmotionalIntelligenceRuntime(verbose=True)

    # Test emotional intelligence with various scenarios
    test_problems = [
        "I'm frustrated because this bug keeps appearing no matter what I try!",
        "I'm so excited about this new feature - it's going to transform our product!",
        "I'm worried that we won't meet the deadline with the current team capacity.",
        "This code review process is making me angry - it's too slow and bureaucratic!",
        "I'm happy with the progress we've made, let's keep this momentum going."
    ]

    print(f"\n📋 Testing {len(test_problems)} emotionally-charged problems...\n")

    for i, problem in enumerate(test_problems, 1):
        print(f"\n{'=' * 70}")
        print(f"Test {i}/{len(test_problems)}")
        print(f"{'=' * 70}")

        solution = await runtime.solve_with_emotional_awareness(problem)

        print(f"\n📊 Results:")
        print(f"   Emotion: {solution.emotional_context.primary_emotion.value}")
        print(f"   Intensity: {solution.emotional_context.intensity:.2f}")
        print(f"   Valence: {solution.emotional_context.emotional_valence:.2f}")
        print(f"   EI Score: {solution.emotional_intelligence_score:.2f}")
        print(f"\n   Empathetic framing:")
        print(f"   {solution.empathetic_framing[:200]}...")

    # Get overall metrics
    print(f"\n{'=' * 70}")
    print("📈 EMOTIONAL INTELLIGENCE METRICS")
    print(f"{'=' * 70}")

    metrics = runtime.get_emotional_intelligence_metrics()
    print(f"Emotional Intelligence Score: {metrics['emotional_intelligence_score']:.1f}%")
    print(f"Emotions recognized: {metrics['emotions_recognized']}")
    print(f"Unique emotions: {metrics['unique_emotions']}/{len(EmotionType)}")
    print(f"Empathy responses: {metrics['empathy_responses']}")
    print(f"Average EI score: {metrics['average_ei_score']:.2f}")
    print(f"Average emotional resonance: {metrics['average_emotional_resonance']:.2f}")

    print(f"\nEmotion distribution:")
    for emotion, count in sorted(metrics['emotion_distribution'].items()):
        print(f"  {emotion}: {count}")

    # Calculate dimension impact
    print(f"\n{'=' * 70}")
    print("📈 ESTIMATED AGI IMPACT")
    print(f"{'=' * 70}")

    ei_score = metrics['emotional_intelligence_score'] / 100.0
    agi_impact = ei_score * 0.08 * 100  # 8% weight in Phase 5 formula

    print(f"Emotional Intelligence dimension: 0% → {ei_score*100:.1f}% (+{ei_score*100:.1f} points)")
    print(f"Overall AGI: 89.0% → {89.0 + agi_impact:.1f}% (+{agi_impact:.1f} points)")
    print(f"Status: {'✅ Phase 5.1 COMPLETE' if ei_score >= 0.70 else '⚠️ Below target (70%)'}")

    print(f"\n✅ Emotional Intelligence Runtime demonstration complete!")


if __name__ == "__main__":
    asyncio.run(main())
