"""
Deliberation Patterns
=====================

9 distinct multi-LLM deliberation patterns for different use cases:

1. DELIBERATION - Standard 3-stage council process
2. DEBATE - Adversarial debate between models
3. DEVILS_ADVOCATE - One model challenges others
4. SOCRATIC - Question-based exploration
5. RED_TEAM - Security/flaw focused analysis
6. TREE_OF_THOUGHT - Branching exploration of solutions
7. SELF_CONSISTENCY - Multiple attempts, majority vote
8. ROUND_ROBIN - Sequential refinement
9. EXPERT_PANEL - Domain-specific expertise
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, List, Any, Optional

from .cli_providers import query_cli_provider, query_providers_parallel
from .config import CLI_COUNCIL_MODELS, CLI_CHAIRMAN_MODEL

logger = logging.getLogger(__name__)


@dataclass
class Pattern:
    """Definition of a deliberation pattern."""
    name: str
    description: str
    stages: List[str]
    recommended_for: List[str]


PATTERNS: Dict[str, Pattern] = {
    "deliberation": Pattern(
        name="Standard Deliberation",
        description="3-stage process: respond, rank, synthesize",
        stages=["collect_responses", "peer_ranking", "synthesis"],
        recommended_for=["general questions", "balanced analysis", "consensus building"]
    ),
    "debate": Pattern(
        name="Adversarial Debate",
        description="Models argue different positions, chairman judges",
        stages=["assign_positions", "opening_arguments", "rebuttals", "judgment"],
        recommended_for=["controversial topics", "exploring tradeoffs", "decision making"]
    ),
    "devils_advocate": Pattern(
        name="Devil's Advocate",
        description="One model challenges the consensus of others",
        stages=["initial_consensus", "challenge", "defense", "resolution"],
        recommended_for=["testing assumptions", "finding flaws", "stress testing ideas"]
    ),
    "socratic": Pattern(
        name="Socratic Dialogue",
        description="Progressive questioning to deepen understanding",
        stages=["initial_response", "questioning", "refinement", "synthesis"],
        recommended_for=["complex topics", "educational content", "deep exploration"]
    ),
    "red_team": Pattern(
        name="Red Team Analysis",
        description="Focused on finding vulnerabilities and issues",
        stages=["proposal", "attack", "defense", "recommendations"],
        recommended_for=["security analysis", "risk assessment", "code review"]
    ),
    "tree_of_thought": Pattern(
        name="Tree of Thought",
        description="Explore multiple solution branches in parallel",
        stages=["branch_generation", "evaluation", "pruning", "selection"],
        recommended_for=["problem solving", "creative tasks", "optimization"]
    ),
    "self_consistency": Pattern(
        name="Self-Consistency",
        description="Multiple independent attempts, aggregate results",
        stages=["parallel_attempts", "consistency_check", "majority_vote"],
        recommended_for=["factual questions", "calculations", "verification"]
    ),
    "round_robin": Pattern(
        name="Round Robin",
        description="Sequential refinement by each model",
        stages=["initial", "refinement_rounds", "final"],
        recommended_for=["iterative improvement", "collaborative writing", "code refinement"]
    ),
    "expert_panel": Pattern(
        name="Expert Panel",
        description="Models take domain-specific expert roles",
        stages=["role_assignment", "expert_opinions", "integration"],
        recommended_for=["multi-disciplinary topics", "comprehensive analysis", "technical decisions"]
    ),
}


def list_patterns() -> List[Dict[str, Any]]:
    """Return metadata for all available patterns."""
    return [
        {
            "id": pattern_id,
            "name": pattern.name,
            "description": pattern.description,
            "stages": pattern.stages,
            "recommended_for": pattern.recommended_for,
        }
        for pattern_id, pattern in PATTERNS.items()
    ]


async def run_pattern(
    pattern_id: str,
    question: str,
    models: Optional[List[str]] = None,
    rounds: int = 2,
    branches: int = 3
) -> Dict[str, Any]:
    """
    Execute a specific deliberation pattern.

    Args:
        pattern_id: Pattern identifier
        question: The question/topic to deliberate
        models: Optional list of models to use
        rounds: Number of rounds (for iterative patterns)
        branches: Number of branches (for tree patterns)

    Returns:
        Dict with pattern results
    """
    if pattern_id not in PATTERNS:
        return {"error": f"Unknown pattern: {pattern_id}"}

    if models is None:
        models = CLI_COUNCIL_MODELS

    pattern = PATTERNS[pattern_id]
    logger.info(f"Running pattern: {pattern.name} with {len(models)} models")

    # Route to specific pattern implementation
    if pattern_id == "deliberation":
        return await _run_deliberation(question, models)
    elif pattern_id == "debate":
        return await _run_debate(question, models, rounds)
    elif pattern_id == "devils_advocate":
        return await _run_devils_advocate(question, models)
    elif pattern_id == "socratic":
        return await _run_socratic(question, models, rounds)
    elif pattern_id == "red_team":
        return await _run_red_team(question, models)
    elif pattern_id == "tree_of_thought":
        return await _run_tree_of_thought(question, models, branches)
    elif pattern_id == "self_consistency":
        return await _run_self_consistency(question, models, rounds)
    elif pattern_id == "round_robin":
        return await _run_round_robin(question, models, rounds)
    elif pattern_id == "expert_panel":
        return await _run_expert_panel(question, models)
    else:
        return {"error": f"Pattern {pattern_id} not implemented"}


async def _run_deliberation(question: str, models: List[str]) -> Dict[str, Any]:
    """Standard 3-stage deliberation."""
    from .council import run_full_council
    return await run_full_council(question, models)


async def _run_debate(question: str, models: List[str], rounds: int) -> Dict[str, Any]:
    """Adversarial debate between models."""
    stages = []

    # Assign positions
    positions = ["FOR", "AGAINST", "MODERATE"][:len(models)]
    position_prompt = f"""Topic: {question}

