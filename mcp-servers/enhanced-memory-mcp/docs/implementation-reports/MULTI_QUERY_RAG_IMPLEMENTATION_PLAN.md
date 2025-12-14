# Multi-Query RAG Implementation Plan

**Date**: November 9, 2025
**Status**: Ready for Implementation
**Tier**: RAG Tier 2 - Query Optimization (Strategy 2.2)
**Expected Timeline**: 3-4 hours
**Complexity**: Medium (5/10)

---

## Executive Summary

This implementation plan provides a step-by-step guide for implementing Multi-Query RAG (RAG Tier 2.2), building on the completed Query Expansion (Tier 2.1). The plan follows a test-driven development approach with clear checkpoints and verification criteria.

**Prerequisites**:
- ✅ Query Expansion (Tier 2.1) complete
- ✅ Technical specification complete
- ✅ Architecture design complete
- ✅ Hybrid search and re-ranking available

**Deliverables**:
1. Core implementation: `multi_query_rag_tools.py`
2. Unit test suite: `test_multi_query_rag.py`
3. Integration test suite: `test_multi_query_rag_mcp.py`
4. MCP server integration
5. Complete documentation

---

## Phase 1: Core Implementation (90 minutes)

### Step 1.1: Create File Structure (5 minutes)

**File**: `multi_query_rag_tools.py`

**Initial Structure**:
```python
"""
Multi-Query RAG Implementation - RAG Tier 2.2
Generates multiple query perspectives for comprehensive coverage
"""
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# Data models will be defined as dataclasses
# Components will be implemented as classes with async methods
# MCP tools will be registered with FastMCP framework
```

**Verification**: File created with imports and docstring

---

### Step 1.2: Implement Data Models (15 minutes)

**Component**: Data classes in `multi_query_rag_tools.py`

**Implementation Order**:

1. **Perspective** (5 minutes):
   - Fields: perspective_type (str), query (str), description (str), weight (float=1.0)
   - Represents a single query perspective (technical, user, or conceptual)

2. **SearchResult** (5 minutes):
   - Fields: id (str), content (str), score (float), metadata (dict), perspective (str)
   - Represents a single search result from one perspective

3. **FusedResult** (5 minutes):
   - Fields: id (str), content (str), rrf_score (float), perspective_scores (dict), contributing_perspectives (list), diversity_score (float), metadata (dict)
   - Represents a fused result after RRF combination

**Verification**: Run unit test for data model serialization

---

### Step 1.3: Implement PerspectiveGenerator (30 minutes)

**Component**: `PerspectiveGenerator` class

**Implementation Steps**:

1. **Initialization** (5 minutes):
   - Store NMF instance reference
   - Define perspective templates dictionary:
     - "technical": ["implementation details of {query}", "technical architecture for {query}", "how {query} works internally"]
     - "user": ["how to use {query}", "user guide for {query}", "practical application of {query}"]
     - "conceptual": ["concepts behind {query}", "theoretical foundation of {query}", "principles of {query}"]

2. **Template-Based Generation** (10 minutes):
   - Method: `generate_perspectives(query, perspective_types, max_perspectives)`
   - Algorithm:
     1. If perspective_types is None, use all three types (technical, user, conceptual)
     2. For each perspective type (up to max_perspectives):
        - Get templates for that type
        - Format first template with query
        - Create Perspective object with formatted query
     3. Return list of Perspective objects

3. **LLM-Based Generation (Future Enhancement)** (10 minutes):
   - Method: `llm_generate_perspectives(query, num_perspectives)`
   - Algorithm:
     1. Check if NMF instance available
     2. If not available, fall back to template-based generation
     3. If available (future): Use NMF's LLM to generate diverse perspectives
     4. Return list of Perspective objects

4. **Diversity Calculation** (5 minutes):
   - Method: `calculate_diversity(perspectives)`
   - Algorithm:
     1. Count unique perspective types in list
     2. Divide by maximum possible types (3)
     3. Return diversity score (0.0 to 1.0)

**Verification**: Unit test perspective generation with 3 perspectives

---

### Step 1.4: Implement MultiQueryExecutor (20 minutes)

**Component**: `MultiQueryExecutor` class

**Implementation Steps**:

1. **Initialization** (5 minutes):
   - Store NMF instance reference
   - This executor will coordinate parallel searches

