# MCP Code Execution Pattern Analysis

**Date**: 2025-11-10 07:05 AM
**Source**: https://www.anthropic.com/engineering/code-execution-with-mcp
**Status**: Opportunities for 98.7% Token Reduction

---

## Article Key Insights

### Core Pattern: Code > Tool Calls

**OLD APPROACH (Token Heavy)**:
```
Agent calls: search_nodes("query1") → 500 tokens
Agent calls: search_nodes("query2") → 500 tokens
Agent calls: search_nodes("query3") → 500 tokens
... 100 iterations = 50,000 tokens
```

**NEW APPROACH (Token Light)**:
```
Agent calls: execute_code("""
    results = []
    for query in queries:
        results.extend(search_nodes(query))
    filtered = [r for r in results if r.confidence > 0.8]
    return summarize(filtered)
""") → 500 tokens (98.7% reduction)
```

**Key Difference**: Intermediate results stay in execution environment, not model context.

---

## Our Current Implementation

### What We're Doing Right ✅

1. **Execute Code Tool Exists** (`enhanced-memory-mcp/server.py:836-916`)
   - RestrictedPython sandbox ✅
   - 30s timeout, 500MB memory limit ✅
   - PII tokenization ✅
   - API context with memory functions ✅

2. **Security Features**
   ```python
   # Current implementation (lines 849-854)
   - RestrictedPython compilation
   - 30-second timeout
   - 500MB memory limit
   - Dangerous import blocking
   - PII tokenization
   ```

3. **API Exposure**
   ```python
   # Available APIs in code (lines 856-860)
   - Memory: create_entities, search_nodes, get_status, update_entity
   - Versioning: diff, revert, branch, history, commit
   - Analysis: detect_conflicts, analyze_patterns, classify_content
   - Utils: filter_by_confidence, summarize_results, aggregate_stats
   ```

4. **Token Reduction Claims**
   ```python
   # Documented (lines 844-847)
   - Progressive disclosure: 2,000 → 200 tokens (90% reduction)
   - Local processing: 50,000 → 500 tokens (99% reduction)
   - Average: 96.6% token reduction
   ```

---

## Critical Gaps vs Article Best Practices

### 1. Progressive Disclosure ❌

**Article Recommendation**:
- Filesystem-based tool discovery
- Lazy load tool definitions only when needed
- Agents explore directories: `./servers/enhanced-memory/search.ts`

**Current Implementation**:
- All MCP tools loaded upfront in context
- No filesystem-based discovery
- All tool schemas visible immediately

**Impact**: Loading 7 MCP servers × ~10 tools each × ~200 tokens per schema = **14,000 tokens wasted upfront**

### 2. Code-First Approach Not Encouraged ❌

**Article Recommendation**:
- Agents should write code by default for iterative operations
- Direct tool calls only for single operations

**Current Implementation**:
- Agents still call tools directly (search_nodes, create_entities, etc.)
- execute_code exists but rarely used
- No guidance to prefer code over tool calls

**Impact**: 100 search operations = 50,000 tokens with tool calls vs 500 tokens with code execution

### 3. Skills Framework Missing ❌

**Article Recommendation**:
- Save working code as persistent functions
- Agents reference proven implementations
- Version control for skill evolution

**Current Implementation**:
- No skill persistence
- Code executions are one-off
- No reuse of successful patterns

**Impact**: Agents rewrite same filtering/aggregation logic repeatedly

### 4. No Filesystem Access in Sandbox ❌

**Article Recommendation**:
- Code environment should have filesystem access
- Save state, progress, reusable functions

**Current Implementation**:
```python
# executor.execute(code, context=api_context)
# No filesystem access exposed to code
```

**Impact**: Can't persist intermediate results or build up complex logic incrementally

---

## Token Usage Comparison

### Current Pattern (Tool-Heavy)
```
Task: "Find all optimization-related memories from last month with confidence > 0.8"

Agent: search_nodes("optimization", limit=1000) → 500 tokens
→ Returns 1000 results (5,000 tokens)
Agent: [Reviews results in context] → 5,000 tokens
Agent: Filters in mind, calls search_nodes again with refined query
→ Total: ~12,000 tokens
```