You will argue the {positions[0]} position. Prepare a compelling opening argument."""

    # Opening arguments
    opening_results = await query_providers_parallel(
        models,
        f"Topic: {question}\n\nProvide an opening argument. Be persuasive and well-reasoned."
    )
    stages.append({"stage": "opening_arguments", "results": opening_results})

    # Rebuttals
    openings_text = "\n\n".join([
        f"[{m}]: {r.get('content', 'No response')}"
        for m, r in opening_results.items()
    ])

    rebuttal_results = await query_providers_parallel(
        models,
        f"""Topic: {question}

Opening arguments:
{openings_text}

Provide a rebuttal addressing the other arguments."""
    )
    stages.append({"stage": "rebuttals", "results": rebuttal_results})

    # Judgment
    full_debate = openings_text + "\n\nRebuttals:\n" + "\n\n".join([
        f"[{m}]: {r.get('content', 'No response')}"
        for m, r in rebuttal_results.items()
    ])

    chairman = models[0] if models else CLI_CHAIRMAN_MODEL
    judgment = await query_cli_provider(
        chairman,
        f"""As judge of this debate on "{question}":

{full_debate}

Provide your judgment: Which position is most convincing and why? What key points decided this?"""
    )
    stages.append({"stage": "judgment", "result": judgment})

    return {
        "pattern": "debate",
        "question": question,
        "stages": stages,
        "final_judgment": judgment.get("content"),
    }


async def _run_devils_advocate(question: str, models: List[str]) -> Dict[str, Any]:
    """One model challenges the consensus."""
    # Initial consensus
    consensus_results = await query_providers_parallel(
        models[:-1] if len(models) > 1 else models,
        f"Question: {question}\n\nProvide your best answer."
    )

    consensus_text = "\n\n".join([
        f"[{m}]: {r.get('content', '')}"
        for m, r in consensus_results.items()
    ])

    # Devil's advocate challenge
    challenger = models[-1] if len(models) > 1 else models[0]
    challenge = await query_cli_provider(
        challenger,
        f"""The following answers have been given to "{question}":

{consensus_text}

As devil's advocate, challenge these answers. Find flaws, gaps, or alternative perspectives."""
    )

    # Defense
    defense_results = await query_providers_parallel(
        models[:-1] if len(models) > 1 else models,
        f"""Your answer was challenged:

{challenge.get('content', '')}

Defend your position or update your answer based on valid criticisms."""
    )

    return {
        "pattern": "devils_advocate",
        "question": question,
        "initial_consensus": consensus_results,
        "challenge": challenge,
        "defense": defense_results,
    }


async def _run_socratic(question: str, models: List[str], rounds: int) -> Dict[str, Any]:
    """Progressive questioning dialogue."""
    stages = []

    # Initial response
    initial = await query_providers_parallel(
        models,
        f"Question: {question}\n\nProvide an initial answer."
    )
    stages.append({"stage": "initial", "results": initial})

    current_context = "\n".join([
        f"[{m}]: {r.get('content', '')}" for m, r in initial.items()
    ])

    # Questioning rounds
    questioner = models[0] if models else CLI_CHAIRMAN_MODEL
    for i in range(rounds):
        # Generate questions
        questions = await query_cli_provider(
            questioner,
            f"""Based on these responses about "{question}":

{current_context}

Generate probing questions to deepen understanding or expose gaps."""
        )
        stages.append({"stage": f"questions_round_{i+1}", "result": questions})

        # Get refined answers
        refined = await query_providers_parallel(
            models,
            f"""Original question: {question}

Previous responses:
{current_context}

Follow-up questions:
{questions.get('content', '')}

Provide a refined, deeper response."""
        )
        stages.append({"stage": f"refinement_round_{i+1}", "results": refined})

        current_context = "\n".join([
            f"[{m}]: {r.get('content', '')}" for m, r in refined.items()
        ])

    return {
        "pattern": "socratic",
        "question": question,
        "rounds": rounds,
        "stages": stages,
    }