2. **Parallel Search Execution** (15 minutes):
   - Method: `execute_parallel_searches(perspectives, limit, score_threshold)`
   - Algorithm:
     1. Define async function `search_perspective(perspective)`:
        - Import and use existing hybrid_search_tools.search_hybrid
        - Execute search with perspective's query
        - Convert results to SearchResult objects
        - Return tuple of (perspective_type, search_results)
        - Handle exceptions gracefully, return empty list on error
     2. Create tasks list for all perspectives
     3. Execute all tasks in parallel using asyncio.gather
     4. Convert results to dictionary {perspective_type: [SearchResult, ...]}
     5. Return results dictionary

**Verification**: Unit test parallel execution with 3 perspectives

---

### Step 1.5: Implement ResultFusionEngine (20 minutes)

**Component**: `ResultFusionEngine` class

**Implementation Steps**:

1. **Initialization** (5 minutes):
   - Store RRF constant k (default: 60)
   - This constant controls RRF score calculation

2. **RRF Score Calculation** (10 minutes):
   - Method: `calculate_rrf_score(results_by_perspective)`
   - Algorithm:
     1. Build doc_rankings dictionary {doc_id: {perspective: rank}}:
        - Iterate through each perspective's results
        - For each result, record its rank (1-based) in that perspective
     2. For each document in doc_rankings:
        - Calculate RRF score using formula: sum(1 / (k + rank)) for all perspectives
        - Get original result data from first perspective that found it
        - Create FusedResult with:
          - RRF score
          - Perspective scores from each contributing perspective
          - List of contributing perspectives
          - Diversity score (num_perspectives / total_perspectives)
          - Original metadata
     3. Return dictionary of {doc_id: FusedResult}

3. **Result Sorting and Limiting** (5 minutes):
   - Method: `fuse_and_rank(results_by_perspective, limit)`
   - Algorithm:
     1. Call calculate_rrf_score to get fused results
     2. Sort fused results by RRF score (descending)
     3. Return top-k results (limit)

**Verification**: Unit test RRF calculation with known rankings

---

## Phase 2: MCP Tool Integration (30 minutes)

### Step 2.1: Implement Main Search Tool (15 minutes)

**Tool**: `search_with_multi_query`

**Implementation**:
- Decorator: `@app.tool()`
- Parameters: query (str), perspective_types (optional list), max_perspectives (int=3), limit (int=10), score_threshold (optional float)
- Algorithm:
  1. Create PerspectiveGenerator and generate perspectives
  2. Create MultiQueryExecutor and execute parallel searches (over-retrieve by 2x for fusion)
  3. Create ResultFusionEngine and fuse results
  4. Calculate diversity score using generator
  5. Format and return response with:
     - Success status
     - Original query
     - List of perspectives generated
     - Count of results
     - Results with RRF scores, perspective scores, diversity scores
     - Metadata: strategy, num_perspectives, diversity_score, total_candidates, fusion_method
  6. Handle exceptions and return error response if needed

**Verification**: MCP tool callable, returns expected format

---

### Step 2.2: Implement Stats Tool (10 minutes)

**Tool**: `get_multi_query_stats`

**Implementation**:
- Decorator: `@app.tool()`
- No parameters
- Algorithm:
  1. Create PerspectiveGenerator instance
  2. Return dictionary with:
     - Status: "ready"
     - Available perspectives: ["technical", "user", "conceptual"]
     - Default max perspectives: 3
     - Fusion method: "rrf"
     - RRF constant: 60
     - LLM available: boolean (nmf is not None)
     - Templates per perspective: count from generator

**Verification**: Stats tool returns correct configuration

---

### Step 2.3: Implement Perspective Analysis Tool (5 minutes)

**Tool**: `analyze_query_perspectives`

**Implementation**:
- Decorator: `@app.tool()`
- Parameters: query (str), max_perspectives (int=3)
- Algorithm:
  1. Create PerspectiveGenerator
  2. Generate perspectives for query
  3. Calculate diversity score
  4. Return analysis without executing searches:
     - Success status
     - Original query
     - List of perspectives with type, query, description, weight
     - Diversity score
     - Analysis: num_perspectives, unique_types
  5. Handle exceptions and return error response if needed

**Verification**: Analysis tool returns perspectives without search

---

## Phase 3: Testing Suite (60 minutes)

### Step 3.1: Unit Tests (30 minutes)

**File**: `test_multi_query_rag.py`

**Test Cases** (10 total):

1. **test_perspective_generation** (5 minutes):
   - Test basic perspective generation for "system architecture"
   - Verify 3 perspectives created
   - Verify all 3 types present (technical, user, conceptual)
   - Verify all have query text

2. **test_perspective_types_selection** (5 minutes):
   - Test custom perspective type selection
   - Generate only technical and user perspectives
   - Verify correct types returned, max 2 perspectives

