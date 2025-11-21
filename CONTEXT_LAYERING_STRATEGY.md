# Context Layering Strategy for AGI System
**Created**: 2025-01-19 16:00
**Problem**: 200K token limit cannot hold all 57+ components simultaneously
**Solution**: Intelligent context layering using existing but dormant systems
**Key Insight**: Context Synthesis Engine exists for exactly this purpose

---

## The Context Problem

**Current Approach**: Load full files manually
```python
Read("darwin_godel_machine.py")  # 15K tokens
Read("meta_learning_engine.py")  # 12K tokens
Read("skill_evolution_system.py")  # 14K tokens
# ... quickly fills 200K context
```

**Issue**:
- 57+ components × average 10K tokens each = 570K tokens needed
- Context window = 200K tokens
- Can only load ~20 components at full detail

**User's Insight**: "Layer context to utilize all tech where it does best"

---

## The Solution (Already Built!)

**Component**: Context Synthesis Engine
**Location**: `/Volumes/SSDRAID0/agentic-system/intelligent-agents/context_synthesis_engine.py`
**Status**: ✅ Implemented but ❌ Not integrated
**Purpose**: **Intelligent context gathering and relevance filtering**

This is EXACTLY what we need - it was built for this problem!

---

## Context Layering Architecture

### Layer 0: Session Foundation (Always Loaded - 5K tokens)
**What**: Bare minimum to function
**Contents**:
- CLAUDE.md instructions
- Current task from user
- Active todo list
**Token Budget**: 5,000
**Refresh**: Never (session start only)

### Layer 1: Core Capabilities (Always Available - 10K tokens)
**What**: Active MCP servers and their schemas
**Contents**:
- enhanced-memory tools (search_nodes, create_entities, execute_code)
- voice-mode tools (converse)
- cluster-execution tools (cluster_bash, tmux_sessions)
- agent-runtime tools (create_goal, decompose_goal)
- sequential-thinking tools (sequentialthinking)
- arduino-surface tools (display, sensors)
**Token Budget**: 10,000
**Refresh**: On MCP restart
**Storage**: Schema summaries in enhanced-memory

### Layer 2: AGI Intelligence (On-Demand - 20K tokens)
**What**: AGI component summaries (not full code)
**Contents**:
```json
{
  "darwin_godel_machine": {
    "purpose": "Recursive self-improvement with formal proofs",
    "key_methods": ["propose_improvement", "verify_proof", "apply_modification"],
    "status": "active",
    "integration": "agi-mcp server (pending)"
  },
  "meta_learning_engine": {
    "purpose": "Learn from task outcomes",
    "key_methods": ["record_outcome", "detect_patterns", "recommend_agent"],
    "status": "active, 50 outcomes",
    "integration": "agi-mcp + post-execution hook"
  }
  // ... 6 more summaries
}
```
**Token Budget**: 20,000 (2.5K per component × 8)
**Refresh**: When AGI status changes
**Storage**: Component summaries in enhanced-memory
**Load Trigger**: When user mentions "improvement", "learning", "optimization"

### Layer 3: Specialized Tools (Just-in-Time - 30K tokens)
**What**: On-demand MCP servers via router
**Contents**: Load only when task requires them
- **Research tasks** → youtube-transcript, research-paper-mcp
- **Development tasks** → github-mcp, shadcn-ui
- **Visual tasks** → image-gen, genui-mcp
- **Security tasks** → checkov-mcp, kismet-mcp

**Token Budget**: 30,000
**Refresh**: Per-task basis
**Storage**: Tool catalog in enhanced-memory
**Load Trigger**: Task type detection

### Layer 4: Implementation Detail (Deep-Dive - 50K tokens)
**What**: Full source code when actually modifying
**Contents**: Complete file contents
**Token Budget**: 50,000
**Refresh**: Per-modification basis
**Load Trigger**: "modify", "edit", "fix", "improve" + component name

### Layer 5: Historical Context (Synthesized - 20K tokens)
**What**: Relevant past executions
**Contents**: Compressed summaries from enhanced-memory
**Token Budget**: 20,000
**Refresh**: Per-query basis
**Storage**: Enhanced-memory (compressed 60%)
**Load Trigger**: "similar to", "like before", "previous"