async def _run_red_team(question: str, models: List[str]) -> Dict[str, Any]:
    """Security/flaw focused analysis."""
    # Proposal
    proposal = await query_cli_provider(
        models[0] if models else CLI_CHAIRMAN_MODEL,
        f"Proposal to analyze: {question}\n\nDescribe the proposal in detail."
    )

    # Attack phase
    attack_results = await query_providers_parallel(
        models,
        f"""Red Team Analysis of:

{proposal.get('content', question)}

Identify all potential vulnerabilities, risks, and failure modes. Be thorough and adversarial."""
    )

    attacks_text = "\n".join([
        f"[{m}]: {r.get('content', '')}" for m, r in attack_results.items()
    ])

    # Recommendations
    recommendations = await query_cli_provider(
        models[0] if models else CLI_CHAIRMAN_MODEL,
        f"""Based on red team analysis:

{attacks_text}

Provide prioritized recommendations to address the identified issues."""
    )

    return {
        "pattern": "red_team",
        "question": question,
        "proposal": proposal,
        "attacks": attack_results,
        "recommendations": recommendations,
    }


async def _run_tree_of_thought(
    question: str,
    models: List[str],
    branches: int
) -> Dict[str, Any]:
    """Explore multiple solution branches."""
    # Generate branches
    branch_results = await query_providers_parallel(
        models[:branches] if len(models) >= branches else models,
        f"""Problem: {question}

Generate a unique approach or solution. Think creatively and explore different angles."""
    )

    branches_text = "\n".join([
        f"Branch {i+1} [{m}]: {r.get('content', '')}"
        for i, (m, r) in enumerate(branch_results.items())
    ])

    # Evaluate branches
    evaluation = await query_cli_provider(
        models[0] if models else CLI_CHAIRMAN_MODEL,
        f"""Evaluate these solution approaches:

{branches_text}

Score each branch (1-10) on feasibility, effectiveness, and innovation. Recommend the best path."""
    )

    return {
        "pattern": "tree_of_thought",
        "question": question,
        "branches": branch_results,
        "evaluation": evaluation,
    }


async def _run_self_consistency(
    question: str,
    models: List[str],
    attempts: int
) -> Dict[str, Any]:
    """Multiple attempts with consistency checking."""
    all_attempts = []

    # Run multiple attempts per model
    for model in models:
        for i in range(attempts):
            result = await query_cli_provider(
                model,
                f"Question: {question}\n\nProvide your answer. Be precise and accurate."
            )
            all_attempts.append({
                "model": model,
                "attempt": i + 1,
                "response": result.get("content", "")
            })

    # Consistency analysis
    attempts_text = "\n".join([
        f"[{a['model']} attempt {a['attempt']}]: {a['response']}"
        for a in all_attempts
    ])

    analysis = await query_cli_provider(
        models[0] if models else CLI_CHAIRMAN_MODEL,
        f"""Multiple attempts to answer "{question}":

{attempts_text}

Analyze consistency. What answer appears most reliable? Note any discrepancies."""
    )

    return {
        "pattern": "self_consistency",
        "question": question,
        "attempts": all_attempts,
        "analysis": analysis,
    }


async def _run_round_robin(
    question: str,
    models: List[str],
    rounds: int
) -> Dict[str, Any]:
    """Sequential refinement."""
    stages = []
    current_answer = ""

    for round_num in range(rounds):
        for model in models:
            prompt = f"Question: {question}\n\n"
            if current_answer:
                prompt += f"Previous answer to improve:\n{current_answer}\n\nRefine and improve this answer."
            else:
                prompt += "Provide an initial answer."

            result = await query_cli_provider(model, prompt)
            current_answer = result.get("content", current_answer)

            stages.append({
                "round": round_num + 1,
                "model": model,
                "response": current_answer,
            })

    return {
        "pattern": "round_robin",
        "question": question,
        "rounds": rounds,
        "stages": stages,
        "final_answer": current_answer,
    }


async def _run_expert_panel(question: str, models: List[str]) -> Dict[str, Any]:
    """Domain-specific expert roles."""
    # Define expert roles
    roles = [
        "Technical Expert (focus on implementation details)",
        "Business Expert (focus on practical applications)",
        "Critical Analyst (focus on risks and concerns)",
        "Innovation Expert (focus on creative possibilities)",
    ][:len(models)]

    # Get expert opinions
    expert_results = {}
    for model, role in zip(models, roles):
        result = await query_cli_provider(
            model,
            f"""As a {role}, analyze:

{question}

Provide your expert perspective from your specific domain."""
        )
        expert_results[f"{model} ({role})"] = result

    # Integration
    experts_text = "\n".join([
        f"[{expert}]: {r.get('content', '')}"
        for expert, r in expert_results.items()
    ])

    integration = await query_cli_provider(
        models[0] if models else CLI_CHAIRMAN_MODEL,
        f"""Expert panel opinions on "{question}":

{experts_text}

Integrate these expert perspectives into a comprehensive answer."""
    )

    return {
        "pattern": "expert_panel",
        "question": question,
        "experts": expert_results,
        "integration": integration,
    }
