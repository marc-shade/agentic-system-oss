"""
Module loading system for Enhanced Memory MCP Server.

Handles conditional loading of tool modules based on MEMORY_PROFILE setting:
- full: Load all 30+ modules (200+ tools)
- orchestrator: Load only essential modules (~15 tools)

Extracted from server.py for better organization.
"""

import asyncio
import os
from typing import Set

from .config import logger, set_tool_usage_callback


# Modules to load in orchestrator mode (minimal set for coordination)
ORCHESTRATOR_MODULES: Set[str] = {
    "nmf_tools",              # nmf_remember, nmf_recall - quick memory ops
    "safla_remote_integration",  # SAFLA embeddings (4 tools)
    "fact_integration",       # fact_search - fast cache-first retrieval
    "unified_search_api",     # unified_search - intelligent routing
    "semantic_cache_tools",   # agi_cached_reasoning - LLM result caching
    "reasoning_bank",         # rb_retrieve, rb_learn - persistent learning
}


def get_memory_profile() -> str:
    """Get the current memory profile from environment."""
    return os.getenv("MEMORY_PROFILE", "full")


def is_orchestrator_mode() -> bool:
    """Check if running in orchestrator mode."""
    return get_memory_profile() == "orchestrator"


def should_load_module(module_name: str) -> bool:
    """
    Check if a module should be loaded based on memory profile.

    Args:
        module_name: Name of the module to check

    Returns:
        True if module should be loaded
    """
    if not is_orchestrator_mode():
        return True  # Full mode: load everything
    return module_name in ORCHESTRATOR_MODULES


def skip_msg(module_name: str) -> str:
    """Generate skip message for orchestrator mode."""
    return f"⏭️  {module_name} skipped (orchestrator mode - cascade to subagent)"


def setup_tool_usage_logging(app) -> None:
    """
    Initialize tool usage logging for eval infrastructure.

    Tracks which tools are actually invoked to inform ORCHESTRATOR_MODULES refinement.
    """
    if os.getenv("TOOL_USAGE_LOGGING", "true").lower() != "true":
        return

    try:
        from tool_usage_logger import (
            ToolUsageLogger,
            register_usage_analysis_tools,
            log_tool_call
        )
        usage_logger = ToolUsageLogger.get_instance()
        register_usage_analysis_tools(app)

        # Wire up the callback for core tools
        set_tool_usage_callback(log_tool_call)

        logger.info(f"Tool usage logging enabled: {usage_logger.log_file}")
    except Exception as e:
        logger.warning(f"Tool usage logging disabled: {e}")


