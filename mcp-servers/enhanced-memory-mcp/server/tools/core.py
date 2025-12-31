"""
Core memory tools for Enhanced Memory MCP Server.

Tools:
- create_entities: Create entities with compression, versioning, enrichment
- search_nodes: Search for entities by name or type
"""

import json
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List

from ..config import DB_PATH, log_tool_usage, logger


# Import optional scoring modules
try:
    from tpu_importance import score_importance, is_tpu_available
    TPU_SCORING_AVAILABLE = True
except ImportError:
    TPU_SCORING_AVAILABLE = False

    def score_importance(text: str, context: str = "memory", source: str = "direct") -> float:
        """Fallback heuristic scoring when TPU module unavailable."""
        score = 0.3
        text_lower = text.lower()
        high_kw = ["error", "critical", "security", "bug", "important", "urgent"]
        for kw in high_kw:
            if kw in text_lower:
                score += 0.15
        return min(1.0, score)

    def is_tpu_available() -> bool:
        return False


try:
    from entropy_scoring import (
        score_entity_entropy,
        combine_scores,
        update_stats as update_entropy_stats,
        get_stats as get_entropy_stats,
    )
    ENTROPY_SCORING_AVAILABLE = True
except ImportError:
    ENTROPY_SCORING_AVAILABLE = False

    def score_entity_entropy(name: str, observations: list, entity_type: str = "general"):
        return None

    def combine_scores(tpu_score: float, entropy_result, **kwargs):
        if tpu_score >= 0.8:
            return tpu_score, "long_term"
        elif tpu_score >= 0.6:
            return tpu_score, "episodic"
        return tpu_score, "working"

    def update_entropy_stats(result):
        pass

    def get_entropy_stats():
        return {}


