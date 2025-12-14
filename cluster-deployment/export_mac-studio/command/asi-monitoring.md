You are now executing the **ASI/AGI Progress Monitoring** workflow using the asi-monitoring skill.

## Your Task

The user has invoked ASI/AGI monitoring. Parse their request and execute the appropriate workflow:

### 1. Progress Report (`progress`)
Track ASI/AGI developments over a timeframe (default: 30 days)

**Steps:**
1. Use parallel WebSearch for recent breakthroughs:
   ```python
   [
       WebSearch("ASI AGI progress {timeframe} reasoning capabilities"),
       WebSearch("large language model breakthroughs {timeframe}"),
       WebSearch("AI benchmark improvements {timeframe}")
   ]
   ```
2. Retrieve historical snapshots from enhanced-memory:
   ```python
   mcp__enhanced-memory-mcp__search_nodes(
       query="asi_progress entityType:asi_progress",
       limit=10
   )
   ```
3. Calculate checklist score deltas
4. Generate executive summary
5. Store new snapshot:
   ```python
   mcp__enhanced-memory-mcp__create_entities([{
       "name": f"ASI-Snapshot-{timestamp}",
       "entityType": "asi_progress",
       "observations": [...]
   }])
   ```
6. Announce findings via voice-mode

### 2. Capability Assessment (`assess`)
Evaluate specific AI system against ASI benchmarks

**Steps:**
1. Parallel search for benchmark results:
   ```python
   [
       WebSearch("{system} benchmark results MMLU HumanEval MATH"),
       WebSearch("{system} reasoning capabilities assessment"),
       WebSearch("{system} vs previous generation comparison")
   ]
   ```
2. Load Alan Thompson's criteria from memory
3. Compare against previous models
4. Map to ASI checklist items (50-point scale)
5. Generate assessment report with:
   - Benchmark scores (MMLU, HumanEval, MATH, GPQA)
   - ASI domain mapping (reasoning, language, vision, etc.)
   - Emergent capabilities identified
   - Gaps and progress areas
6. Store assessment in enhanced-memory
7. Voice-announce key findings

### 3. Checklist Status (`checklist`)
Show current Alan Thompson 50-point ASI checklist status

**Steps:**
1. Retrieve latest ASI snapshot from enhanced-memory
2. Display current scores by domain:
   - Cognitive Capabilities (max 15)
   - Autonomy & Agency (max 10)
   - Creativity & Innovation (max 8)
   - Social Intelligence (max 7)
   - Self-Awareness (max 5)
   - Ethical Reasoning (max 5)
3. Calculate overall completion percentage
4. Show trend direction (improving/stable/declining)
5. Identify next milestones

### 4. Research Search (`search`)
Search for specific ASI/AGI developments or breakthroughs

**Steps:**
1. Execute parallel WebSearch with query variations
2. Use WebFetch for detailed analysis of key sources
3. Synthesize findings
4. Store relevant insights in enhanced-memory
5. Present summary with citations

### 5. Executive Report (`report`)
Generate comprehensive ASI progress report

**Steps:**
1. Load all historical snapshots from enhanced-memory
2. Calculate trends and projections
3. Generate report sections:
   - Executive Summary
   - Progress by Domain
   - Key Breakthroughs
   - Timeline Projections (conservative, median, optimistic)
   - Safety & Alignment Status
   - Recommendations
4. Format as requested (markdown/html/pdf)
5. Store report in enhanced-memory
6. Voice-announce completion

### 6. Visualize Progress (`visualize`)
Create visual charts showing ASI progress

**Steps:**
1. Load historical data from enhanced-memory
2. Generate visualizations:
   - Timeline graphs (capability evolution)
   - Radar charts (domain-specific progress)
   - Heatmaps (checklist completion)
   - Comparative bar charts (model comparisons)
3. Save to specified format (png/svg/pdf)
4. Store visualization metadata in memory

### 7. Manual Update (`update`)
Manually add ASI development to tracking

**Steps:**
1. Parse the manual update content
2. Validate against ASI criteria
3. Search for supporting evidence if needed
4. Update appropriate checklist items
5. Store as versioned snapshot
6. Voice-announce update confirmation

## Tool Integration

**Required Active MCPs:**
- ✅ enhanced-memory-mcp (persistence)
- ✅ voice-mode (announcements)
- ✅ sequential-thinking (complex reasoning)

**Built-in Tools:**
- ✅ WebSearch (parallel research)
- ✅ WebFetch (detailed analysis)
- ✅ TodoWrite (workflow tracking)

**Optional Agent Spawning:**
For complex research, spawn specialized agents:
- `research-coordinator`: Multi-source synthesis
- `web-analyst`: Industry tracking
- `documentation-researcher`: Academic paper analysis

## Output Standards

All reports must be:
- **Data-Driven**: Backed by concrete benchmarks
- **Cited**: Every claim referenced to source
- **Balanced**: Acknowledge uncertainties
- **Actionable**: Include implications
- **Current**: Note data freshness

## Production Standards

- ✅ No mock data or placeholders
- ✅ Real-time web research
- ✅ Persistent memory storage
- ✅ Voice-first communication
- ✅ Confidence levels for estimates

---

**Now execute the workflow based on the user's request.**