def register_optional_modules(app, db_path, nmf_instance=None, memory_client=None) -> None:
    """
    Register all optional tool modules based on memory profile.

    Args:
        app: FastMCP application instance
        db_path: Path to database
        nmf_instance: Optional Neural Memory Fabric instance
        memory_client: Optional MemoryClient instance
    """
    profile = get_memory_profile()
    is_orch = is_orchestrator_mode()
    logger.info(f"Memory Profile: {profile} ({'~15 tools' if is_orch else '200+ tools'})")

    # Reasoning tools (75/15 rule)
    if should_load_module("reasoning_tools"):
        try:
            from reasoning_tools import register_reasoning_tools
            register_reasoning_tools(app, db_path)
            logger.info("Reasoning Prioritization (75/15 rule) integrated")
        except Exception as e:
            logger.warning(f"Reasoning prioritization integration skipped: {e}")
    else:
        logger.info(skip_msg("reasoning_tools"))

    # NMF tools
    if should_load_module("nmf_tools"):
        try:
            from nmf_tools import register_nmf_tools
            register_nmf_tools(app)
            logger.info("Neural Memory Fabric tools integrated")
        except Exception as e:
            logger.warning(f"NMF integration skipped: {e}")
    else:
        logger.info(skip_msg("nmf_tools"))

    # SAFLA local tools
    if should_load_module("safla_tools"):
        try:
            from safla_orchestrator import SAFLAOrchestrator
            from safla_tools import register_safla_tools
            safla = SAFLAOrchestrator(db_path)
            register_safla_tools(app, safla)
            logger.info("SAFLA local tools integrated")
        except Exception as e:
            logger.warning(f"SAFLA local integration skipped: {e}")
    else:
        logger.info(skip_msg("safla_tools"))

    # SAFLA remote tools
    if should_load_module("safla_remote_integration"):
        try:
            from safla_remote_integration import register_safla_remote_tools
            register_safla_remote_tools(app)
            logger.info("SAFLA remote tools integrated (4 tools from safla-mcp merger)")
        except Exception as e:
            logger.warning(f"SAFLA remote integration skipped: {e}")
    else:
        logger.info(skip_msg("safla_remote_integration"))

    # AGI tools Phase 1-4
    _register_agi_phases(app, db_path)

    # Provenance & L-Score tools
    if should_load_module("provenance"):
        try:
            from provenance import register_provenance_tools
            register_provenance_tools(app, db_path)
            logger.info("Provenance/L-Score tools integrated")
        except Exception as e:
            logger.warning(f"Provenance/L-Score integration skipped: {e}")
    else:
        logger.info(skip_msg("provenance"))

    # Shadow Vector tools
    if should_load_module("shadow_vector"):
        try:
            from shadow_vector import register_shadow_vector_tools
            register_shadow_vector_tools(app, db_path)
            logger.info("Shadow Vector tools integrated")
        except Exception as e:
            logger.warning(f"Shadow Vector integration skipped: {e}")
    else:
        logger.info(skip_msg("shadow_vector"))

    # Surprise Consolidation tools
    if should_load_module("surprise_consolidation_tools"):
        try:
            from surprise_consolidation_tools import register_surprise_consolidation_tools
            register_surprise_consolidation_tools(app, db_path)
            logger.info("Surprise Consolidation tools integrated")
        except Exception as e:
            logger.warning(f"Surprise Consolidation integration skipped: {e}")
    else:
        logger.info(skip_msg("surprise_consolidation_tools"))

    # ART tools
    if should_load_module("art_tools"):
        try:
            from art_tools import register_art_tools
            register_art_tools(app)
            logger.info("ART tools integrated")
        except Exception as e:
            logger.warning(f"ART integration skipped: {e}")
    else:
        logger.info(skip_msg("art_tools"))

    # RAG and search tools
    _register_rag_tools(app, nmf_instance)

    # Agentic-flow tools (ModelRouter, Anti-Hallucination, etc.)
    _register_agentic_flow_tools(app)

    # Holographic memory tools
    _register_holographic_tools(app, nmf_instance)


def _register_agi_phases(app, db_path) -> None:
    """Register AGI Memory tools Phase 1-4."""
    phases = [
        ("agi_tools", "agi_tools", "register_agi_tools", "AGI Memory Phase 1"),
        ("agi_tools_phase2", "agi_tools_phase2", "register_agi_phase2_tools", "AGI Memory Phase 2"),
        ("agi_tools_phase3", "agi_tools_phase3", "register_agi_phase3_tools", "AGI Memory Phase 3"),
        ("agi_tools_phase4", "agi_tools_phase4", "register_agi_phase4_tools", "AGI Memory Phase 4"),
    ]

    for module_key, module_name, func_name, description in phases:
        if should_load_module(module_key):
            try:
                mod = __import__(module_name)
                register_func = getattr(mod, func_name)
                register_func(app, db_path)
                logger.info(f"{description} tools integrated")
            except Exception as e:
                logger.warning(f"{description} integration skipped: {e}")
        else:
            logger.info(skip_msg(module_key))


