"""
Procedural Evolution MCP Tools - Phase 3 Holographic Memory

Provides MCP tools for:
- Creating and managing skill variants
- Recording execution outcomes
- Selecting best variants for execution
- Running evolution cycles
- Viewing evolution statistics
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("procedural-evolution-tools")


def register_procedural_evolution_tools(app):
    """Register procedural evolution MCP tools."""

    from agi.procedural_evolution import (
        get_procedural_evolution,
        select_skill_variant,
        record_skill_outcome
    )

    evolution = get_procedural_evolution()

    @app.tool()
    async def create_skill_variant(
        skill_name: str,
        variant_tag: str,
        procedure_steps: List[str],
        preconditions: Optional[List[str]] = None,
        success_criteria: Optional[List[str]] = None,
        parent_variant_id: Optional[int] = None,
        mutation_type: str = "original"
    ) -> Dict[str, Any]:
        """
        Create a new skill variant for A/B testing.

        Part of Phase 3 Holographic Memory - procedures evolve through testing.

        Args:
            skill_name: Name of the skill (e.g., "code_review")
            variant_tag: Tag for this variant (e.g., "v1", "fast", "thorough")
            procedure_steps: List of procedure steps
            preconditions: Optional list of preconditions
            success_criteria: Optional list of success criteria
            parent_variant_id: If mutation, the parent variant ID
            mutation_type: Type of mutation (original, reorder, simplify, elaborate)

        Returns:
            Created variant details
        """
        try:
            variant_id = evolution.create_skill_variant(
                skill_name=skill_name,
                variant_tag=variant_tag,
                procedure_steps=procedure_steps,
                preconditions=preconditions,
                success_criteria=success_criteria,
                parent_variant_id=parent_variant_id,
                mutation_type=mutation_type
            )

            return {
                "success": True,
                "variant_id": variant_id,
                "skill_name": skill_name,
                "variant_tag": variant_tag,
                "steps_count": len(procedure_steps),
                "mutation_type": mutation_type
            }
        except Exception as e:
            logger.error(f"Error creating variant: {e}")
            return {"success": False, "error": str(e)}

    @app.tool()
    async def record_variant_execution(
        variant_id: int,
        success_score: float,
        context_key: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
        outcome: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record a variant execution and update fitness.

        This is how variants learn and improve - every execution updates
        the fitness score and context affinity.

        Args:
            variant_id: Which variant was executed
            success_score: 0.0 to 1.0 success score
            context_key: Optional context identifier for context-aware learning
            execution_time_ms: Execution time in milliseconds
            outcome: Description of outcome
            error_message: Error if failed

        Returns:
            Confirmation of recording
        """
        try:
            evolution.record_execution(
                variant_id=variant_id,
                success_score=success_score,
                context_key=context_key,
                execution_time_ms=execution_time_ms,
                outcome=outcome,
                error_message=error_message
            )

            return {
                "success": True,
                "variant_id": variant_id,
                "success_score": success_score,
                "context_key": context_key
            }
        except Exception as e:
            logger.error(f"Error recording execution: {e}")
            return {"success": False, "error": str(e)}

    @app.tool()
    async def select_best_skill_variant(
        skill_name: str,
        context_key: Optional[str] = None,
        exploration_rate: float = 0.1
    ) -> Dict[str, Any]:
        """
        Select the best variant for a skill using Thompson Sampling.

        Integrates with activation field for context-aware selection.
        Uses exploration/exploitation trade-off for continuous learning.

        Args:
            skill_name: Name of the skill
            context_key: Optional context for context-aware selection
            exploration_rate: Probability of exploring non-best variant (default 0.1)

        Returns:
            Best variant details including procedure steps
        """
        try:
            variant = evolution.select_best_variant(
                skill_name=skill_name,
                context_key=context_key,
                exploration_rate=exploration_rate
            )

            if variant:
                return {
                    "success": True,
                    "found": True,
                    "variant": variant.to_dict()
                }
            else:
                return {
                    "success": True,
                    "found": False,
                    "skill_name": skill_name,
                    "message": "No variants found for this skill"
                }
        except Exception as e:
            logger.error(f"Error selecting variant: {e}")
            return {"success": False, "error": str(e)}

    @app.tool()
    async def get_skill_variants(
        skill_name: str,
        active_only: bool = True
    ) -> Dict[str, Any]:
        """
        Get all variants for a skill.

        Args:
            skill_name: Name of the skill
            active_only: If True, only return active (non-pruned) variants

        Returns:
            List of all variants with their fitness scores
        """
        try:
            variants = evolution.get_variants(skill_name, active_only)

            return {
                "success": True,
                "skill_name": skill_name,
                "variant_count": len(variants),
                "variants": [v.to_dict() for v in variants]
            }
        except Exception as e:
            logger.error(f"Error getting variants: {e}")
            return {"success": False, "error": str(e)}

    @app.tool()
    async def mutate_skill_variant(
        variant_id: int,
        mutation_type: str = "auto"
    ) -> Dict[str, Any]:
        """
        Create a mutated variant from an existing variant.

        Mutation types:
        - "auto": Randomly select mutation type
        - "reorder": Change order of steps
        - "simplify": Remove a step
        - "elaborate": Add detail to a step
        - "combine": Merge two steps

        Args:
            variant_id: Variant to mutate
            mutation_type: Type of mutation (default "auto")

        Returns:
            New variant details
        """
        try:
            variants = evolution.get_variants("", active_only=False)
            source_variant = None

            # Find the source variant
            conn = __import__('sqlite3').connect(evolution._instance.DB_PATH if hasattr(evolution._instance, 'DB_PATH') else str(__import__('pathlib').Path.home() / ".claude" / "enhanced_memories" / "memory.db"))
            conn.row_factory = __import__('sqlite3').Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM skill_variants WHERE variant_id = ?', (variant_id,))
            row = cursor.fetchone()
            conn.close()

            if not row:
                return {
                    "success": False,
                    "error": f"Variant {variant_id} not found"
                }

            from agi.procedural_evolution import SkillVariant
            import json

            source_variant = SkillVariant(
                variant_id=row['variant_id'],
                skill_name=row['skill_name'],
                variant_tag=row['variant_tag'],
                procedure_steps=json.loads(row['procedure_steps']),
                preconditions=json.loads(row['preconditions']) if row['preconditions'] else [],
                success_criteria=json.loads(row['success_criteria']) if row['success_criteria'] else [],
                execution_count=row['execution_count'],
                success_count=row['success_count'],
                total_score=row['total_score'],
                parent_variant_id=row['parent_variant_id'],
                mutation_type=row['mutation_type'],
                created_at=row['created_at'],
                context_affinity=json.loads(row['context_affinity']) if row['context_affinity'] else {}
            )

            new_id = evolution.mutate_variant(source_variant, mutation_type)

            if new_id:
                return {
                    "success": True,
                    "new_variant_id": new_id,
                    "source_variant_id": variant_id,
                    "mutation_type": mutation_type
                }
            else:
                return {
                    "success": False,
                    "error": "Mutation failed"
                }
        except Exception as e:
            logger.error(f"Error mutating variant: {e}")
            return {"success": False, "error": str(e)}

    @app.tool()
    async def run_skill_evolution(
        skill_name: str,
        min_executions: int = 5,
        prune_threshold: float = 0.3,
        mutate_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        Run an evolution cycle for a skill.

        This is the core evolution mechanism:
        1. Prune poor-performing variants (below prune_threshold)
        2. Mutate successful variants (above mutate_threshold)
        3. Keep balanced variants active

        Args:
            skill_name: Skill to evolve
            min_executions: Minimum executions before variant can be pruned
            prune_threshold: Fitness below this gets pruned (default 0.3)
            mutate_threshold: Fitness above this gets mutated (default 0.7)

        Returns:
            Evolution cycle summary
        """
        try:
            result = evolution.run_evolution_cycle(
                skill_name=skill_name,
                min_executions=min_executions,
                prune_threshold=prune_threshold,
                mutate_threshold=mutate_threshold
            )

            return result
        except Exception as e:
            logger.error(f"Error running evolution: {e}")
            return {"success": False, "error": str(e)}

    @app.tool()
    async def get_skill_fitness_summary(
        skill_name: str
    ) -> Dict[str, Any]:
        """
        Get fitness summary for a skill's variants.

        Shows best/worst performers, average fitness, and all variant details.

        Args:
            skill_name: Skill to summarize

        Returns:
            Fitness summary with variant details
        """
        try:
            summary = evolution.get_skill_fitness_summary(skill_name)
            return {"success": True, **summary}
        except Exception as e:
            logger.error(f"Error getting fitness summary: {e}")
            return {"success": False, "error": str(e)}

    @app.tool()
    async def get_evolution_history(
        skill_name: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get evolution cycle history.

        Args:
            skill_name: Optional filter by skill
            limit: Maximum results (default 20)

        Returns:
            List of evolution cycles
        """
        try:
            history = evolution.get_evolution_history(skill_name, limit)

            return {
                "success": True,
                "skill_name": skill_name,
                "cycle_count": len(history),
                "cycles": history
            }
        except Exception as e:
            logger.error(f"Error getting evolution history: {e}")
            return {"success": False, "error": str(e)}

    @app.tool()
    async def get_procedural_evolution_stats() -> Dict[str, Any]:
        """
        Get overall procedural evolution statistics.

        Shows system-wide evolution metrics including:
        - Active variants count
        - Unique skills count
        - Total executions
        - Average fitness
        - Evolution cycle counts

        Returns:
            System-wide evolution statistics
        """
        try:
            stats = evolution.get_stats()
            return {"success": True, **stats}
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"success": False, "error": str(e)}

    @app.tool()
    async def evolve_procedure_from_activation(
        skill_name: str
    ) -> Dict[str, Any]:
        """
        Select a skill variant based on current activation field.

        This is the key Phase 3 integration - the activation field
        from Phase 1 influences which procedure variant is selected.

        Args:
            skill_name: Skill to select variant for

        Returns:
            Selected variant influenced by activation field
        """
        try:
            # Try to get activation field context
            context_key = None
            try:
                from agi.activation_field import get_activation_field
                field = get_activation_field()
                if field.current_state:
                    # Use routing recommendation as context
                    recommendation = field.get_routing_recommendation()
                    context_key = recommendation
            except ImportError:
                logger.debug("Activation field not available, using default selection")

            variant = evolution.select_best_variant(skill_name, context_key)

            if variant:
                return {
                    "success": True,
                    "found": True,
                    "context_key": context_key,
                    "variant": variant.to_dict(),
                    "activation_influenced": context_key is not None
                }
            else:
                return {
                    "success": True,
                    "found": False,
                    "skill_name": skill_name,
                    "message": "No variants found"
                }
        except Exception as e:
            logger.error(f"Error in activation-based selection: {e}")
            return {"success": False, "error": str(e)}

    logger.info("Registered procedural evolution MCP tools")
    return evolution
