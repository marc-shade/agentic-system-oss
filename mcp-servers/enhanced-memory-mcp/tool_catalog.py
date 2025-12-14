#!/usr/bin/env python3
"""
Tool Catalog for Advanced Tool Use Pattern
Based on Anthropic's recommended patterns (Nov 2025)

This implements:
1. Tool categorization (HOT/WARM/COLD tiers)
2. Tool search with semantic matching
3. Deferred loading configuration
4. Usage examples for key tools

Token Optimization:
- HOT tools: Always loaded (~8-10 tools, ~2k tokens)
- WARM tools: Loaded on category match (~20 tools)
- COLD tools: Loaded on specific search (~100+ tools)
- Expected reduction: 77k -> 8.7k tokens (89% reduction)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum
import json

class ToolTier(Enum):
    HOT = "hot"      # Always loaded - most critical/common
    WARM = "warm"    # Loaded on category match
    COLD = "cold"    # Loaded only on specific search

@dataclass
class ToolDefinition:
    """Complete tool definition with metadata for search"""
    name: str
    description: str
    tier: ToolTier
    category: str
    subcategory: str = ""
    keywords: List[str] = field(default_factory=list)
    example: Optional[Dict] = None
    parameters: List[str] = field(default_factory=list)
    module: str = ""

    def to_search_text(self) -> str:
        """Generate searchable text for this tool"""
        parts = [
            self.name,
            self.description,
            self.category,
            self.subcategory,
            " ".join(self.keywords)
        ]
        return " ".join(parts).lower()

# =============================================================================
# TOOL CATALOG - Complete registry of all enhanced-memory tools
# =============================================================================

TOOL_CATALOG: Dict[str, ToolDefinition] = {
    # =========================================================================
    # HOT TIER - Always Loaded (~10 tools, most critical)
    # =========================================================================

    "create_entities": ToolDefinition(
        name="create_entities",
        description="Create entities with compression, storage, automatic versioning, and contextual enrichment",
        tier=ToolTier.HOT,
        category="memory",
        subcategory="core",
        keywords=["create", "store", "save", "add", "memory", "entity", "knowledge"],
        parameters=["entities"],
        module="server",
        example={
            "description": "Store a new concept learned during research",
            "input": {
                "entities": [{
                    "name": "async_await_pattern",
                    "entityType": "concept",
                    "observations": [
                        "async/await provides cleaner syntax than callbacks",
                        "Use for I/O-bound operations, not CPU-bound"
                    ]
                }]
            },
            "output": {"created": 1, "entity_ids": [42]}
        }
    ),

    "search_nodes": ToolDefinition(
        name="search_nodes",
        description="Search for entities by name or type with automatic version history",
        tier=ToolTier.HOT,
        category="memory",
        subcategory="retrieval",
        keywords=["search", "find", "query", "lookup", "retrieve", "memory"],
        parameters=["query", "limit"],
        module="server",
        example={
            "description": "Find all memories about Python patterns",
            "input": {"query": "python design patterns", "limit": 10},
            "output": {"results": [{"name": "singleton_pattern", "relevance": 0.95}]}
        }
    ),

    "get_memory_status": ToolDefinition(
        name="get_memory_status",
        description="Get overall memory system status and statistics",
        tier=ToolTier.HOT,
        category="memory",
        subcategory="system",
        keywords=["status", "health", "stats", "statistics", "system"],
        parameters=[],
        module="server"
    ),

    "execute_code": ToolDefinition(
        name="execute_code",
        description="Execute Python code in secure sandbox with API access for batch operations",
        tier=ToolTier.HOT,
        category="execution",
        subcategory="sandbox",
        keywords=["code", "execute", "run", "python", "script", "batch", "programmatic"],
        parameters=["code", "context_vars"],
        module="server",
        example={
            "description": "Batch search and filter memories programmatically",
            "input": {
                "code": """