def _register_rag_tools(app, nmf_instance) -> None:
    """Register RAG strategy tools (Tier 1-4)."""
    # Re-ranking tools
    if should_load_module("reranking_tools_nmf") and nmf_instance:
        try:
            from reranking_tools_nmf import register_reranking_tools_nmf
            register_reranking_tools_nmf(app, nmf_instance)
            logger.info("Re-ranking (RAG Tier 1) integrated")
        except Exception as e:
            logger.warning(f"Re-ranking integration skipped: {e}")
    elif not should_load_module("reranking_tools_nmf"):
        logger.info(skip_msg("reranking_tools_nmf"))

    # Hybrid search tools
    if should_load_module("hybrid_search_tools_nmf") and nmf_instance:
        try:
            from hybrid_search_tools_nmf import register_hybrid_search_tools_nmf
            register_hybrid_search_tools_nmf(app, nmf_instance)
            logger.info("Hybrid Search (RAG Tier 1) integrated")
        except Exception as e:
            logger.warning(f"Hybrid search integration skipped: {e}")
    elif not should_load_module("hybrid_search_tools_nmf"):
        logger.info(skip_msg("hybrid_search_tools_nmf"))

    # Query expansion tools
    if should_load_module("query_expansion_tools") and nmf_instance:
        try:
            from query_expansion_tools import register_query_expansion_tools
            register_query_expansion_tools(app, nmf_instance)
            logger.info("Query Expansion (RAG Tier 2) integrated")
        except Exception as e:
            logger.warning(f"Query expansion integration skipped: {e}")
    elif not should_load_module("query_expansion_tools"):
        logger.info(skip_msg("query_expansion_tools"))

    # Multi-Query RAG tools
    if should_load_module("multi_query_rag_tools") and nmf_instance:
        try:
            from multi_query_rag_tools import register_multi_query_rag_tools
            register_multi_query_rag_tools(app, nmf_instance)
            logger.info("Multi-Query RAG (RAG Tier 2) integrated")
        except Exception as e:
            logger.warning(f"Multi-Query RAG integration skipped: {e}")
    elif not should_load_module("multi_query_rag_tools"):
        logger.info(skip_msg("multi_query_rag_tools"))

    # Contextual Retrieval tools
    if should_load_module("contextual_retrieval_tools") and nmf_instance:
        try:
            from contextual_retrieval_tools import register_contextual_retrieval_tools
            register_contextual_retrieval_tools(app, nmf_instance)
            logger.info("Contextual Retrieval (RAG Tier 3.1) integrated")
        except Exception as e:
            logger.warning(f"Contextual Retrieval integration skipped: {e}")
    elif not should_load_module("contextual_retrieval_tools"):
        logger.info(skip_msg("contextual_retrieval_tools"))

    # Visual Memory tools
    if should_load_module("visual_memory_tools"):
        try:
            from visual_memory_tools import register_visual_memory_tools
            register_visual_memory_tools(app, use_tpu=True)
            logger.info("Visual Memory (RAG Tier 4) integrated")
        except Exception as e:
            logger.warning(f"Visual Memory integration skipped: {e}")
    else:
        logger.info(skip_msg("visual_memory_tools"))

    # Semantic Cache tools
    if should_load_module("semantic_cache_tools"):
        try:
            from semantic_cache_tools import register_semantic_cache_tools
            register_semantic_cache_tools(app)
            logger.info("Semantic Cache integrated")
        except Exception as e:
            logger.warning(f"Semantic Cache integration skipped: {e}")
    else:
        logger.info(skip_msg("semantic_cache_tools"))

    # FACT Cache tools
    if should_load_module("fact_integration"):
        try:
            from fact_integration import register_fact_tools
            register_fact_tools(app, memory_client=None)  # Will use default
            logger.info("FACT Cache integrated")
        except Exception as e:
            logger.warning(f"FACT Cache integration skipped: {e}")
    else:
        logger.info(skip_msg("fact_integration"))

    # Unified Search API
    if should_load_module("unified_search_api"):
        try:
            from unified_search_api import register_unified_search_tools
            register_unified_search_tools(app, nmf_instance=nmf_instance)
            logger.info("Unified Search API integrated")
        except Exception as e:
            logger.warning(f"Unified Search API integration skipped: {e}")
    else:
        logger.info(skip_msg("unified_search_api"))

    # ReasoningBank
    if should_load_module("reasoning_bank"):
        try:
            from reasoning_bank import register_reasoning_bank_tools
            register_reasoning_bank_tools(app)
            logger.info("ReasoningBank integrated")
        except Exception as e:
            logger.warning(f"ReasoningBank integration skipped: {e}")
    else:
        logger.info(skip_msg("reasoning_bank"))