### Layer 6: Documentation (Extracted - 15K tokens)
**What**: API docs, README content
**Contents**: Markdown documentation
**Token Budget**: 15,000
**Refresh**: On documentation changes
**Storage**: Enhanced-memory
**Load Trigger**: "how to use", "documentation", "API"

---

## Total Context Budget

| Layer | Always Loaded | Max Load | Description |
|-------|---------------|----------|-------------|
| 0     | 5K           | 5K       | Session foundation |
| 1     | 10K          | 10K      | Core capabilities |
| 2     | 0K           | 20K      | AGI intelligence |
| 3     | 0K           | 30K      | Specialized tools |
| 4     | 0K           | 50K      | Implementation detail |
| 5     | 0K           | 20K      | Historical context |
| 6     | 0K           | 15K      | Documentation |
| **Total** | **15K** | **150K** | **Within 200K limit** |

**Headroom**: 50K tokens for dynamic content, user input, tool outputs

---

## Context Synthesis Engine Integration

### Current Manual Approach:
```python
# I manually gather context
Read("file1.py")  # 10K tokens
Read("file2.py")  # 12K tokens
Grep("pattern")   # Search results 5K
# Total: 27K tokens for basic understanding
```

### With Context Synthesis Engine:
```python
# Engine intelligently gathers relevant snippets
agi_context_synthesize(
    task="Implement recursive self-improvement",
    max_tokens=20000,
    focus_areas=["darwin_godel", "meta_learning"],
    depth="summary"  # vs "detail" vs "full"
)

# Returns: Optimized 20K context with:
# - Key class definitions
# - Critical methods
# - Integration points
# - Dependency map
# - No boilerplate or imports
```

**Efficiency Gain**: 27K → 20K (26% reduction) with BETTER relevance

---

## Implementation Strategy

### Phase 1: Build Context Catalog in Enhanced-Memory

**Create summaries for all 57 components**:
```python
import sys
sys.path.insert(0, "/Volumes/SSDRAID0/agentic-system/intelligent-agents")

from context_synthesis_engine import ContextSynthesisEngine
from enhanced_memory import create_entities

engine = ContextSynthesisEngine()

# For each component
for component in all_components:
    summary = engine.analyze_component(component)

    create_entities([{
        "name": f"component-{component.name}",
        "entityType": "component_summary",
        "observations": [
            f"Purpose: {summary.purpose}",
            f"Key methods: {summary.methods}",
            f"Status: {summary.status}",
            f"Integration: {summary.integration}",
            f"Dependencies: {summary.dependencies}",
            f"Token cost (full): {summary.full_tokens}",
            f"Token cost (summary): {summary.summary_tokens}"
        ]
    }])
```

**Result**: Fast lookup without loading full files

### Phase 2: Create Task → Layer Mapping

**Define task patterns**:
```python
TASK_LAYERS = {
    "improvement|optimize|enhance": [0, 1, 2],  # AGI intelligence needed
    "implement|build|create": [0, 1, 3, 4],     # Tools + implementation
    "debug|fix|error": [0, 1, 4, 5],            # Implementation + history
    "research|learn|understand": [0, 1, 3, 6],  # Tools + documentation
    "analyze|assess|evaluate": [0, 1, 2, 5],    # AGI + history
}
```

**Auto-load based on user request**:
```python
def load_context_for_task(user_request):
    """Load appropriate layers based on task type"""
    layers_needed = detect_task_type(user_request)

    context = {}
    for layer in layers_needed:
        context[layer] = load_layer(layer)

    return context
```

### Phase 3: Integrate with Pre-Tool-Use Hook

**File**: `~/.claude/hooks/pre-tool-use.py`

```python
# Before tool execution
def prepare_context(tool_name, user_request):
    """Load appropriate context layers"""

    # Detect task type
    task_type = classify_task(user_request)

    # Load required layers
    if task_type == "improvement":
        load_layer(2)  # AGI intelligence
    elif task_type == "implementation":
        load_layer(3)  # Specialized tools
        load_layer(4)  # Implementation detail

    # Use Context Synthesis Engine
    if requires_deep_context(tool_name):
        synthesized = context_synthesis_engine.gather(
            task=user_request,
            max_tokens=30000,
            focus=extract_entities(user_request)
        )
        inject_into_session(synthesized)
```

