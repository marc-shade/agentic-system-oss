#!/usr/bin/env python3
"""
Reasoning Grader
================

Evaluates reasoning quality across multiple dimensions:
- Logical Coherence: Steps follow logically
- Completeness: All aspects addressed
- Accuracy: Factual correctness
- Clarity: Clear explanations
- Evidence: Claims supported by evidence
"""

import re
import json
from typing import Dict, Any, Tuple, List, Optional
from dataclasses import dataclass


@dataclass
class ReasoningStep:
    """A single step in a reasoning chain."""
    step_number: int
    content: str
    reasoning_type: str  # deductive, inductive, abductive, analogical
    confidence: float


def extract_reasoning_steps(response: str) -> List[ReasoningStep]:
    """Extract structured reasoning steps from a response."""
    steps = []

    # Look for numbered steps
    step_pattern = r'(?:Step\s*)?(\d+)[.):]\s*(.+?)(?=(?:Step\s*)?\d+[.)]|$)'
    matches = re.findall(step_pattern, response, re.DOTALL | re.IGNORECASE)

    for i, (num, content) in enumerate(matches):
        # Classify reasoning type
        content_lower = content.lower()
        if any(w in content_lower for w in ['therefore', 'thus', 'hence', 'must be']):
            reasoning_type = 'deductive'
        elif any(w in content_lower for w in ['likely', 'probably', 'suggests', 'pattern']):
            reasoning_type = 'inductive'
        elif any(w in content_lower for w in ['best explanation', 'hypothesis', 'assume']):
            reasoning_type = 'abductive'
        elif any(w in content_lower for w in ['similar to', 'like', 'analogous']):
            reasoning_type = 'analogical'
        else:
            reasoning_type = 'general'

        steps.append(ReasoningStep(
            step_number=int(num),
            content=content.strip(),
            reasoning_type=reasoning_type,
            confidence=0.8  # Default confidence
        ))

    # If no numbered steps, split by paragraphs
    if not steps:
        paragraphs = [p.strip() for p in response.split('\n\n') if p.strip()]
        for i, para in enumerate(paragraphs):
            steps.append(ReasoningStep(
                step_number=i + 1,
                content=para,
                reasoning_type='general',
                confidence=0.7
            ))

    return steps


def grade_logical_coherence(steps: List[ReasoningStep]) -> Tuple[float, str]:
    """Check if reasoning steps follow logically."""
    if not steps:
        return 0.0, "No reasoning steps found"

    if len(steps) == 1:
        return 0.7, "Single step reasoning"

    score = 1.0
    issues = []

    # Check for logical connectors between steps
    connectors = ['therefore', 'thus', 'hence', 'because', 'since', 'so', 'consequently', 'as a result']
    connector_count = sum(1 for step in steps if any(c in step.content.lower() for c in connectors))

    if connector_count < len(steps) * 0.3:
        score -= 0.2
        issues.append("Few logical connectors")

    # Check for contradictions (simple heuristic)
    for i, step in enumerate(steps):
        for j, other in enumerate(steps[i+1:], i+1):
            if 'not' in step.content.lower() and 'not' not in other.content.lower():
                # Check if they're talking about the same thing
                words1 = set(step.content.lower().split())
                words2 = set(other.content.lower().split())
                overlap = len(words1 & words2) / max(len(words1), len(words2))
                if overlap > 0.5:
                    score -= 0.3
                    issues.append(f"Potential contradiction between steps {i+1} and {j+1}")
                    break

    # Check for jumps in logic (steps that don't reference previous context)
    for i, step in enumerate(steps[1:], 1):
        prev_words = set(steps[i-1].content.lower().split())
        curr_words = set(step.content.lower().split())
        # Remove common words
        common = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                  'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                  'should', 'may', 'might', 'must', 'and', 'or', 'but', 'if', 'then',
                  'that', 'this', 'it', 'to', 'of', 'in', 'for', 'on', 'with'}
        prev_words -= common
        curr_words -= common

        overlap = len(prev_words & curr_words)
        if overlap == 0 and len(prev_words) > 3:
            score -= 0.1
            issues.append(f"Step {i+1} may be disconnected")

    msg = "; ".join(issues) if issues else "Good logical flow"
    return max(0.0, score), msg