def _register_agentic_flow_tools(app) -> None:
    """Register agentic-flow derived tools."""
    # ModelRouter
    if should_load_module("model_router"):
        try:
            from model_router import register_model_router_tools
            register_model_router_tools(app)
            logger.info("ModelRouter integrated")
        except Exception as e:
            logger.warning(f"ModelRouter integration skipped: {e}")
    else:
        logger.info(skip_msg("model_router"))

    # Anti-Hallucination
    if should_load_module("anti_hallucination"):
        try:
            from anti_hallucination import register_anti_hallucination_tools
            register_anti_hallucination_tools(app)
            logger.info("Anti-Hallucination integrated")
        except Exception as e:
            logger.warning(f"Anti-Hallucination integration skipped: {e}")
    else:
        logger.info(skip_msg("anti_hallucination"))

    # Continuous Learning
    if should_load_module("continuous_learning"):
        try:
            from continuous_learning import register_continuous_learning_tools
            register_continuous_learning_tools(app)
            logger.info("Continuous Learning integrated")
        except Exception as e:
            logger.warning(f"Continuous Learning integration skipped: {e}")
    else:
        logger.info(skip_msg("continuous_learning"))

    # Strange Loops Detector
    if should_load_module("strange_loops"):
        try:
            from strange_loops import register_strange_loops_tools
            register_strange_loops_tools(app)
            logger.info("Strange Loops Detector integrated")
        except Exception as e:
            logger.warning(f"Strange Loops Detector integration skipped: {e}")
    else:
        logger.info(skip_msg("strange_loops"))

    # Causal Inference Engine
    if should_load_module("causal_inference"):
        try:
            from causal_inference import register_causal_inference_tools
            register_causal_inference_tools(app)
            logger.info("Causal Inference Engine integrated")
        except Exception as e:
            logger.warning(f"Causal Inference Engine integration skipped: {e}")
    else:
        logger.info(skip_msg("causal_inference"))


def _register_holographic_tools(app, nmf_instance) -> None:
    """Register holographic memory tools (Phases 2-4)."""
    # Activation Field
    if should_load_module("activation_field_tools"):
        try:
            from activation_field_tools import register_activation_field_tools
            register_activation_field_tools(app)
            logger.info("Activation Field integrated")
        except Exception as e:
            logger.warning(f"Activation Field integration skipped: {e}")
    else:
        logger.info(skip_msg("activation_field_tools"))

    # Procedural Evolution
    if should_load_module("procedural_evolution_tools"):
        try:
            from procedural_evolution_tools import register_procedural_evolution_tools
            register_procedural_evolution_tools(app)
            logger.info("Procedural Evolution integrated")
        except Exception as e:
            logger.warning(f"Procedural Evolution integration skipped: {e}")
    else:
        logger.info(skip_msg("procedural_evolution_tools"))

    # Routing Learning
    if should_load_module("routing_learning_tools"):
        try:
            from routing_learning_tools import register_routing_learning_tools
            register_routing_learning_tools(app)
            logger.info("Routing Learning integrated")
        except Exception as e:
            logger.warning(f"Routing Learning integration skipped: {e}")
    else:
        logger.info(skip_msg("routing_learning_tools"))

    # Triple-Signal Search
    if should_load_module("triple_signal_tools"):
        try:
            from triple_signal_tools import register_triple_signal_tools
            register_triple_signal_tools(app, nmf_instance)
            logger.info("Triple-Signal Search integrated")
        except Exception as e:
            logger.warning(f"Triple-Signal Search integration skipped: {e}")
    else:
        logger.info(skip_msg("triple_signal_tools"))

    # Manifold Working Memory
    if should_load_module("manifold_working_memory_tools"):
        try:
            from manifold_working_memory_tools import register_manifold_working_memory_tools
            register_manifold_working_memory_tools(app)
            logger.info("Manifold Working Memory integrated")
        except Exception as e:
            logger.warning(f"Manifold Working Memory integration skipped: {e}")
    else:
        logger.info(skip_msg("manifold_working_memory_tools"))


def initialize_nmf():
    """Initialize Neural Memory Fabric for RAG tools."""
    try:
        from neural_memory_fabric import get_nmf
        nmf_instance = asyncio.run(get_nmf())
        logger.info("Neural Memory Fabric initialized for RAG")
        return nmf_instance
    except Exception as e:
        logger.warning(f"NMF initialization skipped: {e}")
        return None