def register_core_tools(app, memory_client):
    """Register core memory tools with FastMCP app."""

    async def _enrich_new_entities(entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Add contextual prefixes to newly created entities.

        Part of RAG Tier 1 Strategy - Contextual Enrichment
        Expected improvement: -35% retrieval failures
        """
        try:
            from contextual_llm import get_prefix_generator

            generator = get_prefix_generator()
            enriched_count = 0
            failed_count = 0

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            for entity in entities:
                try:
                    entity_name = entity.get('name')
                    entity_type = entity.get('entityType', 'unknown')
                    observations = entity.get('observations', [])

                    cursor.execute('SELECT id FROM entities WHERE name = ?', (entity_name,))
                    result = cursor.fetchone()
                    if not result:
                        logger.warning(f"Entity '{entity_name}' not found for enrichment")
                        failed_count += 1
                        continue

                    entity_id = result[0]

                    prefix, input_tokens, output_tokens = await generator.generate_prefix(
                        entity_name=entity_name,
                        entity_type=entity_type,
                        observations=observations
                    )

                    cursor.execute('''
                        SELECT MIN(created_at) FROM observations WHERE entity_id = ?
                    ''', (entity_id,))
                    min_created = cursor.fetchone()[0]

                    if min_created:
                        if 'T' in min_created:
                            dt = datetime.fromisoformat(min_created.replace('Z', '+00:00'))
                        else:
                            dt = datetime.strptime(min_created, '%Y-%m-%d %H:%M:%S')
                        insert_time = (dt - timedelta(seconds=1)).strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        insert_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                    cursor.execute('''
                        INSERT INTO observations (entity_id, content, created_at)
                        VALUES (?, ?, ?)
                    ''', (entity_id, prefix, insert_time))

                    enriched_count += 1

                except Exception as e:
                    logger.error(f"Error enriching entity '{entity.get('name')}': {e}")
                    failed_count += 1

            conn.commit()
            conn.close()

            stats = generator.get_stats()

            return {
                "enriched": enriched_count,
                "failed": failed_count,
                "tokens": {
                    "input": stats.get("total_input_tokens", 0),
                    "output": stats.get("total_output_tokens", 0)
                },
                "cost_usd": stats.get("estimated_cost_usd", 0.0),
                "using_llm": not stats.get("using_fallback", False)
            }

        except ImportError as e:
            logger.warning(f"Contextual enrichment not available: {e}")
            return {
                "enriched": 0,
                "failed": len(entities),
                "error": "contextual_llm module not available"
            }
        except Exception as e:
            logger.error(f"Error in contextual enrichment: {e}")
            return {
                "enriched": 0,
                "failed": len(entities),
                "error": str(e)
            }

    async def _score_and_tier_entities(entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Score entity importance via TPU + entropy and assign memory tier.

        COMBINED SCORING (PTM paper integration):
        - TPU score (70% weight): Semantic importance from TPU Warm Service
        - Entropy score (30% weight): Information density from PTM-inspired analysis
        """
        scored_count = 0
        tier_changes = {"long_term": 0, "episodic": 0, "working": 0}
        entropy_classifications = {"anchor": 0, "bridge": 0, "mixed": 0}
        tpu_used = is_tpu_available() if TPU_SCORING_AVAILABLE else False
        entropy_used = ENTROPY_SCORING_AVAILABLE

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            for entity in entities:
                try:
                    entity_name = entity.get('name')
                    entity_type = entity.get('entityType', 'general')
                    observations = entity.get('observations', [])

                    combined_text = f"{entity_name}: " + " ".join(
                        str(obs) for obs in observations[:5]
                    )

                    tpu_score = score_importance(combined_text, context="memory", source="direct")

                    entropy_result = None
                    if ENTROPY_SCORING_AVAILABLE:
                        entropy_result = score_entity_entropy(
                            entity_name, observations, entity_type
                        )
                        if entropy_result:
                            update_entropy_stats(entropy_result)
                            entropy_classifications[entropy_result.classification] += 1

                    combined_score, new_tier = combine_scores(
                        tpu_score, entropy_result,
                        tpu_weight=0.7, entropy_weight=0.3
                    )

                    cursor.execute('''
                        UPDATE entities SET tier = ? WHERE name = ?
                    ''', (new_tier, entity_name))

                    if cursor.rowcount > 0:
                        tier_changes[new_tier] += 1
                        scored_count += 1

                except Exception as e:
                    logger.debug(f"Error scoring entity '{entity.get('name')}': {e}")

            conn.commit()
            conn.close()

            return {
                "scored": scored_count,
                "tier_assignments": tier_changes,
                "tpu_available": tpu_used,
                "scoring_method": "tpu+entropy" if entropy_used else (
                    "tpu_warm_service" if tpu_used else "heuristic"
                ),
                "entropy_scoring": {
                    "enabled": entropy_used,
                    "classifications": entropy_classifications if entropy_used else {},
                    "stats": get_entropy_stats() if entropy_used else {}
                }
            }

        except Exception as e:
            logger.error(f"Error in TPU+entropy scoring: {e}")
            return {
                "scored": 0,
                "error": str(e),
                "tpu_available": False,
                "entropy_scoring": {"enabled": False}
            }

    async def _track_entity_provenance(entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Track provenance for newly created entities (STAGE 3 HARDENING).

        Mandatory provenance tracking ensures all entities have:
        - Source attribution
        - Confidence scoring
        - L-Score calculation
        """
        from provenance import calculate_l_score

        tracked_count = 0
        flagged_unverified = 0
        l_score_distribution = {"high": 0, "acceptable": 0, "low": 0}

        DERIVATION_CONFIDENCE = {
            "user_input": 0.7,
            "inference": 0.6,
            "extraction": 0.75,
            "observation": 0.65,
            "citation": 0.85,
            "synthesis": 0.55,
            "api_call": 0.8,
            "unknown": 0.4
        }

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            for entity in entities:
                try:
                    entity_name = entity.get('name')

                    cursor.execute('SELECT id FROM entities WHERE name = ?', (entity_name,))
                    result = cursor.fetchone()
                    if not result:
                        logger.warning(f"Entity '{entity_name}' not found for provenance tracking")
                        continue

                    entity_id = result[0]

                    provenance = entity.get('provenance', {})
                    derivation_method = provenance.get('derivation_method', 'unknown')
                    source_ids = provenance.get('source_ids', [])
                    explicit_confidence = provenance.get('confidence')
                    relevance = provenance.get('relevance', 0.7)

                    if explicit_confidence is not None:
                        confidence = float(explicit_confidence)
                    else:
                        confidence = DERIVATION_CONFIDENCE.get(derivation_method, 0.4)

                    if derivation_method == 'unknown':
                        flagged_unverified += 1
                        logger.warning(
                            f"PROVENANCE: Entity '{entity_name}' has no provenance metadata"
                        )

                    confidence_scores = [confidence]
                    relevance_scores = [relevance]

                    if source_ids:
                        for source_id in source_ids[:5]:
                            cursor.execute('''
                                SELECT l_score, reasoning_quality
                                FROM entities WHERE id = ?
                            ''', (source_id,))
                            source = cursor.fetchone()
                            if source and source[0]:
                                confidence_scores.append(source[1] if source[1] else 0.5)

                    depth = len(source_ids) if source_ids else 1
                    l_score_result = calculate_l_score(
                        confidence_scores=confidence_scores,
                        relevance_scores=relevance_scores,
                        depth=depth
                    )

                    provenance_chain = {
                        "source_ids": source_ids,
                        "confidence_scores": confidence_scores,
                        "relevance_scores": relevance_scores,
                        "derivation_methods": [derivation_method],
                        "timestamps": [datetime.now().isoformat()]
                    }

                    cursor.execute('''
                        UPDATE entities SET
                            l_score = ?,
                            reasoning_quality = ?,
                            source_chain = ?,
                            derivation_depth = ?
                        WHERE id = ?
                    ''', (
                        l_score_result.l_score,
                        l_score_result.reasoning_quality,
                        json.dumps(provenance_chain),
                        depth,
                        entity_id
                    ))

                    tracked_count += 1

                    if l_score_result.l_score >= 0.7:
                        l_score_distribution["high"] += 1
                    elif l_score_result.l_score >= 0.3:
                        l_score_distribution["acceptable"] += 1
                    else:
                        l_score_distribution["low"] += 1
                        logger.warning(
                            f"PROVENANCE: Entity '{entity_name}' has low L-Score "
                            f"({l_score_result.l_score:.2f})"
                        )

                except Exception as e:
                    logger.debug(f"Error tracking provenance for '{entity.get('name')}': {e}")

            conn.commit()
            conn.close()

            return {
                "tracked": tracked_count,
                "flagged_unverified": flagged_unverified,
                "l_score_distribution": l_score_distribution,
                "tracking_mandatory": True
            }

        except Exception as e:
            logger.error(f"Error in provenance tracking: {e}")
            return {
                "tracked": 0,
                "error": str(e),
                "tracking_mandatory": True
            }

    @app.tool()
    async def create_entities(entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create entities with compression, storage, automatic versioning, and contextual enrichment.

        CONCURRENT ACCESS: Uses memory-db Unix socket service for database operations.
        CONTEXTUAL ENRICHMENT: Automatically adds LLM-generated contextual prefixes (RAG Tier 1).
        FACT VALIDATION: Blocks entities with false claims or logical contradictions (Stage 3 hardening).

        Args:
            entities: List of entity objects with name, entityType, and observations

        Returns:
            Results with compression statistics and entity details
        """
        _start = time.time()
        try:
            # Import fact validation
            from fact_validator import validate_entities_before_storage

            # STAGE 3 HARDENING: Validate entities before storage
            validation_result = validate_entities_before_storage(entities)

            blocked_count = len(validation_result.get("blocked_entities", []))
            if blocked_count > 0:
                logger.warning(
                    f"FACT VALIDATION: Blocked {blocked_count} entities with false/contradictory claims"
                )
                for blocked in validation_result["blocked_entities"]:
                    logger.warning(
                        f"  - Blocked: {blocked['entity'].get('name', 'unknown')}: {blocked['reason']}"
                    )

            valid_entities = validation_result.get("valid_entities", [])
            if not valid_entities:
                return {
                    "created": 0,
                    "failed": len(entities),
                    "blocked": blocked_count,
                    "error": "All entities blocked by fact validation",
                    "blocked_details": [
                        {"name": b["entity"].get("name"), "reason": b["reason"]}
                        for b in validation_result.get("blocked_entities", [])
                    ],
                    "validation_stats": validation_result.get("stats", {})
                }

            # Delegate valid entities to memory-db service
            response = await memory_client.create_entities(valid_entities)

            if response.get("success"):
                enrichment_stats = await _enrich_new_entities(valid_entities)
                scoring_stats = await _score_and_tier_entities(valid_entities)
                provenance_stats = await _track_entity_provenance(valid_entities)

                return {
                    "created": response.get("count", 0),
                    "failed": blocked_count,
                    "blocked": blocked_count,
                    "flagged": len(validation_result.get("flagged_entities", [])),
                    "flagged_unverified": provenance_stats.get("flagged_unverified", 0),
                    "results": response.get("results", []),
                    "contextual_enrichment": enrichment_stats,
                    "tpu_scoring": scoring_stats,
                    "provenance_tracking": provenance_stats,
                    "fact_validation": validation_result.get("stats", {}),
                    "blocked_details": [
                        {"name": b["entity"].get("name"), "reason": b["reason"]}
                        for b in validation_result.get("blocked_entities", [])
                    ] if blocked_count > 0 else []
                }
            else:
                return {
                    "created": 0,
                    "failed": len(entities),
                    "blocked": blocked_count,
                    "error": response.get("error", "Unknown error from memory-db service"),
                    "fact_validation": validation_result.get("stats", {})
                }

        except Exception as e:
            log_tool_usage("create_entities", "core", False, (time.time() - _start) * 1000)
            logger.error(f"Error creating entities via memory-db: {str(e)}")
            return {
                "created": 0,
                "failed": len(entities),
                "error": f"Memory-DB service error: {str(e)}"
            }
        finally:
            log_tool_usage("create_entities", "core", True, (time.time() - _start) * 1000)

    @app.tool()
    async def search_nodes(query: str, limit: int = 10) -> Dict[str, Any]:
        """
        Search for entities by name or type with automatic version history.

        CONCURRENT ACCESS: Uses memory-db Unix socket service for database operations.

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of matching entities with version information
        """
        _start = time.time()
        try:
            response = await memory_client.search_nodes(query, limit)

            if response.get("success"):
                return {
                    "query": query,
                    "count": len(response.get("entities", [])),
                    "results": response.get("entities", [])
                }
            else:
                return {
                    "query": query,
                    "count": 0,
                    "results": [],
                    "error": response.get("error", "Unknown error from memory-db service")
                }

        except Exception as e:
            log_tool_usage("search_nodes", "core", False, (time.time() - _start) * 1000)
            logger.error(f"Error searching nodes via memory-db: {str(e)}")
            return {
                "query": query,
                "count": 0,
                "results": [],
                "error": f"Memory-DB service error: {str(e)}"
            }
        finally:
            log_tool_usage("search_nodes", "core", True, (time.time() - _start) * 1000)

    return {
        'create_entities': create_entities,
        'search_nodes': search_nodes,
    }