3. **test_diversity_calculation** (5 minutes):
   - Test diversity score with 3 unique types (should be 1.0)
   - Test diversity score with 1 type (should be 0.0)
   - Test diversity score with 2 types (should be 0.67)

4. **test_rrf_score_calculation** (5 minutes):
   - Create known rankings: doc1 at rank 1 and 2 in two perspectives
   - Calculate expected RRF score manually
   - Verify calculated score matches expected
   - Verify contributing perspectives tracked correctly

5. **test_max_perspectives_limit** (3 minutes):
   - Test that max_perspectives parameter is respected
   - Try with max 1, 2, 3, and 5 (should cap at available)

6. **test_empty_query** (2 minutes):
   - Test behavior with empty string
   - Verify graceful handling

7. **test_parallel_execution** (3 minutes):
   - Mock async search function
   - Verify all searches execute in parallel (asyncio.gather)
   - Verify results collected correctly

8. **test_result_fusion** (3 minutes):
   - Create multiple result sets
   - Verify fusion combines correctly
   - Verify deduplication by ID

9. **test_error_handling** (2 minutes):
   - Test with failing search
   - Verify graceful degradation

10. **test_metadata** (2 minutes):
    - Verify all metadata fields present
    - Verify metadata accuracy

**Verification**: All unit tests pass

---

### Step 3.2: Integration Tests (30 minutes)

**File**: `test_multi_query_rag_mcp.py`

**Test Cases** (5 total):

1. **test_multi_query_stats_tool** (5 minutes):
   - Call MCP stats tool
   - Verify status "ready"
   - Verify all expected fields present
   - Verify configuration correct

2. **test_analyze_perspectives_tool** (5 minutes):
   - Call analysis tool with "voice communication"
   - Verify 3 perspectives generated
   - Verify diversity score in valid range (0.0-1.0)
   - Verify no search executed (analysis only)

3. **test_multi_query_search** (10 minutes):
   - Call search tool with "agent workflow"
   - Verify success status
   - Verify 3 perspectives generated
   - Verify results returned (max 10)
   - Verify all results have RRF scores
   - Verify fusion method "rrf" in metadata

4. **test_custom_perspectives** (5 minutes):
   - Call search with custom perspective types (technical, conceptual only)
   - Verify only 2 perspectives generated
   - Verify correct types used

5. **test_coverage_improvement** (5 minutes):
   - Execute baseline single query search
   - Execute multi-query RAG search with same query
   - Verify multi-query has more total candidates
   - Verify all results have diversity scores
   - Expect +20-30% improvement in coverage

**Verification**: All integration tests pass

---

## Phase 4: Server Integration (15 minutes)

### Step 4.1: Register Tools in server.py (10 minutes)

**File**: `server.py` (add after query expansion registration, around line 1010)

**Code**:
```python
# Register Multi-Query RAG tools (RAG Tier 2 Strategy) - Query Optimization
if nmf_instance:
    try:
        from multi_query_rag_tools import register_multi_query_rag_tools
        register_multi_query_rag_tools(app, nmf_instance)
        logger.info("✅ Multi-Query RAG (RAG Tier 2) integrated - Expected +20-30% coverage")
    except Exception as e:
        logger.warning(f"⚠️  Multi-Query RAG integration skipped: {e}")
else:
    logger.warning("⚠️  Multi-Query RAG skipped: NMF not available")
```

**Verification**: Server starts successfully, logs show integration

---

### Step 4.2: Verify MCP Tool Registration (5 minutes)

**Steps**:
1. Restart MCP server
2. Check server logs for "✅ Multi-Query RAG (RAG Tier 2) integrated"
3. Verify 3 new tools available:
   - `search_with_multi_query`
   - `get_multi_query_stats`
   - `analyze_query_perspectives`

**Verification**: All 3 tools registered and callable

---

## Phase 5: Documentation (45 minutes)

### Step 5.1: Implementation Documentation (20 minutes)

**File**: `MULTI_QUERY_RAG_IMPLEMENTATION.md`

**Sections**:
1. Executive Summary
2. Architecture Overview
3. Implementation Details
4. API Reference
5. Usage Examples
6. Performance Metrics
7. Testing Results
8. Integration Guide
9. Troubleshooting

**Verification**: Complete documentation created

---

### Step 5.2: Session Summary (15 minutes)

**File**: `SESSION_SUMMARY_MULTI_QUERY_RAG.md`

**Sections**:
1. Work Completed
2. Files Created/Modified
3. Test Results
4. Performance Metrics
5. Integration Status
6. Next Steps

**Verification**: Session summary complete

---