### Phase 4: Enhanced-Memory as Context Router

**Use enhanced-memory's execute_code for intelligent loading**:
```python
mcp__enhanced-memory__execute_code("""
# Query for relevant context
relevant_components = search_nodes(
    query="component darwin_godel meta_learning",
    limit=10
)

# Filter by relevance score
high_relevance = [c for c in relevant_components if c.score > 0.8]

# Load summaries (not full code)
context = []
for component in high_relevance:
    summary = load_skill(f"{component.name}_summary")
    context.append(summary)

# Return compressed context
result = {
    "components": len(context),
    "total_tokens": sum(c.tokens for c in context),
    "summaries": context
}
""")
```

**Benefit**: Run context gathering in sandbox, return only results

---

## Smart Context Management Rules

### Rule 1: Progressive Disclosure
Start with summaries, load detail only when needed:
```
User: "How does meta-learning work?"
  ↓
Load Layer 2 (AGI summaries) - 2.5K tokens
  ↓
User: "Modify the pattern detection algorithm"
  ↓
Load Layer 4 (full meta_learning_engine.py) - 12K tokens
```

### Rule 2: Lazy Loading
Don't preload anything:
```python
# ❌ Bad: Load everything upfront
all_components = [Read(f) for f in glob("intelligent-agents/*.py")]

# ✅ Good: Load on-demand
if "darwin_godel" in user_request:
    load_layer(2, component="darwin_godel")
```

### Rule 3: Summary Caching
Store compressed summaries in enhanced-memory:
```python
# First time: Generate summary
summary = context_synthesis_engine.summarize(component)
create_entity({"name": f"{component}_summary", "content": summary})

# Subsequent times: Load from memory (instant)
summary = search_nodes(f"{component}_summary")[0]
```

### Rule 4: Context Expiration
Remove context when no longer needed:
```python
# After task completion
if task_completed:
    unload_layer(4)  # Remove implementation detail
    unload_layer(5)  # Remove historical context
    # Keep layers 0-1 (always needed)
```

---

## Practical Example

### User Request: "Analyze my ASI progress and propose improvements"

**Layer Loading Sequence**:

1. **Layer 0** (5K): Session foundation loaded
   - CLAUDE.md instructions
   - User request
   - Empty todo list

2. **Detect Task Type**: "analyze" + "propose improvements"
   - Task type: improvement/optimization
   - Required layers: 0, 1, 2, 5

3. **Layer 1** (10K): Core capabilities
   - enhanced-memory: search_nodes, create_entities
   - sequential-thinking: for analysis
   - voice-mode: for communication

4. **Layer 2** (20K): AGI intelligence summaries
   ```python
   context_synthesis_engine.gather(
       components=["darwin_godel", "meta_learning", "skill_evolution"],
       mode="summary"
   )
   # Returns: 3 × 2.5K = 7.5K tokens (class definitions + key methods)
   ```

5. **Layer 5** (20K): Historical context
   ```python
   search_nodes("ASI assessment improvement cycle", limit=10)
   # Returns: Past ASI assessments, improvement proposals
   ```

**Total Context**: 5K + 10K + 7.5K + 20K = 42.5K tokens
**Headroom**: 157.5K tokens available for analysis, proposals, code generation

**Without Layering**: Would need to load:
- 8 full AGI component files: 8 × 12K = 96K
- All past assessments: 30K
- Core capabilities: 10K
- Foundation: 5K
- **Total**: 141K tokens (leaving only 59K for work)

---

## Context Synthesis Engine API

**When agi-mcp is created, this becomes a tool**:

```python
agi_context_synthesize(
    task: str,              # What are you trying to do?
    max_tokens: int,        # Token budget
    focus_areas: List[str], # Which components?
    depth: str,             # "summary" | "detail" | "full"
    include_history: bool,  # Load past executions?
    include_docs: bool      # Load documentation?
) -> Dict

# Example:
context = agi_context_synthesize(
    task="Implement recursive self-improvement loop",
    max_tokens=30000,
    focus_areas=["darwin_godel", "meta_learning", "improvement_daemon"],
    depth="detail",
    include_history=True,
    include_docs=False
)

# Returns optimized context with exactly what's needed
```