def grade_completeness(response: str, expected_aspects: List[str] = None) -> Tuple[float, str]:
    """Check if response addresses all required aspects."""
    if not expected_aspects:
        # Generic completeness check
        indicators = {
            'introduction': ['first', 'begin', 'start', 'initial'],
            'analysis': ['because', 'since', 'reason', 'cause'],
            'conclusion': ['therefore', 'thus', 'conclude', 'final', 'result']
        }

        response_lower = response.lower()
        found = []
        for aspect, keywords in indicators.items():
            if any(kw in response_lower for kw in keywords):
                found.append(aspect)

        score = len(found) / len(indicators)
        missing = [a for a in indicators if a not in found]
        msg = f"Missing: {missing}" if missing else "All aspects covered"
        return score, msg

    # Check for specific expected aspects
    response_lower = response.lower()
    found = [aspect for aspect in expected_aspects if aspect.lower() in response_lower]
    score = len(found) / len(expected_aspects)
    missing = [a for a in expected_aspects if a not in found]
    msg = f"Missing: {missing}" if missing else "All expected aspects covered"
    return score, msg


def grade_accuracy(response: str, ground_truth: Dict[str, Any] = None) -> Tuple[float, str]:
    """Check factual accuracy against ground truth if provided."""
    if not ground_truth:
        return 0.8, "No ground truth provided for accuracy check"

    score = 1.0
    issues = []
    response_lower = response.lower()

    for fact, expected in ground_truth.items():
        if isinstance(expected, bool):
            # Boolean fact check
            negations = ['not', 'no', "n't", 'never', 'false']
            has_negation = any(neg in response_lower for neg in negations)
            fact_mentioned = fact.lower() in response_lower

            if fact_mentioned:
                if expected and has_negation:
                    score -= 0.2
                    issues.append(f"Incorrectly negated: {fact}")
                elif not expected and not has_negation:
                    score -= 0.2
                    issues.append(f"Should be negated: {fact}")
        elif isinstance(expected, (int, float)):
            # Numeric fact check
            numbers = re.findall(r'\b\d+\.?\d*\b', response)
            if str(expected) not in numbers and str(int(expected)) not in numbers:
                score -= 0.15
                issues.append(f"Missing or incorrect number for {fact}")
        elif isinstance(expected, str):
            # String fact check
            if expected.lower() not in response_lower:
                score -= 0.15
                issues.append(f"Missing expected: {expected}")

    msg = "; ".join(issues) if issues else "Facts verified"
    return max(0.0, score), msg


def grade_clarity(response: str) -> Tuple[float, str]:
    """Evaluate clarity and readability of explanation."""
    score = 1.0
    issues = []

    words = response.split()
    sentences = re.split(r'[.!?]+', response)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return 0.0, "No sentences found"

    # Average sentence length (target: 15-25 words)
    avg_sentence_len = len(words) / len(sentences)
    if avg_sentence_len > 35:
        score -= 0.2
        issues.append(f"Sentences too long (avg {avg_sentence_len:.0f} words)")
    elif avg_sentence_len < 8:
        score -= 0.1
        issues.append(f"Sentences too short (avg {avg_sentence_len:.0f} words)")

    # Check for jargon density
    jargon_indicators = ['aforementioned', 'heretofore', 'whereby', 'thereof', 'therein']
    jargon_count = sum(response.lower().count(j) for j in jargon_indicators)
    if jargon_count > 3:
        score -= 0.15
        issues.append(f"High jargon density ({jargon_count} instances)")

    # Check for structure (paragraphs, lists)
    has_structure = '\n\n' in response or re.search(r'^\s*[-*\d]+[.)]', response, re.MULTILINE)
    if len(words) > 100 and not has_structure:
        score -= 0.1
        issues.append("Long response lacks structure")

    # Check for hedging (too many uncertainty markers)
    hedges = ['maybe', 'perhaps', 'possibly', 'might', 'could be', 'uncertain']
    hedge_count = sum(response.lower().count(h) for h in hedges)
    if hedge_count > len(sentences) * 0.3:
        score -= 0.1
        issues.append("Excessive hedging")

    msg = "; ".join(issues) if issues else "Clear explanation"
    return max(0.0, score), msg