### Step 5.3: Update Status Documents (10 minutes)

**Files to Update**:

1. **`RAG_IMPLEMENTATION_STATUS.md`**:
   - Update progress: 3 of 11 strategies (27% complete)
   - Mark Multi-Query RAG as COMPLETE
   - Update Tier 2 to 100% (2/2 strategies)

2. **`COMPLETE_RAG_ROADMAP.md`**:
   - Update Phase 2 status to "COMPLETE"
   - Confirm Phase 3 timeline

**Verification**: Status documents updated

---

## Checkpoints and Verification

### Checkpoint 1: Core Implementation Complete
- ✅ All data models implemented
- ✅ PerspectiveGenerator working
- ✅ MultiQueryExecutor working
- ✅ ResultFusionEngine working
- ✅ Unit tests passing

### Checkpoint 2: MCP Integration Complete
- ✅ All 3 tools registered
- ✅ Server starts successfully
- ✅ Tools callable via MCP
- ✅ Integration tests passing

### Checkpoint 3: Documentation Complete
- ✅ Implementation doc created
- ✅ Session summary created
- ✅ Status documents updated
- ✅ API reference complete

### Checkpoint 4: Production Ready
- ✅ All tests passing (15+ tests)
- ✅ No errors in logs
- ✅ Performance acceptable (<600ms)
- ✅ Coverage improvement verified (+20-30%)

---

## Risk Mitigation

### Risk 1: Perspective Quality
**Mitigation**: Start with template-based, enhance with LLM later
**Fallback**: Use simple rephrasing if templates fail

### Risk 2: RRF Parameter Tuning
**Mitigation**: Use standard k=60, document tuning options
**Fallback**: Provide configurable k parameter

### Risk 3: Performance
**Mitigation**: Parallel execution, limit over-retrieval to 2x
**Fallback**: Reduce max_perspectives if latency too high

### Risk 4: Integration Conflicts
**Mitigation**: Additive only, no modifications to existing tools
**Fallback**: Can disable via server config

---

## Dependencies

### Required Components:
- ✅ NMF instance (Neural Memory Fabric)
- ✅ Qdrant vector database
- ✅ Hybrid search (from RAG Tier 1)
- ✅ FastMCP server framework
- ✅ asyncio for parallel execution

### Optional Enhancements:
- ⚪ Ollama LLM (for better perspective generation)
- ⚪ Re-ranking (can chain after multi-query)

---

## Success Criteria

### Functional Requirements:
- ✅ Generates 3 perspectives (technical, user, conceptual)
- ✅ Executes parallel searches (<600ms total)
- ✅ Fuses results using RRF
- ✅ Returns top-k with diversity scores
- ✅ All MCP tools working

### Performance Requirements:
- ✅ Total latency ≤600ms (3 parallel searches @ 200ms each)
- ✅ Coverage improvement +20-30% over single query
- ✅ Diversity score >0.7 for varied queries

### Quality Requirements:
- ✅ 100% test coverage (15+ tests)
- ✅ Complete documentation
- ✅ Production-ready code
- ✅ No breaking changes

---

## Timeline

**Total Estimated Time**: 3-4 hours

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Phase 1: Core Implementation | 90 min | 1.5 hours |
| Phase 2: MCP Integration | 30 min | 2.0 hours |
| Phase 3: Testing Suite | 60 min | 3.0 hours |
| Phase 4: Server Integration | 15 min | 3.25 hours |
| Phase 5: Documentation | 45 min | 4.0 hours |

**Buffer**: +30 minutes for debugging and refinement

---

## Post-Implementation

### Immediate Next Steps:
1. Test with real queries
2. Measure coverage improvement
3. Tune RRF parameter if needed
4. Add more perspective templates

### Future Enhancements:
1. LLM-based perspective generation
2. Learned perspective weights
3. Query classification for perspective selection
4. Adaptive max_perspectives based on query

---

## Conclusion

This implementation plan provides a complete roadmap for Multi-Query RAG (RAG Tier 2.2). The plan emphasizes:

- **Test-Driven Development**: Tests written alongside implementation
- **Incremental Verification**: Checkpoints at each phase
- **Clear Dependencies**: Prerequisites identified upfront
- **Risk Mitigation**: Fallbacks for each risk
- **Production Standards**: Complete testing and documentation

**Status**: Ready to begin implementation
**Next Action**: Create `multi_query_rag_tools.py` with initial structure
**Expected Completion**: 3-4 hours from start to production-ready

---

**Implementation Plan Complete**
**Date**: November 9, 2025
**Ready for**: Phase 1 - Core Implementation