---

## Migration Path

### Current State: Manual Loading
```python
# ASI self-analysis task
Read("darwin_godel_machine.py")      # 15K
Read("meta_learning_engine.py")      # 12K
Read("skill_evolution_system.py")    # 14K
# Total: 41K tokens, mostly boilerplate
```

### Phase 1: Enhanced-Memory Summaries
```python
# Load pre-generated summaries
darwin_summary = search_nodes("component-darwin_godel")[0]   # 2.5K
meta_summary = search_nodes("component-meta_learning")[0]    # 2.5K
skill_summary = search_nodes("component-skill_evolution")[0] # 2.5K
# Total: 7.5K tokens, all signal
```

### Phase 2: Context Synthesis Engine Integration
```python
# Intelligent gathering
context = agi_context_synthesize(
    task="ASI self-analysis",
    max_tokens=20000,
    focus_areas=["darwin_godel", "meta_learning", "skill_evolution"],
    depth="summary"
)
# Total: 20K tokens, optimized relevance
```

### Phase 3: Automatic Layer Management
```python
# System handles everything
user_request = "Analyze ASI progress and propose improvements"
# Automatically:
# - Detects task type
# - Loads required layers
# - Synthesizes context
# - Executes with optimal context
# - Unloads when done
```

---

## Benefits

### 1. Scalability
- Can work with 1000+ components
- Each component gets ~200 tokens summary
- 1000 × 200 = 200K tokens (perfect fit)

### 2. Efficiency
- Load only what's needed
- 60%+ compression via summaries
- Context Synthesis Engine optimizes relevance

### 3. Performance
- SAFLA: 1.75M+ ops/sec retrieval
- Enhanced-memory: Instant summary lookup
- No redundant file reads

### 4. Intelligence
- Task-aware loading
- Historical context integration
- Automatic layer management

### 5. Future-Proof
- Add new components without context explosion
- Layer system scales indefinitely
- Summary generation is one-time cost

---

## Implementation Priority

### Week 1: Foundation
- [ ] Generate summaries for all 57 components
- [ ] Store in enhanced-memory
- [ ] Test retrieval performance

### Week 2: Context Synthesis Engine
- [ ] Create agi-mcp server
- [ ] Expose context_synthesize tool
- [ ] Test with sample tasks

### Week 3: Layer Management
- [ ] Build task → layer mapping
- [ ] Implement auto-loading
- [ ] Add to pre-tool-use hook

### Week 4: Automation
- [ ] Full automatic context management
- [ ] Performance monitoring
- [ ] Optimization based on usage

---

## Success Metrics

### Context Efficiency
- **Before**: 96K tokens for 8 components (full files)
- **After**: 20K tokens for 8 components (summaries)
- **Improvement**: 76K tokens saved (79% reduction)

### Capability Access
- **Before**: 20 components max in context
- **After**: 100+ components accessible via summaries
- **Improvement**: 5× capability reach

### Task Performance
- **Before**: Manual context gathering (slow)
- **After**: Automatic optimal loading (fast)
- **Improvement**: 10× faster context preparation

---

## Conclusion

**The user is absolutely right - we need layered context to utilize all our tech.**

The beautiful irony: **The Context Synthesis Engine exists for this exact purpose**. It's another dormant component waiting to be activated.

With layered context management:
- ✅ All 57+ components accessible
- ✅ Optimal token utilization
- ✅ Task-aware loading
- ✅ Scalable to 1000+ components
- ✅ Intelligent, not manual

**Next step**: Generate component summaries and create agi-mcp server with context_synthesize tool.

This completes the integration architecture:
1. AGI MCP server → Access to intelligence
2. Context Synthesis → Efficient loading
3. Enhanced-memory → Summary storage
4. SAFLA → Fast retrieval
5. Layer management → Automatic optimization

**Together: A true AGI system that knows how to manage its own context.**