results = search_nodes("optimization", limit=100)
high_conf = filter_by_confidence(results, 0.8)
result = summarize_results(high_conf)
"""
            },
            "output": {"success": True, "result": {"count": 15, "summary": "..."}}
        }
    ),

    "nmf_recall": ToolDefinition(
        name="nmf_recall",
        description="Retrieve memories from Neural Memory Fabric with semantic, graph, temporal, or hybrid modes",
        tier=ToolTier.HOT,
        category="memory",
        subcategory="retrieval",
        keywords=["recall", "retrieve", "semantic", "neural", "memory", "search"],
        parameters=["query", "mode", "agent_id", "limit"],
        module="nmf_tools"
    ),

    "nmf_remember": ToolDefinition(
        name="nmf_remember",
        description="Store a new memory in the Neural Memory Fabric",
        tier=ToolTier.HOT,
        category="memory",
        subcategory="core",
        keywords=["remember", "store", "save", "neural", "memory"],
        parameters=["content", "agent_id", "tags", "metadata"],
        module="nmf_tools"
    ),

    "add_episode": ToolDefinition(
        name="add_episode",
        description="Add an episode to episodic memory (experiences and events)",
        tier=ToolTier.HOT,
        category="memory",
        subcategory="episodic",
        keywords=["episode", "event", "experience", "log", "record"],
        parameters=["event_type", "episode_data", "significance_score"],
        module="agi_tools"
    ),

    "search_with_reranking": ToolDefinition(
        name="search_with_reranking",
        description="Search with cross-encoder re-ranking for improved precision (+40-55%)",
        tier=ToolTier.HOT,
        category="memory",
        subcategory="retrieval",
        keywords=["search", "rerank", "precision", "accuracy", "rag"],
        parameters=["query", "limit", "over_retrieve_factor"],
        module="reranking_tools"
    ),

    "cluster_brain_status": ToolDefinition(
        name="cluster_brain_status",
        description="Get unified cluster brain status - knowledge, goals, learnings across all nodes",
        tier=ToolTier.HOT,
        category="cluster",
        subcategory="status",
        keywords=["cluster", "status", "brain", "nodes", "health"],
        parameters=[],
        module="cluster_brain_tools"
    ),

    "record_action_outcome": ToolDefinition(
        name="record_action_outcome",
        description="Record an action and its outcome for learning",
        tier=ToolTier.HOT,
        category="learning",
        subcategory="action_tracking",
        keywords=["action", "outcome", "learn", "record", "track"],
        parameters=["action_type", "action_description", "expected_result", "actual_result", "success_score"],
        module="agi_tools"
    ),

    # =========================================================================
    # WARM TIER - Loaded on category match (~30 tools)
    # =========================================================================

    # Memory Management (WARM)
    "memory_diff": ToolDefinition(
        name="memory_diff",
        description="Get diff between two versions of a memory",
        tier=ToolTier.WARM,
        category="memory",
        subcategory="versioning",
        keywords=["diff", "compare", "version", "history", "change"],
        parameters=["entity_name", "version1", "version2"],
        module="server"
    ),

    "memory_revert": ToolDefinition(
        name="memory_revert",
        description="Revert a memory to a specific version",
        tier=ToolTier.WARM,
        category="memory",
        subcategory="versioning",
        keywords=["revert", "restore", "rollback", "version", "undo"],
        parameters=["entity_name", "version"],
        module="server"
    ),

    "memory_branch": ToolDefinition(
        name="memory_branch",
        description="Create a branch of a memory for experimentation",
        tier=ToolTier.WARM,
        category="memory",
        subcategory="versioning",
        keywords=["branch", "fork", "experiment", "clone"],
        parameters=["entity_name", "branch_name", "description"],
        module="server"
    ),

    "detect_memory_conflicts": ToolDefinition(
        name="detect_memory_conflicts",
        description="Detect duplicate or conflicting memories",
        tier=ToolTier.WARM,
        category="memory",
        subcategory="maintenance",
        keywords=["conflict", "duplicate", "detect", "cleanup"],
        parameters=["threshold"],
        module="server"
    ),

    # Cluster Brain (WARM)
    "cluster_add_knowledge": ToolDefinition(
        name="cluster_add_knowledge",
        description="Add knowledge to the shared cluster brain - accessible to ALL nodes",
        tier=ToolTier.WARM,
        category="cluster",
        subcategory="knowledge",
        keywords=["cluster", "knowledge", "share", "add", "brain"],
        parameters=["concept", "category", "content", "confidence"],
        module="cluster_brain_tools"
    ),

    "cluster_query_knowledge": ToolDefinition(
        name="cluster_query_knowledge",
        description="Query the shared cluster knowledge base",
        tier=ToolTier.WARM,
        category="cluster",
        subcategory="knowledge",
        keywords=["cluster", "query", "knowledge", "search", "brain"],
        parameters=["query", "category", "limit"],
        module="cluster_brain_tools"
    ),

    "cluster_add_goal": ToolDefinition(
        name="cluster_add_goal",
        description="Add a cluster-wide goal that all nodes work toward",
        tier=ToolTier.WARM,
        category="cluster",
        subcategory="goals",
        keywords=["cluster", "goal", "objective", "task", "assign"],
        parameters=["goal", "description", "priority", "assigned_nodes"],
        module="cluster_brain_tools"
    ),

    "cluster_add_learning": ToolDefinition(
        name="cluster_add_learning",
        description="Share a learning with the entire cluster",
        tier=ToolTier.WARM,
        category="cluster",
        subcategory="learning",
        keywords=["cluster", "learning", "share", "insight", "lesson"],
        parameters=["learning", "category", "source_task", "success_score"],
        module="cluster_brain_tools"
    ),

    # AGI Core (WARM)
    "add_to_working_memory": ToolDefinition(
        name="add_to_working_memory",
        description="Add item to working memory (temporary, volatile storage)",
        tier=ToolTier.WARM,
        category="memory",
        subcategory="working",
        keywords=["working", "memory", "temporary", "context", "active"],
        parameters=["context_key", "content", "priority", "ttl_minutes"],
        module="agi_tools"
    ),

    "get_working_memory": ToolDefinition(
        name="get_working_memory",
        description="Get items from working memory",
        tier=ToolTier.WARM,
        category="memory",
        subcategory="working",
        keywords=["working", "memory", "get", "retrieve", "context"],
        parameters=["context_key", "limit"],
        module="agi_tools"
    ),

    "add_concept": ToolDefinition(
        name="add_concept",
        description="Add or update a concept in semantic memory (timeless knowledge)",
        tier=ToolTier.WARM,
        category="memory",
        subcategory="semantic",
        keywords=["concept", "semantic", "knowledge", "definition", "fact"],
        parameters=["concept_name", "concept_type", "definition", "related_concepts"],
        module="agi_tools"
    ),

    "get_agent_identity": ToolDefinition(
        name="get_agent_identity",
        description="Get persistent agent identity including skills, traits, beliefs, and stats",
        tier=ToolTier.WARM,
        category="agent",
        subcategory="identity",
        keywords=["agent", "identity", "skills", "traits", "personality"],
        parameters=["agent_id"],
        module="agi_tools"
    ),

    "start_session": ToolDefinition(
        name="start_session",
        description="Start a new session with context from previous session",
        tier=ToolTier.WARM,
        category="agent",
        subcategory="session",
        keywords=["session", "start", "context", "continuity"],
        parameters=["agent_id", "context_summary"],
        module="agi_tools"
    ),

    "get_similar_actions": ToolDefinition(
        name="get_similar_actions",
        description="Find similar past actions to learn from",
        tier=ToolTier.WARM,
        category="learning",
        subcategory="action_tracking",
        keywords=["similar", "action", "history", "learn", "pattern"],
        parameters=["action_type", "context", "limit"],
        module="agi_tools"
    ),

    # RAG Tools (WARM)
    "search_hybrid": ToolDefinition(
        name="search_hybrid",
        description="Search using hybrid BM25 + Vector search with RRF fusion (+20-30% recall)",
        tier=ToolTier.WARM,
        category="memory",
        subcategory="retrieval",
        keywords=["search", "hybrid", "bm25", "vector", "fusion", "rag"],
        parameters=["query", "limit", "score_threshold"],
        module="hybrid_search_tools"
    ),

    "search_with_query_expansion": ToolDefinition(
        name="search_with_query_expansion",
        description="Search using query expansion for broader coverage (+15-25% recall)",
        tier=ToolTier.WARM,
        category="memory",
        subcategory="retrieval",
        keywords=["search", "query", "expansion", "synonym", "broader"],
        parameters=["query", "max_expansions", "strategies", "limit"],
        module="query_expansion_tools"
    ),

    "search_with_multi_query": ToolDefinition(
        name="search_with_multi_query",
        description="Search using multi-query RAG for comprehensive coverage (+20-30%)",
        tier=ToolTier.WARM,
        category="memory",
        subcategory="retrieval",
        keywords=["search", "multi", "query", "perspective", "comprehensive"],
        parameters=["query", "perspective_types", "limit"],
        module="multi_query_rag_tools"
    ),

    # ART (Adaptive Resonance Theory) Tools (WARM)
    "art_learn": ToolDefinition(
        name="art_learn",
        description="Learn a new pattern using Fuzzy ART - online learning without catastrophic forgetting",
        tier=ToolTier.WARM,
        category="learning",
        subcategory="art_clustering",
        keywords=["art", "learn", "pattern", "cluster", "online", "resonance", "neural"],
        parameters=["data", "metadata", "vigilance"],
        module="art_tools",
        example={
            "description": "Learn a pattern from embedding vector",
            "input": {"data": [0.1, 0.2, 0.3, 0.4], "vigilance": 0.75},
            "output": {"category_id": "cat_001", "is_new_category": True, "match_score": 0.0}
        }
    ),

    "art_classify": ToolDefinition(
        name="art_classify",
        description="Classify a pattern without learning (inference only)",
        tier=ToolTier.WARM,
        category="learning",
        subcategory="art_clustering",
        keywords=["art", "classify", "pattern", "inference", "category", "match"],
        parameters=["data", "vigilance"],
        module="art_tools"
    ),

    "art_adjust_vigilance": ToolDefinition(
        name="art_adjust_vigilance",
        description="Adjust THE KEY DIAL - vigilance controls category granularity (0.9=fine, 0.3=coarse)",
        tier=ToolTier.WARM,
        category="learning",
        subcategory="art_clustering",
        keywords=["art", "vigilance", "adjust", "granularity", "control", "dial"],
        parameters=["vigilance", "instance"],
        module="art_tools",
        example={
            "description": "Set vigilance for fine-grained categories",
            "input": {"vigilance": 0.9, "instance": "main"},
            "output": {"old_vigilance": 0.75, "new_vigilance": 0.9, "effect": "Very fine-grained"}
        }
    ),

    "art_get_categories": ToolDefinition(
        name="art_get_categories",
        description="Get all learned ART categories with their prototypes and stats",
        tier=ToolTier.WARM,
        category="learning",
        subcategory="art_clustering",
        keywords=["art", "categories", "clusters", "prototypes", "list", "stats"],
        parameters=[],
        module="art_tools"
    ),

    "art_hybrid_learn": ToolDefinition(
        name="art_hybrid_learn",
        description="Learn from transformer embeddings using ART Hybrid - combines semantic embeddings with ART clustering",
        tier=ToolTier.WARM,
        category="learning",
        subcategory="art_clustering",
        keywords=["art", "hybrid", "embedding", "transformer", "learn", "cluster"],
        parameters=["embedding", "content", "metadata"],
        module="art_tools"
    ),

    "art_hybrid_find_similar": ToolDefinition(
        name="art_hybrid_find_similar",
        description="Find similar ART categories for an embedding without learning",
        tier=ToolTier.WARM,
        category="learning",
        subcategory="art_clustering",
        keywords=["art", "hybrid", "similar", "find", "match", "embedding"],
        parameters=["embedding", "top_k"],
        module="art_tools"
    ),

    "art_get_stats": ToolDefinition(
        name="art_get_stats",
        description="Get comprehensive ART system statistics",
        tier=ToolTier.WARM,
        category="learning",
        subcategory="art_clustering",
        keywords=["art", "stats", "statistics", "status", "system"],
        parameters=[],
        module="art_tools"
    ),

    # =========================================================================
    # COLD TIER - Loaded only on specific search (~90+ tools)
    # =========================================================================

    # Belief Tracking (COLD)
    "record_belief_state": ToolDefinition(
        name="record_belief_state",
        description="Record an agent's belief state with probability and evidence (Stanford Research)",
        tier=ToolTier.COLD,
        category="cognition",
        subcategory="beliefs",
        keywords=["belief", "probability", "evidence", "track", "state"],
        parameters=["belief_statement", "probability", "belief_category", "confidence"],
        module="agi_tools"
    ),

    "update_belief_probability": ToolDefinition(
        name="update_belief_probability",
        description="Update belief probability based on new evidence",
        tier=ToolTier.COLD,
        category="cognition",
        subcategory="beliefs",
        keywords=["belief", "update", "probability", "evidence", "revise"],
        parameters=["belief_id", "new_probability", "revision_trigger", "evidence_provided"],
        module="agi_tools"
    ),

    "analyze_belief_rigidity": ToolDefinition(
        name="analyze_belief_rigidity",
        description="Analyze how rigid or flexible an agent's beliefs are",
        tier=ToolTier.COLD,
        category="cognition",
        subcategory="beliefs",
        keywords=["belief", "rigidity", "flexibility", "analysis", "metacognition"],
        parameters=["agent_id", "belief_id", "time_window_hours"],
        module="agi_tools"
    ),

    "create_counterfactual_scenario": ToolDefinition(
        name="create_counterfactual_scenario",
        description="Create a counterfactual scenario to test belief flexibility",
        tier=ToolTier.COLD,
        category="cognition",
        subcategory="beliefs",
        keywords=["counterfactual", "scenario", "belief", "test", "flexibility"],
        parameters=["scenario_name", "scenario_description", "target_belief_id"],
        module="agi_tools"
    ),

    # Causal Reasoning (COLD)
    "create_causal_link": ToolDefinition(
        name="create_causal_link",
        description="Create a causal link between two entities",
        tier=ToolTier.COLD,
        category="cognition",
        subcategory="causality",
        keywords=["causal", "link", "cause", "effect", "relationship"],
        parameters=["cause_entity_id", "effect_entity_id", "relationship_type", "strength"],
        module="agi_tools"
    ),

    "get_causal_chain": ToolDefinition(
        name="get_causal_chain",
        description="Get causal chain from an entity (forward or backward)",
        tier=ToolTier.COLD,
        category="cognition",
        subcategory="causality",
        keywords=["causal", "chain", "trace", "cause", "effect"],
        parameters=["entity_id", "direction", "depth", "min_strength"],
        module="agi_tools"
    ),

    "predict_outcome": ToolDefinition(
        name="predict_outcome",
        description="Predict likely outcomes of an action based on causal history",
        tier=ToolTier.COLD,
        category="cognition",
        subcategory="causality",
        keywords=["predict", "outcome", "causal", "forecast", "action"],
        parameters=["action_entity_id", "context"],
        module="agi_tools"
    ),

    # Emotional/Salience (COLD)
    "tag_entity_emotion": ToolDefinition(
        name="tag_entity_emotion",
        description="Tag an entity with emotional metadata (valence, arousal, dominance)",
        tier=ToolTier.COLD,
        category="memory",
        subcategory="emotional",
        keywords=["emotion", "tag", "valence", "arousal", "salience"],
        parameters=["entity_id", "valence", "arousal", "dominance", "primary_emotion"],
        module="agi_tools"
    ),

    "search_by_emotion": ToolDefinition(
        name="search_by_emotion",
        description="Search memories by emotional criteria",
        tier=ToolTier.COLD,
        category="memory",
        subcategory="emotional",
        keywords=["search", "emotion", "feeling", "valence", "mood"],
        parameters=["emotion_filter", "limit"],
        module="agi_tools"
    ),

    # Symbolic Regression (COLD)
    "pysr_create_dataset": ToolDefinition(
        name="pysr_create_dataset",
        description="Create a dataset for PySR symbolic regression",
        tier=ToolTier.COLD,
        category="learning",
        subcategory="symbolic_regression",
        keywords=["pysr", "dataset", "symbolic", "regression", "formula"],
        parameters=["name", "X", "y", "description"],
        module="pysr_tools"
    ),

    "pysr_run_regression": ToolDefinition(
        name="pysr_run_regression",
        description="Run PySR symbolic regression to discover equations",
        tier=ToolTier.COLD,
        category="learning",
        subcategory="symbolic_regression",
        keywords=["pysr", "regression", "equation", "discover", "formula"],
        parameters=["dataset_name", "config"],
        module="pysr_tools"
    ),

    # Letta Memory Blocks (COLD)
    "nmf_open_block": ToolDefinition(
        name="nmf_open_block",
        description="Load a memory block into context (Letta-style)",
        tier=ToolTier.COLD,
        category="memory",
        subcategory="letta",
        keywords=["block", "letta", "context", "load", "open"],
        parameters=["agent_id", "block_name"],
        module="letta_tools"
    ),

    "nmf_edit_block": ToolDefinition(
        name="nmf_edit_block",
        description="Edit a memory block (Letta-style)",
        tier=ToolTier.COLD,
        category="memory",
        subcategory="letta",
        keywords=["block", "letta", "edit", "update", "modify"],
        parameters=["agent_id", "block_name", "new_value"],
        module="letta_tools"
    ),

    # SAFLA Tools (COLD)
    "safla_store_vector": ToolDefinition(
        name="safla_store_vector",
        description="Store vector in SAFLA hybrid memory architecture",
        tier=ToolTier.COLD,
        category="memory",
        subcategory="safla",
        keywords=["safla", "vector", "store", "embedding", "hybrid"],
        parameters=["content", "metadata", "namespace"],
        module="safla_tools"
    ),

    "safla_search": ToolDefinition(
        name="safla_search",
        description="Search SAFLA memory with hybrid retrieval",
        tier=ToolTier.COLD,
        category="memory",
        subcategory="safla",
        keywords=["safla", "search", "hybrid", "retrieval", "vector"],
        parameters=["query", "limit", "namespace"],
        module="safla_tools"
    ),

    # Consolidation (COLD)
    "run_full_consolidation": ToolDefinition(
        name="run_full_consolidation",
        description="Run all consolidation processes (sleep-like consolidation)",
        tier=ToolTier.COLD,
        category="maintenance",
        subcategory="consolidation",
        keywords=["consolidation", "sleep", "memory", "compress", "optimize"],
        parameters=["time_window_hours"],
        module="agi_tools"
    ),

    "run_pattern_extraction": ToolDefinition(
        name="run_pattern_extraction",
        description="Extract patterns from recent episodic memories",
        tier=ToolTier.COLD,
        category="maintenance",
        subcategory="consolidation",
        keywords=["pattern", "extract", "episodic", "consolidate"],
        parameters=["time_window_hours", "min_pattern_frequency"],
        module="agi_tools"
    ),

    "run_causal_discovery": ToolDefinition(
        name="run_causal_discovery",
        description="Discover causal relationships from recent action outcomes",
        tier=ToolTier.COLD,
        category="maintenance",
        subcategory="consolidation",
        keywords=["causal", "discovery", "learn", "relationship", "pattern"],
        parameters=["time_window_hours", "min_confidence"],
        module="agi_tools"
    ),

    # Self-Improvement (COLD)
    "start_improvement_cycle": ToolDefinition(
        name="start_improvement_cycle",
        description="Start a new self-improvement cycle (performance, knowledge, reasoning, meta)",
        tier=ToolTier.COLD,
        category="learning",
        subcategory="self_improvement",
        keywords=["improvement", "cycle", "self", "optimize", "enhance"],
        parameters=["agent_id", "cycle_type", "improvement_goals"],
        module="agi_tools"
    ),

    "validate_improvements": ToolDefinition(
        name="validate_improvements",
        description="Validate that improvements met success criteria",
        tier=ToolTier.COLD,
        category="learning",
        subcategory="self_improvement",
        keywords=["validate", "improvement", "success", "criteria", "check"],
        parameters=["cycle_id", "new_metrics", "success_criteria"],
        module="agi_tools"
    ),

    # Knowledge Graph (COLD)
    "calculate_centrality_scores": ToolDefinition(
        name="calculate_centrality_scores",
        description="Calculate graph centrality scores for knowledge graph nodes (PageRank, degree, betweenness)",
        tier=ToolTier.COLD,
        category="cognition",
        subcategory="knowledge_graph",
        keywords=["centrality", "pagerank", "graph", "importance", "network"],
        parameters=["limit"],
        module="mirror_mind_enhancements"
    ),

    "get_cognitive_trajectory": ToolDefinition(
        name="get_cognitive_trajectory",
        description="Get cognitive evolution trajectory for a concept over time",
        tier=ToolTier.COLD,
        category="cognition",
        subcategory="knowledge_graph",
        keywords=["trajectory", "evolution", "concept", "history", "temporal"],
        parameters=["entity_name"],
        module="mirror_mind_enhancements"
    ),

    "add_to_dual_manifold": ToolDefinition(
        name="add_to_dual_manifold",
        description="Add knowledge to dual manifold architecture (individual or collective)",
        tier=ToolTier.COLD,
        category="cognition",
        subcategory="knowledge_graph",
        keywords=["manifold", "dual", "individual", "collective", "knowledge"],
        parameters=["content", "manifold", "knowledge_type", "domain"],
        module="mirror_mind_enhancements"
    ),

    # Metacognition (COLD)
    "record_metacognitive_state": ToolDefinition(
        name="record_metacognitive_state",
        description="Record current meta-cognitive awareness state",
        tier=ToolTier.COLD,
        category="cognition",
        subcategory="metacognition",
        keywords=["metacognition", "awareness", "self", "state", "cognitive"],
        parameters=["agent_id", "self_awareness", "knowledge_awareness", "process_awareness"],
        module="agi_tools"
    ),

    "identify_knowledge_gap": ToolDefinition(
        name="identify_knowledge_gap",
        description="Identify and record a knowledge gap for targeted learning",
        tier=ToolTier.COLD,
        category="cognition",
        subcategory="metacognition",
        keywords=["knowledge", "gap", "identify", "learning", "unknown"],
        parameters=["agent_id", "domain", "gap_description", "gap_type", "severity"],
        module="agi_tools"
    ),

    "track_reasoning_strategy": ToolDefinition(
        name="track_reasoning_strategy",
        description="Track usage and effectiveness of reasoning strategy",
        tier=ToolTier.COLD,
        category="cognition",
        subcategory="metacognition",
        keywords=["reasoning", "strategy", "track", "effectiveness", "deductive"],
        parameters=["agent_id", "strategy_name", "strategy_type", "success", "confidence"],
        module="agi_tools"
    ),

    # Cluster Beliefs (COLD)
    "create_cluster_belief_block": ToolDefinition(
        name="create_cluster_belief_block",
        description="Create shared memory block for cluster-wide beliefs",
        tier=ToolTier.COLD,
        category="cluster",
        subcategory="beliefs",
        keywords=["cluster", "belief", "shared", "block", "consensus"],
        parameters=["belief_domain", "initial_beliefs", "consensus_threshold"],
        module="agi_tools"
    ),

    "detect_cluster_belief_divergence": ToolDefinition(
        name="detect_cluster_belief_divergence",
        description="Detect when agents hold significantly different beliefs",
        tier=ToolTier.COLD,
        category="cluster",
        subcategory="beliefs",
        keywords=["cluster", "belief", "divergence", "detect", "difference"],
        parameters=["cluster_id", "threshold"],
        module="agi_tools"
    ),

    # Association Network (COLD)
    "create_association": ToolDefinition(
        name="create_association",
        description="Create associative link between two entities (semantic, temporal, causal)",
        tier=ToolTier.COLD,
        category="memory",
        subcategory="associations",
        keywords=["association", "link", "connect", "semantic", "temporal"],
        parameters=["entity_a_id", "entity_b_id", "association_type", "strength"],
        module="agi_tools"
    ),

    "spread_activation": ToolDefinition(
        name="spread_activation",
        description="Spread activation from source entity through associative network",
        tier=ToolTier.COLD,
        category="memory",
        subcategory="associations",
        keywords=["activation", "spread", "associative", "recall", "network"],
        parameters=["source_entity_id", "initial_activation", "max_hops"],
        module="agi_tools"
    ),

    # Skills/Procedural (COLD)
    "add_skill": ToolDefinition(
        name="add_skill",
        description="Add or update a skill in procedural memory (how-to knowledge)",
        tier=ToolTier.COLD,
        category="memory",
        subcategory="procedural",
        keywords=["skill", "procedure", "how-to", "add", "learn"],
        parameters=["skill_name", "skill_category", "procedure_steps"],
        module="agi_tools"
    ),

    "record_skill_execution": ToolDefinition(
        name="record_skill_execution",
        description="Record skill execution for learning and improvement",
        tier=ToolTier.COLD,
        category="memory",
        subcategory="procedural",
        keywords=["skill", "execution", "record", "learn", "improve"],
        parameters=["skill_name", "success", "execution_time_ms"],
        module="agi_tools"
    ),

    # Agent Coordination (COLD)
    "send_coordination_message": ToolDefinition(
        name="send_coordination_message",
        description="Send coordination message to another agent",
        tier=ToolTier.COLD,
        category="cluster",
        subcategory="coordination",
        keywords=["coordination", "message", "send", "agent", "communicate"],
        parameters=["sender_agent_id", "recipient_agent_id", "message_type", "subject", "content"],
        module="agi_tools"
    ),

    "receive_coordination_messages": ToolDefinition(
        name="receive_coordination_messages",
        description="Receive pending coordination messages",
        tier=ToolTier.COLD,
        category="cluster",
        subcategory="coordination",
        keywords=["coordination", "message", "receive", "pending", "agent"],
        parameters=["agent_id", "status"],
        module="agi_tools"
    ),
}

# =============================================================================
# CATEGORY MAPPINGS - For efficient tier loading
# =============================================================================

CATEGORIES = {
    "memory": ["core", "retrieval", "versioning", "maintenance", "working", "semantic",
               "episodic", "emotional", "letta", "safla", "associations", "procedural"],
    "cluster": ["status", "knowledge", "goals", "learning", "beliefs", "coordination"],
    "learning": ["action_tracking", "symbolic_regression", "self_improvement", "art_clustering"],
    "cognition": ["beliefs", "causality", "knowledge_graph", "metacognition"],
    "agent": ["identity", "session"],
    "execution": ["sandbox"],
    "maintenance": ["consolidation"],
}

# Tools that should ALWAYS be loaded regardless of search
ALWAYS_LOAD = {
    "create_entities",
    "search_nodes",
    "get_memory_status",
    "execute_code",
    "nmf_recall",
    "nmf_remember",
    "cluster_brain_status",
    "record_action_outcome",
    "search_with_reranking",
    "add_episode",
}

def get_tools_by_tier(tier: ToolTier) -> List[ToolDefinition]:
    """Get all tools in a specific tier"""
    return [t for t in TOOL_CATALOG.values() if t.tier == tier]

def get_tools_by_category(category: str) -> List[ToolDefinition]:
    """Get all tools in a specific category"""
    return [t for t in TOOL_CATALOG.values() if t.category == category]

def get_hot_tools() -> List[str]:
    """Get list of tool names that should always be loaded"""
    return list(ALWAYS_LOAD)

def get_tool_count_by_tier() -> Dict[str, int]:
    """Get count of tools in each tier"""
    return {
        "hot": len([t for t in TOOL_CATALOG.values() if t.tier == ToolTier.HOT]),
        "warm": len([t for t in TOOL_CATALOG.values() if t.tier == ToolTier.WARM]),
        "cold": len([t for t in TOOL_CATALOG.values() if t.tier == ToolTier.COLD]),
        "total": len(TOOL_CATALOG)
    }

if __name__ == "__main__":
    # Print catalog statistics
    counts = get_tool_count_by_tier()
    print(f"Tool Catalog Statistics:")
    print(f"  HOT:   {counts['hot']} tools (always loaded)")
    print(f"  WARM:  {counts['warm']} tools (category match)")
    print(f"  COLD:  {counts['cold']} tools (on-demand)")
    print(f"  TOTAL: {counts['total']} tools cataloged")
    print(f"\nCategories: {list(CATEGORIES.keys())}")