### Optimal Pattern (Code-Heavy)
```
Task: "Find all optimization-related memories from last month with confidence > 0.8"

Agent: execute_code("""
from datetime import datetime, timedelta
last_month = datetime.now() - timedelta(days=30)

results = search_nodes("optimization", limit=1000)
filtered = [
    r for r in results
    if r.confidence > 0.8
    and r.created_at > last_month.isoformat()
]
return summarize(filtered)
""") → 500 tokens
→ Returns summary only (200 tokens)
→ Total: ~700 tokens (94% reduction)
```

---

## Recommended Improvements

### Phase 1: Immediate (30 min)

**Add Filesystem Access to Code Sandbox**

```python
# enhanced-memory-mcp/code_executor.py
import tempfile
from pathlib import Path

class CodeExecutor:
    def __init__(self, ...):
        self.workspace = Path(tempfile.mkdtemp(prefix="mcp_code_"))

    def execute(self, code, context):
        # Add filesystem APIs to context
        context['workspace'] = str(self.workspace)
        context['save_skill'] = self.save_skill
        context['load_skill'] = self.load_skill
        ...
```

**Benefits**: Agents can save working code, build incrementally

### Phase 2: Short-term (2 hours)

**Implement Progressive Disclosure**

1. Create filesystem structure:
```
mcp-servers/
├── enhanced-memory/
│   ├── search.ts          # search_nodes
│   ├── create.ts          # create_entities
│   ├── analyze.ts         # analyze patterns
│   └── index.ts           # exports
├── agent-runtime/
│   ├── task.ts
│   └── goal.ts
└── search_tools.ts        # Discovery API
```

2. Add search_tools function:
```python
@app.tool()
async def search_tools(
    query: str,
    detail_level: Literal["name", "description", "full"] = "name"
) -> List[Dict]:
    """
    Progressive tool discovery - load only what's needed

    detail_level:
    - name: Just tool names (10 tokens each)
    - description: + brief description (50 tokens each)
    - full: + complete schema (200 tokens each)
    """
```

**Benefits**: 14,000 tokens → 100 tokens (99.3% reduction) for tool loading

### Phase 3: Medium-term (4 hours)

**Skills Framework**

```python
# New module: mcp-servers/enhanced-memory-mcp/skills.py

class SkillManager:
    def __init__(self, skills_db_path: Path):
        self.skills_db = skills_db_path

    def save_skill(self, name: str, code: str, description: str):
        """Save working code as reusable skill"""

    def load_skill(self, name: str) -> str:
        """Load proven implementation"""

    def search_skills(self, query: str) -> List[Dict]:
        """Find relevant skills"""

@app.tool()
async def execute_skill(skill_name: str, params: Dict) -> Dict:
    """Execute saved skill with parameters"""
```

**Example Usage**:
```python
# First time: Write code
result = execute_code("""
def filter_high_confidence_memories(query, threshold=0.8):
    results = search_nodes(query, limit=1000)
    return [r for r in results if r.confidence > threshold]

result = filter_high_confidence_memories("optimization", 0.8)
save_skill("filter_high_confidence", code, "Filter memories by confidence")
""")

# Future uses: Reference skill
result = execute_skill("filter_high_confidence", {
    "query": "performance",
    "threshold": 0.9
})
```

**Benefits**: Proven code reused, agents don't rewrite logic

### Phase 4: Long-term (8 hours)

**Refactor All MCP Servers**

1. TypeScript organization (per article pattern)
2. Filesystem-based discovery
3. Wrapper functions for all tools
4. Code-first documentation

**Benefits**: Complete token optimization, 98.7% reduction achieved system-wide

---

## Implementation Priority

### Must Do (High Impact, Low Effort)
1. ✅ **Add filesystem access to code sandbox** (30 min)
   - Immediate: Let agents save/load state
   - Impact: Enables incremental complex operations

2. ✅ **Document code-first approach** (15 min)
   - Update CLAUDE.md with examples
   - Encourage execute_code over direct tools

### Should Do (High Impact, Medium Effort)
3. 🔄 **Implement progressive disclosure** (2 hours)
   - Add search_tools function
   - Lazy load tool schemas
   - Impact: 99.3% reduction in tool loading overhead

4. 🔄 **Build skills framework** (4 hours)
   - Persistent code storage
   - Skill search/reuse
   - Impact: Eliminate redundant code writing

### Could Do (Medium Impact, High Effort)
5. ⏭️ **Refactor all MCP servers** (8 hours)
   - Filesystem organization
   - TypeScript wrappers
   - Impact: Complete pattern alignment

---