def grade_evidence(response: str, requires_evidence: bool = True) -> Tuple[float, str]:
    """Check if claims are supported by evidence."""
    if not requires_evidence:
        return 1.0, "Evidence not required"

    score = 1.0
    issues = []

    # Evidence indicators
    evidence_markers = [
        'because', 'since', 'as shown', 'for example', 'for instance',
        'evidence', 'study', 'research', 'data', 'according to',
        'demonstrated', 'proven', 'indicates', 'suggests'
    ]

    response_lower = response.lower()
    evidence_count = sum(1 for marker in evidence_markers if marker in response_lower)

    # Count claims (sentences with strong assertions)
    claim_indicators = ['is', 'are', 'will', 'must', 'always', 'never', 'definitely']
    sentences = re.split(r'[.!?]+', response)
    claim_count = sum(1 for s in sentences if any(ci in s.lower() for ci in claim_indicators))

    if claim_count > 0:
        evidence_ratio = evidence_count / claim_count
        if evidence_ratio < 0.3:
            score -= 0.3
            issues.append("Claims lack supporting evidence")
        elif evidence_ratio < 0.5:
            score -= 0.15
            issues.append("Some claims unsupported")

    # Check for citations or references
    has_citations = bool(re.search(r'\[\d+\]|\(\d{4}\)|et al\.', response))
    if has_citations:
        score = min(1.0, score + 0.1)

    msg = "; ".join(issues) if issues else "Claims well-supported"
    return max(0.0, score), msg


def grade_reasoning(
    response: str,
    expected_aspects: List[str] = None,
    ground_truth: Dict[str, Any] = None,
    requires_evidence: bool = True,
    weights: Dict[str, float] = None
) -> Dict[str, Any]:
    """
    Comprehensive reasoning evaluation.

    Args:
        response: The reasoning response to evaluate
        expected_aspects: List of aspects that should be addressed
        ground_truth: Dict of facts to verify
        requires_evidence: Whether claims need evidence
        weights: Custom weights for dimensions

    Returns:
        Dict with overall score and dimension breakdowns
    """
    default_weights = {
        'coherence': 0.30,
        'completeness': 0.20,
        'accuracy': 0.20,
        'clarity': 0.15,
        'evidence': 0.15
    }
    weights = weights or default_weights

    # Extract reasoning steps
    steps = extract_reasoning_steps(response)

    results = {}

    # Run all graders
    coherence_score, coherence_msg = grade_logical_coherence(steps)
    results['coherence'] = {'score': coherence_score, 'message': coherence_msg}

    complete_score, complete_msg = grade_completeness(response, expected_aspects)
    results['completeness'] = {'score': complete_score, 'message': complete_msg}

    accuracy_score, accuracy_msg = grade_accuracy(response, ground_truth)
    results['accuracy'] = {'score': accuracy_score, 'message': accuracy_msg}

    clarity_score, clarity_msg = grade_clarity(response)
    results['clarity'] = {'score': clarity_score, 'message': clarity_msg}

    evidence_score, evidence_msg = grade_evidence(response, requires_evidence)
    results['evidence'] = {'score': evidence_score, 'message': evidence_msg}

    # Calculate weighted overall score
    overall = sum(results[dim]['score'] * weights.get(dim, 0) for dim in results)

    return {
        'overall_score': round(overall, 3),
        'passed': overall >= 0.7,
        'reasoning_steps': len(steps),
        'dimensions': results,
        'weights': weights
    }


if __name__ == "__main__":
    # Test the grader
    test_response = '''
    Step 1: First, let's analyze the problem. We need to determine why the system is running slowly.

    Step 2: Based on the metrics, CPU usage is at 95%. This indicates a computational bottleneck.

    Step 3: Looking at the process list, we can see that the database query process is consuming most resources.

    Step 4: Therefore, we should optimize the database queries. For example, we could add indexes to frequently queried columns.

    Step 5: In conclusion, the root cause is inefficient database queries, and the solution is to add appropriate indexes.
    '''

    result = grade_reasoning(test_response)
    print(f"Overall Score: {result['overall_score']}")
    print(f"Passed: {result['passed']}")
    print(f"Reasoning Steps: {result['reasoning_steps']}")
    for dim, data in result['dimensions'].items():
        print(f"  {dim}: {data['score']:.2f} - {data['message']}")