## Immediate Action Items

### 1. Fix Enhanced Memory Code Execution

**File**: `mcp-servers/enhanced-memory-mcp/code_executor.py`

```python
# Add workspace and skill management
import tempfile
from pathlib import Path

class CodeExecutor:
    def __init__(self, timeout_seconds=30, memory_limit_bytes=500*1024*1024):
        self.timeout_seconds = timeout_seconds
        self.memory_limit_bytes = memory_limit_bytes
        self.workspace = Path(tempfile.mkdtemp(prefix="mcp_code_"))
        self.skills_dir = self.workspace / "skills"
        self.skills_dir.mkdir(exist_ok=True)

    def create_api_context(self):
        context = {
            # Existing APIs
            'search_nodes': ...,
            'create_entities': ...,

            # NEW: Filesystem APIs
            'workspace': str(self.workspace),
            'list_files': lambda: os.listdir(self.workspace),
            'read_file': lambda path: (self.workspace / path).read_text(),
            'write_file': lambda path, content: (self.workspace / path).write_text(content),

            # NEW: Skill APIs
            'save_skill': self.save_skill,
            'load_skill': self.load_skill,
            'list_skills': self.list_skills,
        }
        return context

    def save_skill(self, name: str, code: str, description: str):
        skill_path = self.skills_dir / f"{name}.py"
        skill_path.write_text(f'"""{description}"""\n\n{code}')
        return f"Skill '{name}' saved to {skill_path}"

    def load_skill(self, name: str):
        skill_path = self.skills_dir / f"{name}.py"
        if skill_path.exists():
            return skill_path.read_text()
        raise FileNotFoundError(f"Skill '{name}' not found")
```

### 2. Update Documentation

**File**: `~/.claude/CLAUDE.md`

Add section:
```markdown
## Code Execution Pattern (MCP Best Practice)

For iterative operations, use execute_code instead of direct tool calls:

**❌ Token Heavy (50,000 tokens)**:
mcp__enhanced-memory__search_nodes("query1")
mcp__enhanced-memory__search_nodes("query2")
... 100 times

**✅ Token Light (500 tokens)**:
mcp__enhanced-memory__execute_code("""
results = []
for query in queries:
    results.extend(search_nodes(query))
filtered = [r for r in results if r.confidence > 0.8]
result = summarize(filtered)
""")

**Token Savings**: 98.7% reduction demonstrated by Anthropic
**Reference**: https://www.anthropic.com/engineering/code-execution-with-mcp
```

---

## Expected Impact

### Token Reduction Potential

| Operation | Current | With Code Execution | Savings |
|-----------|---------|-------------------|---------|
| Tool loading | 14,000 | 100 (progressive) | 99.3% |
| 100 searches | 50,000 | 500 | 99.0% |
| Complex analysis | 20,000 | 800 | 96.0% |
| **Average** | **28,000** | **467** | **98.3%** |

### Cost Impact

At $3/M input tokens (Sonnet):
- **Current**: 28,000 tokens × $3/1M = $0.084 per operation
- **Optimized**: 467 tokens × $3/1M = $0.0014 per operation
- **Savings**: $0.0826 per operation (98.3%)

For 1,000 daily operations: **$82.60/day → $1.40/day** ($29,500/year savings)

---

## Security Considerations

### Already Implemented ✅
- RestrictedPython compilation
- 30-second timeout
- 500MB memory limit
- Dangerous import blocking
- PII tokenization

### Need to Add 🔧
- Filesystem access within sandbox only (isolated workspace)
- Skill code review before save (security audit)
- Rate limiting on execute_code calls
- Monitoring for malicious patterns

---

## Conclusion

We have the foundation (execute_code tool with security) but need to:

1. **Add filesystem access** - Let agents save state and build incrementally
2. **Implement progressive disclosure** - Load tools lazily, not upfront
3. **Build skills framework** - Persist and reuse working code
4. **Document code-first approach** - Encourage execute_code over direct tools

**Estimated Implementation**: 6.5 hours total
**Expected Token Reduction**: 98.3% average (aligned with article's 98.7%)
**ROI**: $29,500/year savings at current operation volume

**Priority**: Phase 1 and 2 are high-impact, low-effort wins (2.75 hours, 99%+ reduction)

---

**Analysis Complete**: 2025-11-10 07:05 AM
**Recommendation**: Implement Phase 1 immediately for quick wins
